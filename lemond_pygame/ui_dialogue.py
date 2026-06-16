"""Choice-based dialogue overlay for the named characters.

Walks a conversation from :mod:`core.dialogue`: shows the current node's line and
the options whose conditions are met, lets the player pick with Up/Down + Enter,
applies the option's effects (faction favor, granted artifact), and follows the
graph. Returns an ending token (only Rosmund triggers one) or None.
"""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core import dialogue as dlg
from .core.artifacts import make_artifact
from .core.loot import INVENTORY_LIMIT
from .ui_common import line, panel, wrap_text


def _grant(hero, artifact_id: str) -> None:
    if len(hero.inventory) < INVENTORY_LIMIT:
        tier = 1 + min(5, hero.depth // 2)
        hero.inventory.append(make_artifact(artifact_id, tier))


async def dialogue_screen(screen, who: str, hero) -> str | None:
    convo = dlg.CONVERSATIONS[who]
    name = i18n.t("dlg." + who + ".name")
    font = fonts.get_font(20)
    node_id = dlg.START

    while True:
        node = convo[node_id]
        options = dlg.visible_options(node, hero)
        body = wrap_text(font, i18n.t(node["text"]), cfg.SCREEN_W - 200)
        sel = 0

        # Inner loop: redraw + handle selection for the current node.
        while True:
            screen.fill(cfg.C_BG)
            rect = pg.Rect(70, 60, cfg.SCREEN_W - 140, cfg.SCREEN_H - 120)
            panel(screen, rect, name, icon="icon.language")
            y = rect.y + 54
            for ln in body:
                line(screen, font, ln, rect.x + 24, y, (225, 220, 235))
                y += 26
            y += 14
            for i, opt in enumerate(options):
                selected = i == sel
                if selected:
                    hl = pg.Rect(rect.x + 14, y - 3, rect.w - 28, 28)
                    pg.draw.rect(screen, (44, 46, 70), hl, border_radius=6)
                col = (245, 240, 200) if selected else (180, 185, 205)
                line(screen, font, f"{i + 1}. {i18n.t(opt['text'])}", rect.x + 26, y, col)
                y += 30
            line(
                screen,
                font,
                i18n.t("ui.dialogue.hint"),
                rect.x + 24,
                rect.bottom - 32,
                (160, 160, 200),
            )
            pg.display.flip()
            await asyncio.sleep(0)

            chosen = None
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    pg.quit()
                    raise SystemExit
                if e.type != pg.KEYDOWN:
                    continue
                if e.key == pg.K_UP:
                    sel = (sel - 1) % len(options)
                elif e.key == pg.K_DOWN:
                    sel = (sel + 1) % len(options)
                elif e.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
                    chosen = options[sel]
                elif pg.K_1 <= e.key <= pg.K_9 and e.key - pg.K_1 < len(options):
                    chosen = options[e.key - pg.K_1]
            if chosen is not None:
                break

        grant = dlg.apply_effects(hero, chosen)
        if grant:
            _grant(hero, grant)
        if chosen.get("ending"):
            return chosen["ending"]
        if chosen.get("goto") is None:
            if who in dlg.MET_FLAG:
                hero.flags[dlg.MET_FLAG[who]] = True
            return None
        node_id = chosen["goto"]
