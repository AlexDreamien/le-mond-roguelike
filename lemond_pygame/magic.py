"""Directional magic bolt cast by the hero."""

from __future__ import annotations

import pygame as pg

from . import i18n
from .core import config as cfg
from .core.dungeon import WALL
from .ui_common import line, panel

_DIR_KEYS = {
    pg.K_UP: (0, -1),
    pg.K_DOWN: (0, 1),
    pg.K_LEFT: (-1, 0),
    pg.K_RIGHT: (1, 0),
}


def do_cast(screen, draw_map_cb, draw_hud_cb, d, hero, hx, hy, monsters, visible) -> str:
    font = pg.font.SysFont(None, 20)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, 120)
    while True:
        draw_map_cb(visible)
        draw_hud_cb()
        panel(screen, rect, i18n.t("ui.magic.title"))
        line(screen, font, i18n.t("ui.magic.hint"), rect.x + 20, rect.y + 50)
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type != pg.KEYDOWN:
                continue
            if e.key == pg.K_ESCAPE:
                return i18n.t("msg.cancel")
            if e.key in _DIR_KEYS:
                dx, dy = _DIR_KEYS[e.key]
                spell_range = 3 + hero.int_ // 3
                dmg = 3 + hero.int_ + hero.skills["MAGIC"] * 2
                for i in range(1, spell_range + 1):
                    x, y = hx + dx * i, hy + dy * i
                    if not d.inside(x, y) or d.grid[y][x] == WALL:
                        break
                    if (x, y) in monsters:
                        m = monsters[(x, y)]
                        m.hp -= dmg
                        name = i18n.monster_name(m)
                        if m.hp <= 0:
                            return i18n.t("magic.spell_killed", name=name, dmg=dmg)
                        return i18n.t("magic.spell_hit", name=name, dmg=dmg)
                return i18n.t("magic.spell_miss")
