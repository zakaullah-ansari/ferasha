#!/usr/bin/env python
"""Django administrative command-line utility for Ferasha backend-core."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ImportError(
            "Could not import Django. Ensure it is installed and that the "
            "virtual environment is activated."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
