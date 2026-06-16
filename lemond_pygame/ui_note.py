"""Reading overlay for explorer notes and wall inscriptions.

A parchment-styled panel with a word-wrapped body. Used when the hero steps onto
a lore tile; closes on any key. Inscriptions get a stonier tint than paper notes.
"""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg


def _wrap(font, text: str, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if font.size(trial)[0] <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


async def note_screen(screen, title: str, body: str, inscription: bool = False) -> None:
    title_font = fonts.get_font(24, bold=True)
    font = fonts.get_font(20)
    w = min(cfg.SCREEN_W - 160, 680)
    inner_w = w - 56
    body_lines = _wrap(font, body, inner_w)
    h = 130 + len(body_lines) * 26
    rect = pg.Rect((cfg.SCREEN_W - w) // 2, (cfg.SCREEN_H - h) // 2, w, h)

    paper = (54, 44, 32) if inscription else (60, 54, 38)
    border = (120, 110, 80) if inscription else (150, 130, 80)
    ink = (210, 200, 175)
    head_col = (200, 200, 220) if inscription else (235, 220, 160)

    while True:
        screen.fill(cfg.C_BG)
        pg.draw.rect(screen, paper, rect, border_radius=10)
        pg.draw.rect(screen, border, rect, 2, border_radius=10)
        head = i18n.t("ui.note.inscription" if inscription else "ui.note.title")
        fonts.draw_text(screen, title_font, head, rect.x + 28, rect.y + 18, head_col)
        if title:
            fonts.draw_text(screen, font, title, rect.x + 28, rect.y + 50, (170, 160, 140))
        y = rect.y + 84
        for ln in body_lines:
            fonts.draw_text(screen, font, ln, rect.x + 28, y, ink)
            y += 26
        fonts.draw_text(
            screen, font, i18n.t("ui.note.close"), rect.x + 28, rect.bottom - 34, (150, 140, 110)
        )
        pg.display.flip()
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                return
