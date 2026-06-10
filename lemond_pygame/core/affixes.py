"""Item affixes: tier-scaled bonus properties rolled onto dropped gear. Pure rules.

An item carries a list of affix keys (``item.affixes``). Each affix maps to one
stat the rest of the game reads through :func:`item_bonus` /
:func:`equipment_bonus`:

* ``sharp``    - weapons: bonus damage added to that weapon's swings/shots
* ``arcane``   - weapons: bonus spell power (like a better staff/wand)
* ``vampiric`` - weapons: the wielder heals for a third of damage dealt
* ``swift``    - any gear: counts as extra DODGE skill points
* ``sturdy``   - armour pieces: bonus armour

Rarity is implicit: 0 affixes = common, 1 = magic, 2 = rare. The localization
layer renders names like "Sword 3 of Sharpness"; the UI colours by rarity.
"""

from __future__ import annotations

import random

from .weapons import category as weapon_category

# affix -> the stat it feeds. ``vampiric`` is a flag (ratio fixed at dmg//3).
AFFIX_STAT = {
    "sharp": "damage",
    "arcane": "magic",
    "vampiric": "lifesteal",
    "swift": "dodge",
    "sturdy": "armor",
}

# Which affixes can roll on which gear. Weapon pools depend on the category;
# armour pieces (shield/helmet/armor/gloves/boots) share one pool.
_POOLS = {
    "melee": ("sharp", "vampiric", "swift"),
    "ranged": ("sharp", "vampiric", "swift"),
    "magic": ("arcane", "swift"),
    "armor": ("sturdy", "swift"),
}

AFFIX_CHANCE = 0.25  # chance a dropped item gets one affix...
SECOND_AFFIX_CHANCE = 0.10  # ...and, if it did, a second one (rare)


def _pool(item) -> tuple[str, ...]:
    cat = weapon_category(item.kind)
    if cat:
        return _POOLS[cat]
    if item.slot in ("OFF", "HEAD", "BODY", "HANDS", "FEET"):
        return _POOLS["armor"]
    return ()


def affix_value(affix: str, tier: int) -> int:
    """Magnitude of an affix on a tier-``tier`` item."""
    t = max(1, tier)
    if affix in ("sharp", "sturdy"):
        return 1 + t // 2
    if affix == "arcane":
        return 1 + t // 3
    if affix == "swift":
        return 1 + t // 4
    return 1  # vampiric: presence flag; the heal ratio is fixed


def item_bonus(item, stat: str) -> int:
    """Total bonus this single item gives to ``stat`` (0 if none)."""
    if item is None:
        return 0
    total = 0
    for affix in getattr(item, "affixes", ()):
        if AFFIX_STAT.get(affix) == stat:
            total += affix_value(affix, item.tier)
    return total


def equipment_bonus(equipment: dict, stat: str) -> int:
    """Sum of ``stat`` bonuses across all equipped items."""
    return sum(item_bonus(it, stat) for it in equipment.values() if it)


def roll_affixes(item, rng: random.Random | None = None) -> None:
    """Maybe roll one or two distinct affixes onto a freshly dropped item."""
    r = rng or random
    pool = _pool(item)
    if not pool or r.random() >= AFFIX_CHANCE:
        return
    first = r.choice(pool)
    item.affixes.append(first)
    rest = [a for a in pool if a != first]
    if rest and r.random() < SECOND_AFFIX_CHANCE:
        item.affixes.append(r.choice(rest))
