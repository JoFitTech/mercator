from __future__ import annotations

from pathlib import Path


def test_admin_trade_republic_tab_contains_only_local_import_button() -> None:
    file_path = Path(__file__).resolve().parents[1] / "src" / "ui" / "pages" / "admin_trade_republic_tab.py"
    content = file_path.read_text(encoding="utf-8")

    assert "Lokale TR-CSV importieren" in content
    assert "Remote aktualisieren" not in content
    assert "PDF scrapen" not in content
    assert "Quelle online ziehen" not in content

