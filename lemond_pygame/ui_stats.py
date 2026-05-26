"""Stats and skills windows."""

from __future__ import annotations

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .ui_common import line, panel


def stats_window(screen, hero) -> str:
    font = fonts.get_font(22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, cfg.SCREEN_H - 180)
    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.stats.title"))
        y = rect.y + 50
        rows = [
            i18n.t("ui.stats.level", level=hero.level, xp=hero.xp, next=hero.xp_to_next()),
            i18n.t("ui.stats.str", value=hero.str_),
            i18n.t("ui.stats.dex", value=hero.dex),
            i18n.t("ui.stats.int", value=hero.int_),
            i18n.t("ui.stats.hp", hp=hero.hp, max=hero.max_hp),
            i18n.t(
                "ui.stats.skills",
                melee=hero.skills["MELEE"],
                dodge=hero.skills["DODGE"],
                magic=hero.skills["MAGIC"],
            ),
        ]
        for s in rows:
            line(screen, font, s, rect.x + 20, y)
            y += 28
        line(screen, font, i18n.t("ui.close_hint"), rect.x + 20, rect.bottom - 40, (160, 160, 200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN and e.key in (pg.K_ESCAPE, pg.K_RETURN):
                return "OK"


def skills_window(screen, hero) -> str:
    return i18n.t("ui.skills.auto")
