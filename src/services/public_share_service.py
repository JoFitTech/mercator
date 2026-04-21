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
    ):
        self.cloudflared_bin = cloudflared_bin
        self.startup_timeout_seconds = startup_timeout_seconds
        self.healthcheck_timeout_seconds = healthcheck_timeout_seconds
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

        command = [resolved_bin, "tunnel", "--url", local_url]
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
        reader_thread = threading.Thread(
            target=self._enqueue_output,
            args=(process, output_queue),
            daemon=True,
            name="cloudflared-output-reader",
        )
        reader_thread.start()

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

        reader_thread.join(timeout=0.2)

        if found_url and process.poll() is None:
            return TunnelSession(
                provider="cloudflare",
                local_url=local_url,
                public_url=found_url,
                pid=process.pid,
                started_at=started_at,
                status=TunnelStatus.RUNNING,
                raw_log_tail=list(log_tail),
                process=process,
            )

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

        process_alive = self._is_session_process_alive(session)
        session.last_process_alive = process_alive
        if not process_alive:
            session.stale_reason = "Tunnelprozess ist nicht mehr aktiv."
            session.error_message = "Tunnelprozess ist beendet. Eine neue öffentliche URL ist erforderlich."
            return TunnelStatus.STALE

        if session.last_healthcheck_at and datetime.now(timezone.utc) - session.last_healthcheck_at < timedelta(
            seconds=_HEALTHCHECK_INTERVAL_SECONDS
        ):
            if session.last_public_healthcheck_ok is False:
                return TunnelStatus.STALE
            return TunnelStatus.RUNNING if session.last_healthcheck_ok else TunnelStatus.WARNING

        local_healthy = self._is_local_url_healthy(session.local_url)
        public_healthy = self._is_public_url_reachable(session.public_url)
        public_error = self._last_public_url_error
        session.last_healthcheck_at = datetime.now(timezone.utc)
        session.last_local_healthcheck_ok = local_healthy
        session.last_public_healthcheck_ok = public_healthy
        session.last_healthcheck_ok = local_healthy and public_healthy

        if not local_healthy:
            session.error_message = "Tunnelprozess läuft, aber die lokale Streamlit-App ist derzeit nicht erreichbar."
            session.stale_reason = None
            return TunnelStatus.WARNING

        if not public_healthy:
            session.error_message = public_error or "Öffentliche Tunnel-URL ist nicht erreichbar. Neue URL erforderlich."
            session.stale_reason = session.error_message
            return TunnelStatus.STALE

        if local_healthy and public_healthy:
            session.error_message = None
            session.stale_reason = None
            return TunnelStatus.RUNNING

        session.error_message = "Tunnelzustand unklar."
        return TunnelStatus.WARNING

    @staticmethod
    def _enqueue_output(process: subprocess.Popen[str], output_queue: Queue[str | None]) -> None:
        stdout = process.stdout
        if stdout is None:
            output_queue.put(None)
            return

        try:
            for line in stdout:
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

    def _check_public_url(self, url: str | None) -> tuple[bool, str | None]:
        if not url:
            return False, "Keine öffentliche URL vorhanden."

        for method in ("HEAD", "GET"):
            req = url_request.Request(url, method=method)
            try:
                with url_request.urlopen(req, timeout=self.healthcheck_timeout_seconds) as resp:
                    status = getattr(resp, "status", 200)
                    if 200 <= status < 500:
                        return True, None
                    return False, f"Öffentliche URL antwortet mit HTTP {status}."
            except url_error.HTTPError as exc:
                if 200 <= exc.code < 500:
                    return True, None
                detail = f"Öffentliche URL antwortet mit HTTP {exc.code}."
                if exc.code == 530:
                    try:
                        body = exc.read().decode("utf-8", errors="ignore")
                        if "1033" in body:
                            detail = "Öffentliche URL ist nicht mehr auflösbar (Cloudflare Error 1033)."
                    except Exception:
                        pass
                return False, detail
            except url_error.URLError as exc:
                return False, f"Öffentliche URL nicht erreichbar: {exc.reason}."
            except Exception as exc:
                return False, f"Öffentliche URL-Prüfung fehlgeschlagen: {exc}."
        return False, "Öffentliche URL nicht erreichbar."

    def _is_public_url_reachable(self, url: str | None) -> bool:
        """Kompatibilitätsmethode: boolsche Erreichbarkeit der öffentlichen URL."""
        reachable, detail = self._check_public_url(url)
        self._last_public_url_error = detail
        return reachable

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
