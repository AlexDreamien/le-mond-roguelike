"""Build tile surfaces and per-entity animation sets from the sprite atlas."""

from __future__ import annotations

import json

import pygame as pg

from .core import config as cfg
from .respath import resource_path

ENTITY_KEYS = ["hero", "goblin", "orc", "bat", "ogre", "armor", "vampire"]


def build_tiles() -> dict[str, pg.Surface]:
    wall = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    wall.fill((70, 70, 80))
    pg.draw.rect(wall, (110, 110, 120), (0, 0, cfg.TILE, cfg.TILE), 1)

    floor = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    floor.fill((24, 24, 32))

    chest = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    chest.fill((50, 50, 20))
    pg.draw.rect(chest, (210, 170, 40), (4, 6, cfg.TILE - 8, cfg.TILE - 10), border_radius=4)

    exit_tile = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    exit_tile.fill((22, 26, 30))
    pg.draw.rect(exit_tile, (40, 180, 180), (2, 2, cfg.TILE - 4, cfg.TILE - 4), 2, border_radius=6)

    shadow_soft = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    shadow_soft.fill((0, 0, 0, 120))
    shadow_hard = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    shadow_hard.fill((0, 0, 0, 200))

    return {
        "wall": wall,
        "floor": floor,
        "chest": chest,
        "exit": exit_tile,
        "shadow_soft": shadow_soft,
        "shadow_hard": shadow_hard,
    }


def build_animsets_from_atlas() -> dict[str, dict[str, list[pg.Surface]]]:
    png_path = resource_path("assets", "le_mond_sprite_atlas.png")
    json_path = resource_path("assets", "le_mond_sprite_atlas.json")
    atlas = pg.image.load(png_path).convert_alpha()
    with open(json_path, encoding="utf-8") as f:
        meta = json.load(f)

    def slice_rect(r):
        s = pg.Surface((r["w"], r["h"]), pg.SRCALPHA)
        s.blit(atlas, (0, 0), (r["x"], r["y"], r["w"], r["h"]))
        return s

    def load_entity(ent_key):
        return {
            k: [slice_rect(rc) for rc in rects] for k, rects in meta["entities"][ent_key].items()
        }

    return {ent: load_entity(ent) for ent in ENTITY_KEYS}
