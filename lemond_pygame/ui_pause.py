"""Pause screen: minimap and scrollable event log."""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import progression
from .core.dungeon import CHEST, ENTRY, EXIT, FLOOR, LOOT, POTION, WALL
from .drawing import object_icon
from .ui_common import line, panel


def _draw_minimap_surface(d, hero_pos, monsters, size):
    w, h = d.w, d.h
    surf = pg.Surface(size)
    surf.fill((12, 12, 18))
    pad = 8
    avail_w = size[0] - pad * 2
    avail_h = size[1] - pad * 2
    tw = max(2, int(avail_w / w))
    th = max(2, int(avail_h / h))
    ox = (size[0] - w * tw) // 2
    oy = (size[1] - h * th) // 2
    for y in range(h):
        for x in range(w):
            if not d.seen[y][x]:
                continue
            t = d.grid[y][x]
            color = (26, 26, 34)
            if t == WALL:
                color = (90, 90, 110)
            elif t in (FLOOR, ENTRY):
                color = (36, 36, 46)
            elif t == EXIT:
                color = (40, 180, 180)
            elif t == CHEST:
                color = (210, 170, 40)
            elif t == LOOT:
                color = (200, 200, 120)
            elif t == POTION:
                color = (200, 110, 110)
            pg.draw.rect(surf, color, (ox + x * tw, oy + y * th, tw, th))
    for (mx, my), _m in monsters.items():
        if 0 <= mx < w and 0 <= my < h and d.seen[my][mx]:
            pg.draw.rect(surf, (200, 60, 60), (ox + mx * tw, oy + my * th, tw, th))
    hx, hy = hero_pos
    pg.draw.rect(surf, (60, 200, 120), (ox + hx * tw, oy + hy * th, tw, th))
    return surf


async def pause_screen(
    screen, d, hero, hero_pos, monsters, last_msg, event_log, on_save=None, options=None, music=None
) -> str:
    font = fonts.get_font(20)
    title_font = fonts.get_font(24, bold=True)
    outer = pg.Rect(30, 30, cfg.SCREEN_W - 60, cfg.SCREEN_H - 120)
    left = pg.Rect(outer.x + 14, outer.y + 64, int(outer.w * 0.48) - 20, outer.h - 200)
    right = pg.Rect(
        outer.x + int(outer.w * 0.52), outer.y + 64, int(outer.w * 0.48) - 20, outer.h - 200
    )

    lines = list(event_log) if event_log else []
    max_rows = max(4, (right.h - 20) // 18)
    offset = max(0, len(lines) - max_rows)

    def redraw():
        screen.fill(cfg.C_BG)
        panel(screen, outer, i18n.t("ui.pause.title"), icon="icon.pause")
        head = i18n.t(
            "ui.pause.header",
            name=hero.name,
            cls=i18n.class_name(hero.class_kind),
            level=hero.level,
            depth=d.depth,
            potions=hero.potions,
            gold=hero.gold,
        )
        line(screen, title_font, head, outer.x + 16, outer.y + 36, (210, 210, 240))
        pg.draw.rect(screen, (26, 26, 34), left, border_radius=8)
        pg.draw.rect(screen, (70, 70, 90), left, 1, border_radius=8)
        mm = _draw_minimap_surface(d, hero_pos, monsters, (left.w - 10, left.h - 10))
        screen.blit(mm, (left.x + 5, left.y + 5))
        pg.draw.rect(screen, (26, 26, 34), right, border_radius=8)
        pg.draw.rect(screen, (70, 70, 90), right, 1, border_radius=8)
        view = lines[offset : offset + max_rows]
        y = right.y + 8
        for s in view:
            line(screen, font, s, right.x + 10, y, (220, 220, 230))
            y += 18

        # Settings group: one clearly labelled column of toggles.
        line(
            screen,
            font,
            i18n.t("ui.pause.settings"),
            outer.x + 16,
            outer.bottom - 132,
            (190, 200, 230),
        )
        if options is not None:
            on = (200, 240, 200)
            off = (170, 170, 180)
            rows = [
                ("auto_stats", "ui.pause.auto_stats", "1", None),
                ("auto_skills", "ui.pause.auto_skills", "2", None),
                ("music", "ui.pause.music", "3", "music"),
            ]
            for i, (key, label_key, hint, extra) in enumerate(rows):
                value = options.get(key, True)
                ry = outer.bottom - 106 + i * 24
                x = outer.x + 32
                cb = object_icon("ui.checkbox_on" if value else "ui.checkbox_off", 18)
                if cb:
                    screen.blit(cb, (x, ry + 1))
                    x += 24
                label = f"{i18n.t(label_key)} ({hint})"
                line(screen, font, label, x, ry, on if value else off)
                if extra == "music":
                    mi = object_icon("icon.music_on" if value else "icon.music_off", 18)
                    if mi:
                        screen.blit(mi, (x + font.size(label)[0] + 8, ry))

        line(
            screen, font, i18n.t("ui.pause.hint"), outer.x + 16, outer.bottom - 26, (160, 160, 200)
        )
        pg.display.flip()

    redraw()
    while True:
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                if on_save:
                    on_save()
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_p):
                    return "resume"
                if e.key == pg.K_s and on_save:
                    on_save()
                if options is not None and e.key == pg.K_1:
                    options["auto_stats"] = not options["auto_stats"]
                    if options["auto_stats"]:
                        progression.auto_assign(hero, do_stats=True, do_skills=False)
                    redraw()
                if options is not None and e.key == pg.K_2:
                    options["auto_skills"] = not options["auto_skills"]
                    if options["auto_skills"]:
                        progression.auto_assign(hero, do_stats=False, do_skills=True)
                    redraw()
                if options is not None and e.key == pg.K_3:
                    options["music"] = not options.get("music", True)
                    if music is not None:
                        music.set_enabled(options["music"])
                    redraw()
                if e.key == pg.K_UP:
                    offset = max(0, offset - 1)
                    redraw()
                if e.key == pg.K_DOWN:
                    offset = min(max(0, len(lines) - max_rows), offset + 1)
                    redraw()
                if e.key == pg.K_PAGEUP:
                    offset = max(0, offset - max_rows)
                    redraw()
                if e.key == pg.K_PAGEDOWN:
                    offset = min(max(0, len(lines) - max_rows), offset + max_rows)
                    redraw()
                if e.key == pg.K_HOME:
                    offset = 0
                    redraw()
                if e.key == pg.K_END:
                    offset = max(0, len(lines) - max_rows)
                    redraw()
