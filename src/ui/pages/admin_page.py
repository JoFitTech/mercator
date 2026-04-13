"""Admin Dashboard für DB-Verwaltung und Datenmanipulationen."""

from __future__ import annotations

import streamlit as st

from src.config.settings import AppSettings
from src.db.mongo_client import MongoClientWrapper
from src.db.mysql_client import MySqlClient
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


class AdminDashboardService:
    """Service für Admin-Dashboard-Operationen."""

    def __init__(
        self,
        settings: AppSettings,
        mysql_client: MySqlClient,
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
        return False, "❌ Löschaktionen sind deaktiviert (Review Mode / MERCATOR_DISABLE_ADMIN_DELETE)."

    def get_mysql_stats(self) -> dict:
        """Holt Statistiken für MySQL-Datenbank."""
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
        """Löscht alle Einträge aus MySQL companies-Tabelle."""
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
                            "❌ Löschung abgebrochen: companies ist referenziert (%s insider_trades). "
                            "Lösche zuerst insider_trades oder nutze eine dedizierte Komplettlöschung."
                            % ref_count,
                        )

                    cursor.execute("DELETE FROM companies")
                    deleted_count = cursor.rowcount
                    conn.commit()

            msg = f"✅ {deleted_count} Unternehmen gelöscht"
            LOGGER.info("MySQL companies gelöscht: %d Einträge", deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Löschen von companies: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mysql_trades(self) -> tuple[bool, str]:
        """Löscht alle Einträge aus MySQL insider_trades-Tabelle."""
        if self._deletes_blocked():
            return self._blocked_message()

        try:
            with self.mysql_client.connection(include_database=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM insider_trades")
                    deleted_count = cursor.rowcount
                    conn.commit()

            msg = f"✅ {deleted_count} Insidertrades gelöscht"
            LOGGER.info("MySQL insider_trades gelöscht: %d Einträge", deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Löschen von insider_trades: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mysql_all(self) -> tuple[bool, str]:
        """Löscht alle Daten aus MySQL-Datenbank."""
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

            msg = f"✅ MySQL Datenbank geleert: {total_deleted} Einträge gelöscht"
            LOGGER.info("MySQL Datenbank komplett geleert: %d Einträge", total_deleted)
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Leeren der MySQL-Datenbank: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_companies(self) -> tuple[bool, str]:
        """Löscht alle Einträge aus MongoDB companies-Collection."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "❌ MongoDB nicht verfügbar"

        try:
            db = self.mongo_client.get_database()
            collection = db["companies"]
            result = collection.delete_many({})

            msg = f"✅ {result.deleted_count} Unternehmen gelöscht"
            LOGGER.info("MongoDB companies geleert: %d Dokumente", result.deleted_count)
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Löschen von MongoDB companies: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_trades(self) -> tuple[bool, str]:
        """Löscht alle Einträge aus MongoDB insider_trades_raw-Collection."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "❌ MongoDB nicht verfügbar"

        try:
            db = self.mongo_client.get_database()
            collection = db["insider_trades_raw"]
            result = collection.delete_many({})

            msg = f"✅ {result.deleted_count} Insidertrades gelöscht"
            LOGGER.info(
                "MongoDB insider_trades_raw geleert: %d Dokumente", result.deleted_count
            )
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Löschen von MongoDB insider_trades_raw: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def clear_mongo_all(self) -> tuple[bool, str]:
        """Löscht alle Daten aus MongoDB."""
        if self._deletes_blocked():
            return self._blocked_message()

        if not self.mongo_available or not self.mongo_client:
            return False, "❌ MongoDB nicht verfügbar"

        try:
            db = self.mongo_client.get_database()
            collections_to_clear = ["companies", "insider_trades_raw"]
            total_deleted = 0

            for collection_name in collections_to_clear:
                collection = db[collection_name]
                result = collection.delete_many({})
                total_deleted += result.deleted_count

            msg = f"✅ MongoDB Datenbank geleert: {total_deleted} Dokumente gelöscht"
            LOGGER.info("MongoDB Datenbank komplett geleert: %d Dokumente", total_deleted)
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Leeren der MongoDB: {e}"
            LOGGER.error(error_msg)
            return False, error_msg

    def rebuild_mysql_schema(self) -> tuple[bool, str]:
        """Initialisiert/repariert das MySQL-Schema."""
        try:
            actions = self.mysql_client.initialize_schema()
            if not actions:
                msg = "✅ Schema ist aktuell. Keine Änderungen nötig."
            else:
                msg = f"✅ Schema aktualisiert: {len(actions)} Änderungen\n\n"
                for action in actions:
                    msg += f"  • {action}\n"
            LOGGER.info("MySQL-Schema aktualisiert")
            return True, msg
        except Exception as e:
            error_msg = f"❌ Fehler beim Schema-Update: {e}"
            LOGGER.error(error_msg)
            return False, error_msg


def render_admin_page(
    settings: AppSettings, mysql_client: MySqlClient, mongo_available: bool = True
) -> None:
    """Rendert das Admin-Dashboard."""

    st.set_page_config(page_title="Admin Dashboard", layout="wide")

    st.markdown("# 🔐 Admin Dashboard")
    st.markdown("---")

    delete_blocked = settings.review_mode or settings.disable_admin_delete
    if settings.review_mode:
        st.warning("Review Instance - Read Only: Löschaktionen sind deaktiviert.")

    # Initialize service
    admin_service = AdminDashboardService(settings, mysql_client, mongo_available)

    # Tabs für verschiedene Bereiche
    tab_stats, tab_mysql, tab_mongo, tab_sync = st.tabs(
        [
            "📊 Statistiken",
            "🗄️ MySQL Management",
            "🍃 MongoDB Management",
            "🔄 Synchronisation",
        ]
    )

    # ===== STATISTIKEN TAB =====
    with tab_stats:
        st.markdown("## Datenbankstatistiken")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🗄️ MySQL")
            mysql_stats = admin_service.get_mysql_stats()

            if mysql_stats:
                metric_cols = st.columns(2)
                with metric_cols[0]:
                    st.metric(
                        "Unternehmen",
                        mysql_stats.get("companies_count", 0),
                        delta=None,
                    )
                with metric_cols[1]:
                    st.metric(
                        "Insidertrades",
                        mysql_stats.get("trades_count", 0),
                        delta=None,
                    )

                metric_cols = st.columns(2)
                with metric_cols[0]:
                    st.metric(
                        "Filter Settings",
                        mysql_stats.get("filter_settings_count", 0),
                        delta=None,
                    )
                with metric_cols[1]:
                    st.metric(
                        "DB-Größe (MB)",
                        f"{mysql_stats.get('database_size_mb', 0):.2f}",
                        delta=None,
                    )

                # Connection info
                with st.expander("ℹ️ Verbindungsinformationen"):
                    st.write(
                        f"**Ziel:** {settings.mysql.mysql_active_target}"
                    )
                    active_target = settings.mysql.get_active_mysql_target()
                    st.write(f"**Host:** {active_target.host}")
                    st.write(f"**Port:** {active_target.port}")
                    st.write(f"**Datenbank:** {active_target.database}")
            else:
                st.warning("Fehler beim Abrufen von MySQL-Statistiken")

        with col2:
            st.markdown("### 🍃 MongoDB")
            if mongo_available:
                mongo_stats = admin_service.get_mongo_stats()

                if mongo_stats:
                    metric_cols = st.columns(2)
                    with metric_cols[0]:
                        st.metric(
                            "Unternehmen",
                            mongo_stats.get("companies_count", 0),
                            delta=None,
                        )
                    with metric_cols[1]:
                        st.metric(
                            "Insidertrades",
                            mongo_stats.get("insider_trades_raw_count", 0),
                            delta=None,
                        )

                    # Connection info
                    with st.expander("ℹ️ Verbindungsinformationen"):
                        st.write(
                            f"**Datenbank:** {settings.mongo.database}"
                        )
                else:
                    st.warning("Fehler beim Abrufen von MongoDB-Statistiken")
            else:
                st.error("MongoDB nicht verfügbar")

    # ===== MySQL MANAGEMENT TAB =====
    with tab_mysql:
        st.markdown("## 🗄️ MySQL-Verwaltung")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Daten löschen")

            if st.button(
                "🗑️ Alle Companies löschen",
                key="delete_mysql_companies",
                help="Löscht alle Einträge aus der companies-Tabelle",
                disabled=delete_blocked,
            ):
                with st.spinner("Lösche companies..."):
                    success, message = admin_service.clear_mysql_companies()
                if success:
                    st.success(message)
                else:
                    st.error(message)

            if st.button(
                "🗑️ Alle Insider Trades löschen",
                key="delete_mysql_trades",
                help="Löscht alle Einträge aus der insider_trades-Tabelle",
                disabled=delete_blocked,
            ):
                with st.spinner("Lösche insider_trades..."):
                    success, message = admin_service.clear_mysql_trades()
                if success:
                    st.success(message)
                else:
                    st.error(message)

        with col2:
            st.markdown("### Datenbank-Operationen")

            if st.button(
                "⚠️ ALLE Daten löschen (Gefährlich!)",
                key="delete_mysql_all",
                help="Löscht ALLE Daten aus der MySQL-Datenbank",
                disabled=delete_blocked,
            ):
                st.warning(
                    "⚠️ **Dies ist gefährlich!** Alle Daten werden gelöscht!"
                )
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button(
                        "🔴 Bestätigen - ALLE Daten löschen",
                        key="confirm_delete_all",
                        type="primary",
                    ):
                        with st.spinner("Lösche alle Daten..."):
                            success, message = admin_service.clear_mysql_all()
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Schema-Verwaltung")

            if st.button(
                "🔧 Schema initialisieren/reparieren",
                key="rebuild_schema",
                help="Erstellt fehlende Tabellen und Spalten",
            ):
                with st.spinner("Aktualisiere Schema..."):
                    success, message = admin_service.rebuild_mysql_schema()
                if success:
                    st.success(message)
                else:
                    st.error(message)

        with col2:
            st.markdown("### Info")
            st.info(
                "💡 **Tipp:** Verwende diese Funktionen nur wenn du weißt, was du tust!"
            )

    # ===== MONGODB MANAGEMENT TAB =====
    with tab_mongo:
        st.markdown("## 🍃 MongoDB-Verwaltung")

        if not mongo_available:
            st.error("❌ MongoDB nicht verfügbar")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Daten löschen")

                if st.button(
                    "🗑️ Alle Companies löschen",
                    key="delete_mongo_companies",
                    help="Löscht alle Dokumente aus der companies-Collection",
                    disabled=delete_blocked,
                ):
                    with st.spinner("Lösche companies..."):
                        success, message = admin_service.clear_mongo_companies()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

                if st.button(
                    "🗑️ Alle Insider Trades löschen",
                    key="delete_mongo_trades",
                    help="Löscht alle Dokumente aus der insider_trades-Collection",
                    disabled=delete_blocked,
                ):
                    with st.spinner("Lösche insider_trades..."):
                        success, message = admin_service.clear_mongo_trades()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

            with col2:
                st.markdown("### Datenbank-Operationen")

                if st.button(
                    "⚠️ ALLE Daten löschen (Gefährlich!)",
                    key="delete_mongo_all",
                    help="Löscht ALLE Daten aus MongoDB",
                    disabled=delete_blocked,
                ):
                    st.warning(
                        "⚠️ **Dies ist gefährlich!** Alle Daten werden gelöscht!"
                    )
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button(
                            "🔴 Bestätigen - ALLE Daten löschen",
                            key="confirm_delete_mongo_all",
                            type="primary",
                        ):
                            with st.spinner("Lösche alle Daten..."):
                                success, message = admin_service.clear_mongo_all()
                            if success:
                                st.success(message)
                            else:
                                st.error(message)

            st.markdown("---")

            st.markdown("### Info")
            st.info(
                "💡 MongoDB wird für die Daten-Ingestion genutzt. Gelöschte Daten können bei nächstem Import wiederhergestellt werden."
            )

    # ===== SYNCHRONISATION TAB =====
    with tab_sync:
        st.markdown("## 🔄 Synchronisation")

        st.markdown("### Datenbank-Synchronisation")

        sync_info = st.expander("ℹ️ Über Synchronisation", expanded=True)
        with sync_info:
            st.markdown(
                """
            **Synchronisation** bedeutet, dass Daten zwischen MongoDB und MySQL abgeglichen werden:
            
            - **MongoDB** enthält die "Quelle" für Insidertrade-Daten (via FMP-API)
            - **MySQL** enthält die "Anwendungs-Datenbank" für Analysen
            - Synchronisation: MongoDB → MySQL (unidirektional)
            
            **Wichtig:**
            - Synchronisation läuft normalerweise automatisch während Imports
            - Manuelle Sync nur bei Bedarf (z.B. nach manuellen Datenänderungen)
            """
            )

        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Status")
            if settings.mysql.mysql_sync_enabled:
                st.success("✅ Synchronisation aktiviert")
            else:
                st.warning("⚠️ Synchronisation deaktiviert")

        with col2:
            st.markdown("### Aktive Ziele")
            st.write(f"**MySQL:** {settings.mysql.mysql_active_target}")
            st.write(f"**Mongo:** {settings.mongo.active_target}")

        with col3:
            st.markdown("### Letzte Aktion")
            st.write(f"_Keine Info verfügbar_")

        st.markdown("---")

        st.info(
            "ℹ️ Erweiterte Sync-Funktionen: In Zukunft können hier bidirektionale Sync, "
            "Konflikt-Auflösung und selektive Synchronisation konfiguriert werden."
        )

