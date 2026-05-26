"""Build tile surfaces and per-entity animation sets from the sprite atlas."""

from __future__ import annotations

import json
import random

import pygame as pg

from .core import config as cfg
from .respath import resource_path

ENTITY_KEYS = ["hero", "goblin", "orc", "bat", "ogre", "armor", "vampire"]

FLOOR_VARIANTS = 6


def _make_floor(seed: int) -> pg.Surface:
    """A dark stone floor tile with deterministic speckle so it does not look flat."""
    t = cfg.TILE
    surf = pg.Surface((t, t), pg.SRCALPHA)
    surf.fill((24, 24, 32))
    rng = random.Random(seed)
    for _ in range(14):
        x, y = rng.randrange(t), rng.randrange(t)
        shade = rng.choice([(18, 18, 26), (30, 30, 40), (21, 21, 30)])
        surf.set_at((x, y), shade)
    # a couple of faint cracks
    for _ in range(2):
        x0, y0 = rng.randrange(t), rng.randrange(t)
        x1, y1 = min(t - 1, x0 + rng.randint(-6, 6)), min(t - 1, y0 + rng.randint(-6, 6))
        pg.draw.line(surf, (16, 16, 24), (x0, y0), (x1, y1), 1)
    return surf


def _make_wall() -> pg.Surface:
    """A beveled wall block: lit top/left edges, shadowed bottom/right."""
    t = cfg.TILE
    surf = pg.Surface((t, t), pg.SRCALPHA)
    surf.fill((58, 58, 72))
    pg.draw.rect(surf, (84, 84, 102), (0, 0, t, 3))  # top highlight
    pg.draw.rect(surf, (74, 74, 92), (0, 0, 3, t))  # left highlight
    pg.draw.rect(surf, (34, 34, 46), (0, t - 4, t, 4))  # bottom shadow
    pg.draw.rect(surf, (40, 40, 52), (t - 3, 0, 3, t))  # right shadow
    pg.draw.line(surf, (44, 44, 56), (0, t // 2), (t, t // 2), 1)  # mortar seam
    return surf


def _make_chest() -> pg.Surface:
    t = cfg.TILE
    surf = pg.Surface((t, t), pg.SRCALPHA)
    body = pg.Rect(4, 8, t - 8, t - 12)
    pg.draw.rect(surf, (120, 80, 24), body, border_radius=3)
    pg.draw.rect(surf, (210, 170, 40), body, 2, border_radius=3)
    pg.draw.rect(surf, (235, 200, 90), (4, 8, t - 8, 6), border_radius=3)  # lid
    pg.draw.rect(surf, (60, 40, 12), (t // 2 - 2, t // 2 - 1, 4, 5))  # lock
    return surf


def _make_exit() -> pg.Surface:
    t = cfg.TILE
    surf = pg.Surface((t, t), pg.SRCALPHA)
    c = t // 2
    for i, col in enumerate([(20, 70, 80), (30, 120, 140), (70, 210, 220)]):
        pg.draw.circle(surf, col, (c, c), c - 2 - i * 4)
    pg.draw.circle(surf, (180, 250, 255), (c, c), 3)
    return surf


def _make_loot() -> pg.Surface:
    """A small glint marking loot lying on the ground."""
    t = cfg.TILE
    surf = pg.Surface((t, t), pg.SRCALPHA)
    c = t // 2
    pg.draw.polygon(surf, (220, 200, 110), [(c, c - 5), (c + 5, c), (c, c + 5), (c - 5, c)])
    pg.draw.polygon(surf, (255, 240, 170), [(c, c - 3), (c + 3, c), (c, c + 3), (c - 3, c)])
    return surf


def build_tiles() -> dict[str, object]:
    return {
        "wall": _make_wall(),
        "floor": _make_floor(0),
        "floor_variants": [_make_floor(i) for i in range(FLOOR_VARIANTS)],
        "chest": _make_chest(),
        "exit": _make_exit(),
        "loot": _make_loot(),
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
