"""Loot resolution.

Floor tiles carry a fixed reward decided at generation time (coins -> gold,
potion -> a potion), so the caller reads the tile and uses :func:`floor_gold_amount`
or adds a potion directly. Chests are the only source of equipment and are
resolved here. Pure: mutates the hero and reports what happened.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .entities import Item, random_loot
from .weapons import can_equip

INVENTORY_LIMIT = 9
CHEST_POTION_CHANCE = 0.2  # chest: occasional potion instead of gear


@dataclass
class PickupResult:
    outcome: str  # "potion" | "mana_potion" | "equipped" | "stored" | "inventory_full"
    item: Item | None = None
    equip_status: str | None = None  # i18n code returned by Hero.equip when equipped


def floor_gold_amount(depth: int, rng=None) -> int:
    # Trimmed from the old (5+2d, 12+6d) so gold income no longer outpaces the
    # trainer/merchant prices and shopping stays a meaningful choice.
    r = rng or random
    return r.randint(4 + depth, 10 + depth * 4)


def resolve_chest(hero, depth: int, rng=None) -> PickupResult:
    r = rng or random
    if r.random() < CHEST_POTION_CHANCE:
        if r.random() < 0.5:  # split the potion drop between health and mana
            hero.mana_potions += 1
            return PickupResult("mana_potion")
        hero.potions += 1
        return PickupResult("potion")
    item = random_loot(depth, rng=r)
    ok, _unmet = can_equip(hero, item)
    if ok and hero.equipment.get(item.slot) is None:
        status = hero.equip(item, to_slot=item.slot)
        return PickupResult("equipped", item=item, equip_status=status)
    if len(hero.inventory) < INVENTORY_LIMIT:
        hero.inventory.append(item)
        return PickupResult("stored", item=item)
    return PickupResult("inventory_full", item=item)
