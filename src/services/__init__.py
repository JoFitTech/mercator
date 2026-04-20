"""Service-Schicht für Import, Analyse und Dashboard-Aufbereitung.

Verzichtet bewusst auf eager Imports, um zirkuläre Paketimporte zu vermeiden.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	from src.services.analysis_service import AnalysisService
	from src.services.dashboard_service import DashboardService
	from src.services.database_status_service import DatabaseStatusService
	from src.services.import_service import ImportService

_EXPORT_MODULES = {
	"AnalysisService": "src.services.analysis_service",
	"DashboardService": "src.services.dashboard_service",
	"DatabaseStatusService": "src.services.database_status_service",
	"ImportService": "src.services.import_service",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
	module_name = _EXPORT_MODULES.get(name)
	if module_name is None:
		raise AttributeError(f"module 'src.services' has no attribute {name!r}")
	return getattr(import_module(module_name), name)


def __dir__() -> list[str]:
	return sorted(list(globals().keys()) + list(_EXPORT_MODULES.keys()))

