"""Zentrale Konfiguration für Mercator.

Dieses Modul lädt Umgebungsvariablen und stellt Konfigurationsobjekte bereit,
die in Datenimport, Datenbankzugriff und UI genutzt werden.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Lädt lokale .env-Datei, falls vorhanden.
load_dotenv()


@dataclass(frozen=True)
class AppSettings:
    """Konfigurationscontainer für Anwendung und Infrastruktur.

    Verantwortung:
    - zentrale Ablage von App-Metadaten
    - Definition von Pfaden für Roh-, Zwischen- und Zieldaten
    - Bereitstellung von DB-Verbindungsparametern
    """

    app_env: str
    app_title: str
    dataset_path: str
    project_root: Path
    data_raw_path: Path
    data_interim_path: Path
    data_processed_path: Path
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str
    mongo_uri: str
    mongo_database: str


def load_settings() -> AppSettings:
    """Erstellt ein `AppSettings`-Objekt aus Umgebungsvariablen.

    Returns:
        AppSettings: Vollständige Konfiguration für Laufzeitmodule.

    Hinweise:
        - MYSQL_PASSWORD und MONGO_URI sind Platzhalter und müssen für reale
          Umgebungen über eine lokale `.env` überschrieben werden.
        - Keine echten Credentials im Repository hinterlegen.
    """

    project_root = Path(__file__).resolve().parents[2]

    return AppSettings(
        app_env=os.getenv("APP_ENV", "local"),
        app_title=os.getenv("APP_TITLE", "Mercator"),
        dataset_path=os.getenv("DATASET_PATH", "data/raw/"),
        project_root=project_root,
        data_raw_path=project_root / "data" / "raw",
        data_interim_path=project_root / "data" / "interim",
        data_processed_path=project_root / "data" / "processed",
        mysql_host=os.getenv("MYSQL_HOST", "localhost"),
        mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
        mysql_database=os.getenv("MYSQL_DATABASE", "mercator"),
        mysql_user=os.getenv("MYSQL_USER", "root"),
        mysql_password=os.getenv("MYSQL_PASSWORD", "change_me"),
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
        mongo_database=os.getenv("MONGO_DATABASE", "mercator"),
    )
