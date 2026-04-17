"""Admin Dashboard für DB-Verwaltung und Datenmanipulationen."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config.settings import AppSettings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_client import MySqlClient
from src.domain_rules import ScoreGatePolicy
from src.services.app_settings_service import AppSettingsService
from src.ui.components.page_scaffold import render_page_header
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


class AdminDashboardService:
    """Service für Admin-Dashboard-Operationen."""

    def __init__(
        self,
        settings: AppSettings,
        mysql_client: MySqlClient | None,
        mongo_available: bool = True,
    ):
        self.settings = settings
        self.mysql_client = mysql_client
        self.mongo_available = mongo_available
        self.mongo_client = None
        if mongo_available:
            try:
                self.mongo_client = MongoClientWrapper(settings.mongo)
            except Exception as e:
                LOGGER.warning("MongoDB nicht verfügbar: %s", e)
                self.mongo_available = False

    def _deletes_blocked(self) -> bool:
        return bool(self.settings.review_mode or self.settings.disable_admin_delete)

    def _blocked_message(self) -> tuple[bool, str]:
        return False, "Loeschaktionen sind deaktiviert (Review Mode / MERCATOR_DISABLE_ADMIN_DELETE)."

    def get_mysql_stats(self) -> dict:
        """Holt Statistiken für MySQL-Datenbank."""
        if not self.mysql_client:
            return {}
        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    stats = {}

                    # Companies count
                    cursor.execute("SELECT COUNT(*) as count FROM companies")
                    stats["companies_count"] = cursor.fetchone()["count"]

                    # Insider trades count
                    cursor.execute("SELECT COUNT(*) as count FROM insider_trades")
                    stats["trades_count"] = cursor.fetchone()["count"]

                    # Filter settings count
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM app_filter_settings"
                    )
                    stats["filter_settings_count"] = cursor.fetchone()["count"]

                    # Runtime preferences count
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM app_runtime_preferences"
                    )
                    stats["runtime_prefs_count"] = cursor.fetchone()["count"]

                    # Database size (in MB)
                    cursor.execute(
                        f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb "
                        f"FROM information_schema.tables WHERE table_schema = DATABASE()"
                    )
                    result = cursor.fetchone()
                    stats["database_size_mb"] = (
                        result["size_mb"] if result["size_mb"] else 0
                    )
                    try:
                        cursor.execute(
                            "SELECT source_url, source_last_refreshed_at, instrument_count, last_error "
                            "FROM trade_republic_universe_meta ORDER BY source_last_refreshed_at DESC LIMIT 1"
                        )
                        stats["trade_republic_meta"] = cursor.fetchone() or {}
                    except Exception:
                        stats["trade_republic_meta"] = {}
                    try:
                        cursor.execute(
                            "SELECT COUNT(*) AS cnt FROM companies "
                            "WHERE COALESCE(trade_republic_universe_status, 'UNKNOWN') = 'UNKNOWN'"
                        )
                        stats["trade_republic_unknown_count"] = int((cursor.fetchone() or {}).get("cnt", 0))
                    except Exception:
                        stats["trade_republic_unknown_count"] = 0
                    try:
                        cursor.execute(
                            "SELECT COUNT(*) AS cnt FROM companies "
                            "WHERE COALESCE(trade_republic_universe_status, 'UNKNOWN') = 'IN_UNIVERSE'"
                        )
                        stats["trade_republic_in_universe_count"] = int((cursor.fetchone() or {}).get("cnt", 0))
                    except Exception:
                        stats["trade_republic_in_universe_count"] = 0

            return stats
        except Exception as e:
            LOGGER.error("Fehler beim Abrufen von MySQL-Statistiken: %s", e)
            return {}

    def get_mongo_stats(self) -> dict:
        """Holt Statistiken für MongoDB."""
        if not self.mongo_available or not self.mongo_client:
            return {}

        try:
            db = self.mongo_client.get_database()
            stats = {}

            # Collection counts
            for collection_name in ["companies", "insider_trades_raw"]:
                collection = db[collection_name]
                stats[f"{collection_name}_count"] = collection.count_documents({})

            return stats
        except Exception as e:
            LOGGER.error("Fehler beim Abrufen von MongoDB-Statistiken: %s", e)
            return {}

    def clear_mysql_companies(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MySQL companies-Tabelle."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS ref_count
                        FROM insider_trades t
                        INNER JOIN companies c ON c.company_key = t.company_key
                        """
                    )
                    ref_count = int((cursor.fetchone() or {}).get("ref_count", 0))
                    if ref_count > 0:
                        return (
                            False,
                            "Loeschung abgebrochen: companies ist referenziert (%s insider_trades). "
                            "Loesche zuerst insider_trades oder nutze eine dedizierte Komplettloeschung."
                            % ref_count,
                        )

                    cursor.execute("DELETE FROM companies")
                    deleted_count = cursor.rowcount
                    conn.commit()

            msg = f"{deleted_count} Unternehmen geloescht"
            LOGGER.info("MySQL companies geloescht: %d Eintraege", deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von companies: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mysql_trades(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MySQL insider_trades-Tabelle."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM insider_trades")
                    deleted_count = cursor.rowcount
                    conn.commit()

            msg = f"{deleted_count} Insidertrades geloescht"
            LOGGER.info("MySQL insider_trades geloescht: %d Eintraege", deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von insider_trades: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mysql_all(self) -> tuple[bool, str]:
        """Loecht alle Daten aus MySQL-Datenbank."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        if self._deletes_blocked():
            return self._blocked_message()

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    tables_to_clear = [
                        "insider_trades",
                        "companies",
                        "app_filter_settings",
                        "app_runtime_preferences",
                    ]
                    total_deleted = 0

                    for table in tables_to_clear:
                        cursor.execute(f"DELETE FROM {table}")
                        total_deleted += cursor.rowcount
                    conn.commit()

            msg = f"MySQL Datenbank geleert: {total_deleted} Eintraege geloescht"
            LOGGER.info("MySQL Datenbank komplett geleert: %d Eintraege", total_deleted)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Leeren der MySQL-Datenbank: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_companies(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MongoDB companies-Collection."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfuegbar"

        try:
            db = self.mongo_client.get_database()
            collection = db["companies"]
            result = collection.delete_many({})

            msg = f"{result.deleted_count} Unternehmen geloescht"
            LOGGER.info("MongoDB companies geleert: %d Dokumente", result.deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von MongoDB companies: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_trades(self) -> tuple[bool, str]:
        """Loecht alle Eintraege aus MongoDB insider_trades_raw-Collection."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfuegbar"

        try:
            db = self.mongo_client.get_database()
            collection = db["insider_trades_raw"]
            result = collection.delete_many({})

            msg = f"{result.deleted_count} Insidertrades geloescht"
            LOGGER.info(
                "MongoDB insider_trades_raw geleert: %d Dokumente", result.deleted_count
            )
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Loeschen von MongoDB insider_trades_raw: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_all(self) -> tuple[bool, str]:
        """Loecht alle Daten aus MongoDB."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "MongoDB nicht verfuegbar"

        try:
            db = self.mongo_client.get_database()
            collections_to_clear = ["companies", "insider_trades_raw"]
            total_deleted = 0

            for collection_name in collections_to_clear:
                collection = db[collection_name]
                result = collection.delete_many({})
                total_deleted += result.deleted_count

            msg = f"MongoDB Datenbank geleert: {total_deleted} Dokumente geloescht"
            LOGGER.info("MongoDB Datenbank komplett geleert: %d Dokumente", total_deleted)
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Leeren der MongoDB: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def refresh_tr_universe(self) -> tuple[bool, str]:
        """Triggered einen manuellen Refresh des TR-Universums."""
        from src.services.trade_republic_universe_service import TradeRepublicUniverseIngestionService
        ingest = TradeRepublicUniverseIngestionService(self.settings, self.mysql_client)
        success, reason = ingest.refresh_if_stale(force=True)
        if success:
            return True, "Trade Republic Universum erfolgreich aktualisiert."
        return False, f"Refresh nicht durchgefuehrt: {reason}"

    def rebuild_mysql_schema(self) -> tuple[bool, str]:
        """Initialisiert/repariert das MySQL-Schema."""
        if not self.mysql_client:
            return False, "MySQL-Verbindung nicht verfuegbar."
        try:
            actions = self.mysql_client.initialize_schema()
            if not actions:
                msg = "Schema ist aktuell. Keine Aenderungen noetig."
            else:
                msg = f"Schema aktualisiert: {len(actions)} Aenderungen\n\n"
                for action in actions:
                    msg += f"  - {action}\n"
            LOGGER.info("MySQL-Schema aktualisiert")
            return True, msg
        except Exception as e:
            error_msg = f"Fehler beim Schema-Update: {e}"
            LOGGER.error(error_msg)
            return False, error_msg


def render_admin_page(
    settings: AppSettings,
    mysql_client: MySqlClient | None,
    mongo_available: bool = True,
    settings_service: AppSettingsService | None = None,
    import_service: ImportService | None = None,
) -> None:
    """Rendert die Admin-Seite als präzisen Regelarbeitsplatz."""

    # 0. HEADER MIT SYSTEM-CHECK
    actions = [{"label": "🔍 System Check", "type": "secondary"}]
    results = render_page_header(
        "Admin", 
        "Konfiguration von Gates, Scoring-Regeln und Datenquellen.",
        actions=actions
    )
    
    if results and results[0]:
        st.session_state["show_system_check"] = True

    if st.session_state.get("show_system_check", False):
        with st.container(border=True):
            st.markdown("### 🔍 System-Verfügbarkeit")
            c1, c2 = st.columns(2)
            if mysql_client:
                c1.success("MySQL: Verbunden", icon="✅")
            else:
                c1.error("MySQL: Getrennt", icon="❌")
            
            if mongo_available:
                c2.success("MongoDB: Verbunden", icon="✅")
            else:
                c2.warning("MongoDB: Nicht verfügbar", icon="⚠️")
            
            if st.button("Schließen", use_container_width=True):
                st.session_state["show_system_check"] = False
                st.rerun()

    # 1. Hauptnavigation über echte Tabs (Requirement 8.2)
    tab_import, tab_sync, tab_db_control = st.tabs([
        "📥 Import & API2", "⚙️ Sync-Status", "🛠️ Datenbank-Control"
    ])

    admin_service = AdminDashboardService(settings, mysql_client, mongo_available)

    # 2. IMPORT & API2 TAB
    with tab_import:
        st.subheader("Datenimport & API2-Steuerung")
        st.caption("Manueller Anstoß des FMP-Imports und Konfiguration des API2-Verhaltens.")

        if settings_service:
            runtime_settings = settings_service.load()
            
            with st.form("api2_config_form", border=True):
                st.markdown("#### API2-Firing Konfiguration")
                api2_mode = st.selectbox(
                    "API2-Firing Mode (vor Import)",
                    options=["ONLY PASS", "PASS + PENDING", "ALL VALID", "DISABLED"],
                    index=["ONLY PASS", "PASS + PENDING", "ALL VALID", "DISABLED"].index(runtime_settings.api2_firing_mode) if runtime_settings.api2_firing_mode in ["ONLY PASS", "PASS + PENDING", "ALL VALID", "DISABLED"] else 1,
                    help="Steuert, für welche Trades das Company-Enrichment (API2) im Importlauf ausgeführt wird."
                )
                
                if st.form_submit_button("API2-Modus speichern", use_container_width=True):
                    runtime_settings.api2_firing_mode = api2_mode
                    settings_service.save(runtime_settings)
                    st.success(f"API2-Modus auf '{api2_mode}' gesetzt.")
                    st.rerun()

        st.markdown("---")
        st.markdown("#### Manueller Import")
        col1, col2 = st.columns([1, 1])
        import_page = col1.number_input("Feed-Seite", min_value=1, value=1)
        import_limit = col2.number_input("Records pro Seite", min_value=1, max_value=1000, value=100)

        if st.button("🚀 Import jetzt starten", type="primary", use_container_width=True):
            if not import_service:
                st.error("Import-Service nicht verfügbar.")
            else:
                with st.spinner("Importiere Daten von FMP..."):
                    try:
                        summary = import_service.run_hourly_import(page=int(import_page), limit=int(import_limit))
                        st.success("Import erfolgreich abgeschlossen!")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Feed Records", summary.fetched_feed_records)
                        c2.metric("Neue Raw Records", summary.inserted_raw_records)
                        c3.metric("Upserted Clean", summary.upserted_clean_records)
                        st.balloons()
                    except Exception as e:
                        st.error(f"Fehler beim Import: {e}")

    # 3. SYNC STATUS TAB
    with tab_sync:
        st.subheader("Synchronisations-Status")
        st.caption("Status der Datenspiegelung zwischen MongoDB (Rohdaten) und MySQL (Analyse).")
        
        col1, col2 = st.columns(2)
        mysql_stats = admin_service.get_mysql_stats()
        mongo_stats = admin_service.get_mongo_stats()
        
        with col1:
            st.markdown("#### MySQL (Analyse)")
            st.metric("Trades", f"{mysql_stats.get('trades_count', 0):,}")
            st.metric("Companies", f"{mysql_stats.get('companies_count', 0):,}")
            st.metric("Größe (MB)", f"{mysql_stats.get('database_size_mb', 0):.2f}")
            
        with col2:
            st.markdown("#### MongoDB (Rohdaten)")
            st.metric("Raw Trades", f"{mongo_stats.get('insider_trades_raw_count', 0):,}")
            st.metric("Raw Companies", f"{mongo_stats.get('companies_count', 0):,}")

    # 4. DB CONTROL TAB
    with tab_db_control:
        st.subheader("Datenbank-Wartung & Resets")
        st.caption("Technische Werkzeuge zur Fehlerbehebung und Datenbereinigung.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Wartung")
            if st.button("🛠️ Schema reparieren", use_container_width=True, help="Initialisiert oder aktualisiert das Tabellen-Schema in MySQL"):
                with st.spinner("Repariere Schema..."):
                    success, msg = admin_service.rebuild_mysql_schema()
                    if success: st.success(msg)
                    else: st.error(msg)
            
            if st.button("🔄 TR Universum Refresh", use_container_width=True, help="Aktualisiert die Liste der handelbaren Ticker von Trade Republic"):
                with st.spinner("Aktualisiere TR-Universum..."):
                    success, msg = admin_service.refresh_tr_universe()
                    if success: st.success(msg)
                    else: st.warning(msg)
        
        with c2:
            st.markdown("#### Gefahrenzone")
            
            with st.popover("🗑️ MySQL Daten löschen", use_container_width=True):
                st.error("### ACHTUNG: Datenverlust")
                st.write("Dies löscht alle verarbeiteten Insider-Trades und Firmendaten in MySQL.")
                st.write("Rohdaten in MongoDB bleiben erhalten.")
                
                confirm_mysql = st.checkbox("Ich bin mir der Konsequenzen bewusst", key="confirm_mysql_delete_final_v2")
                if st.button("JETZT MySQL LÖSCHEN", type="primary", use_container_width=True, disabled=not confirm_mysql):
                    with st.spinner("Lösche MySQL Daten..."):
                        success, msg = admin_service.clear_mysql_all()
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if st.session_state.get("advanced_mode", False):
                with st.popover("🔥 MongoDB Rohdaten löschen", use_container_width=True):
                    st.error("### KRITISCHE AKTION: Rohdatenverlust")
                    st.write("Dies löscht alle importierten Rohdaten in MongoDB.")
                    
                    confirm_mongo = st.checkbox("Ich möchte wirklich alle Rohdaten löschen", key="confirm_mongo_delete_final_v2")
                    if st.button("JETZT MongoDB LÖSCHEN", type="primary", use_container_width=True, disabled=not confirm_mongo):
                        with st.spinner("Lösche MongoDB Daten..."):
                            success, msg = admin_service.clear_mongo_all()
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
