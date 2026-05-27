"""Render one representative gameplay frame to a PNG (no real display needed).

Usage:
    python tools/capture_screenshot.py [output_path]

Runs headless with the SDL dummy drivers so it works in CI and over SSH.
"""

from __future__ import annotations

import os
import random
import sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame as pg  # noqa: E402

from lemond_pygame import i18n  # noqa: E402
from lemond_pygame.core import config as cfg  # noqa: E402
from lemond_pygame.core.combat import generate_monster  # noqa: E402
from lemond_pygame.core.dungeon import Dungeon  # noqa: E402
from lemond_pygame.core.entities import Hero, Item  # noqa: E402
from lemond_pygame.drawing import (  # noqa: E402
    build_animsets_from_atlas,
    build_creature_animsets,
    build_hero_animset,
    build_tiles,
)
from lemond_pygame.render import AnimState, SlideFX, draw_hud, draw_map, draw_msg  # noqa: E402


def main(out_path: str) -> None:
    pg.init()
    screen = pg.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
    i18n.load_locales()
    i18n.set_locale("en")
    random.seed(7)

    tiles = build_tiles()
    animsets = build_animsets_from_atlas()
    hero_art = build_hero_animset()
    if hero_art:
        animsets["hero"] = hero_art
    animsets.update(build_creature_animsets("monsters"))
    npc_art = build_creature_animsets("npc")
    animsets.update(npc_art)
    d = Dungeon(cfg.MAP_W, cfg.MAP_H, depth=1)
    d.generate()
    monsters = {pos: generate_monster(1) for pos in d.monsters}

    hero = Hero(
        kind="hero",
        max_hp=36,
        hp=30,
        str_=10,
        dex=4,
        int_=1,
        glyph="hero",
        name="Gustav",
        class_kind="warrior",
    )
    hero.equip(Item(kind="sword", slot="MAIN", tier=1, power=1), to_slot="MAIN")
    hero.level = 2
    hero.xp = 10
    hero.potions = 2
    hero.gold = 120

    hero_anim = AnimState(animsets["hero"])
    monsters_anim = {
        id(m): AnimState(animsets.get(m.glyph) or animsets["goblin"]) for m in monsters.values()
    }
    mon_slide = {id(m): SlideFX() for m in monsters.values()}

    hx, hy = d.entry
    for y in range(d.h):
        for x in range(d.w):
            d.seen[y][x] = True
    visible = {(x, y) for y in range(d.h) for x in range(d.w)}

    # Showcase a merchant and a trainer on free floor tiles.
    free = [
        (x, y)
        for (x, y) in ((c % cfg.MAP_W, c // cfg.MAP_W) for c in range(cfg.MAP_W * cfg.MAP_H))
        if d.grid[y][x] == 0 and (x, y) not in monsters and (x, y) != d.entry
    ]
    npcs = {}
    npc_anim = {}
    for kind, pos in zip(("merchant", "trainer"), free, strict=False):
        if kind in animsets:
            npcs[pos] = kind
            npc_anim[pos] = AnimState(animsets[kind])
            npc_anim[pos].set_facing("south")

    screen.fill(cfg.C_BG)
    draw_map(
        screen,
        tiles,
        hero_anim,
        monsters_anim,
        d,
        hero,
        float(hx),
        float(hy),
        monsters,
        visible,
        mon_slide,
        npcs,
        npc_anim,
    )
    draw_hud(screen, hero)
    draw_msg(screen, i18n.t("msg.level_intro", depth=1))
    pg.image.save(screen, out_path)
    print("saved", out_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshot.png")
