from lemond_pygame.core.entities import Hero, Item
from lemond_pygame.core.weapons import (
    can_equip,
    category,
    governing_skill,
    magic_power,
    ranged_damage,
    requirements,
    weapon_range,
)


def hero(str_=5, dex=5, int_=5, melee=0, acc=0, magic=0):
    h = Hero(kind="hero", max_hp=20, hp=20, str_=str_, dex=dex, int_=int_)
    h.skills = {"MELEE": melee, "DODGE": 0, "MAGIC": magic, "ACCURACY": acc}
    return h


def test_categories_and_governing_skills():
    assert category("sword") == "melee"
    assert category("bow") == "ranged"
    assert category("wand") == "magic"
    assert category("shield") is None  # not a weapon
    assert governing_skill("crossbow") == "ACCURACY"
    assert governing_skill("staff") == "MAGIC"


def test_requirements_scale_with_tier():
    # primary = 4 + 2T, secondary = 2 + T, skill = T - 1.
    req1 = requirements(Item(kind="sword", slot="MAIN", tier=1))
    assert req1 == {"str": 6, "dex": 3, "skill_name": "MELEE", "skill_level": 0}
    req3 = requirements(Item(kind="sword", slot="MAIN", tier=3))
    assert req3["str"] == 10 and req3["dex"] == 5 and req3["skill_level"] == 2
    # single-stat weapon has no secondary.
    assert "dex" not in requirements(Item(kind="axe", slot="MAIN", tier=2))
    # non-weapons have no requirements.
    assert requirements(Item(kind="boots", slot="FEET", tier=3)) == {}


def test_can_equip_gates_on_stat_and_skill():
    bow1 = Item(kind="bow", slot="MAIN", tier=1)  # needs dex 6, ACCURACY 0
    assert can_equip(hero(dex=4), bow1) == (False, "dex")
    assert can_equip(hero(dex=6), bow1) == (True, None)
    bow3 = Item(kind="bow", slot="MAIN", tier=3)  # needs dex 10, ACCURACY 2
    assert can_equip(hero(dex=12, acc=1), bow3) == (False, "ACCURACY")
    assert can_equip(hero(dex=12, acc=2), bow3) == (True, None)


def test_ranged_damage_scales_and_crossbow_hits_harder():
    h = hero(dex=10, acc=3)  # flat = 1 + 10//2 + 3 = 9
    bow = Item(kind="bow", slot="MAIN", tier=2, power=2)
    xbow = Item(kind="crossbow", slot="MAIN", tier=2, power=3)
    assert ranged_damage(h, bow) == (10, 12)  # mid = 9 + 2 = 11
    assert ranged_damage(h, xbow) == (19, 23)  # mid = 2*9 + 3 = 21, stronger per bolt
    assert weapon_range(h, xbow) >= weapon_range(h, bow)


def test_magic_power_staff_beats_wand():
    staff = Item(kind="staff", slot="MAIN", tier=3, power=3)
    wand = Item(kind="wand", slot="MAIN", tier=3, power=3)
    assert magic_power(staff) == 3
    assert magic_power(wand) == 2  # one less than the staff
    assert magic_power(Item(kind="sword", slot="MAIN", tier=3, power=3)) == 0
