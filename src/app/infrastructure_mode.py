"""Zentrale Infrastruktur- und Degraded-Mode-Logik für die UI."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from src.services.database_status_service import DatabaseStatus


@dataclass(frozen=True)
class InfrastructureMode:
    mysql_online: bool
    mongo_online: bool
    analysis_available: bool
    import_available: bool
    settings_persistence_available: bool

    @property
    def write_available(self) -> bool:
        return self.mysql_online and self.mongo_online

    @property
    def is_degraded(self) -> bool:
        return not (self.mysql_online and self.mongo_online)


def build_infrastructure_mode(db_status: DatabaseStatus) -> InfrastructureMode:
    return InfrastructureMode(
        mysql_online=db_status.mysql.is_connected,
        mongo_online=db_status.mongo.is_connected,
        analysis_available=db_status.is_analysis_available,
        import_available=db_status.mysql.is_connected and db_status.mongo.is_connected,
        settings_persistence_available=db_status.mysql.is_connected,
    )


def render_infrastructure_banner(mode: InfrastructureMode) -> None:
    if not mode.is_degraded:
        return

    messages: list[str] = []
    if not mode.mysql_online:
        messages.append(
            "MySQL derzeit nicht verfügbar. Analysefunktionen laufen im eingeschränkten Lesemodus."
        )
    if not mode.mongo_online:
        messages.append(
            "MongoDB derzeit nicht verfügbar. Import- und Rohdatenfunktionen sind vorübergehend deaktiviert."
        )
    if not mode.settings_persistence_available:
        messages.append(
            "Einstellungen werden mangels Datenbankverbindung nur für diese Sitzung übernommen."
        )

    with st.container(border=True):
        st.subheader("Eingeschränkter Infrastrukturmodus")
        for message in messages:
            st.write(f"- {message}")
