"""In-process event bus abstraction."""
from __future__ import annotations

from collections.abc import Callable


class EventBus:
    """Very small synchronous event bus for backend modules."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[dict], None]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[dict], None]) -> None:
        self._listeners.setdefault(event_name, []).append(callback)

    def emit(self, event_name: str, payload: dict) -> None:
        for callback in self._listeners.get(event_name, []):
            callback(payload)
