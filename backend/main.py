"""Compatibility module for the previous backend entrypoint path."""
from __future__ import annotations

import warnings


def main() -> None:
    """Delegate execution to root ``main.py`` in the v2 stack."""
    warnings.warn(
        "Use 'python main.py' instead of 'python backend/main.py'.",
        DeprecationWarning,
        stacklevel=2,
    )
    from main import main as root_main

    root_main()


if __name__ == "__main__":
    main()
