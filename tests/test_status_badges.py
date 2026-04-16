from __future__ import annotations

from src.ui.components import status_badges


def test_trade_republic_universe_badge_maps_to_text_and_style(monkeypatch) -> None:
    captured = {}

    def _fake_status_badge(label: str, status_type: str = "INFO", help: str | None = None) -> None:
        captured["label"] = label
        captured["status_type"] = status_type

    monkeypatch.setattr(status_badges, "status_badge", _fake_status_badge)
    status_badges.trade_republic_universe_badge("IN_UNIVERSE")

    assert captured["label"] == "Im Universum"
    assert captured["status_type"] == "SUCCESS"
