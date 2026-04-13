"""Base simulation engine contracts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Tick:
    """Represents a generic simulation tick."""

    index: int
    delta_s: float
