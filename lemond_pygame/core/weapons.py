"""Weapon categories, equip requirements, and ranged/magic power. Pure rules.

A weapon's ``kind`` decides its category (melee / ranged / magic), which governing
skill it trains and gates on, and its stat/skill requirements (scaling with tier).
This module imports nothing from :mod:`entities` so it can be imported by it
without a cycle; it duck-types on ``item.kind/.tier/.power`` and
``hero.str_/.dex/.int_/.skills``.

Numbers follow the combat-overhaul balance pass and are the single place to tune
weapon feel.
"""

from __future__ import annotations

WEAPON_CATEGORY = {
    "sword": "melee",
    "dagger": "melee",
    "axe": "melee",
    "mace": "melee",
    "bow": "ranged",
    "crossbow": "ranged",
    "staff": "magic",
    "wand": "magic",
}
CATEGORY_SKILL = {"melee": "MELEE", "ranged": "ACCURACY", "magic": "MAGIC"}

# kind -> (primary stat, secondary stat | None) governing the equip requirement.
_ROLES = {
    "sword": ("str", "dex"),
    "dagger": ("dex", "str"),
    "axe": ("str", None),
    "mace": ("str", None),
    "bow": ("dex", None),
    "crossbow": ("dex", "str"),
    "staff": ("int", "str"),
    "wand": ("int", None),
}


def category(kind: str) -> str | None:
    return WEAPON_CATEGORY.get(kind)


def is_weapon(kind: str) -> bool:
    return kind in WEAPON_CATEGORY


def governing_skill(kind: str) -> str | None:
    cat = WEAPON_CATEGORY.get(kind)
    return CATEGORY_SKILL.get(cat) if cat else None


def requirements(item) -> dict:
    """Stat and skill thresholds to equip ``item``; empty for non-weapons.

    Scales with tier T: primary stat = 4 + 2T, secondary stat = 2 + T, and the
    matching skill level = T - 1. A fresh class clears tier 1 of its own weapon.
    """
    roles = _ROLES.get(item.kind)
    if not roles:
        return {}
    tier = max(1, item.tier)
    primary, secondary = roles
    req: dict = {primary: 4 + 2 * tier}
    if secondary:
        req[secondary] = 2 + tier
    req["skill_name"] = governing_skill(item.kind)
    req["skill_level"] = max(0, tier - 1)
    return req


def can_equip(hero, item) -> tuple[bool, str | None]:
    """Whether ``hero`` meets ``item``'s requirements. Returns (ok, unmet_code)
    where the code is 'str' / 'dex' / 'int' / a skill name, for the UI."""
    req = requirements(item)
    if not req:
        return True, None
    have = {"str": hero.str_, "dex": hero.dex, "int": hero.int_}
    for stat, value in have.items():
        if req.get(stat, 0) > value:
            return False, stat
    skill = req.get("skill_name")
    if skill and hero.skills.get(skill, 0) < req.get("skill_level", 0):
        return False, skill
    return True, None


def weapon_range(hero, weapon) -> int:
    """Reach in tiles for a ranged shot (dex-scaled, not skill-scaled)."""
    if weapon and weapon.kind == "crossbow":
        return 5 + hero.dex // 5
    return 4 + hero.dex // 4


def ranged_damage(hero, weapon) -> tuple[int, int]:
    """Damage range for a bow/crossbow shot. Scales with dex + marksmanship.

    The crossbow roughly doubles the flat term (it fires every other turn), so it
    hits about twice as hard per bolt as the bow with a wider spread.
    """
    from .affixes import item_bonus  # local import: affixes imports this module

    flat = 1 + hero.dex // 2 + hero.skills.get("ACCURACY", 0)
    power = (weapon.power + item_bonus(weapon, "damage")) if weapon else 0
    if weapon and weapon.kind == "crossbow":
        mid, spread = 2 * flat + power, 2
    else:
        mid, spread = flat + power, 1
    return (max(1, mid - spread), mid + spread)


def magic_power(weapon) -> int:
    """Bonus spell damage from an equipped magic weapon (0 if none/not magic).

    Staves are two-handed and give their full power; one-handed wands give one
    less but free the off-hand for a shield. An 'arcane' affix adds on top
    (and works on any weapon, so an enchanted blade can aid a battle-mage)."""
    from .affixes import item_bonus  # local import: affixes imports this module

    if not weapon:
        return 0
    base = 0
    if weapon.kind == "staff":
        base = max(0, weapon.power)
    elif weapon.kind == "wand":
        base = max(0, weapon.power - 1)
    return base + item_bonus(weapon, "magic")
