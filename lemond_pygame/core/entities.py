"""Entity data model: items, creatures, and the player hero.

Pure data and rules only. Display names are produced by the localization layer
from the stable ``kind`` keys stored here, never hard-coded in this module.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

EQUIP_SLOTS = ["MAIN", "OFF", "HEAD", "BODY", "HANDS", "FEET"]

# Loot table: kind -> (slot, power offset added to tier, two_handed).
LOOT_TABLE = [
    (0.25, "sword", "MAIN", 0, False),
    (0.40, "axe", "MAIN", 1, True),
    (0.55, "staff", "MAIN", 0, False),
    (0.70, "shield", "OFF", 0, False),
    (0.80, "helmet", "HEAD", 0, False),
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
    skills: dict = field(default_factory=lambda: {"MELEE": 0, "DODGE": 0, "MAGIC": 0})
    potions: int = 0
    depth: int = 1
    unlocked_depth: int = 1
    last_dir: tuple[int, int] = (1, 0)

    def total_armor(self) -> int:
        val = 0
        for it in self.equipment.values():
            if it and it.slot in ("OFF", "HEAD", "BODY", "HANDS", "FEET"):
                val += max(0, it.power)
        return val + (self.str_ // 5)

    def weapon_damage(self) -> tuple[int, int]:
        weapon = self.equipment.get("MAIN")
        base = 1 + self.str_ // 2 + self.skills["MELEE"]
        if weapon:
            base += weapon.power
        return (max(1, base - 1), base + 1)

    def melee_damage(self) -> tuple[int, int]:
        return self.weapon_damage()

    def recompute_max_hp(self) -> None:
        self.max_hp = 16 + self.str_ * 2

    def xp_to_next(self) -> int:
        return 20 + (self.level - 1) * 15

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


def random_loot(depth: int, rng: random.Random | None = None) -> Item:
    r = rng or random
    roll = r.random()
    tier = 1 + min(5, depth // 2)
    for threshold, kind, slot, power_offset, two_handed in LOOT_TABLE:
        if roll < threshold:
            return Item(
                kind=kind, slot=slot, tier=tier, power=tier + power_offset, two_handed=two_handed
            )
    last = LOOT_TABLE[-1]
    return Item(kind=last[1], slot=last[2], tier=tier, power=tier + last[3], two_handed=last[4])
