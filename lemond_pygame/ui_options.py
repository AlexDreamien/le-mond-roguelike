"""Options screen: animation speed, particle intensity, volume, and language."""

from __future__ import annotations

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .ui_common import icon_label, line, panel

NUMERIC = [
    ("ui.options.anim_speed", "anim_speed", 0.5, 2.0, 0.1),
    ("ui.options.particles", "particles", 0.0, 2.0, 0.1),
    ("ui.options.volume", "volume", 0.0, 1.0, 0.05),
]


def options_screen(screen, options: dict, apply_fn) -> str:
    font = fonts.get_font(20)
    rect = pg.Rect(70, 70, cfg.SCREEN_W - 140, cfg.SCREEN_H - 180)
    idx = 0
    row_count = len(NUMERIC) + 1  # numeric rows + language row
    lang_idx = len(NUMERIC)

    def value_bar(x, y, w, h, v, vmin, vmax):
        pg.draw.rect(screen, (30, 30, 40), (x, y, w, h), border_radius=4)
        t = (v - vmin) / (vmax - vmin)
        pg.draw.rect(
            screen, (90, 140, 200), (x + 2, y + 2, int((w - 4) * t), h - 4), border_radius=4
        )

    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.options.title"), icon="icon.options")
        y = rect.y + 60
        for i, (label_key, key, vmin, vmax, _step) in enumerate(NUMERIC):
            r = pg.Rect(rect.x + 30, y, rect.w - 60, 46)
            pg.draw.rect(screen, (26, 26, 34), r, border_radius=6)
            pg.draw.rect(screen, (70, 70, 90), r, 1, border_radius=6)
            color = (220, 220, 220) if i != idx else (200, 240, 200)
            line(screen, font, f"{i18n.t(label_key)}: {options[key]:.2f}", r.x + 10, r.y + 8, color)
            value_bar(r.x + 10, r.y + 24, r.w - 20, 12, options[key], vmin, vmax)
            y += 54
        # Language row
        r = pg.Rect(rect.x + 30, y, rect.w - 60, 46)
        pg.draw.rect(screen, (26, 26, 34), r, border_radius=6)
        pg.draw.rect(screen, (70, 70, 90), r, 1, border_radius=6)
        color = (220, 220, 220) if idx != lang_idx else (200, 240, 200)
        lang_name = i18n.LOCALE_NAMES.get(i18n.get_locale(), i18n.get_locale())
        icon_label(
            screen,
            font,
            "icon.language",
            f"{i18n.t('ui.options.language')}: {lang_name}",
            r.x + 10,
            r.y + 14,
            color,
        )

        line(
            screen, font, i18n.t("ui.options.hint"), rect.x + 30, rect.bottom - 40, (160, 160, 200)
        )
        pg.display.flip()

        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type != pg.KEYDOWN:
                continue
            if e.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_KP_ENTER):
                return i18n.t("msg.done")
            if e.key == pg.K_UP:
                idx = (idx - 1) % row_count
            elif e.key == pg.K_DOWN:
                idx = (idx + 1) % row_count
            elif e.key in (pg.K_LEFT, pg.K_RIGHT):
                if idx == lang_idx:
                    code = i18n.next_locale()
                    i18n.set_locale(code)
                    options["language"] = code
                    apply_fn(options)
                else:
                    _, key, vmin, vmax, step = NUMERIC[idx]
                    delta = -step if e.key == pg.K_LEFT else step
                    options[key] = max(vmin, min(vmax, round(options[key] + delta, 2)))
                    apply_fn(options)
            elif e.key == pg.K_r:
                options["anim_speed"] = 1.0
                options["particles"] = 1.0
                options["volume"] = 0.7
                apply_fn(options)
