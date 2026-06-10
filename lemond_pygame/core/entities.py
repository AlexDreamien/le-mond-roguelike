"""Entity data model: items, creatures, and the player hero.

Pure data and rules only. Display names are produced by the localization layer
from the stable ``kind`` keys stored here, never hard-coded in this module.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .affixes import equipment_bonus, item_bonus, roll_affixes
from .weapons import category as weapon_category

EQUIP_SLOTS = ["MAIN", "OFF", "HEAD", "BODY", "HANDS", "FEET"]

# Loot table: (cumulative threshold, kind, slot, power offset added to tier,
# two_handed). Two-handed weapons (axe, bow, crossbow, staff) block the shield.
LOOT_TABLE = [
    (0.12, "sword", "MAIN", 0, False),
    (0.22, "dagger", "MAIN", 0, False),
    (0.31, "axe", "MAIN", 1, True),
    (0.39, "mace", "MAIN", 0, False),
    (0.47, "bow", "MAIN", 0, True),
    (0.53, "crossbow", "MAIN", 1, True),
    (0.60, "staff", "MAIN", 0, True),
    (0.66, "wand", "MAIN", 0, False),
    (0.74, "shield", "OFF", 0, False),
    (0.81, "helmet", "HEAD", 0, False),
    (0.90, "armor", "BODY", 1, False),
    (0.95, "gloves", "HANDS", 0, False),
    (1.00, "boots", "FEET", 0, False),
]


@dataclass
class Item:
    kind: str
    slot: str | None
    tier: int = 1
    power: int = 0
    two_handed: bool = False
    affixes: list = field(default_factory=list)  # affix keys; see core.affixes


@dataclass
class Creature:
    kind: str
    max_hp: int
    hp: int
    str_: int
    dex: int
    int_: int
    glyph: str = "?"
    hostile: bool = True
    xp_reward: int = 5
    armor: int = 0

    def melee_damage(self) -> tuple[int, int]:
        base = max(1, self.str_ // 2)
        return (base, base + 2)


@dataclass
class Hero(Creature):
    name: str = "Gustav"
    class_kind: str = "warrior"
    inventory: list = field(default_factory=list)
    equipment: dict = field(default_factory=lambda: {s: None for s in EQUIP_SLOTS})
    level: int = 1
    xp: int = 0
    stat_points: int = 0
    skill_points: int = 0
    skills: dict = field(
        default_factory=lambda: {"MELEE": 0, "DODGE": 0, "MAGIC": 0, "ACCURACY": 0}
    )
    potions: int = 0
    mana_potions: int = 0
    mana: int = 0
    max_mana: int = 0
    active_spell: str = "magic_arrow"  # spell cast by F; chosen in the spellbook
    gold: int = 0
    depth: int = 1
    unlocked_depth: int = 1
    last_dir: tuple[int, int] = (1, 0)

    def total_armor(self) -> int:
        val = 0
        for it in self.equipment.values():
            if it and it.slot in ("OFF", "HEAD", "BODY", "HANDS", "FEET"):
                val += max(0, it.power)
        return val + (self.str_ // 5) + equipment_bonus(self.equipment, "armor")

    def dodge_bonus(self) -> int:
        """Extra dodge-skill points granted by 'swift' gear."""
        return equipment_bonus(self.equipment, "dodge")

    def weapon_damage(self) -> tuple[int, int]:
        # Only melee weapons add their power to a swing; swinging a bow or staff
        # in melee is improvised, so it lands as the unarmed base.
        weapon = self.equipment.get("MAIN")
        base = 1 + self.str_ // 2 + self.skills["MELEE"]
        if weapon and weapon_category(weapon.kind) == "melee":
            base += weapon.power + item_bonus(weapon, "damage")
        return (max(1, base - 1), base + 1)

    def melee_damage(self) -> tuple[int, int]:
        return self.weapon_damage()

    def recompute_max_hp(self) -> None:
        self.max_hp = 16 + self.str_ * 2

    def recompute_max_mana(self) -> None:
        self.max_mana = 10 + self.int_ * 4

    def xp_to_next(self) -> int:
        # Geometric ramp (~1.5x per level) via exact integer arithmetic, so
        # leveling slows down as the dungeon deepens instead of staying linear.
        n = self.level - 1
        return 20 * 3**n // 2**n

    def gain_xp(self, amount: int) -> None:
        self.xp += amount
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            self.stat_points += 2
            self.skill_points += 1

    def equip(self, item: Item, to_slot: str | None = None) -> str:
        """Equip ``item``. Returns a status code understood by the i18n layer."""
        slot = to_slot or item.slot
        if not slot:
            return "equip.not_equippable"
        if slot == "MAIN" and item.two_handed and self.equipment.get("OFF") is not None:
            return "equip.two_handed_blocked"
        if slot == "OFF":
            main = self.equipment.get("MAIN")
            if main and getattr(main, "two_handed", False):
                return "equip.shield_blocked"
        self.equipment[slot] = item
        return "equip.ok"


def random_item(tier: int, rng: random.Random | None = None) -> Item:
    r = rng or random
    roll = r.random()
    row = LOOT_TABLE[-1]
    for threshold, kind, slot, power_offset, two_handed in LOOT_TABLE:
        if roll < threshold:
            row = (threshold, kind, slot, power_offset, two_handed)
            break
    item = Item(kind=row[1], slot=row[2], tier=tier, power=tier + row[3], two_handed=row[4])
    roll_affixes(item, rng=r)
    return item


def random_loot(depth: int, rng: random.Random | None = None) -> Item:
    return random_item(1 + min(5, depth // 2), rng)
