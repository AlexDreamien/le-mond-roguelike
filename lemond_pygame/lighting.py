"""Smooth torch-light fog and a static vignette for the play area.

The fog is computed at tile resolution (one alpha value per tile) and then
``smoothscale``-d up to pixel resolution, which turns the old blocky per-tile
shadows into soft gradients for free.
"""

from __future__ import annotations

import math

import pygame as pg

from .core import config as cfg

_AMBIENT_EDGE = 125  # darkness alpha at the edge of the lit radius
_SEEN_DARK = 200  # explored but currently out of sight
_UNSEEN_DARK = 255  # never seen
_TINT = (6, 8, 16)  # cool dungeon-blue darkness

_vignette_cache: pg.Surface | None = None


def _build_fog(d, visible, hero_rx, hero_ry, radius) -> pg.Surface:
    w, h = d.w, d.h
    fog = pg.Surface((w, h), pg.SRCALPHA)
    cx, cy = hero_rx + 0.5, hero_ry + 0.5
    r, g, b = _TINT
    for y in range(h):
        seen_row = d.seen[y]
        for x in range(w):
            if (x, y) in visible:
                dist = math.hypot((x + 0.5) - cx, (y + 0.5) - cy)
                t = min(1.0, dist / radius)
                alpha = int(_AMBIENT_EDGE * (t**1.6))
            elif seen_row[x]:
                alpha = _SEEN_DARK
            else:
                alpha = _UNSEEN_DARK
            fog.set_at((x, y), (r, g, b, alpha))
    return fog


def _vignette() -> pg.Surface:
    global _vignette_cache
    if _vignette_cache is None:
        sw, sh = 16, 10
        small = pg.Surface((sw, sh), pg.SRCALPHA)
        cx, cy = (sw - 1) / 2, (sh - 1) / 2
        maxd = math.hypot(cx, cy)
        for y in range(sh):
            for x in range(sw):
                dn = math.hypot(x - cx, y - cy) / maxd
                small.set_at((x, y), (0, 0, 0, int(95 * dn**2.4)))
        _vignette_cache = pg.transform.smoothscale(small, (cfg.SCREEN_W, cfg.MAP_H * cfg.TILE))
    return _vignette_cache


def apply(surface, d, visible, hero_rx, hero_ry, radius) -> None:
    fog = _build_fog(d, visible, hero_rx, hero_ry, radius)
    surface.blit(pg.transform.smoothscale(fog, (d.w * cfg.TILE, d.h * cfg.TILE)), (0, 0))
    surface.blit(_vignette(), (0, 0))
