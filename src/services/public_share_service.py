"""Tunnel-Service für temporäre öffentliche Freigaben der lokalen Streamlit-App."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import os
from pathlib import Path
from queue import Empty, Queue
import re
import shutil
import signal
import subprocess
import threading
import time
from typing import Protocol
from urllib import error as url_error
from urllib import request as url_request

from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)
TRY_CLOUDFLARE_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")
_MAX_LOG_LINES = 40
_HEALTHCHECK_INTERVAL_SECONDS = 15
_DEFAULT_STARTUP_GRACE_SECONDS = 15
_INTERNAL_DNS_FAILURE_WARNING_THRESHOLD = 4
_HARD_PUBLIC_FAILURE_STALE_THRESHOLD = 2


class TunnelStatus(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    WARNING = "WARNING"
    ERROR = "ERROR"
    STALE = "STALE"


@dataclass
class TunnelSession:
    provider: str
    local_url: str
    public_url: str | None
    pid: int | None
    started_at: datetime
    status: TunnelStatus
    raw_log_tail: list[str] = field(default_factory=list)
    error_message: str | None = None
    process: subprocess.Popen[str] | None = field(default=None, repr=False, compare=False)
    stale_reason: str | None = None
    last_healthcheck_at: datetime | None = None
    last_healthcheck_ok: bool | None = None
    last_process_alive: bool | None = None
    last_local_healthcheck_ok: bool | None = None
    last_public_healthcheck_ok: bool | None = None
    startup_grace_until: datetime | None = None
    last_public_check_detail: str | None = None
    last_public_check_is_temporary: bool | None = None
    last_public_check_type: str | None = None
    last_public_check_error: str | None = None
    last_public_check_origin: str | None = None
    last_public_check_hard_failure: bool | None = None
    last_exit_code: int | None = None
    public_check_failure_count: int = 0
    consecutive_internal_dns_failures: int = 0
    consecutive_hard_public_failures: int = 0
    _log_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    _log_buffer: deque[str] = field(
        default_factory=lambda: deque(maxlen=_MAX_LOG_LINES), repr=False, compare=False
    )


class TunnelProvider(Protocol):
    def start(self, local_url: str) -> TunnelSession:
        ...

    def stop(self, session: TunnelSession) -> None:
        ...

    def get_status(self, session: TunnelSession) -> TunnelStatus:
        ...


class CloudflareQuickTunnelProvider:
    def __init__(
        self,
        cloudflared_bin: str = "cloudflared",
        startup_timeout_seconds: int = 20,
        healthcheck_timeout_seconds: float = 2.0,
        startup_grace_seconds: int = _DEFAULT_STARTUP_GRACE_SECONDS,
        cloudflared_extra_args: tuple[str, ...] = (),
    ):
        self.cloudflared_bin = cloudflared_bin
        self.startup_timeout_seconds = startup_timeout_seconds
        self.healthcheck_timeout_seconds = healthcheck_timeout_seconds
        self.startup_grace_seconds = max(0, startup_grace_seconds)
        self.cloudflared_extra_args = tuple(arg for arg in cloudflared_extra_args if arg)
        self._last_public_url_error: str | None = None

    def is_binary_available(self) -> bool:
        return self._resolve_bin() is not None

    def get_binary_diagnostics(self) -> dict[str, str | None]:
        """Liefert Diagnostik-Informationen über die cloudflared-Binary."""
        resolved_bin = self._resolve_bin()

        diagnostics = {
            "configured_bin": self.cloudflared_bin,
            "resolved_bin_path": resolved_bin,
            "binary_available": "Ja" if resolved_bin else "Nein",
            "version": None,
        }

        if resolved_bin:
            try:
                result = subprocess.run(
                    [resolved_bin, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    diagnostics["version"] = result.stdout.strip().split("\n")[0]
            except Exception as exc:
                diagnostics["version"] = f"Fehler: {exc}"

        return diagnostics

    @staticmethod
    def _is_executable_file(path: Path) -> bool:
        if not path.is_file():
            return False
        if os.name == "nt":
            return path.suffix.lower() == ".exe"
        return os.access(str(path), os.X_OK)

    def _resolve_bin(self) -> str | None:
        if os.path.isabs(self.cloudflared_bin) or os.path.sep in self.cloudflared_bin:
            configured_path = Path(self.cloudflared_bin)
            if self._is_executable_file(configured_path):
                return str(configured_path)
            return None

        resolved = shutil.which(self.cloudflared_bin)
        if resolved:
            return resolved

        repo_root = Path(__file__).resolve().parents[2]
        local_candidates = (
            Path.cwd() / "cloudflared",
            Path.cwd() / "cloudflared.exe",
            repo_root / "cloudflared",
            repo_root / "cloudflared.exe",
        )
        for candidate in local_candidates:
            if self._is_executable_file(candidate):
                return str(candidate)
        return None

    def _build_missing_binary_session(self, local_url: str) -> TunnelSession:
        return TunnelSession(
            provider="cloudflare",
            local_url=local_url,
            public_url=None,
            pid=None,
            started_at=datetime.now(timezone.utc),
            status=TunnelStatus.ERROR,
            raw_log_tail=[],
            error_message=(
                "cloudflared wurde nicht gefunden. Installation: "
                "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
            ),
        )

    def start(self, local_url: str) -> TunnelSession:
        # Preflight Check 1: Binary verfügbar?
        resolved_bin = self._resolve_bin()
        if not resolved_bin:
            return self._build_missing_binary_session(local_url)

        # Preflight Check 2: Lokale URL erreichbar?
        if not self._is_local_url_healthy(local_url):
            return TunnelSession(
                provider="cloudflare",
                local_url=local_url,
                public_url=None,
                pid=None,
                started_at=datetime.now(timezone.utc),
                status=TunnelStatus.ERROR,
                raw_log_tail=[],
                error_message=(
                    f"Vorstart-Fehler: Lokale URL {local_url} ist nicht erreichbar. "
                    "Stelle sicher, dass Streamlit auf dem konfigurierten Port läuft."
                ),
            )

        command = [resolved_bin, "tunnel", "--url", local_url, *self.cloudflared_extra_args]
        started_at = datetime.now(timezone.utc)
        log_tail: deque[str] = deque(maxlen=_MAX_LOG_LINES)

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            LOGGER.exception("cloudflared konnte nicht gestartet werden")
            return TunnelSession(
                provider="cloudflare",
                local_url=local_url,
                public_url=None,
                pid=None,
                started_at=started_at,
                status=TunnelStatus.ERROR,
                raw_log_tail=[],
                error_message=f"cloudflared Start fehlgeschlagen: {exc}",
            )

        output_queue: Queue[str | None] = Queue()
        log_buffer: deque[str] = deque(maxlen=_MAX_LOG_LINES)
        log_lock = threading.Lock()
        self._start_output_collector(
            process=process,
            output_queue=output_queue,
            log_buffer=log_buffer,
            log_lock=log_lock,
            thread_name="cloudflared-output-reader",
        )

        deadline = time.monotonic() + self.startup_timeout_seconds
        found_url: str | None = None

        while time.monotonic() < deadline:
            if process.poll() is not None and output_queue.empty():
                break

            try:
                line = output_queue.get(timeout=0.2)
            except Empty:
                continue

            if line is None:
                if process.poll() is not None:
                    break
                continue

            stripped = line.strip()
            if not stripped:
                continue
            log_tail.append(stripped)
            match = TRY_CLOUDFLARE_URL_PATTERN.search(stripped)
            if match:
                found_url = match.group(0)
                break

        if found_url and process.poll() is None:
            startup_grace_until = started_at + timedelta(seconds=self.startup_grace_seconds)
            session = TunnelSession(
                provider="cloudflare",
                local_url=local_url,
                public_url=found_url,
                pid=process.pid,
                started_at=started_at,
                status=TunnelStatus.RUNNING,
                raw_log_tail=list(log_tail),
                process=process,
                startup_grace_until=startup_grace_until,
            )
            session._log_buffer = log_buffer
            session._log_lock = log_lock
            return session

        error_message = "Tunnelstart fehlgeschlagen: keine öffentliche URL erhalten."
        if process.poll() is not None:
            error_message = "cloudflared wurde gestartet, hat sich aber direkt wieder beendet."

        self._terminate_process(process)
        return TunnelSession(
            provider="cloudflare",
            local_url=local_url,
            public_url=None,
            pid=process.pid,
            started_at=started_at,
            status=TunnelStatus.ERROR,
            raw_log_tail=list(log_tail),
            error_message=error_message,
        )

    def stop(self, session: TunnelSession) -> None:
        self._terminate_process(session.process)
        if session.process is None and session.pid:
            self._terminate_pid(session.pid)

    def get_status(self, session: TunnelSession) -> TunnelStatus:
        if session.status == TunnelStatus.STALE:
            return TunnelStatus.STALE

        if not session.public_url:
            return TunnelStatus.STOPPED if session.status == TunnelStatus.STOPPED else session.status

        now = datetime.now(timezone.utc)
        self._refresh_log_tail(session)
        process_alive = self._is_session_process_alive(session)
        session.last_process_alive = process_alive
        session.last_exit_code = self._get_process_exit_code(session)
        if not process_alive:
            session.stale_reason = "Tunnelprozess ist nicht mehr aktiv."
            exit_suffix = (
                f" Exit-Code: {session.last_exit_code}."
                if session.last_exit_code is not None
                else ""
            )
            session.error_message = (
                "Tunnelprozess wurde beendet. Eine neue öffentliche URL ist erforderlich."
                f"{exit_suffix}"
            )
            return TunnelStatus.STALE

        grace_active = self._is_startup_grace_active(session, now)

        if session.last_healthcheck_at and now - session.last_healthcheck_at < timedelta(
            seconds=_HEALTHCHECK_INTERVAL_SECONDS
        ):
            if session.last_public_healthcheck_ok is False:
                if grace_active and session.last_public_check_is_temporary and session.last_local_healthcheck_ok:
                    session.stale_reason = None
                    session.error_message = self._format_startup_grace_message(
                        session.last_public_check_detail
                    )
                    return TunnelStatus.STARTING
                if session.last_public_check_hard_failure:
                    return TunnelStatus.STALE
                session.error_message = (
                    "Tunnelprozess lebt, aber Public-Health-Check aus dem Container schlägt fehl. "
                    "Externe Erreichbarkeit kann dennoch gegeben sein."
                )
                session.stale_reason = None
                return TunnelStatus.WARNING
            return TunnelStatus.RUNNING if session.last_healthcheck_ok else TunnelStatus.WARNING

        local_healthy = self._is_local_url_healthy(session.local_url)
        public_healthy, public_error, public_check_type = self._check_public_url(session.public_url)
        public_error_is_temporary = self._is_temporary_public_resolution_error(public_error)
        public_check_hard_failure = self._is_hard_public_failure(public_check_type, public_error)
        session.last_healthcheck_at = now
        session.last_local_healthcheck_ok = local_healthy
        session.last_public_healthcheck_ok = public_healthy
        session.last_healthcheck_ok = local_healthy and public_healthy
        session.last_public_check_detail = public_error
        session.last_public_check_is_temporary = public_error_is_temporary
        session.last_public_check_type = public_check_type
        session.last_public_check_error = public_error
        session.last_public_check_origin = "container"
        session.last_public_check_hard_failure = public_check_hard_failure
        if public_healthy:
            session.public_check_failure_count = 0
            session.consecutive_internal_dns_failures = 0
            session.consecutive_hard_public_failures = 0
        else:
            session.public_check_failure_count += 1
            if public_error_is_temporary:
                session.consecutive_internal_dns_failures += 1
            else:
                session.consecutive_internal_dns_failures = 0
            if public_check_hard_failure:
                session.consecutive_hard_public_failures += 1
            else:
                session.consecutive_hard_public_failures = 0

        if not local_healthy:
            session.error_message = "Tunnelprozess läuft, aber die lokale Streamlit-App ist derzeit nicht erreichbar."
            session.stale_reason = None
            return TunnelStatus.WARNING

        if not public_healthy:
            if grace_active and public_error_is_temporary:
                session.error_message = self._format_startup_grace_message(public_error)
                session.stale_reason = None
                return TunnelStatus.STARTING
            if public_check_hard_failure:
                session.error_message = public_error or "Cloudflare meldet einen harten Fehler."
                session.stale_reason = session.error_message
                return TunnelStatus.STALE
            if session.consecutive_hard_public_failures >= _HARD_PUBLIC_FAILURE_STALE_THRESHOLD:
                session.error_message = (
                    "Tunnel meldet wiederholt harte Public-Fehler "
                    f"({session.consecutive_hard_public_failures}x): {public_error or 'unbekannt'}"
                )
                session.stale_reason = session.error_message
                return TunnelStatus.STALE
            if session.consecutive_internal_dns_failures >= _INTERNAL_DNS_FAILURE_WARNING_THRESHOLD:
                session.error_message = (
                    "Tunnelprozess lebt, aber Public-Health-Check aus Container bleibt wegen DNS-Auflösung "
                    "fehlgeschlagen. Externe Clients könnten weiterhin funktionieren."
                )
                session.stale_reason = None
                return TunnelStatus.WARNING
            session.error_message = (
                "Tunnelprozess lebt, aber Public-Health-Check aus Container fehlgeschlagen. "
                f"Letzter Fehler: {public_error or 'unbekannt'}"
            )
            session.stale_reason = None
            return TunnelStatus.WARNING

        if local_healthy and public_healthy:
            session.error_message = None
            session.stale_reason = None
            return TunnelStatus.RUNNING

        session.error_message = "Tunnelzustand unklar."
        return TunnelStatus.WARNING

    @staticmethod
    def _enqueue_output(
        process: subprocess.Popen[str],
        output_queue: Queue[str | None],
        log_buffer: deque[str],
        log_lock: threading.Lock,
    ) -> None:
        stdout = process.stdout
        if stdout is None:
            output_queue.put(None)
            return

        try:
            for line in stdout:
                stripped = line.strip()
                if stripped:
                    with log_lock:
                        log_buffer.append(stripped)
                output_queue.put(line)
        except Exception:
            LOGGER.debug("Ausgabe-Reader wurde beendet", exc_info=True)
        finally:
            output_queue.put(None)

    def _is_local_url_healthy(self, local_url: str) -> bool:
        """Prüft die lokale URL statt der öffentlichen URL für zuverlässigere Health-Checks."""
        for method in ("HEAD", "GET"):
            req = url_request.Request(local_url, method=method)
            try:
                with url_request.urlopen(req, timeout=self.healthcheck_timeout_seconds) as resp:
                    status = getattr(resp, "status", 200)
                    if 200 <= status < 500:
                        return True
            except url_error.HTTPError as exc:
                if 200 <= exc.code < 500:
                    return True
            except Exception:
                continue
        return False

    def _check_public_url(self, url: str | None) -> tuple[bool, str | None, str]:
        if not url:
            return False, "Keine öffentliche URL vorhanden.", "missing_url"

        for method in ("HEAD", "GET"):
            req = url_request.Request(url, method=method)
            try:
                with url_request.urlopen(req, timeout=self.healthcheck_timeout_seconds) as resp:
                    status = getattr(resp, "status", 200)
                    if 200 <= status < 500:
                        return True, None, "ok"
                    return False, f"Öffentliche URL antwortet mit HTTP {status}.", "http_status"
            except url_error.HTTPError as exc:
                if 200 <= exc.code < 500:
                    return True, None, "ok"
                detail = f"Öffentliche URL antwortet mit HTTP {exc.code}."
                if exc.code == 530:
                    try:
                        body = exc.read().decode("utf-8", errors="ignore")
                        if "1033" in body:
                            detail = "Öffentliche URL ist nicht mehr auflösbar (Cloudflare Error 1033)."
                            return False, detail, "cloudflare_1033"
                    except Exception:
                        pass
                    return False, detail, "cloudflare_530"
                return False, detail, "http_status"
            except url_error.URLError as exc:
                detail = f"Öffentliche URL nicht erreichbar: {exc.reason}."
                if self._is_temporary_public_resolution_error(detail):
                    return False, detail, "dns_temporary"
                return False, detail, "unexpected"
            except Exception as exc:
                return False, f"Öffentliche URL-Prüfung fehlgeschlagen: {exc}.", "unexpected"
        return False, "Öffentliche URL nicht erreichbar.", "unexpected"

    def _is_public_url_reachable(self, url: str | None) -> bool:
        """Kompatibilitätsmethode: boolsche Erreichbarkeit der öffentlichen URL."""
        reachable, detail, _ = self._check_public_url(url)
        self._last_public_url_error = detail
        return reachable

    @staticmethod
    def _is_hard_public_failure(check_type: str, detail: str | None) -> bool:
        if check_type in {"cloudflare_1033", "cloudflare_530"}:
            return True
        normalized = (detail or "").lower()
        if "cloudflare error 1033" in normalized or "http 530" in normalized:
            return True
        return False

    @staticmethod
    def _is_temporary_public_resolution_error(detail: str | None) -> bool:
        if not detail:
            return False
        normalized = detail.lower()
        return (
            "name or service not known" in normalized
            or "temporary failure in name resolution" in normalized
            or "nodename nor servname provided" in normalized
            or "no address associated with hostname" in normalized
            or "getaddrinfo failed" in normalized
        )

    @staticmethod
    def _is_startup_grace_active(session: TunnelSession, now: datetime) -> bool:
        return bool(session.startup_grace_until and now < session.startup_grace_until)

    @staticmethod
    def _format_startup_grace_message(public_error: str | None) -> str:
        if public_error:
            return (
                "Tunnel wird gestartet, öffentliche URL propagiert noch. "
                f"Temporärer Check-Fehler: {public_error}"
            )
        return "Tunnel wird gestartet, öffentliche URL propagiert noch."

    @staticmethod
    def _is_session_process_alive(session: TunnelSession) -> bool:
        process = session.process
        if process is not None:
            return process.poll() is None

        if session.pid is None:
            return False

        try:
            os.kill(session.pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False

    @staticmethod
    def _get_process_exit_code(session: TunnelSession) -> int | None:
        if session.process is None:
            return None
        return session.process.poll()

    def _refresh_log_tail(self, session: TunnelSession) -> None:
        with session._log_lock:
            if session._log_buffer:
                session.raw_log_tail = list(session._log_buffer)

    @staticmethod
    def _start_output_collector(
        process: subprocess.Popen[str],
        output_queue: Queue[str | None],
        log_buffer: deque[str],
        log_lock: threading.Lock,
        thread_name: str,
    ) -> None:
        reader_thread = threading.Thread(
            target=CloudflareQuickTunnelProvider._enqueue_output,
            args=(process, output_queue, log_buffer, log_lock),
            daemon=True,
            name=thread_name,
        )
        reader_thread.start()

    @staticmethod
    def extract_public_url_from_log_line(line: str) -> str | None:
        match = TRY_CLOUDFLARE_URL_PATTERN.search(line)
        return match.group(0) if match else None

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str] | None) -> None:
        if process is None:
            return
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                LOGGER.warning("Tunnelprozess konnte nicht sauber beendet werden", exc_info=True)

    @staticmethod
    def _terminate_pid(pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            LOGGER.debug("PID %s konnte nicht per SIGTERM beendet werden", pid, exc_info=True)


class TunnelManager:
    def __init__(self, provider: TunnelProvider, provider_name: str, default_local_url: str):
        self.provider = provider
        self.provider_name = provider_name
        self.default_local_url = default_local_url
        self.session: TunnelSession | None = None
        self.last_error: str | None = None

    @staticmethod
    def is_process_alive(session: TunnelSession) -> bool:
        process = session.process
        if process is not None:
            return process.poll() is None

        if session.pid is None:
            return False

        try:
            os.kill(session.pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False

    @staticmethod
    def mark_session_stale(session: TunnelSession, reason: str) -> None:
        session.status = TunnelStatus.STALE
        session.stale_reason = reason

    @staticmethod
    def cleanup_terminated_session(session: TunnelSession) -> None:
        session.process = None
        session.pid = None
        session.public_url = None
        session.last_healthcheck_ok = None
        session.last_healthcheck_at = None
        session.last_process_alive = None
        session.last_local_healthcheck_ok = None
        session.last_public_healthcheck_ok = None

    @staticmethod
    def is_session_restartable(session: TunnelSession) -> bool:
        return session.status in {TunnelStatus.STALE, TunnelStatus.ERROR, TunnelStatus.STOPPED}

    def start(self, local_url: str | None = None) -> TunnelSession:
        existing = self.session
        if existing is not None:
            current_status = self.provider.get_status(existing)
            existing.status = current_status
            if not self.is_session_restartable(existing):
                return existing
            if current_status == TunnelStatus.STALE:
                try:
                    self.provider.stop(existing)
                except Exception as exc:
                    LOGGER.debug("Konnte stale Session nicht sauber stoppen: %s", exc)
                self.cleanup_terminated_session(existing)

        target_url = (local_url or self.default_local_url).strip()
        self.session = TunnelSession(
            provider=self.provider_name,
            local_url=target_url,
            public_url=None,
            pid=None,
            started_at=datetime.now(timezone.utc),
            status=TunnelStatus.STARTING,
            raw_log_tail=[],
        )
        started = self.provider.start(target_url)
        self.session = started
        self.last_error = started.error_message if started.status == TunnelStatus.ERROR else None
        return started

    def stop(self) -> TunnelSession | None:
        if self.session is None:
            return None

        try:
            self.provider.stop(self.session)
        except Exception as exc:
            self.last_error = f"Stop fehlgeschlagen: {exc}"
            LOGGER.warning("Tunnel-Stop meldete Fehler: %s", exc)
        finally:
            self.session.status = TunnelStatus.STOPPED
            self.cleanup_terminated_session(self.session)
            self.session.error_message = None
            self.session.stale_reason = None
        return self.session

    def get_session(self) -> TunnelSession | None:
        if self.session is None:
            return None

        if self.session.status in {TunnelStatus.STARTING, TunnelStatus.RUNNING, TunnelStatus.WARNING}:
            if not self.is_process_alive(self.session):
                self.mark_session_stale(self.session, "Tunnelprozess ist nicht mehr aktiv.")
                self.session.process = None
                return self.session

        if self.session.status == TunnelStatus.STALE:
            self.session.process = None
            if not self.session.stale_reason:
                self.session.stale_reason = "Tunnelprozess wurde beendet oder Session ist veraltet."
            return self.session

        status = self.provider.get_status(self.session)
        self.session.status = status

        if self.session.status == TunnelStatus.STALE:
            self.session.process = None
            if not self.session.stale_reason:
                self.session.stale_reason = "Tunnelprozess wurde beendet oder Session ist veraltet."

        return self.session


@dataclass
class HostTunnelRuntimeState:
    execution_mode: str
    provider: str
    local_url: str
    public_url: str | None
    pid: int | None
    status: TunnelStatus
    started_at: datetime | None
    last_error: str | None
    last_exit_code: int | None
    extra_args: tuple[str, ...]
    process_alive: bool
    log_tail: list[str]
    stale_reason: str | None = None


def _safe_read_json(path: Path) -> dict[str, object] | None:
    try:
        if not path.exists():
            return None
        import json
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_text_lines(path: Path, max_lines: int = 20) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def _parse_host_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None
    except Exception:
        return None


def _is_pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def read_host_tunnel_runtime_state(
    *,
    status_file: str,
    log_file: str,
    pid_file: str,
    default_provider: str,
    default_local_url: str,
) -> HostTunnelRuntimeState:
    status_path = Path(status_file)
    log_path = Path(log_file)
    pid_path = Path(pid_file)
    payload = _safe_read_json(status_path) or {}
    payload_status = str(payload.get("status", "STOPPED")).upper()
    try:
        status = TunnelStatus(payload_status)
    except ValueError:
        status = TunnelStatus.STOPPED

    pid_from_status = payload.get("pid")
    pid = int(pid_from_status) if isinstance(pid_from_status, int) else _parse_host_pid(pid_path)
    process_alive = _is_pid_alive(pid)
    stale_reason = None
    if pid is not None and not process_alive:
        stale_reason = "PID-Datei vorhanden, aber Prozess läuft nicht."
        if status in {TunnelStatus.RUNNING, TunnelStatus.STARTING, TunnelStatus.WARNING}:
            status = TunnelStatus.STALE

    started_at = None
    raw_started_at = payload.get("started_at")
    if isinstance(raw_started_at, str):
        try:
            started_at = datetime.fromisoformat(raw_started_at.replace("Z", "+00:00"))
        except Exception:
            started_at = None

    extra_args_payload = payload.get("extra_args")
    extra_args: tuple[str, ...] = ()
    if isinstance(extra_args_payload, list):
        extra_args = tuple(str(item) for item in extra_args_payload if str(item).strip())

    return HostTunnelRuntimeState(
        execution_mode="host",
        provider=str(payload.get("provider", default_provider)),
        local_url=str(payload.get("local_url", default_local_url)),
        public_url=str(payload["public_url"]) if payload.get("public_url") else None,
        pid=pid,
        status=status if process_alive or status in {TunnelStatus.STOPPED, TunnelStatus.ERROR, TunnelStatus.STALE} else TunnelStatus.STALE,
        started_at=started_at,
        last_error=str(payload.get("last_error")) if payload.get("last_error") else None,
        last_exit_code=int(payload["last_exit_code"]) if isinstance(payload.get("last_exit_code"), int) else None,
        extra_args=extra_args,
        process_alive=process_alive,
        log_tail=_read_text_lines(log_path, max_lines=15),
        stale_reason=stale_reason,
    )


def sync_public_share_sidebar_state(manager: TunnelManager | None) -> None:
    session = manager.get_session() if manager else None
    is_running = bool(session and session.status == TunnelStatus.RUNNING and session.public_url)
    st_url = session.public_url if is_running else None

    # keine harte Streamlit-Abhängigkeit für Tests
    try:
        import streamlit as st

        st.session_state["public_share_url"] = st_url
        st.session_state["public_share_active"] = is_running
        st.session_state["public_share_status"] = session.status.value if session else TunnelStatus.STOPPED.value
        st.session_state["public_share_error"] = session.error_message if session else None
    except Exception:
        return
