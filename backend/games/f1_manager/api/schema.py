"""Message schema placeholders for UI bridge payloads."""
from __future__ import annotations

from typing import TypedDict


class Ack(TypedDict):
    ok: bool
    message: str
