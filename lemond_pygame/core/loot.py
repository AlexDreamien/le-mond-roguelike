"""Pickup resolution shared by floor loot, chests, and the manual grab key.

Centralises the rule that used to be copy-pasted in three places in the game
loop. Pure: mutates the hero and reports what happened; the caller handles
sound, messages, and the map tile.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .entities import Item, random_loot

INVENTORY_LIMIT = 9
POTION_CHANCE = 0.4


@dataclass
class PickupResult:
    outcome: str  # "potion" | "equipped" | "stored" | "inventory_full"
    item: Item | None = None
    equip_status: str | None = None  # i18n code returned by Hero.equip when equipped


def resolve_pickup(hero, depth: int, rng: random.Random | None = None) -> PickupResult:
    r = rng or random
    if r.random() < POTION_CHANCE:
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
