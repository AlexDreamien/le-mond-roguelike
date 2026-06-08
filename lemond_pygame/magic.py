"""Hero spellcasting front end: spell menu, aiming, and projectile effects.

The pure rules (which spells exist, their reach and damage, and which monsters
a cast strikes) live in :mod:`lemond_pygame.core.spells`. This module is the
pygame layer: it lets the player pick a spell and a direction, then animates the
projectile flying to its impact and bursting.

Rendering is driven by a ``render_frame(dt, overlay=None)`` callback supplied by
the game loop. It updates and draws the world to the screen (without flipping);
the ``overlay(world_surface)`` hook lets this module paint the projectile onto
the world before any screen shake is applied. Each routine flips the display
itself.
"""

from __future__ import annotations

import asyncio
import math

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core.dungeon import WALL
from .ui_common import line, panel

_DIR_KEYS = {
    pg.K_UP: (0, -1),
    pg.K_DOWN: (0, 1),
    pg.K_LEFT: (-1, 0),
    pg.K_RIGHT: (1, 0),
}


def _tile_center(cell: tuple[int, int]) -> tuple[int, int]:
    x, y = cell
    return (x * cfg.TILE + cfg.TILE // 2, y * cfg.TILE + cfg.TILE // 2)


def _glow(surface, px: int, py: int, color, radius: int) -> None:
    """Blit an additive filled circle so projectiles read as glowing energy."""
    g = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
    pg.draw.circle(g, (*color, 255), (radius, radius), radius)
    surface.blit(g, (px - radius, py - radius), special_flags=pg.BLEND_RGB_ADD)


def _reachable_tiles(reach, d, origin):
    """Tiles reachable in each cardinal direction up to ``reach`` (stops at walls)."""
    ox, oy = origin
    tiles = []
    for dx, dy in _DIR_KEYS.values():
        for i in range(1, reach + 1):
            x, y = ox + dx * i, oy + dy * i
            if not d.inside(x, y) or d.grid[y][x] == WALL:
                break
            tiles.append((x, y))
    return tiles


async def choose_direction(screen, render_frame, clock, d, origin, reach, title):
    """Aim overlay. Returns a (dx, dy) direction, or None if cancelled.

    Purely a choice of direction: the hero never steps as a side effect. The
    tiles reachable within ``reach`` are highlighted green so the player sees how
    far the spell or shot will travel. ``title`` is a pre-localized header.
    """
    font = fonts.get_font(20)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, 90)
    tiles = _reachable_tiles(reach, d, origin)
    fill = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    fill.fill((80, 230, 120, 70))

    def overlay(world):
        for x, y in tiles:
            px, py = x * cfg.TILE, y * cfg.TILE
            world.blit(fill, (px, py))
            pg.draw.rect(world, (120, 240, 150), (px, py, cfg.TILE, cfg.TILE), 1)

    while True:
        dt = clock.tick(cfg.FPS) / 1000.0
        render_frame(dt, overlay)
        panel(screen, rect, title, icon="icon.magic")
        line(screen, font, i18n.t("ui.magic.hint"), rect.x + 20, rect.y + 50)
        pg.display.flip()
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type != pg.KEYDOWN:
                continue
            if e.key == pg.K_ESCAPE:
                return None
            if e.key in _DIR_KEYS:
                return _DIR_KEYS[e.key]


async def animate_shot(screen, render_frame, clock, origin, end, sounds, color=(235, 220, 150)):
    """Fly a small projectile (arrow/bolt) from ``origin`` to ``end`` and spark."""
    start = _tile_center(origin)
    finish = _tile_center(end)
    sounds["magic"].play()
    dist = math.hypot(finish[0] - start[0], finish[1] - start[1])
    flight = max(0.07, dist / 900.0)
    elapsed = 0.0
    while elapsed < flight:
        dt = clock.tick(cfg.FPS) / 1000.0
        elapsed += dt
        f = min(1.0, elapsed / flight)
        bx = int(start[0] + (finish[0] - start[0]) * f)
        by = int(start[1] + (finish[1] - start[1]) * f)

        def overlay(world, bx=bx, by=by):
            pg.draw.line(world, color, start, (bx, by), 2)
            _glow(world, bx, by, color, 5)

        render_frame(dt, overlay)
        pg.display.flip()
        await asyncio.sleep(0)


async def _run_for(seconds, clock, render_frame, overlay=None):
    """Drive render_frame for a fixed wall-clock duration."""
    elapsed = 0.0
    while elapsed < seconds:
        dt = clock.tick(cfg.FPS) / 1000.0
        elapsed += dt
        render_frame(dt, overlay)
        pg.display.flip()
        await asyncio.sleep(0)


async def animate_cast(
    screen, render_frame, clock, origin, result, ps, shake, sounds, particle_scale=1.0
):
    """Play the projectile flight and the impact burst for a resolved cast."""
    spell = result.spell
    color = spell.color
    start = _tile_center(origin)
    end = _tile_center(result.impact)
    sounds["magic"].play()

    # --- Flight: a glowing mote (or growing beam, for pierce) travels to impact.
    dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
    flight = max(0.10, dist / 700.0)
    elapsed = 0.0
    while elapsed < flight:
        dt = clock.tick(cfg.FPS) / 1000.0
        elapsed += dt
        f = min(1.0, elapsed / flight)
        bx = int(start[0] + (end[0] - start[0]) * f)
        by = int(start[1] + (end[1] - start[1]) * f)

        def overlay(world, bx=bx, by=by, f=f):
            if spell.shape == "pierce":
                pg.draw.line(world, color, start, (bx, by), 4)
            _glow(world, bx, by, color, 9)
            _glow(world, bx, by, color, 5)

        render_frame(dt, overlay)
        pg.display.flip()
        await asyncio.sleep(0)

    # --- Impact: burst particles, screen shake, and any chain arcs.
    def scaled(n):
        return max(0, int(n * particle_scale))

    if spell.shape in ("aoe", "meteor"):
        shake.trigger(mag=5.0 if spell.shape == "aoe" else 8.0, dur=0.18)
        sounds["hit"].play()
        if scaled(28):
            ps.spawn_sparkles(result.impact[0], result.impact[1], n=scaled(28), col=color)

    targets = [h.pos for h in result.hits] or [result.impact]
    for cell in targets:
        if scaled(20):
            ps.spawn_burst(cell[0], cell[1], n=scaled(20), base_col=color)

    if spell.shape == "chain" and result.hits:
        points = [start] + [_tile_center(h.pos) for h in result.hits]

        def overlay(world, points=points):
            for a, b in zip(points, points[1:], strict=False):
                pg.draw.line(world, color, a, b, 3)

        await _run_for(0.22, clock, render_frame, overlay)
    else:
        await _run_for(0.22, clock, render_frame)
