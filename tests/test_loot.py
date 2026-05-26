from lemond_pygame.core.entities import EQUIP_SLOTS, Hero, Item
from lemond_pygame.core.loot import INVENTORY_LIMIT, resolve_pickup


class StubRandom:
    """Returns a fixed sequence from ``random()``; that is all the loot code uses."""

    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def random(self):
        v = self.values[self.i]
        self.i += 1
        return v


def make_hero():
    return Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5)


def test_potion_outcome_increments_potions():
    h = make_hero()
    result = resolve_pickup(h, depth=3, rng=StubRandom([0.1]))  # < POTION_CHANCE
    assert result.outcome == "potion"
    assert h.potions == 1


def test_equipped_outcome_when_slot_is_empty():
    h = make_hero()  # all equipment slots are None
    # 0.5 -> not a potion, 0.1 -> first loot row (sword, MAIN)
    result = resolve_pickup(h, depth=3, rng=StubRandom([0.5, 0.1]))
    assert result.outcome == "equipped"
    assert result.equip_status == "equip.ok"
    assert h.equipment["MAIN"] is result.item


def test_stored_outcome_when_slot_is_occupied():
    h = make_hero()
    for slot in EQUIP_SLOTS:
        h.equipment[slot] = Item(kind="sword", slot=slot, tier=1, power=1)
    result = resolve_pickup(h, depth=3, rng=StubRandom([0.5, 0.1]))
    assert result.outcome == "stored"
    assert result.item in h.inventory


def test_inventory_full_outcome():
    h = make_hero()
    for slot in EQUIP_SLOTS:
        h.equipment[slot] = Item(kind="sword", slot=slot, tier=1, power=1)
    h.inventory = [Item(kind="boots", slot="FEET", tier=1, power=1) for _ in range(INVENTORY_LIMIT)]
    result = resolve_pickup(h, depth=3, rng=StubRandom([0.5, 0.1]))
    assert result.outcome == "inventory_full"
    assert len(h.inventory) == INVENTORY_LIMIT  # nothing added
