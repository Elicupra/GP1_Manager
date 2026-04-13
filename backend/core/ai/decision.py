"""Shared AI decision contracts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Decision:
    """Generic AI decision payload."""

    action: str
    confidence: float
