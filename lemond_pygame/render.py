"""Rendering layer: animation state and all map/HUD drawing.

Depends on :mod:`core` for data and geometry but owns no game rules. The game
loop feeds it state each frame.
"""

from __future__ import annotations

import math

import pygame as pg

from . import i18n
from .core import config as cfg
from .core.combat import dodge_chance
from .core.dungeon import CHEST, EXIT, WALL, Dungeon
from .core.entities import Hero


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
        if facing in ("left", "right"):
            self.facing = facing

    def set(self, state: str, one_shot: bool = False, queue_to: str = "idle") -> None:
        if self.state != state:
            self.state = state
            self.frame = 0
            self.timer = 0.0
        self.one_shot = one_shot
        self._queued = queue_to if one_shot else None

    def _frames_for_state(self):
        key = f"{self.state}_{self.facing}"
        return (
            self.sheets.get(key)
            or self.sheets.get(self.state)
            or self.sheets.get("idle_right")
            or self.sheets.get("idle_left")
        )

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
    font = pg.font.SysFont(None, 20)
    draw_hp_bar(screen, 10, top + 10, 260, 18, hero.hp, hero.max_hp)
    _line(screen, font, f"HP: {hero.hp}/{hero.max_hp}", 16, top + 11, (0, 0, 0))
    dmg_min, dmg_max = hero.weapon_damage()
    dodge = int(dodge_chance(hero, hero.skills["DODGE"]) * 100)
    hud = (
        f"Lv{hero.level}  "
        f"{i18n.t('stat.str')}:{hero.str_} {i18n.t('stat.dex')}:{hero.dex} "
        f"{i18n.t('stat.int')}:{hero.int_}  "
        f"ARM:{hero.total_armor()}  DMG:{dmg_min}-{dmg_max}  DODGE:{dodge}%  "
        f"XP:{hero.xp}/{hero.xp_to_next()}  {i18n.t('hud.potions')}:{hero.potions}"
    )
    _line(screen, font, hud, 10, top + 36, cfg.C_TEXT)


def draw_msg(screen, text: str) -> None:
    font = pg.font.SysFont(None, 20)
    _line(screen, font, text, 10, cfg.MAP_H * cfg.TILE + 64, (200, 200, 160))


def draw_map(
    screen,
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
) -> None:
    for y in range(d.h):
        for x in range(d.w):
            r = pg.Rect(x * cfg.TILE, y * cfg.TILE, cfg.TILE, cfg.TILE)
            screen.blit(tiles["floor"], r)
            t = d.grid[y][x]
            if t == WALL:
                screen.blit(tiles["wall"], r)
            elif t == CHEST:
                screen.blit(tiles["chest"], r)
            elif t == EXIT:
                screen.blit(tiles["exit"], r)
            if (x, y) not in visible:
                screen.blit(tiles["shadow_hard"] if not d.seen[y][x] else tiles["shadow_soft"], r)
            else:
                d.seen[y][x] = True
    for (x, y), m in list(monsters.items()):
        if (x, y) in visible:
            a = monsters_anim.get(id(m))
            frame = a.get_frame() if a else None
            fx = mon_slide.get(id(m))
            offx = int((fx.ox if fx else 0.0) * cfg.TILE)
            offy = int((fx.oy if fx else 0.0) * cfg.TILE)
            r = pg.Rect(x * cfg.TILE + offx, y * cfg.TILE + offy, cfg.TILE, cfg.TILE)
            if frame:
                screen.blit(frame, r)
    r = pg.Rect(int(render_px * cfg.TILE), int(render_py * cfg.TILE), cfg.TILE, cfg.TILE)
    screen.blit(hero_anim.get_frame(), r)


def _line(screen, font, text, x, y, col=(220, 220, 220)) -> None:
    screen.blit(font.render(text, True, col), (x, y))
