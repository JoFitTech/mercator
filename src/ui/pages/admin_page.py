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
    col_header, col_status = st.columns([0.7, 0.3], vertical_alignment="center")
    with col_header:
        render_page_header(
            "Admin", 
            "Konfiguration von Gates, Scoring-Regeln und Datenquellen."
        )
    
    with col_status:
        if st.button("🔍 System Check", use_container_width=True, help="Status der Datenbankverbindungen prüfen"):
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

    # 1. Hauptnavigation über echte Tabs
    tab_gates, tab_score, tab_sync, tab_import = st.tabs([
        "🎯 Gates", "📊 Score-Regeln", "⚙️ Sync & Daten", "📥 Import"
    ])

    admin_service = AdminDashboardService(settings, mysql_client, mongo_available)

    # 2. GATES TAB (Dynamisch)
    with tab_gates:
        st.subheader("Gate-Konfiguration")
        st.caption("Definition der harten Ausschlusskriterien für den Dashboard-Scope.")
        
        if settings_service:
            policy = settings_service.load_score_gate_policy()
            with st.form("gate_policy_form", border=True):
                g1, g2 = st.columns(2)
                gate_min_value = g1.number_input("Min Trade Value ($)", value=policy.gate_min_trade_value, step=10000)
                gate_form_type = g2.text_input("Required Form Type", value=policy.gate_form_type_required)
                
                s1, s2 = st.columns(2)
                gate_security_name = s1.text_input("Required Security Name", value=policy.gate_security_name_required)
                gate_validation = s2.selectbox("Required Validation Status", options=["VALID", "INVALID", "UNCHECKED"], index=0 if policy.gate_validation_status_required == "VALID" else 1)
                
                a1, a2 = st.columns(2)
                allowed_aod = a1.text_input("Allowed A/D (CSV)", value=",".join(policy.gate_allowed_acquisition_or_disposition))
                excluded_tt = a2.text_input("Excluded Trans. Types (CSV)", value=",".join(policy.gate_excluded_transaction_types))
                
                if st.form_submit_button("Gate-Regeln speichern", type="primary", use_container_width=True):
                    new_policy = ScoreGatePolicy(
                        score_threshold_fail_max=policy.score_threshold_fail_max,
                        score_threshold_hold_min=policy.score_threshold_hold_min,
                        score_threshold_pass_min=policy.score_threshold_pass_min,
                        fail_label=policy.fail_label,
                        hold_label=policy.hold_label,
                        pass_label=policy.pass_label,
                        fail_color=policy.fail_color,
                        hold_color=policy.hold_color,
                        pass_color=policy.pass_color,
                        gate_validation_status_required=gate_validation,
                        gate_form_type_required=gate_form_type,
                        gate_security_name_required=gate_security_name,
                        gate_allowed_acquisition_or_disposition=tuple(v.strip().upper() for v in allowed_aod.split(",") if v.strip()),
                        gate_excluded_transaction_types=tuple(v.strip() for v in excluded_tt.split(",") if v.strip()),
                        gate_min_trade_value=int(gate_min_value)
                    )
                    settings_service.save_score_gate_policy(new_policy)
                    st.success("Gate-Policy erfolgreich aktualisiert.")
                    st.rerun()
        else:
            st.warning("Settings-Service nicht verfügbar. Bitte Konfiguration prüfen.")

    # 3. SCORE REGELN TAB (Dynamisch)
    with tab_score:
        st.subheader("Scoring-Logik & Klassifizierung")
        st.caption("Konfiguration der Schwellenwerte für die Score-Klassen (FAIL, HOLD, PASS).")
        
        if settings_service:
            policy = settings_service.load_score_gate_policy()
            with st.form("score_policy_form", border=True):
                st.markdown("#### Schwellenwerte")
                t1, t2, t3 = st.columns(3)
                th_pass = t1.number_input("PASS ab", min_value=0.0, max_value=100.0, value=policy.score_threshold_pass_min)
                th_hold = t2.number_input("HOLD ab", min_value=0.0, max_value=100.0, value=policy.score_threshold_hold_min)
                th_fail_max = t3.number_input("FAIL bis", min_value=0.0, max_value=100.0, value=policy.score_threshold_fail_max)
                
                st.markdown("#### Labels & Farben")
                l1, l2, l3 = st.columns(3)
                label_pass = l1.text_input("Label PASS", value=policy.pass_label)
                label_hold = l2.text_input("Label HOLD", value=policy.hold_label)
                label_fail = l3.text_input("Label FAIL", value=policy.fail_label)
                
                c1, c2, c3 = st.columns(3)
                color_pass = c1.color_picker("Farbe PASS", value=policy.pass_color)
                color_hold = c2.color_picker("Farbe HOLD", value=policy.hold_color)
                color_fail = c3.color_picker("Farbe FAIL", value=policy.fail_color)
                
                if st.form_submit_button("Scoring-Konfiguration speichern", type="primary", use_container_width=True):
                    new_policy = ScoreGatePolicy(
                        score_threshold_fail_max=float(th_fail_max),
                        score_threshold_hold_min=float(th_hold),
                        score_threshold_pass_min=float(th_pass),
                        fail_label=label_fail,
                        hold_label=label_hold,
                        pass_label=label_pass,
                        fail_color=color_fail,
                        hold_color=color_hold,
                        pass_color=color_pass,
                        gate_validation_status_required=policy.gate_validation_status_required,
                        gate_form_type_required=policy.gate_form_type_required,
                        gate_security_name_required=policy.gate_security_name_required,
                        gate_allowed_acquisition_or_disposition=policy.gate_allowed_acquisition_or_disposition,
                        gate_excluded_transaction_types=policy.gate_excluded_transaction_types,
                        gate_min_trade_value=policy.gate_min_trade_value
                    )
                    settings_service.save_score_gate_policy(new_policy)
                    st.success("Scoring-Policy erfolgreich aktualisiert.")
                    st.rerun()
        else:
            st.info("Score-Konfiguration wird aktuell nur über Umgebungsvariablen gesteuert.")

    # 4. SYNC & DATEN TAB
    with tab_sync:
        st.subheader("Datenbank-Management")
        col1, col2 = st.columns(2)
        with col1:
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
        
        with col2:
            st.markdown("#### Gefahrenzone")
            
            with st.popover("🗑️ MySQL Daten loeschen", use_container_width=True):
                st.error("### ACHTUNG: Datenverlust")
                st.write("Dies löscht alle verarbeiteten Insider-Trades und Firmendaten in MySQL.")
                st.write("Rohdaten in MongoDB bleiben erhalten.")
                
                confirm_mysql = st.checkbox("Ich bin mir der Konsequenzen bewusst", key="confirm_mysql_delete_final")
                if st.button("JETZT MySQL LÖSCHEN", type="primary", use_container_width=True, disabled=not confirm_mysql):
                    with st.spinner("Lösche MySQL Daten..."):
                        success, msg = admin_service.clear_mysql_all()
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            if st.session_state.get("advanced_mode", False):
                with st.popover("🔥 MongoDB Rohdaten loeschen", use_container_width=True):
                    st.error("### KRITISCHE AKTION: Rohdatenverlust")
                    st.write("Dies löscht alle importierten Rohdaten in MongoDB.")
                    st.write("Daten können nur durch neuen API-Import wiederhergestellt werden.")
                    
                    confirm_mongo = st.checkbox("Ich möchte wirklich alle Rohdaten löschen", key="confirm_mongo_delete_final")
                    if st.button("JETZT MongoDB LÖSCHEN", type="primary", use_container_width=True, disabled=not confirm_mongo):
                        with st.spinner("Lösche MongoDB Daten..."):
                            success, msg = admin_service.clear_mongo_all()
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    # 5. IMPORT TAB
    with tab_import:
        st.subheader("Daten-Ingestion (FMP API to Storage)")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            page = c1.number_input("Feed-Seite", min_value=0, value=0, help="Startseite für den API-Abruf")
            limit = c2.number_input("Limit", min_value=1, max_value=1000, value=100, help="Anzahl der abzurufenden Records pro Request")
            
            if st.button("🚀 Manuellen Import starten", type="primary", use_container_width=True):
                if not import_service:
                    st.error("Import-Service nicht verfügbar.")
                else:
                    with st.status("Import läuft...") as status:
                        try:
                            summary = import_service.run_hourly_import(page=int(page), limit=int(limit))
                            status.update(label="Import erfolgreich!", state="complete")
                            
                            # Import Summary anzeigen
                            with st.expander("Import-Zusammenfassung", expanded=True):
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("Feed Records", summary.fetched_feed_records)
                                col2.metric("Raw Inserted", summary.inserted_raw_records)
                                col3.metric("Clean Upserted", summary.upserted_clean_records)
                                col4.metric("Profiles Fetched", summary.fetched_profiles)
                            
                            st.toast("Daten wurden erfolgreich importiert", icon="📥")
                        except Exception as e:
                            status.update(label=f"Fehler: {e}", state="error")
                            st.error(f"Import fehlgeschlagen: {e}")
        
        st.markdown("### Aktuelle Speicher-Metriken")
        mysql_stats = admin_service.get_mysql_stats()
        mongo_stats = admin_service.get_mongo_stats()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("MySQL Trades", f"{mysql_stats.get('trades_count', 0):,}")
        m2.metric("MySQL Companies", f"{mysql_stats.get('companies_count', 0):,}")
        m3.metric("DB Size (MB)", f"{mysql_stats.get('database_size_mb', 0):.2f}")
        
        if st.session_state.get("advanced_mode", False):
            a1, a2 = st.columns(2)
            a1.metric("Mongo Raw Trades", f"{mongo_stats.get('insider_trades_raw_count', 0):,}")
            a2.metric("Mongo Companies", f"{mongo_stats.get('companies_count', 0):,}")
