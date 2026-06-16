"""Full-screen ending. Shows the ending's title and body, then waits for a key.

Tinted per ending so the mood reads at a glance (gold for seizing the power,
cold blue for sealing, green for destroying, violet for the cult, warm for
Rosmund's redemption).
"""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .ui_common import wrap_text

_TINT = {
    "seize": (40, 32, 12),
    "destroy": (14, 30, 18),
    "seal": (14, 20, 36),
    "cult": (28, 14, 34),
    "redeem": (34, 26, 14),
}
_ACCENT = {
    "seize": (255, 205, 90),
    "destroy": (120, 220, 150),
    "seal": (130, 175, 245),
    "cult": (200, 140, 235),
    "redeem": (250, 220, 150),
}


async def ending_screen(screen, ending_id: str) -> None:
    title_font = fonts.get_font(40, bold=True)
    font = fonts.get_font(22)
    tint = _TINT.get(ending_id, (20, 20, 28))
    accent = _ACCENT.get(ending_id, (230, 230, 230))
    title = i18n.t("ending." + ending_id + ".title")
    body = wrap_text(font, i18n.t("ending." + ending_id + ".body"), cfg.SCREEN_W - 200)

    while True:
        screen.fill(tint)
        tsurf = title_font.render(title, True, accent)
        screen.blit(tsurf, tsurf.get_rect(centerx=cfg.SCREEN_W // 2, y=90))
        y = 200
        for ln in body:
            s = font.render(ln, True, (224, 222, 214))
            screen.blit(s, s.get_rect(centerx=cfg.SCREEN_W // 2, y=y))
            y += 30
        hint = font.render(i18n.t("ending.close"), True, (170, 170, 190))
        screen.blit(hint, hint.get_rect(centerx=cfg.SCREEN_W // 2, y=cfg.SCREEN_H - 70))
        pg.display.flip()
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN and e.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_ESCAPE):
                return
