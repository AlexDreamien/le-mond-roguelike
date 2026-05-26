"""Inventory screen: view equipment, equip items, drop items."""

from __future__ import annotations

import pygame as pg

from . import i18n
from .core import config as cfg
from .core.entities import EQUIP_SLOTS
from .ui_common import line, panel


def inventory_screen(screen, hero) -> str:
    font = pg.font.SysFont(None, 20)
    rect = pg.Rect(60, 60, cfg.SCREEN_W - 120, cfg.SCREEN_H - 140)
    sel = 0

    def redraw():
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.inventory.title"))
        x = rect.x + 16
        y = rect.y + 46
        line(screen, font, i18n.t("ui.inventory.equipment"), x, y, (200, 210, 240))
        y += 22
        for slot in EQUIP_SLOTS:
            it = hero.equipment.get(slot)
            name = i18n.item_name(it) if it else i18n.t("ui.inventory.empty")
            line(screen, font, f"{slot:>4}: {name}", x, y)
            y += 20
        y += 8
        line(screen, font, i18n.t("ui.inventory.items_hint"), x, y, (200, 210, 240))
        y += 24
        for i, it in enumerate(hero.inventory):
            pre = "> " if i == sel else "  "
            col = (220, 240, 220) if i == sel else (220, 220, 220)
            line(screen, font, pre + i18n.item_describe(it), x, y, col)
            y += 20
        line(screen, font, i18n.t("ui.inventory.close_hint"), x, rect.bottom - 36, (160, 160, 200))
        pg.display.flip()

    redraw()
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_ESCAPE:
                    return i18n.t("msg.closed")
                if e.key == pg.K_UP:
                    sel = max(0, sel - 1)
                    redraw()
                if e.key == pg.K_DOWN:
                    sel = min(max(0, len(hero.inventory) - 1), sel + 1)
                    redraw()
                if e.key in (pg.K_RETURN, pg.K_KP_ENTER) and 0 <= sel < len(hero.inventory):
                    it = hero.inventory.pop(sel)
                    status = hero.equip(it, to_slot=it.slot)
                    redraw()
                    return i18n.t(status, item=i18n.item_name(it))
                if e.key in (pg.K_DELETE, pg.K_BACKSPACE) and 0 <= sel < len(hero.inventory):
                    hero.inventory.pop(sel)
                    redraw()
                    return i18n.t("msg.dropped")
