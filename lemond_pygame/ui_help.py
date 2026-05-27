"""Help overlay (H): all controls and hotkeys, grouped, with icons."""

from __future__ import annotations

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .drawing import object_icon
from .ui_common import icon_label, line, panel

# (icon_key | "section" | None, text_key, key_label)
_ROWS = [
    ("section", "ui.help.sec_move", None),
    ("arrows", "ui.help.move", None),
    ("section", "ui.help.sec_actions", None),
    ("icon.grab", "ui.help.grab", "G"),
    ("icon.drink", "ui.help.drink", "Z"),
    ("icon.magic", "ui.help.magic", "F"),
    ("section", "ui.help.sec_menus", None),
    ("icon.inventory", "ui.help.inventory", "I"),
    ("icon.stats", "ui.help.stats", "S"),
    ("icon.skills", "ui.help.skills", "K"),
    ("icon.options", "ui.help.options", "O"),
    ("icon.pause", "ui.help.pause", "P"),
    (None, "ui.help.help", "H"),
    ("icon.language", "ui.help.language", "L"),
    ("icon.quit", "ui.help.quit", "Q"),
]


def _key_box(screen, font, label, x, y) -> None:
    box = pg.Rect(x, y - 2, 30, 24)
    pg.draw.rect(screen, (40, 40, 52), box, border_radius=4)
    pg.draw.rect(screen, (80, 80, 100), box, 1, border_radius=4)
    surf = font.render(label, True, (225, 225, 235))
    screen.blit(surf, surf.get_rect(center=box.center))


def help_screen(screen) -> None:
    font = fonts.get_font(20)
    section_font = fonts.get_font(22, bold=True)
    rect = pg.Rect(140, 50, cfg.SCREEN_W - 280, cfg.SCREEN_H - 120)
    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.help.title"), icon="icon.options")
        x = rect.x + 26
        y = rect.y + 54
        for icon_key, text_key, key_label in _ROWS:
            if icon_key == "section":
                y += 6
                line(screen, section_font, i18n.t(text_key), x, y, (190, 205, 240))
                y += 30
                continue
            if key_label:
                _key_box(screen, font, key_label, x, y)
            tx = x + 42
            if icon_key == "arrows":
                for arrow in ("ui.arrow_up", "ui.arrow_down", "ui.arrow_left", "ui.arrow_right"):
                    ic = object_icon(arrow, 18)
                    if ic:
                        screen.blit(ic, (tx, y))
                        tx += 20
                line(screen, font, i18n.t(text_key), tx + 8, y)
            elif icon_key:
                icon_label(screen, font, icon_key, i18n.t(text_key), tx, y, size=20)
            else:
                line(screen, font, i18n.t(text_key), tx, y)
            y += 30
        line(screen, font, i18n.t("ui.help.close"), rect.x + 26, rect.bottom - 36, (160, 160, 200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN and e.key in (pg.K_ESCAPE, pg.K_h, pg.K_RETURN):
                return
