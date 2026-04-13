"""Budget helpers shared by game implementations."""
from __future__ import annotations


def remaining_budget(cap_m: float, spent_m: float) -> float:
    """Return remaining budget in millions."""
    return max(cap_m - spent_m, 0.0)
