"""Resolve paths to bundled resources (assets, locales).

Works both when running from source (``python -m lemond_pygame``) and from a
frozen PyInstaller build, where data files live under ``sys._MEIPASS``.
"""

from __future__ import annotations

import os
import sys


def resource_path(*parts: str) -> str:
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS, "lemond_pygame")  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, *parts)
