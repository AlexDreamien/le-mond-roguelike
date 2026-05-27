"""Pickup resolution: floor loot vs chests.

Pure: mutates the hero and reports what happened; the caller handles sound,
messages, and the map tile. Floor tiles only ever hold gold or a potion;
equipment comes exclusively from chests.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .entities import Item, random_loot

INVENTORY_LIMIT = 9
FLOOR_GOLD_CHANCE = 0.5  # floor: gold vs potion
CHEST_POTION_CHANCE = 0.2  # chest: occasional potion instead of gear


@dataclass
class PickupResult:
    outcome: str  # "gold" | "potion" | "equipped" | "stored" | "inventory_full"
    item: Item | None = None
    equip_status: str | None = None  # i18n code returned by Hero.equip when equipped
    gold: int = 0


def _gold_amount(depth: int, r) -> int:
    return r.randint(5 + depth * 2, 12 + depth * 6)


def resolve_pickup(hero, depth: int, from_chest: bool = False, rng=None) -> PickupResult:
    r = rng or random
    if not from_chest:
        # Floor tiles only ever hold money or a potion.
        if r.random() < FLOOR_GOLD_CHANCE:
            amount = _gold_amount(depth, r)
            hero.gold += amount
            return PickupResult("gold", gold=amount)
        hero.potions += 1
        return PickupResult("potion")

    # Chests are the only source of equipment.
    if r.random() < CHEST_POTION_CHANCE:
        hero.potions += 1
        return PickupResult("potion")
    item = random_loot(depth, rng=r)
    if hero.equipment.get(item.slot) is None:
        status = hero.equip(item, to_slot=item.slot)
        return PickupResult("equipped", item=item, equip_status=status)
    if len(hero.inventory) < INVENTORY_LIMIT:
        hero.inventory.append(item)
        return PickupResult("stored", item=item)
    return PickupResult("inventory_full", item=item)
