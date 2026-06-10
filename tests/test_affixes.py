import random

from lemond_pygame.core import economy
from lemond_pygame.core.affixes import (
    affix_value,
    equipment_bonus,
    item_bonus,
    roll_affixes,
)
from lemond_pygame.core.entities import Hero, Item
from lemond_pygame.core.weapons import magic_power, ranged_damage


class StubRandom:
    """random() replays a sequence; choice() picks the first option."""

    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def random(self):
        v = self.values[self.i]
        self.i += 1
        return v

    def choice(self, seq):
        return seq[0]


def hero(**kw):
    base = dict(kind="hero", max_hp=20, hp=20, str_=10, dex=10, int_=10)
    base.update(kw)
    h = Hero(**base)
    h.skills = {"MELEE": 2, "DODGE": 0, "MAGIC": 2, "ACCURACY": 2}
    return h


def test_affix_value_scales_with_tier():
    assert affix_value("sharp", 1) == 1
    assert affix_value("sharp", 4) == 3
    assert affix_value("sturdy", 6) == 4
    assert affix_value("arcane", 3) == 2
    assert affix_value("swift", 4) == 2
    assert affix_value("vampiric", 6) == 1  # presence flag, no scaling


def test_roll_respects_chance_and_pools():
    sword = Item(kind="sword", slot="MAIN", tier=2)
    roll_affixes(sword, rng=StubRandom([0.9]))  # above AFFIX_CHANCE -> nothing
    assert sword.affixes == []
    roll_affixes(sword, rng=StubRandom([0.1, 0.5]))  # one affix, no second
    assert sword.affixes == ["sharp"]  # first of the melee pool via choice()
    rare = Item(kind="sword", slot="MAIN", tier=2)
    roll_affixes(rare, rng=StubRandom([0.1, 0.05]))  # second roll under 0.10
    assert len(rare.affixes) == 2
    assert len(set(rare.affixes)) == 2  # distinct
    boots = Item(kind="boots", slot="FEET", tier=2)
    roll_affixes(boots, rng=StubRandom([0.1, 0.5]))
    assert boots.affixes == ["sturdy"]  # armour pool, never sharp
    potionish = Item(kind="misc", slot=None, tier=1)
    roll_affixes(potionish, rng=StubRandom([0.0]))
    assert potionish.affixes == []  # no pool -> never rolls


def test_bonuses_feed_damage_armor_and_dodge():
    h = hero()
    sword = Item(kind="sword", slot="MAIN", tier=4, power=4, affixes=["sharp"])
    h.equipment["MAIN"] = sword
    base = 1 + 10 // 2 + 2  # unarmed mid: 8
    assert h.weapon_damage() == (base + 4 + 3 - 1, base + 4 + 3 + 1)  # +power +sharp(3)
    h.equipment["BODY"] = Item(kind="armor", slot="BODY", tier=4, power=4, affixes=["sturdy"])
    assert h.total_armor() == 4 + 10 // 5 + 3  # power + str//5 + sturdy(3)
    h.equipment["FEET"] = Item(kind="boots", slot="FEET", tier=4, power=1, affixes=["swift"])
    assert h.dodge_bonus() == 2  # swift at tier 4
    assert equipment_bonus(h.equipment, "damage") == item_bonus(sword, "damage") == 3


def test_ranged_and_magic_affixes():
    h = hero()
    bow = Item(kind="bow", slot="MAIN", tier=2, power=1, affixes=["sharp"])
    plain = Item(kind="bow", slot="MAIN", tier=2, power=1)
    sharp_min, _ = ranged_damage(h, bow)
    plain_min, _ = ranged_damage(h, plain)
    assert sharp_min - plain_min == affix_value("sharp", 2)
    wand = Item(kind="wand", slot="MAIN", tier=3, power=3, affixes=["arcane"])
    assert magic_power(wand) == (3 - 1) + affix_value("arcane", 3)


def test_affixes_raise_item_value():
    plain = Item(kind="sword", slot="MAIN", tier=3, power=3)
    enchanted = Item(kind="sword", slot="MAIN", tier=3, power=3, affixes=["sharp", "swift"])
    assert economy.item_value(enchanted) == economy.item_value(plain) + 2 * (8 + 3 * 4)


def test_random_items_eventually_roll_affixes():
    from lemond_pygame.core.entities import random_item

    rng = random.Random(7)
    rolled = [len(random_item(3, rng=rng).affixes) for _ in range(300)]
    assert any(n == 1 for n in rolled)  # magic items appear
    assert any(n == 2 for n in rolled)  # rare items appear
    assert sum(1 for n in rolled if n > 0) < len(rolled) // 2  # but stay uncommon


def test_affixed_item_naming():
    from lemond_pygame import i18n

    i18n.load_locales()
    i18n.set_locale("en")
    named = Item(kind="sword", slot="MAIN", tier=3, power=3, affixes=["sharp"])
    assert i18n.item_name(named) == "Sword 3 of Sharpness"
    i18n.set_locale("ru")
    assert i18n.item_name(named) == "Меч 3 остроты"
    i18n.set_locale("en")
