"""Start menu: save slots, class selection, and language switch."""

from __future__ import annotations

import pygame as pg

from . import i18n
from .core import config as cfg
from .core.entities import Hero, Item
from .storage import DEFAULT_OPTIONS, delete_save, list_saves, load_hero, save_hero
from .ui_common import line, panel, prompt_yes_no

# class_kind -> (stats, skill, starting weapon kind)
CLASSES = [
    ("warrior", {"STR": 10, "DEX": 4, "INT": 1}, "MELEE", "sword"),
    ("thief", {"STR": 5, "DEX": 10, "INT": 5}, "DODGE", "dagger"),
    ("mage", {"STR": 3, "DEX": 2, "INT": 10}, "MAGIC", "staff"),
]


def _slot_rect(i):
    return pg.Rect(60, 60 + (i - 1) * 90, cfg.SCREEN_W - 120, 72)


def _del_rect(r):
    return pg.Rect(r.right - 120, r.y + 18, 100, 36)


def _lang_rect():
    return pg.Rect(cfg.SCREEN_W - 260, 14, 240, 28)


def _draw_slot(screen, font, info):
    r = _slot_rect(info["slot"])
    pg.draw.rect(screen, (30, 30, 40), r, border_radius=8)
    pg.draw.rect(screen, (70, 70, 90), r, 1, border_radius=8)
    if info["exists"]:
        text = i18n.t(
            "ui.start.slot",
            slot=info["slot"],
            name=info["name"],
            cls=i18n.class_name(info["class_kind"]),
            level=info["level"],
            depth=info["depth"],
        )
        line(screen, font, text, r.x + 12, r.y + 12)
        dr = _del_rect(r)
        pg.draw.rect(screen, (120, 60, 60), dr, border_radius=6)
        pg.draw.rect(screen, (200, 120, 120), dr, 1, border_radius=6)
        line(screen, font, i18n.t("ui.start.delete"), dr.x + 16, dr.y + 10, (250, 230, 230))
    else:
        line(
            screen,
            font,
            i18n.t("ui.start.new_slot", slot=info["slot"]),
            r.x + 12,
            r.y + 22,
            (200, 220, 200),
        )


def _toggle_language():
    i18n.set_locale(i18n.next_locale())


def class_select(screen):
    font = pg.font.SysFont(None, 24)
    rect = pg.Rect(60, 60, cfg.SCREEN_W - 120, cfg.SCREEN_H - 160)
    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.class.title"))
        w = (rect.w - 40) // 3
        cards = []
        for i, (class_kind, stats, _skill, weapon_kind) in enumerate(CLASSES):
            r = pg.Rect(rect.x + 20 + i * w, rect.y + 60, w - 20, 180)
            cards.append((r, class_kind))
            pg.draw.rect(screen, (26, 26, 34), r, border_radius=8)
            pg.draw.rect(screen, (70, 70, 90), r, 1, border_radius=8)
            line(screen, font, i18n.class_name(class_kind), r.x + 12, r.y + 10, (220, 220, 240))
            line(screen, font, f"{i18n.t('stat.str')}: {stats['STR']}", r.x + 12, r.y + 44)
            line(screen, font, f"{i18n.t('stat.dex')}: {stats['DEX']}", r.x + 12, r.y + 68)
            line(screen, font, f"{i18n.t('stat.int')}: {stats['INT']}", r.x + 12, r.y + 92)
            line(
                screen,
                font,
                i18n.t(f"class.{class_kind}.perk"),
                r.x + 12,
                r.y + 124,
                (200, 210, 200),
            )
            weapon = f"{i18n.t('item.' + weapon_kind)} 1"
            line(
                screen,
                font,
                i18n.t("class.start", item=weapon),
                r.x + 12,
                r.y + 148,
                (200, 210, 200),
            )
        line(screen, font, i18n.t("ui.class.hint"), rect.x + 20, rect.bottom - 36, (160, 160, 200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                return None
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                for r, class_kind in cards:
                    if r.collidepoint(e.pos):
                        return class_kind


def create_hero_for_class(class_kind: str) -> Hero:
    stats, skill, weapon_kind = next((s, sk, wk) for (ck, s, sk, wk) in CLASSES if ck == class_kind)
    h = Hero(
        kind="hero",
        max_hp=16,
        hp=16,
        str_=stats["STR"],
        dex=stats["DEX"],
        int_=stats["INT"],
        glyph="hero",
        name="Gustav",
        class_kind=class_kind,
    )
    h.skills[skill] = 1
    h.recompute_max_hp()
    h.hp = h.max_hp
    h.depth = 1
    h.unlocked_depth = 1
    h.potions = 1
    h.equip(Item(kind=weapon_kind, slot="MAIN", tier=1, power=1, two_handed=False), to_slot="MAIN")
    return h


def start_menu(screen, sounds):
    font = pg.font.SysFont(None, 24)
    title_font = pg.font.SysFont(None, 36)
    while True:
        screen.fill(cfg.C_BG)
        line(screen, title_font, i18n.t("ui.start.title"), 60, 16, (210, 210, 240))
        lang_name = i18n.LOCALE_NAMES.get(i18n.get_locale(), i18n.get_locale())
        lr = _lang_rect()
        pg.draw.rect(screen, (30, 30, 40), lr, border_radius=6)
        pg.draw.rect(screen, (70, 70, 90), lr, 1, border_radius=6)
        line(
            screen,
            font,
            i18n.t("ui.start.language", name=lang_name),
            lr.x + 8,
            lr.y + 4,
            (200, 210, 240),
        )
        panel(
            screen, pg.Rect(40, 40, cfg.SCREEN_W - 80, cfg.SCREEN_H - 120), i18n.t("ui.start.panel")
        )
        infos = list_saves()
        rects = []
        for info in infos:
            _draw_slot(screen, font, info)
            rects.append((_slot_rect(info["slot"]), info))
        line(screen, font, i18n.t("ui.start.hint"), 60, cfg.SCREEN_H - 60, (160, 160, 200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_ESCAPE:
                    pg.quit()
                    raise SystemExit
                if e.key == pg.K_l:
                    _toggle_language()
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if _lang_rect().collidepoint(e.pos):
                    _toggle_language()
                    continue
                for r, info in rects:
                    if not r.collidepoint(e.pos):
                        continue
                    if info.get("exists") and _del_rect(r).collidepoint(e.pos):
                        if prompt_yes_no(
                            screen, i18n.t("ui.start.delete_confirm", slot=info["slot"])
                        ):
                            delete_save(info["slot"])
                        break
                    if info.get("exists"):
                        hero, opts = load_hero(info["slot"])
                        if hero is None:
                            break
                        i18n.set_locale(opts.get("language", i18n.get_locale()))
                        sounds["open"].play()
                        return info["slot"], hero, opts
                    class_kind = class_select(screen)
                    if not class_kind:
                        break
                    hero = create_hero_for_class(class_kind)
                    opts = dict(DEFAULT_OPTIONS)
                    opts["language"] = i18n.get_locale()
                    save_hero(info["slot"], hero, opts)
                    sounds["open"].play()
                    return info["slot"], hero, opts
