"""Build tile surfaces and per-entity animation sets from the sprite atlas."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pygame as pg

from .core import config as cfg
from .respath import resource_path

ENTITY_KEYS = ["hero", "goblin", "orc", "bat", "ogre", "armor", "vampire"]

# Hero animation states -> PixelLab export folder prefix (see assets/main_hero).
HERO_DIRS = ("south", "north", "east", "west")
HERO_STATES = {
    "walk": "Walking",
    "attack": "Lead_Jab",
    "cast": "Fireball",
    "pickup": "Picking_Up",
    "drink": "Drinking",
}

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


def build_object_sprites() -> dict[str, pg.Surface]:
    """Load the packed objects atlas into ``{key: Surface}`` (empty if missing)."""
    png = resource_path("assets", "objects_atlas.png")
    meta = resource_path("assets", "objects_atlas.json")
    if not (Path(png).exists() and Path(meta).exists()):
        return {}
    atlas = pg.image.load(png).convert_alpha()
    with open(meta, encoding="utf-8") as f:
        index = json.load(f)
    out: dict[str, pg.Surface] = {}
    for key, (x, y, w, h) in index.items():
        sprite = pg.Surface((w, h), pg.SRCALPHA)
        sprite.blit(atlas, (0, 0), (x, y, w, h))
        out[key] = sprite
    return out


def build_tiles() -> dict[str, object]:
    """Tile/sprite set, sourced from the objects atlas with a procedural fallback."""
    obj = build_object_sprites()
    walls = [obj[k] for k in ("wall_0", "wall_1", "wall_2", "wall_3") if k in obj]
    floors = [obj[k] for k in ("floor_0", "floor_1", "floor_2") if k in obj]
    return {
        "wall_variants": walls or [_make_wall()],
        "floor_variants": floors or [_make_floor(i) for i in range(FLOOR_VARIANTS)],
        "chest": obj.get("chest") or _make_chest(),
        "stairs_down": obj.get("stairs_down") or _make_exit(),
        "stairs_up": obj.get("stairs_up"),  # None -> entry shows plain floor
        "coins": obj.get("coins") or _make_loot(),
        "potion": obj.get("potion") or _make_loot(),
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


def _fit_to_tile(raw: pg.Surface, bbox: pg.Rect) -> pg.Surface:
    """Crop ``raw`` to the shared content ``bbox`` and bottom-center it on a tile.

    The PixelLab canvas (60x60) is mostly transparent padding around a ~tile-sized
    character; cropping to a bbox shared by every frame removes the padding without
    shrinking the hero or making the animation jitter. The crop is only scaled down
    if it would not fit the tile.
    """
    crop = raw.subsurface(bbox).copy()
    cw, ch = crop.get_size()
    scale = min(cfg.TILE / cw, cfg.TILE / ch, 1.0)
    if scale < 1.0:
        crop = pg.transform.smoothscale(
            crop, (max(1, round(cw * scale)), max(1, round(ch * scale)))
        )
        cw, ch = crop.get_size()
    surf = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA)
    surf.blit(crop, ((cfg.TILE - cw) // 2, cfg.TILE - ch))  # bottom-centered: feet on the tile
    return surf


def _find_character_dir(base: Path) -> Path | None:
    """The single subfolder holding animations/ or rotations/ (PixelLab layout)."""
    if not base.is_dir():
        return None
    return next(
        (p for p in base.iterdir() if (p / "animations").is_dir() or (p / "rotations").is_dir()),
        None,
    )


def _load_animset(char: Path, states: dict[str, str], dirs) -> dict[str, list[pg.Surface]]:
    """Load a PixelLab character into ``{state}_{dir} -> [tile-fitted frames]``.

    Animations come from ``animations/<prefix>/<dir>/frame_*.png``; any idle
    direction an animation did not produce falls back to the static ``rotations``.
    All frames are cropped to one shared content box and fitted to the tile so the
    character keeps a consistent size and anchor.
    """
    raw: dict[str, list[pg.Surface]] = {}
    anim_dir = char / "animations"
    by_prefix = (
        {p.name.split("-")[0]: p for p in anim_dir.iterdir() if p.is_dir()}
        if anim_dir.is_dir()
        else {}
    )
    for state, prefix in states.items():
        folder = by_prefix.get(prefix)
        if folder is None:
            continue
        for d in dirs:
            sub = folder / d
            if sub.is_dir():
                files = sorted(sub.glob("frame_*.png"))
                raw[f"{state}_{d}"] = [pg.image.load(str(f)).convert_alpha() for f in files]

    rotations = char / "rotations"
    if rotations.is_dir():
        for d in dirs:
            img = rotations / f"{d}.png"
            if img.exists():
                raw.setdefault(f"idle_{d}", [pg.image.load(str(img)).convert_alpha()])

    if not raw:
        return {}
    bbox: pg.Rect | None = None
    for frames in raw.values():
        for frame in frames:
            r = frame.get_bounding_rect()
            bbox = r if bbox is None else bbox.union(r)
    return {key: [_fit_to_tile(frame, bbox) for frame in frames] for key, frames in raw.items()}


def build_hero_animset() -> dict[str, list[pg.Surface]]:
    """4-directional hero: walk/attack/cast/pickup/drink + idle from rotations."""
    char = _find_character_dir(Path(resource_path("assets", "main_hero")))
    return _load_animset(char, HERO_STATES, HERO_DIRS) if char else {}


def build_creature_animsets(group: str) -> dict[str, dict[str, list[pg.Surface]]]:
    """South-facing idle animsets for every kind under ``assets/<group>/<kind>/``.

    ``group`` is "monsters" or "npc". Returns ``{kind: {"idle_south": [...]}}``.
    """
    base = Path(resource_path("assets", group))
    out: dict[str, dict[str, list[pg.Surface]]] = {}
    if not base.is_dir():
        return out
    for kind_dir in sorted(base.iterdir()):
        char = _find_character_dir(kind_dir) if kind_dir.is_dir() else None
        if char is None:
            continue
        animset = _load_animset(char, {"idle": "Breathing_Idle"}, ("south",))
        if animset:
            out[kind_dir.name] = animset
    return out
