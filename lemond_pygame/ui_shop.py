"""Merchant shop: sell inventory items and buy higher-tier gear for gold."""

from __future__ import annotations

from dataclasses import replace

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import economy
from .core.entities import random_item
from .core.loot import INVENTORY_LIMIT
from .ui_common import line, panel

STOCK_SIZE = 6


def shop_screen(screen, hero, depth) -> None:
    font = fonts.get_font(20)
    rect = pg.Rect(40, 40, cfg.SCREEN_W - 80, cfg.SCREEN_H - 120)
    stock = [random_item(economy.shop_tier(depth)) for _ in range(STOCK_SIZE)]
    col = 0  # 0 = sell (inventory), 1 = buy (stock)
    sel = [0, 0]
    msg = ""

    def clamp():
        sel[0] = max(0, min(sel[0], max(0, len(hero.inventory) - 1)))
        sel[1] = max(0, min(sel[1], max(0, len(stock) - 1)))

    def redraw():
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.shop.title"))
        line(
            screen,
            font,
            i18n.t("ui.gold", gold=hero.gold),
            rect.x + 16,
            rect.y + 10,
            (240, 220, 120),
        )
        lx = rect.x + 24
        rx = rect.x + rect.w // 2 + 12
        top = rect.y + 54
        line(screen, font, i18n.t("ui.shop.sell"), lx, top, (200, 210, 240))
        line(screen, font, i18n.t("ui.shop.buy"), rx, top, (200, 210, 240))
        y = top + 28
        if hero.inventory:
            for i, it in enumerate(hero.inventory):
                pre = "> " if (col == 0 and i == sel[0]) else "  "
                c = (220, 240, 220) if (col == 0 and i == sel[0]) else (220, 220, 220)
                text = f"{pre}{i18n.item_describe(it)}  [{economy.sell_price(it)}]"
                line(screen, font, text, lx, y + i * 22, c)
        else:
            line(screen, font, i18n.t("ui.shop.empty"), lx, y, (160, 160, 170))
        for i, it in enumerate(stock):
            pre = "> " if (col == 1 and i == sel[1]) else "  "
            c = (220, 240, 220) if (col == 1 and i == sel[1]) else (220, 220, 220)
            text = f"{pre}{i18n.item_describe(it)}  [{economy.buy_price(it)}]"
            line(screen, font, text, rx, y + i * 22, c)
        if msg:
            line(screen, font, msg, rect.x + 16, rect.bottom - 52, (200, 200, 160))
        line(screen, font, i18n.t("ui.shop.hint"), rect.x + 16, rect.bottom - 28, (160, 160, 200))
        pg.display.flip()

    redraw()
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type != pg.KEYDOWN:
                continue
            if e.key == pg.K_ESCAPE:
                return
            if e.key in (pg.K_TAB, pg.K_LEFT, pg.K_RIGHT):
                col = 1 - col
            elif e.key == pg.K_UP:
                sel[col] -= 1
                clamp()
            elif e.key == pg.K_DOWN:
                sel[col] += 1
                clamp()
            elif e.key in (pg.K_RETURN, pg.K_KP_ENTER):
                if col == 0 and hero.inventory:
                    it = hero.inventory.pop(sel[0])
                    price = economy.sell_price(it)
                    hero.gold += price
                    msg = i18n.t("msg.sold", item=i18n.item_name(it), gold=price)
                    clamp()
                elif col == 1 and stock:
                    it = stock[sel[1]]
                    price = economy.buy_price(it)
                    if hero.gold < price:
                        msg = i18n.t("msg.cant_afford")
                    elif len(hero.inventory) >= INVENTORY_LIMIT:
                        msg = i18n.t("msg.shop_full")
                    else:
                        hero.gold -= price
                        hero.inventory.append(replace(it))
                        msg = i18n.t("msg.bought", item=i18n.item_name(it), gold=price)
            redraw()
