"""Stats and skills windows; allocate points manually when auto-distribute is off."""

from __future__ import annotations

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import progression
from .ui_common import line, panel

_STAT_KEYS = {pg.K_1: "str", pg.K_2: "dex", pg.K_3: "int"}
_SKILL_KEYS = {pg.K_1: "MELEE", pg.K_2: "DODGE", pg.K_3: "MAGIC"}


def stats_window(screen, hero, options=None) -> None:
    font = fonts.get_font(22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, cfg.SCREEN_H - 180)
    manual = options is not None and not options.get("auto_stats", True)
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
        ]
        for s in rows:
            line(screen, font, s, rect.x + 20, y)
            y += 28
        if manual:
            line(
                screen,
                font,
                i18n.t("ui.stats.points", n=hero.stat_points),
                rect.x + 20,
                y + 8,
                (200, 240, 200),
            )
        line(screen, font, i18n.t("ui.close_hint"), rect.x + 20, rect.bottom - 40, (160, 160, 200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_RETURN):
                    return
                if manual and e.key in _STAT_KEYS:
                    progression.add_stat(hero, _STAT_KEYS[e.key])


def skills_window(screen, hero, options=None) -> None:
    font = fonts.get_font(22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, cfg.SCREEN_H - 180)
    manual = options is not None and not options.get("auto_skills", True)
    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.skills.title"))
        y = rect.y + 50
        line(
            screen,
            font,
            i18n.t(
                "ui.stats.skills",
                melee=hero.skills["MELEE"],
                dodge=hero.skills["DODGE"],
                magic=hero.skills["MAGIC"],
            ),
            rect.x + 20,
            y,
        )
        if manual:
            line(
                screen,
                font,
                i18n.t("ui.skills.points", n=hero.skill_points),
                rect.x + 20,
                y + 36,
                (200, 240, 200),
            )
        line(screen, font, i18n.t("ui.close_hint"), rect.x + 20, rect.bottom - 40, (160, 160, 200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_RETURN):
                    return
                if manual and e.key in _SKILL_KEYS:
                    progression.add_skill(hero, _SKILL_KEYS[e.key])
