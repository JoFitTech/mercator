"""Hilfsfunktionen für einheitliches Logging."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Erzeugt einen standardisierten Logger für Modulzwecke."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    return logging.getLogger(name)
