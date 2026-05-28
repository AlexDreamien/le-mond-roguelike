"""Stats and skills windows; allocate points manually when auto-distribute is off."""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import progression
from .ui_common import icon_label, line, panel

_STAT_KEYS = {pg.K_1: "str", pg.K_2: "dex", pg.K_3: "int"}
_SKILL_KEYS = {pg.K_1: "MELEE", pg.K_2: "DODGE", pg.K_3: "MAGIC"}


async def stats_window(screen, hero, options=None) -> None:
    font = fonts.get_font(22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, cfg.SCREEN_H - 180)
    manual = options is not None and not options.get("auto_stats", True)
    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.stats.title"), icon="icon.stats")
        rows = [
            (
                "icon.levelup",
                i18n.t("ui.stats.level", level=hero.level, xp=hero.xp, next=hero.xp_to_next()),
            ),
            ("icon.str", i18n.t("ui.stats.str", value=hero.str_)),
            ("icon.dex", i18n.t("ui.stats.dex", value=hero.dex)),
            ("icon.int", i18n.t("ui.stats.int", value=hero.int_)),
            ("icon.hp", i18n.t("ui.stats.hp", hp=hero.hp, max=hero.max_hp)),
        ]
        y = rect.y + 50
        for key, text in rows:
            icon_label(screen, font, key, text, rect.x + 20, y, size=22)
            y += 32
        if manual:
            line(
                screen,
                font,
                i18n.t("ui.stats.points", n=hero.stat_points),
                rect.x + 20,
                y + 6,
                (200, 240, 200),
            )
        line(screen, font, i18n.t("ui.close_hint"), rect.x + 20, rect.bottom - 40, (160, 160, 200))
        pg.display.flip()
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_RETURN):
                    return
                if manual and e.key in _STAT_KEYS:
                    progression.add_stat(hero, _STAT_KEYS[e.key])


async def skills_window(screen, hero, options=None) -> None:
    font = fonts.get_font(22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, cfg.SCREEN_H - 180)
    manual = options is not None and not options.get("auto_skills", True)
    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.skills.title"), icon="icon.skills")
        rows = [
            ("icon.dmg", i18n.t("ui.skills.melee", value=hero.skills["MELEE"])),
            ("icon.dodge", i18n.t("ui.skills.dodge", value=hero.skills["DODGE"])),
            ("icon.magic", i18n.t("ui.skills.magic", value=hero.skills["MAGIC"])),
        ]
        y = rect.y + 50
        for key, text in rows:
            icon_label(screen, font, key, text, rect.x + 20, y, size=22)
            y += 32
        if manual:
            line(
                screen,
                font,
                i18n.t("ui.skills.points", n=hero.skill_points),
                rect.x + 20,
                y + 6,
                (200, 240, 200),
            )
        line(screen, font, i18n.t("ui.close_hint"), rect.x + 20, rect.bottom - 40, (160, 160, 200))
        pg.display.flip()
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_RETURN):
                    return
                if manual and e.key in _SKILL_KEYS:
                    progression.add_skill(hero, _SKILL_KEYS[e.key])
