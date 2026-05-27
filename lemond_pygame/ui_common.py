"""Shared UI primitives: text, panels, message box, and a yes/no prompt."""

from __future__ import annotations

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .drawing import object_icon


def line(screen, font, text, x, y, col=(220, 220, 220)) -> None:
    fonts.draw_text(screen, font, text, x, y, col)


def icon_label(screen, font, icon_key, text, x, y, col=(220, 220, 220), size=18, gap=6) -> int:
    """Draw an atlas icon (with text fallback) then ``text``; return the next x."""
    icon = object_icon(icon_key, size)
    if icon:
        screen.blit(icon, (x, y + max(0, (font.get_height() - size) // 2)))
        x += size + gap
    if text:
        line(screen, font, text, x, y, col)
        x += font.size(text)[0]
    return x


def panel(screen, rect, title=None, icon=None) -> None:
    pg.draw.rect(screen, cfg.C_PANEL, rect, border_radius=8)
    pg.draw.rect(screen, cfg.C_PANEL_BORDER, rect, 1, border_radius=8)
    if title:
        font = fonts.get_font(22, bold=True)
        tx = rect.x + 10
        ic = object_icon(icon, 22) if icon else None
        if ic:
            screen.blit(ic, (tx, rect.y + 7))
            tx += 28
        line(screen, font, title, tx, rect.y + 8, (200, 200, 240))


def message_box(screen, lines) -> None:
    font = fonts.get_font(22)
    w = max(400, max(font.size(s)[0] for s in lines) + 40)
    h = 60 + 26 * len(lines)
    rect = pg.Rect((cfg.SCREEN_W - w) // 2, (cfg.SCREEN_H - h) // 2, w, h)
    panel(screen, rect, i18n.t("ui.message.title"))
    y = rect.y + 40
    for s in lines:
        line(screen, font, s, rect.x + 20, y)
        y += 26
    line(
        screen,
        font,
        i18n.t("ui.message.close_hint"),
        rect.x + 20,
        rect.bottom - 28,
        (160, 160, 200),
    )
    pg.display.flip()
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN and e.key in (pg.K_RETURN, pg.K_ESCAPE):
                return


def prompt_yes_no(screen, text: str) -> bool:
    font = fonts.get_font(22)
    w = max(420, font.size(text)[0] + 60)
    h = 140
    rect = pg.Rect((cfg.SCREEN_W - w) // 2, (cfg.SCREEN_H - h) // 2, w, h)
    panel(screen, rect, i18n.t("ui.confirm.title"))
    line(screen, font, text, rect.x + 20, rect.y + 48)
    line(screen, font, i18n.t("ui.confirm.hint"), rect.x + 20, rect.bottom - 30, (160, 160, 200))
    pg.display.flip()
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_y, pg.K_RETURN):
                    return True
                if e.key in (pg.K_n, pg.K_ESCAPE):
                    return False
