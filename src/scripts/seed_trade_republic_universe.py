from __future__ import annotations

from src.config.settings import load_settings
from src.db.mysql_client import MySqlClient
from src.services.trade_republic_universe_service import TradeRepublicUniverseIngestionService


def main() -> int:
    settings = load_settings()
    mysql_client = MySqlClient(settings.mysql.get_active_mysql_target())
    service = TradeRepublicUniverseIngestionService(settings=settings, mysql_client=mysql_client)
    summary = service.import_local_csv(force=True)

    if summary.status != "refreshed":
        print(f"TR seed fehlgeschlagen: {summary.status} - {summary.error}")
        return 1

    print(
        "TR seed erfolgreich: "
        f"rows={summary.inserted_rows} source={summary.source_url} hash={summary.source_hash[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

