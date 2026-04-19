"""Repository für App-Einstellungen und Laufzeitpräferenzen in MySQL."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
from src.db.mysql_client import MySqlClient

class AppFilterSettingsRepository:
    """Persistiert UI-Filterzustände mit fachlichem Business-Key (scope + key)."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _encode_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode_json(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list, int, float, bool)):
            return value
        return json.loads(str(value))

    def load(self, setting_scope: str, setting_key: str) -> Any:
        query = "SELECT setting_value_json FROM app_filter_settings WHERE setting_scope = %s AND setting_key = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (setting_scope, setting_key))
                row = cursor.fetchone()
                return self._decode_json(row[0]) if row else None

    def list_all(self, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        query = "SELECT * FROM app_filter_settings ORDER BY setting_scope, setting_key LIMIT %s OFFSET %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return [dict(zip(columns, row, strict=False)) for row in rows]

    def upsert(self, payload: dict[str, Any]) -> None:
        created_at = payload.get("created_at") or payload.get("updated_at") or datetime.now(timezone.utc)
        updated_at = payload.get("updated_at") or datetime.now(timezone.utc)
        sql = """
            INSERT INTO app_filter_settings (
                setting_scope, setting_key, setting_value_json, source_system, sync_version, created_at, updated_at
            ) VALUES (
                %(setting_scope)s, %(setting_key)s, %(setting_value_json)s, %(source_system)s, %(sync_version)s, %(created_at)s, %(updated_at)s
            )
            ON DUPLICATE KEY UPDATE
                setting_value_json = VALUES(setting_value_json),
                source_system = VALUES(source_system),
                sync_version = VALUES(sync_version),
                created_at = COALESCE(created_at, VALUES(created_at)),
                updated_at = VALUES(updated_at)
        """
        params = {
            "setting_scope": payload.get("setting_scope"),
            "setting_key": payload.get("setting_key"),
            "setting_value_json": self._encode_json(payload.get("setting_value_json")),
            "source_system": payload.get("source_system", "app"),
            "sync_version": int(payload.get("sync_version") or 1),
            "created_at": created_at,
            "updated_at": updated_at,
        }
        self._client.execute(sql, params)

class AppRuntimePreferencesRepository:
    """Persistiert allgemeine Laufzeitpräferenzen mit Business-Key `preference_key`."""

    def __init__(self, client: MySqlClient) -> None:
        self._client = client

    @staticmethod
    def _encode_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode_json(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list, int, float, bool)):
            return value
        return json.loads(str(value))

    def load(self, preference_key: str) -> Any:
        query = "SELECT preference_value_json FROM app_runtime_preferences WHERE preference_key = %s LIMIT 1"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (preference_key,))
                row = cursor.fetchone()
                return self._decode_json(row[0]) if row else None

    def list_all(self, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        query = "SELECT * FROM app_runtime_preferences ORDER BY preference_key LIMIT %s OFFSET %s"
        with self._client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                return [dict(zip(columns, row, strict=False)) for row in rows]

    def upsert(self, payload: dict[str, Any]) -> None:
        created_at = payload.get("created_at") or payload.get("updated_at") or datetime.now(timezone.utc)
        updated_at = payload.get("updated_at") or datetime.now(timezone.utc)
        sql = """
            INSERT INTO app_runtime_preferences (
                preference_key, preference_value_json, source_system, sync_version, created_at, updated_at
            ) VALUES (
                %(preference_key)s, %(preference_value_json)s, %(source_system)s, %(sync_version)s, %(created_at)s, %(updated_at)s
            )
            ON DUPLICATE KEY UPDATE
                preference_value_json = VALUES(preference_value_json),
                source_system = VALUES(source_system),
                sync_version = VALUES(sync_version),
                created_at = COALESCE(created_at, VALUES(created_at)),
                updated_at = VALUES(updated_at)
        """
        params = {
            "preference_key": payload.get("preference_key"),
            "preference_value_json": self._encode_json(payload.get("preference_value_json")),
            "source_system": payload.get("source_system", "app"),
            "sync_version": int(payload.get("sync_version") or 1),
            "created_at": created_at,
            "updated_at": updated_at,
        }
        self._client.execute(sql, params)
