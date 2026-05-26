"""Cached UI fonts and shadowed text drawing for readability over the map."""

from __future__ import annotations

import pygame as pg

# Comma-separated preference list; SysFont picks the first installed and falls
# back to PyGame's default font if none are present (e.g. on a minimal CI box).
_PREFERRED = "Segoe UI,DejaVu Sans,Verdana,Arial"
_cache: dict[tuple[int, bool], pg.font.Font] = {}


def get_font(size: int, bold: bool = False) -> pg.font.Font:
    key = (size, bold)
    font = _cache.get(key)
    if font is None:
        font = pg.font.SysFont(_PREFERRED, size, bold=bold)
        _cache[key] = font
    return font


def draw_text(surface, font, text, x, y, col=(220, 220, 220), shadow=(0, 0, 0)) -> None:
    if shadow is not None:
        surface.blit(font.render(text, True, shadow), (x + 1, y + 1))
    surface.blit(font.render(text, True, col), (x, y))
