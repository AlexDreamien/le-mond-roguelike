"""Pack the PixelLab "objects" export (64 separate 32x32 PNGs in nested folders)
into a single atlas PNG + JSON with clean game keys.

PixelLab downloaded each object as ``objects/<name>/<name>/rotations/unknown.png``
with prompt-derived folder names. This tool maps each by a distinctive substring
to a stable key, lays them out in a grid, and writes:

    assets/objects_atlas.png
    assets/objects_atlas.json   ({key: [x, y, w, h]})

Usage:
    python tools/pack_objects.py [source_dir] [out_basename]
"""

from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame as pg  # noqa: E402

TILE = 32

# Distinctive path substring (lowercased) -> stable key.
NAME_MAP = {
    "dungeon_wall_dark_grey-blue": "wall_0",
    "dungeon_wall_cracked": "wall_1",
    "dungeon_wall_mossy": "wall_2",
    "dungeon_wall_stone_with_embed": "wall_3",
    "dungeon_floor_dark_stone_flag": "floor_0",
    "dungeon_floor_dark_cobble": "floor_1",
    "dungeon_floor_cracked": "floor_2",
    "stone_staircase_descending": "stairs_down",
    "stone_staircase_going_up": "stairs_up",
    "closed_wooden_dungeon_door": "door_closed",
    "open_dark_doorway": "door_open",
    "lit_wall_torch": "torch",
    "closed_wooden_treasure_chest": "chest",
    "small_pile_of_scattered": "coins",
    "round_glass_flask": "potion",
    "short_steel_sword": "item.sword",
    "small_curved_dagger": "item.dagger",
    "heavy_two-handed_battle_axe": "item.axe",
    "wooden_magic_staff": "item.staff",
    "round_wooden_shield": "item.shield",
    "steel_helmet": "item.helmet",
    "steel_chestplate": "item.armor",
    "pair_of_leather_gloves": "item.gloves",
    "pair_of_leather_boots": "item.boots",
    "red_heart": "icon.hp",
    "flexed_muscular_arm": "icon.str",
    "winged_boot_or_feather": "icon.dex",
    "open_spellbook": "icon.int",
    "small_steel_shield_armor": "icon.armor",
    "two_crossed_swords": "icon.dmg",
    "dodging_figure": "icon.dodge",
    "glowing_blue_star_orb": "icon.xp",
    "upward_golden_chevron": "icon.levelup",
    "single_gold_coin": "icon.gold",
    "small_red_potion_bottle": "icon.potion",
    "leather_backpack": "icon.inventory",
    "character_stat_scroll": "icon.stats",
    "branching_skill_tree": "icon.skills",
    "gear_cog": "icon.options",
    "pause_symbol": "icon.pause",
    "swirling_magic_sparkle": "icon.magic",
    "open_grabbing_hand": "icon.grab",
    "potion_tipped_to_drink": "icon.drink",
    "floppy_disk": "icon.save",
    "globe_language": "icon.language",
    "musical_note_music_on": "icon.music_on",
    "musical_note_with_a_slash": "icon.music_off",
    "door_with_an_exit_arrow": "icon.quit",
    "sword_silhouette": "slot.MAIN",
    "shield_silhouette": "slot.OFF",
    "helmet_silhouette": "slot.HEAD",
    "chestplate_silhouette": "slot.BODY",
    "glove_silhouette": "slot.HANDS",
    "boot_silhouette": "slot.FEET",
    "crossed_sword_and_shield": "class.warrior",
    "hooded_mask_with_a_dagger": "class.thief",
    "wizard_hat_with_a_star": "class.mage",
    "empty_checkbox": "ui.checkbox_off",
    "checked_checkbox": "ui.checkbox_on",
    "up_arrow": "ui.arrow_up",
    "down_arrow": "ui.arrow_down",
    "left_arrow": "ui.arrow_left",
    "right_arrow": "ui.arrow_right",
    "selection_pointer": "ui.cursor",
}


def _match_key(path: str) -> str | None:
    p = path.replace("\\", "/").lower()
    hits = [key for sub, key in NAME_MAP.items() if sub in p]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        print(f"  AMBIGUOUS {path} -> {hits}")
    return None


def main(source: str, out_base: str) -> None:
    pg.init()
    pg.display.set_mode((64, 64))
    pngs = []
    for root, _dirs, files in os.walk(source):
        for f in files:
            if f.endswith(".png"):
                pngs.append(os.path.join(root, f))

    found: dict[str, str] = {}
    for path in sorted(pngs):
        key = _match_key(path)
        if key is None:
            print(f"  UNMAPPED {path}")
            continue
        if key in found:
            print(f"  DUPLICATE key {key}: {path} (already {found[key]})")
            continue
        found[key] = path

    missing = sorted(set(NAME_MAP.values()) - set(found))
    if missing:
        print(f"  MISSING keys: {missing}")

    keys = sorted(found)
    cols = 8
    rows = (len(keys) + cols - 1) // cols
    atlas = pg.Surface((cols * TILE, rows * TILE), pg.SRCALPHA)
    index: dict[str, list[int]] = {}
    for i, key in enumerate(keys):
        cx, cy = (i % cols) * TILE, (i // cols) * TILE
        sprite = pg.image.load(found[key]).convert_alpha()
        if sprite.get_size() != (TILE, TILE):
            sprite = pg.transform.smoothscale(sprite, (TILE, TILE))
        atlas.blit(sprite, (cx, cy))
        index[key] = [cx, cy, TILE, TILE]

    pg.image.save(atlas, out_base + ".png")
    with open(out_base + ".json", "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"packed {len(keys)} sprites -> {out_base}.png ({cols * TILE}x{rows * TILE})")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "lemond_pygame/assets/objects"
    out = sys.argv[2] if len(sys.argv) > 2 else "lemond_pygame/assets/objects_atlas"
    main(src, out)
