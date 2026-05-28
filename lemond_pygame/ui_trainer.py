"""Trainer: buy stat and skill points for gold (expensive)."""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import economy, progression
from .ui_common import icon_label, line, panel


async def trainer_screen(screen, hero, options) -> None:
    font = fonts.get_font(22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W - 160, cfg.SCREEN_H - 200)
    msg = ""

    def redraw():
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.trainer.title"), icon="icon.str")
        icon_label(
            screen,
            font,
            "icon.gold",
            i18n.t("ui.gold", gold=hero.gold),
            rect.right - 180,
            rect.y + 12,
            (240, 220, 120),
        )
        y = rect.y + 64
        icon_label(
            screen,
            font,
            "icon.str",
            i18n.t(
                "ui.trainer.buy_stat", cost=economy.stat_point_cost(hero), points=hero.stat_points
            ),
            rect.x + 20,
            y,
            size=22,
        )
        icon_label(
            screen,
            font,
            "icon.skills",
            i18n.t(
                "ui.trainer.buy_skill",
                cost=economy.skill_point_cost(hero),
                points=hero.skill_points,
            ),
            rect.x + 20,
            y + 36,
            size=22,
        )
        if msg:
            line(screen, font, msg, rect.x + 20, rect.bottom - 60, (200, 200, 160))
        line(
            screen, font, i18n.t("ui.trainer.hint"), rect.x + 20, rect.bottom - 30, (160, 160, 200)
        )
        pg.display.flip()

    redraw()
    while True:
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type != pg.KEYDOWN:
                continue
            if e.key == pg.K_ESCAPE:
                return
            if e.key == pg.K_1:
                cost = economy.stat_point_cost(hero)
                if hero.gold < cost:
                    msg = i18n.t("msg.cant_afford")
                else:
                    hero.gold -= cost
                    hero.stat_points += 1
                    if options is not None and options.get("auto_stats", True):
                        progression.auto_assign(hero, do_stats=True, do_skills=False)
                    msg = i18n.t("msg.trained", points=hero.stat_points)
            elif e.key == pg.K_2:
                cost = economy.skill_point_cost(hero)
                if hero.gold < cost:
                    msg = i18n.t("msg.cant_afford")
                else:
                    hero.gold -= cost
                    hero.skill_points += 1
                    if options is not None and options.get("auto_skills", True):
                        progression.auto_assign(hero, do_stats=False, do_skills=True)
                    msg = i18n.t("msg.trained", points=hero.skill_points)
            redraw()
