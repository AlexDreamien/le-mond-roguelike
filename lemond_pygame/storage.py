"""Persistence: hero saves and options stored as JSON under %LOCALAPPDATA%."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from .core.entities import EQUIP_SLOTS, Hero, Item

DEFAULT_OPTIONS = {
    "anim_speed": 1.0,
    "particles": 1.0,
    "volume": 0.7,
    "language": "en",
    "auto_stats": True,
    "auto_skills": True,
    "music": True,
}
SAVE_SLOTS = 5


def _folder() -> Path:
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    p = Path(base) / "Le-Mond Roguelike"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_path(slot: int) -> str:
    return str(_folder() / f"save_{slot}.json")


def _item_to_dict(it: Item) -> dict:
    return {
        "kind": it.kind,
        "slot": it.slot,
        "tier": it.tier,
        "power": it.power,
        "two_handed": it.two_handed,
        "affixes": list(getattr(it, "affixes", ())),
        "unique": getattr(it, "unique", ""),
    }


# Legacy saves (pre-i18n) stored localized item names and a localized class.
# Map them to the stable keys used since the refactor.
_LEGACY_NAME_TO_KIND = {
    "меч": "sword", "кинжал": "dagger", "топор": "axe", "посох": "staff",
    "щит": "shield", "шлем": "helmet", "броня": "armor", "перчатки": "gloves", "сапоги": "boots",
}  # fmt: skip
_SLOT_DEFAULT_KIND = {
    "MAIN": "sword", "OFF": "shield", "HEAD": "helmet",
    "BODY": "armor", "HANDS": "gloves", "FEET": "boots",
}  # fmt: skip
_LEGACY_CLASS_TO_KIND = {"Воин": "warrior", "Вор": "thief", "Маг": "mage"}


def _item_from_dict(d: dict) -> Item:
    kind = d.get("kind")
    tier = d.get("tier", 1)
    if kind is None:  # migrate legacy {"name": "Меч 2", ...}
        parts = (d.get("name") or "").split()
        base = parts[0].lower() if parts else ""
        if len(parts) >= 2 and parts[-1].isdigit():
            tier = int(parts[-1])
        kind = _LEGACY_NAME_TO_KIND.get(base) or _SLOT_DEFAULT_KIND.get(d.get("slot"), "sword")
    return Item(
        kind=kind,
        slot=d.get("slot"),
        tier=tier,
        power=d.get("power", 0),
        two_handed=d.get("two_handed", False),
        affixes=list(d.get("affixes", [])),
        unique=d.get("unique", ""),
    )


def save_hero(slot: int, hero: Hero, options: dict) -> None:
    data = {
        "name": hero.name,
        "class_kind": hero.class_kind,
        "max_hp": hero.max_hp,
        "hp": hero.hp,
        "str_": hero.str_,
        "dex": hero.dex,
        "int_": hero.int_,
        "level": hero.level,
        "xp": hero.xp,
        "stat_points": hero.stat_points,
        "skill_points": hero.skill_points,
        "depth": hero.depth,
        "unlocked_depth": hero.unlocked_depth,
        "skills": hero.skills,
        "potions": hero.potions,
        "mana_potions": hero.mana_potions,
        "mana": hero.mana,
        "max_mana": hero.max_mana,
        "active_spell": hero.active_spell,
        "lore_seen": list(hero.lore_seen),
        "deaths": hero.deaths,
        "flags": dict(hero.flags),
        "gold": hero.gold,
        "inventory": [_item_to_dict(it) for it in hero.inventory],
        "equipment": {
            s: (None if it is None else _item_to_dict(it)) for s, it in hero.equipment.items()
        },
        "options": options or dict(DEFAULT_OPTIONS),
    }
    with open(save_path(slot), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_hero(slot: int) -> tuple[Hero | None, dict]:
    p = save_path(slot)
    opts = dict(DEFAULT_OPTIONS)
    if not os.path.exists(p):
        return None, opts
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        class_kind = data.get("class_kind") or _LEGACY_CLASS_TO_KIND.get(
            data.get("class"), "warrior"
        )
        h = Hero(
            kind="hero",
            max_hp=data.get("max_hp", 20),
            hp=data.get("hp", 20),
            str_=data.get("str_", 5),
            dex=data.get("dex", 5),
            int_=data.get("int_", 5),
            glyph="hero",
            name=data.get("name", "Gustav"),
            class_kind=class_kind,
        )
        h.level = data.get("level", 1)
        h.xp = data.get("xp", 0)
        h.stat_points = data.get("stat_points", 0)
        h.skill_points = data.get("skill_points", 0)
        h.depth = data.get("depth", 1)
        h.unlocked_depth = data.get("unlocked_depth", h.depth)
        h.skills = data.get("skills", {"MELEE": 0, "DODGE": 0, "MAGIC": 0, "ACCURACY": 0})
        for sk in ("MELEE", "DODGE", "MAGIC", "ACCURACY"):
            h.skills.setdefault(sk, 0)  # backfill new skills on legacy saves
        h.potions = data.get("potions", 0)
        h.mana_potions = data.get("mana_potions", 0)
        h.recompute_max_mana()  # derive from int, then honour any saved values
        h.max_mana = data.get("max_mana", h.max_mana)
        h.mana = data.get("mana", h.max_mana)
        h.active_spell = data.get("active_spell", "magic_arrow")
        h.lore_seen = list(data.get("lore_seen", []))
        h.deaths = data.get("deaths", 0)
        h.flags.update(data.get("flags", {}))  # keep defaults for any missing keys
        h.gold = data.get("gold", 0)
        h.inventory = [_item_from_dict(it) for it in data.get("inventory", [])]
        h.equipment = {s: None for s in EQUIP_SLOTS}
        for slot_key, it in data.get("equipment", {}).items():
            h.equipment[slot_key] = None if it is None else _item_from_dict(it)
        opts.update(data.get("options", {}))
    except (OSError, ValueError, KeyError, TypeError):
        return None, opts
    return h, opts


def list_saves() -> list[dict]:
    res = []
    for i in range(1, SAVE_SLOTS + 1):
        p = save_path(i)
        if not os.path.exists(p):
            res.append({"slot": i, "exists": False})
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            res.append(
                {
                    "slot": i,
                    "name": d.get("name", "Gustav"),
                    "class_kind": d.get("class_kind")
                    or _LEGACY_CLASS_TO_KIND.get(d.get("class"), "warrior"),
                    "level": d.get("level", 1),
                    "depth": d.get("depth", 1),
                    "unlocked_depth": d.get("unlocked_depth", d.get("depth", 1)),
                    "exists": True,
                }
            )
        except (OSError, ValueError):
            res.append({"slot": i, "exists": False})
    return res


def delete_save(slot: int) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.remove(save_path(slot))
