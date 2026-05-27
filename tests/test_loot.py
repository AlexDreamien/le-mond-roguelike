from lemond_pygame.core.entities import EQUIP_SLOTS, Hero, Item
from lemond_pygame.core.loot import INVENTORY_LIMIT, floor_gold_amount, resolve_chest


class StubRandom:
    """Deterministic stand-in: random() replays a sequence, randint returns lo."""

    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def random(self):
        v = self.values[self.i]
        self.i += 1
        return v

    def randint(self, a, b):
        return a


def make_hero():
    return Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5)


def test_floor_gold_amount_is_positive_and_scales():
    assert floor_gold_amount(1, StubRandom([])) > 0
    shallow = floor_gold_amount(1)
    deep = floor_gold_amount(10)
    assert deep >= shallow  # range grows with depth


def test_chest_equips_into_empty_slot():
    h = make_hero()
    # 0.9 -> not the rare potion, 0.1 -> first loot row (sword, MAIN)
    result = resolve_chest(h, depth=3, rng=StubRandom([0.9, 0.1]))
    assert result.outcome == "equipped"
    assert h.equipment["MAIN"] is result.item


def test_chest_stores_when_slot_occupied():
    h = make_hero()
    for slot in EQUIP_SLOTS:
        h.equipment[slot] = Item(kind="sword", slot=slot, tier=1, power=1)
    result = resolve_chest(h, depth=3, rng=StubRandom([0.9, 0.1]))
    assert result.outcome == "stored"
    assert result.item in h.inventory


def test_chest_inventory_full_keeps_item():
    h = make_hero()
    for slot in EQUIP_SLOTS:
        h.equipment[slot] = Item(kind="sword", slot=slot, tier=1, power=1)
    h.inventory = [Item(kind="boots", slot="FEET", tier=1, power=1) for _ in range(INVENTORY_LIMIT)]
    result = resolve_chest(h, depth=3, rng=StubRandom([0.9, 0.1]))
    assert result.outcome == "inventory_full"
    assert len(h.inventory) == INVENTORY_LIMIT


def test_chest_can_give_potion():
    h = make_hero()
    result = resolve_chest(h, depth=3, rng=StubRandom([0.05]))  # < potion chance
    assert result.outcome == "potion"
    assert h.potions == 1
