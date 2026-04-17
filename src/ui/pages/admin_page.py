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
) -> None:
    """Rendert die Admin-Seite als präzisen Regelarbeitsplatz."""

    render_page_header(
        "Admin", 
        "Konfiguration von Gates, Scoring-Regeln und Datenquellen.",
        actions=[{"label": "System Check", "type": "secondary"}]
    )

    # 1. Sekundärnavigation (Sub-Modes)
    sub_mode = st.radio(
        "Admin-Bereich",
        options=["Gates", "Score-Regeln", "Sync & Daten", "Import"],
        horizontal=True,
        label_visibility="collapsed"
    )

    admin_service = AdminDashboardService(settings, mysql_client, mongo_available)
    st.markdown("---")

    if sub_mode == "Import":
        st.subheader("Daten-Ingestion (Raw to Storage)")
        # Hier die Logik, die früher auf dem Dashboard war
        with st.container(border=True):
            c1, c2 = st.columns(2)
            page = c1.number_input("Feed-Seite", min_value=0, value=0)
            limit = c2.number_input("Limit", min_value=1, max_value=1000, value=100)
            
            if st.button("Manuellen Import starten", type="primary", use_container_width=True):
                st.info("Import gestartet... (Simulation)")
        
        st.markdown("### System-Health")
        mysql_stats = admin_service.get_mysql_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("MySQL Trades", mysql_stats.get("trades_count", 0))
        c2.metric("MySQL Companies", mysql_stats.get("companies_count", 0))
        c3.metric("DB Size (MB)", f"{mysql_stats.get('database_size_mb', 0):.2f}")

    elif sub_mode == "Gates":
        st.subheader("Gate-Konfiguration")
        st.info("Hier werden die Ausschlusskriterien für Trades definiert.")
        with st.container(border=True):
            st.checkbox("Require Common Stock", value=True)
            st.checkbox("Require Purchase Event", value=True)
            st.number_input("Min Trade Value ($)", value=100000)
            st.button("Gate-Regeln speichern", type="primary")

    elif sub_mode == "Score-Regeln":
        st.subheader("Scoring-Logik")
        st.caption("Definition der Gewichtungen für die Score-Klassen.")
        # Beispiel-Regeln
        df_rules = pd.DataFrame([
            {"Regel": "Hohes Volumen", "Gewichtung": 0.4, "Status": "Aktiv"},
            {"Regel": "Insider-Rang", "Gewichtung": 0.3, "Status": "Aktiv"},
            {"Regel": "Kursreaktion", "Gewichtung": 0.3, "Status": "Vorschau"},
        ])
        st.table(df_rules)

    elif sub_mode == "Sync & Daten":
        st.subheader("Datenbank-Management")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### MySQL")
            if st.button("Schema reparieren", use_container_width=True):
                admin_service.rebuild_mysql_schema()
            if st.button("TR Universum Refresh", use_container_width=True):
                admin_service.refresh_tr_universe()
        
        with col2:
            st.markdown("#### Gefahrenzone")
            if st.button("Alle MySQL Daten loeschen", use_container_width=True, type="secondary"):
                st.warning("Wirklich loeschen?")
