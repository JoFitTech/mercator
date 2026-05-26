from __future__ import annotations

import streamlit_app
from src.config.settings import SettingsError


class _DbStatus:
    class _Mysql:
        is_connected = True
        active_target = "uni"

    class _Mongo:
        is_connected = True

    mysql = _Mysql()
    mongo = _Mongo()
    is_ingestion_available = True


def test_main_orders_startup_sync_before_auto_import(monkeypatch) -> None:
    calls: list[str] = []

    class _Factory:
        mysql_client = object()

        def create_app_settings_service(self):
            class _Svc:
                def load(self):
                    return object()

            return _Svc()

        def create_import_service(self):
            calls.append("create_import_service")
            return None

        def create_dashboard_service(self):
            return None

        def create_analysis_service(self):
            return None

        def create_company_repository(self):
            return None

        def create_api_usage_service(self):
            return None

    class _Settings:
        disable_import = False
        review_mode = False
        ui_test_mode = False
        public_share = type("_P", (), {"enabled": False, "execution_mode": "host"})()

    monkeypatch.setattr(streamlit_app, "bootstrap_app", lambda: (_Settings(), _DbStatus(), None, _Factory()))
    monkeypatch.setattr(streamlit_app, "build_infrastructure_mode", lambda db: object())
    monkeypatch.setattr(streamlit_app, "ensure_valid_nav_target", lambda: "Dashboard")
    monkeypatch.setattr(streamlit_app, "render_navigation_topbar", lambda: "Dashboard")
    monkeypatch.setattr(streamlit_app, "render_sidebar_navigation", lambda: None)
    monkeypatch.setattr(streamlit_app, "render_system_status_sidebar", lambda db, res: None)
    monkeypatch.setattr(streamlit_app, "render_infrastructure_banner", lambda infra: None)
    monkeypatch.setattr(streamlit_app, "render_dashboard_page", lambda **kwargs: calls.append("page"))
    monkeypatch.setattr(streamlit_app, "handle_startup_sync", lambda **kwargs: calls.append("startup_sync") or object())
    monkeypatch.setattr(streamlit_app, "render_startup_sync_toast_or_banner", lambda outcome: calls.append("startup_toast"))
    monkeypatch.setattr(streamlit_app, "handle_auto_import", lambda *args, **kwargs: calls.append("auto_import"))
    monkeypatch.setattr(streamlit_app, "render_import_status_toast", lambda: calls.append("import_toast"))
    monkeypatch.setattr(streamlit_app.st, "session_state", {})

    streamlit_app.main()

    assert calls.index("startup_sync") < calls.index("auto_import")
    assert calls.index("startup_toast") < calls.index("auto_import")


def test_main_renders_settings_error_when_bootstrap_fails(monkeypatch) -> None:
    captured_error_messages: list[str] = []
    captured_codes: list[str] = []

    class _ExpanderStub:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        streamlit_app,
        "bootstrap_app",
        lambda: (_ for _ in ()).throw(SettingsError("MongoDB database mismatch")),
    )
    monkeypatch.setattr(streamlit_app, "render_error_state", lambda msg: captured_error_messages.append(msg))
    monkeypatch.setattr(streamlit_app.st, "expander", lambda *args, **kwargs: _ExpanderStub())
    monkeypatch.setattr(streamlit_app.st, "code", lambda text, language="text": captured_codes.append(text))

    streamlit_app.main()

    assert captured_error_messages
    assert "Konfigurationsfehler" in captured_error_messages[0]
    assert captured_codes == ["MongoDB database mismatch"]

