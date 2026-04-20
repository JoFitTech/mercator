"""Tunnel-Service für temporäre öffentliche Freigaben der lokalen Streamlit-App."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import os
import re
import select
import shutil
import subprocess
import time
from typing import Protocol

from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)
TRY_CLOUDFLARE_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")
_MAX_LOG_LINES = 40


class TunnelStatus(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
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


class TunnelProvider(Protocol):
    def start(self, local_url: str) -> TunnelSession:
        ...

    def stop(self, session: TunnelSession) -> None:
        ...

    def get_status(self, session: TunnelSession) -> TunnelStatus:
        ...


class CloudflareQuickTunnelProvider:
    def __init__(self, cloudflared_bin: str = "cloudflared", startup_timeout_seconds: int = 20):
        self.cloudflared_bin = cloudflared_bin
        self.startup_timeout_seconds = startup_timeout_seconds

    def is_binary_available(self) -> bool:
        if os.path.isabs(self.cloudflared_bin) or os.path.sep in self.cloudflared_bin:
            return os.path.isfile(self.cloudflared_bin) and os.access(self.cloudflared_bin, os.X_OK)
        return shutil.which(self.cloudflared_bin) is not None

    def _resolve_bin(self) -> str:
        if os.path.isabs(self.cloudflared_bin) or os.path.sep in self.cloudflared_bin:
            return self.cloudflared_bin
        resolved = shutil.which(self.cloudflared_bin)
        return resolved or self.cloudflared_bin

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
        if not self.is_binary_available():
            return self._build_missing_binary_session(local_url)

        command = [self._resolve_bin(), "tunnel", "--url", local_url]
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

        deadline = time.monotonic() + self.startup_timeout_seconds
        found_url: str | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break

            stdout = process.stdout
            if stdout is None:
                break

            ready, _, _ = select.select([stdout], [], [], 0.2)
            if not ready:
                continue

            line = stdout.readline().strip()
            if not line:
                continue
            log_tail.append(line)
            match = TRY_CLOUDFLARE_URL_PATTERN.search(line)
            if match:
                found_url = match.group(0)
                break

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

    def get_status(self, session: TunnelSession) -> TunnelStatus:
        process = session.process
        if process is None:
            return session.status

        if process.poll() is None:
            return TunnelStatus.RUNNING

        if session.status in {TunnelStatus.RUNNING, TunnelStatus.STARTING}:
            return TunnelStatus.STALE
        return TunnelStatus.STOPPED

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


class TunnelManager:
    def __init__(self, provider: TunnelProvider, provider_name: str, default_local_url: str):
        self.provider = provider
        self.provider_name = provider_name
        self.default_local_url = default_local_url
        self.session: TunnelSession | None = None
        self.last_error: str | None = None

    def start(self, local_url: str | None = None) -> TunnelSession:
        existing = self.session
        if existing is not None:
            current_status = self.provider.get_status(existing)
            existing.status = current_status
            if current_status in {TunnelStatus.STARTING, TunnelStatus.RUNNING}:
                return existing

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
            self.session.process = None
            self.session.public_url = None
        return self.session

    def get_session(self) -> TunnelSession | None:
        if self.session is None:
            return None
        self.session.status = self.provider.get_status(self.session)
        return self.session


def sync_public_share_sidebar_state(manager: TunnelManager | None) -> None:
    session = manager.get_session() if manager else None
    if session and session.status == TunnelStatus.RUNNING and session.public_url:
        st_url = session.public_url
    else:
        st_url = None

    # keine harte Streamlit-Abhängigkeit für Tests
    try:
        import streamlit as st

        st.session_state["public_share_url"] = st_url
        st.session_state["public_share_status"] = session.status.value if session else TunnelStatus.STOPPED.value
    except Exception:
        return
