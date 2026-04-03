"""Leichte Smoke-Tests fuer zentrale Modulimporte."""

from __future__ import annotations

import importlib


MODULES = [
    "streamlit_app",
    "src.config.settings",
    "src.db.schema",
    "src.db.mysql_client",
    "src.db.mysql_repository",
    "src.services.import_service",
    "src.services.analysis_service",
    "src.services.dashboard_service",
]


def test_core_modules_importable() -> None:
    """Prueft, dass zentrale Module ohne Importfehler geladen werden koennen."""

    for module_name in MODULES:
        importlib.import_module(module_name)
