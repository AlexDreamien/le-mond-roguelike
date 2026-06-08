"""Spellbook (B): choose which spell the F key casts.

Lists every unlocked spell with its damage, range, effect, and mana cost, and
shows the next spell to unlock (dimmed) with its requirement. The selected spell
is bound to the hero with Enter; F then casts it directly without a per-cast menu.
"""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import spells as sp
from .ui_common import line, panel


async def spellbook_screen(screen, hero) -> None:
    font = fonts.get_font(20)
    small = fonts.get_font(17)
    skill = hero.skills["MAGIC"]
    avail = sp.available_spells(skill) or [sp.SPELLS[0]]
    nxt = sp.next_locked(skill)
    sel = next((i for i, s in enumerate(avail) if s.key == hero.active_spell), 0)
    rect = pg.Rect(70, 50, cfg.SCREEN_W - 140, cfg.SCREEN_H - 120)

    while True:
        screen.fill(cfg.C_BG)
        panel(screen, rect, i18n.t("ui.spellbook.title"), icon="icon.magic")
        y = rect.y + 52
        for i, spell in enumerate(avail):
            name = i18n.t("magic.spell." + spell.key)
            dmg = sp.spell_damage(spell, hero.int_, skill)
            rng = sp.spell_range(spell, hero.int_)
            effect = i18n.t("magic.effect." + spell.key)
            selected = i == sel
            active = spell.key == hero.active_spell
            if selected:
                hl = pg.Rect(rect.x + 12, y - 4, rect.w - 24, 44)
                pg.draw.rect(screen, (44, 46, 70), hl, border_radius=6)
            head = f"{name}   {i18n.t('ui.spellbook.bound')}" if active else name
            line(
                screen, font, head, rect.x + 24, y, (235, 235, 245) if selected else (205, 210, 225)
            )
            params = i18n.t(
                "ui.spellbook.params", dmg=dmg, rng=rng, mana=spell.mana_cost, effect=effect
            )
            line(screen, small, params, rect.x + 36, y + 22, (165, 178, 200))
            y += 50
        if nxt:  # dim line: the next spell to unlock and its requirement
            y += 4
            locked = i18n.t(
                "ui.spellbook.next", name=i18n.t("magic.spell." + nxt.key), skill=nxt.min_skill
            )
            line(screen, small, locked, rect.x + 24, y, (110, 115, 138))
        line(
            screen,
            font,
            i18n.t("ui.spellbook.hint"),
            rect.x + 22,
            rect.bottom - 34,
            (160, 160, 200),
        )
        pg.display.flip()
        await asyncio.sleep(0)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type != pg.KEYDOWN:
                continue
            if e.key in (pg.K_ESCAPE, pg.K_b):
                return
            if e.key == pg.K_UP:
                sel = (sel - 1) % len(avail)
            elif e.key == pg.K_DOWN:
                sel = (sel + 1) % len(avail)
            elif e.key in (pg.K_RETURN, pg.K_KP_ENTER):
                hero.active_spell = avail[sel].key
