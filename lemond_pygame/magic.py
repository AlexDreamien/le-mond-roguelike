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

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import spells as sp
from .ui_common import line, panel

_DIR_KEYS = {
    pg.K_UP: (0, -1),
    pg.K_DOWN: (0, 1),
    pg.K_LEFT: (-1, 0),
    pg.K_RIGHT: (1, 0),
}
_NUM_KEYS = {pg.K_1: 0, pg.K_2: 1, pg.K_3: 2, pg.K_4: 3, pg.K_5: 4}


def _tile_center(cell: tuple[int, int]) -> tuple[int, int]:
    x, y = cell
    return (x * cfg.TILE + cfg.TILE // 2, y * cfg.TILE + cfg.TILE // 2)


def _glow(surface, px: int, py: int, color, radius: int) -> None:
    """Blit an additive filled circle so projectiles read as glowing energy."""
    g = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
    pg.draw.circle(g, (*color, 255), (radius, radius), radius)
    surface.blit(g, (px - radius, py - radius), special_flags=pg.BLEND_RGB_ADD)


async def choose_spell(screen, render_frame, hero, clock):
    """Spell picker overlay. Returns the chosen Spell, or None if cancelled."""
    font = fonts.get_font(20)
    skill = hero.skills["MAGIC"]
    avail = sp.available_spells(skill) or [sp.SPELLS[0]]
    sel = 0
    rect = pg.Rect(80, 70, cfg.SCREEN_W - 160, 70 + len(sp.SPELLS) * 30)
    while True:
        dt = clock.tick(cfg.FPS) / 1000.0
        render_frame(dt)
        panel(screen, rect, i18n.t("ui.magic.choose"), icon="icon.magic")
        y = rect.y + 44
        for spell in sp.SPELLS:
            name = i18n.t("magic.spell." + spell.key)
            if sp.is_unlocked(spell, skill):
                slot = avail.index(spell) + 1
                dmg = sp.spell_damage(spell, hero.int_, skill)
                rng = sp.spell_range(spell, hero.int_)
                label = f"{slot}. {name}   ({i18n.t('ui.magic.stat', dmg=dmg, rng=rng)})"
                selected = avail[sel] is spell
                if selected:
                    hl = pg.Rect(rect.x + 12, y - 3, rect.w - 24, 27)
                    pg.draw.rect(screen, (44, 44, 66), hl, border_radius=6)
                col = (235, 235, 245) if selected else (175, 185, 205)
            else:
                label = f"-. {name}   ({i18n.t('ui.magic.locked', skill=spell.min_skill)})"
                col = (110, 110, 125)
            line(screen, font, label, rect.x + 24, y, col)
            y += 30
        line(
            screen,
            font,
            i18n.t("ui.magic.choose_hint"),
            rect.x + 20,
            rect.bottom - 30,
            (160, 160, 200),
        )
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
            if e.key in (pg.K_UP, pg.K_LEFT):
                sel = (sel - 1) % len(avail)
            elif e.key in (pg.K_DOWN, pg.K_RIGHT):
                sel = (sel + 1) % len(avail)
            elif e.key in (pg.K_RETURN, pg.K_f):
                return avail[sel]
            elif e.key in _NUM_KEYS and _NUM_KEYS[e.key] < len(avail):
                return avail[_NUM_KEYS[e.key]]


async def choose_direction(screen, render_frame, hero, clock, spell):
    """Aim overlay. Returns a (dx, dy) direction, or None if cancelled.

    Purely a choice of direction: the hero never steps as a side effect.
    """
    font = fonts.get_font(20)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, 90)
    name = i18n.t("magic.spell." + spell.key)
    while True:
        dt = clock.tick(cfg.FPS) / 1000.0
        render_frame(dt)
        panel(screen, rect, i18n.t("ui.magic.dir_title", spell=name), icon="icon.magic")
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
