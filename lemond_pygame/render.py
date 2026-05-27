"""Rendering layer: animation state and all map/HUD drawing.

Depends on :mod:`core` for data and geometry but owns no game rules. The game
loop feeds it state each frame.
"""

from __future__ import annotations

import math
import random

import pygame as pg

from . import fonts, i18n, lighting
from .core import config as cfg
from .core.combat import dodge_chance
from .core.dungeon import CHEST, ENTRY, EXIT, LOOT, POTION, WALL, Dungeon
from .core.entities import Hero
from .drawing import object_icon

_shadow_cache: pg.Surface | None = None


def _entity_shadow() -> pg.Surface:
    global _shadow_cache
    if _shadow_cache is None:
        t = cfg.TILE
        s = pg.Surface((t, t // 3), pg.SRCALPHA)
        pg.draw.ellipse(s, (0, 0, 0, 90), (2, 0, t - 4, t // 3))
        _shadow_cache = s
    return _shadow_cache


def _blit_shadow(surface, px, py) -> None:
    s = _entity_shadow()
    surface.blit(s, (px, py + cfg.TILE - s.get_height() + 2))


_npc_cache: dict[str, pg.Surface] = {}


def _npc_marker(kind: str) -> pg.Surface:
    s = _npc_cache.get(kind)
    if s is None:
        t = cfg.TILE
        s = pg.Surface((t, t), pg.SRCALPHA)
        color = (235, 205, 95) if kind == "merchant" else (110, 200, 235)
        pg.draw.circle(s, color, (t // 2, t // 2), t // 2 - 3)
        pg.draw.circle(s, (20, 20, 28), (t // 2, t // 2), t // 2 - 3, 2)
        symbol = "$" if kind == "merchant" else "+"
        glyph = fonts.get_font(22, bold=True).render(symbol, True, (30, 30, 40))
        s.blit(glyph, glyph.get_rect(center=(t // 2, t // 2)))
        _npc_cache[kind] = s
    return s


class AnimState:
    def __init__(self, sheets: dict, fps: int = 8, speed_scale: float = 1.0):
        self.sheets = sheets
        self.state = "idle"
        self.frame = 0
        self.timer = 0.0
        self.fps = fps
        self.one_shot = False
        self._queued = None
        self.speed_scale = speed_scale
        self.facing = "right"

    def set_speed(self, scale: float) -> None:
        self.speed_scale = max(0.2, min(3.0, scale))

    def set_facing(self, facing: str) -> None:
        # Monsters face left/right (atlas); the hero faces 4 compass directions.
        if facing in ("left", "right", "north", "south", "east", "west"):
            self.facing = facing

    def set(self, state: str, one_shot: bool = False, queue_to: str = "idle") -> None:
        if self.state != state:
            self.state = state
            self.frame = 0
            self.timer = 0.0
        self.one_shot = one_shot
        self._queued = queue_to if one_shot else None

    def _frames_for_state(self):
        for key in (f"{self.state}_{self.facing}", self.state, f"idle_{self.facing}"):
            if self.sheets.get(key):
                return self.sheets[key]
        for key in ("idle_south", "idle_right", "idle_left"):
            if self.sheets.get(key):
                return self.sheets[key]
        return next(iter(self.sheets.values()), None)

    def update(self, dt: float) -> None:
        frames = self._frames_for_state()
        if not frames:
            return
        self.timer += dt
        spf = 1.0 / max(1, self.fps) / self.speed_scale
        while self.timer >= spf:
            self.timer -= spf
            self.frame = (self.frame + 1) % len(frames)
            if self.one_shot and self.frame == 0:
                self.one_shot = False
                if self._queued:
                    self.state = self._queued
                    self._queued = None

    def get_frame(self):
        frames = self._frames_for_state()
        if not frames:
            return None
        return frames[self.frame % len(frames)]


class SlideFX:
    def __init__(self):
        self.t = 0.0
        self.dur = 0.0
        self.dir = (0.0, 0.0)
        self.dist = 0.0
        self.mode = "dash"
        self.ox = 0.0
        self.oy = 0.0

    def trigger(self, dx, dy, dist=0.25, dur=0.12, mode="dash") -> None:
        n = math.hypot(dx, dy) or 1.0
        self.dir = (dx / n, dy / n)
        self.dist = dist
        self.dur = max(0.05, dur)
        self.t = 0.0
        self.mode = mode

    def update(self, dt: float) -> None:
        if self.t >= self.dur:
            self.ox = self.oy = 0.0
            return
        self.t += dt
        phase = min(1.0, self.t / self.dur)
        amp = math.sin(math.pi * phase) if self.mode == "dash" else (1.0 - phase)
        self.ox = self.dir[0] * self.dist * amp
        self.oy = self.dir[1] * self.dist * amp


def draw_hp_bar(surface, x, y, w, h, cur, maxv) -> None:
    pg.draw.rect(surface, cfg.C_HP_BG, (x, y, w, h), border_radius=3)
    if maxv <= 0:
        return
    frac = max(0.0, min(1.0, cur / maxv))
    pg.draw.rect(surface, cfg.C_HP_FG, (x + 2, y + 2, int((w - 4) * frac), h - 4), border_radius=3)


def draw_hud(screen, hero: Hero) -> None:
    top = cfg.MAP_H * cfg.TILE
    pg.draw.rect(screen, cfg.C_PANEL, (0, top, cfg.SCREEN_W, cfg.HUD_H))
    pg.draw.rect(screen, cfg.C_PANEL_BORDER, (0, top, cfg.SCREEN_W, cfg.HUD_H), 2)
    font = fonts.get_font(20)

    # HP bar with a heart icon; the value sits centred on the bar.
    bar_y, bar_h = top + 10, 18
    heart = object_icon("icon.hp", 18)
    bar_x = 36 if heart else 10
    if heart:
        screen.blit(heart, (12, bar_y))
    draw_hp_bar(screen, bar_x, bar_y, 230, bar_h, hero.hp, hero.max_hp)
    hp_y = bar_y + (bar_h - font.get_height()) // 2
    _line(screen, font, f"{hero.hp}/{hero.max_hp}", bar_x + 8, hp_y, (0, 0, 0))

    # Stat row: an icon (with text fallback) followed by its value.
    dmg_min, dmg_max = hero.weapon_damage()
    dodge = int(dodge_chance(hero, hero.skills["DODGE"]) * 100)
    pairs = [
        ("icon.str", i18n.t("stat.str"), hero.str_),
        ("icon.dex", i18n.t("stat.dex"), hero.dex),
        ("icon.int", i18n.t("stat.int"), hero.int_),
        ("icon.armor", "ARM", hero.total_armor()),
        ("icon.dmg", "DMG", f"{dmg_min}-{dmg_max}"),
        ("icon.dodge", "DODGE", f"{dodge}%"),
        ("icon.xp", "XP", f"{hero.xp}/{hero.xp_to_next()}"),
        ("icon.potion", i18n.t("hud.potions"), hero.potions),
        ("icon.gold", i18n.t("hud.gold"), hero.gold),
    ]
    y = top + 40
    x = 10
    _line(screen, font, f"Lv{hero.level}", x, y, (210, 210, 240))
    x += font.size(f"Lv{hero.level}")[0] + 18
    for key, label, value in pairs:
        icon = object_icon(key, 20)
        if icon:
            screen.blit(icon, (x, y - 1))
            x += 24
        else:
            _line(screen, font, f"{label}:", x, y, (170, 170, 190))
            x += font.size(f"{label}:")[0] + 4
        text = str(value)
        _line(screen, font, text, x, y, cfg.C_TEXT)
        x += font.size(text)[0] + 16


def draw_msg(screen, text: str) -> None:
    font = fonts.get_font(20)
    _line(screen, font, text, 10, cfg.MAP_H * cfg.TILE + 64, (200, 200, 160))


def draw_map(
    surface,
    tiles,
    hero_anim,
    monsters_anim,
    d: Dungeon,
    hero,
    render_px,
    render_py,
    monsters,
    visible,
    mon_slide,
    npcs=None,
    npc_anim=None,
) -> None:
    floors = tiles["floor_variants"]
    walls = tiles["wall_variants"]
    nwall = len(walls)
    floor = floors[d.depth % len(floors)]  # one floor sprite per level, varies by depth
    stairs_up = tiles.get("stairs_up")
    for y in range(d.h):
        for x in range(d.w):
            r = pg.Rect(x * cfg.TILE, y * cfg.TILE, cfg.TILE, cfg.TILE)
            surface.blit(floor, r)
            t = d.grid[y][x]
            if t == WALL:
                surface.blit(walls[(x * 5 + y * 11) % nwall], r)
            elif t == CHEST:
                surface.blit(tiles["chest"], r)
            elif t == EXIT:
                surface.blit(tiles["stairs_down"], r)
            elif t == ENTRY and stairs_up:
                surface.blit(stairs_up, r)
            elif t == LOOT:
                surface.blit(tiles["coins"], r)
            elif t == POTION:
                surface.blit(tiles["potion"], r)
            if (x, y) in visible:
                d.seen[y][x] = True
    for (x, y), m in list(monsters.items()):
        if (x, y) in visible:
            a = monsters_anim.get(id(m))
            frame = a.get_frame() if a else None
            fx = mon_slide.get(id(m))
            offx = int((fx.ox if fx else 0.0) * cfg.TILE)
            offy = int((fx.oy if fx else 0.0) * cfg.TILE)
            _blit_shadow(surface, x * cfg.TILE, y * cfg.TILE)
            if frame:
                surface.blit(frame, (x * cfg.TILE + offx, y * cfg.TILE + offy))
    if npcs:
        for (x, y), kind in npcs.items():
            if (x, y) not in visible:
                continue
            _blit_shadow(surface, x * cfg.TILE, y * cfg.TILE)
            anim = npc_anim.get((x, y)) if npc_anim else None
            frame = anim.get_frame() if anim else None
            surface.blit(frame or _npc_marker(kind), (x * cfg.TILE, y * cfg.TILE))
    hpx, hpy = int(render_px * cfg.TILE), int(render_py * cfg.TILE)
    _blit_shadow(surface, hpx, hpy)
    hero_frame = hero_anim.get_frame()
    if hero_frame:
        surface.blit(hero_frame, (hpx, hpy))
    lighting.apply(surface, d, visible, render_px, render_py, cfg.FOV_RADIUS)


def _line(screen, font, text, x, y, col=(220, 220, 220)) -> None:
    fonts.draw_text(screen, font, text, x, y, col)


class Shake:
    """Decaying camera shake. trigger() on impact, offset() each frame."""

    def __init__(self):
        self.t = 0.0
        self.dur = 0.0
        self.mag = 0.0

    def trigger(self, mag: float = 6.0, dur: float = 0.18) -> None:
        self.mag = max(self.mag if self.t > 0 else 0.0, mag)
        self.dur = dur
        self.t = dur

    def update(self, dt: float) -> None:
        if self.t > 0:
            self.t = max(0.0, self.t - dt)
            if self.t == 0:
                self.mag = 0.0

    def offset(self) -> tuple[int, int]:
        if self.t <= 0:
            return (0, 0)
        amp = self.mag * (self.t / self.dur)
        return (random.randint(-int(amp), int(amp)), random.randint(-int(amp), int(amp)))


_flash_cache: pg.Surface | None = None


def draw_damage_flash(screen, frac: float) -> None:
    """Red full-screen flash; ``frac`` in (0, 1] is the remaining intensity."""
    global _flash_cache
    if _flash_cache is None:
        _flash_cache = pg.Surface((cfg.SCREEN_W, cfg.SCREEN_H))
        _flash_cache.fill((150, 20, 20))
    _flash_cache.set_alpha(int(110 * max(0.0, min(1.0, frac))))
    screen.blit(_flash_cache, (0, 0))
