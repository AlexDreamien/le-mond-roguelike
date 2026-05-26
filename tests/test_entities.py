import random

from lemond_pygame.core.entities import EQUIP_SLOTS, LOOT_TABLE, Hero, Item, random_loot


def make_hero(**kw):
    base = dict(kind="hero", max_hp=20, hp=20, str_=10, dex=5, int_=5)
    base.update(kw)
    return Hero(**base)


def test_weapon_damage_without_and_with_weapon():
    h = make_hero(str_=10)
    h.skills["MELEE"] = 0
    assert h.weapon_damage() == (5, 7)  # base = 1 + 10//2 = 6 -> (5, 7)
    h.equipment["MAIN"] = Item(kind="sword", slot="MAIN", tier=1, power=3)
    assert h.weapon_damage() == (8, 10)  # base += 3


def test_total_armor_counts_only_armor_slots_plus_str_bonus():
    h = make_hero(str_=10)
    h.equipment["BODY"] = Item(kind="armor", slot="BODY", tier=1, power=4)
    h.equipment["MAIN"] = Item(kind="sword", slot="MAIN", tier=1, power=9)  # weapon ignored
    assert h.total_armor() == 4 + 10 // 5


def test_gain_xp_levels_up_and_awards_points():
    h = make_hero()
    h.gain_xp(h.xp_to_next())  # exactly one level
    assert h.level == 2
    assert h.stat_points == 2
    assert h.skill_points == 1


def test_gain_xp_handles_multiple_levels_at_once():
    h = make_hero()
    h.gain_xp(1000)
    assert h.level > 2
    assert h.xp < h.xp_to_next()


def test_equip_blocks_shield_with_two_handed_weapon():
    h = make_hero()
    h.equipment["MAIN"] = Item(kind="axe", slot="MAIN", tier=1, power=2, two_handed=True)
    assert h.equip(Item(kind="shield", slot="OFF", tier=1, power=1)) == "equip.shield_blocked"


def test_equip_blocks_two_handed_weapon_with_shield():
    h = make_hero()
    h.equipment["OFF"] = Item(kind="shield", slot="OFF", tier=1, power=1)
    two_handed = Item(kind="axe", slot="MAIN", tier=1, power=2, two_handed=True)
    assert h.equip(two_handed) == "equip.two_handed_blocked"


def test_equip_ok_sets_slot():
    h = make_hero()
    sword = Item(kind="sword", slot="MAIN", tier=1, power=1)
    assert h.equip(sword) == "equip.ok"
    assert h.equipment["MAIN"] is sword


def test_random_loot_kinds_and_slots_are_valid():
    kinds = {row[1] for row in LOOT_TABLE}
    slots = set(EQUIP_SLOTS)
    rng = random.Random(0)
    for _ in range(200):
        it = random_loot(depth=6, rng=rng)
        assert it.kind in kinds
        assert it.slot in slots
        assert it.power >= it.tier  # power offset is non-negative


def test_random_loot_tier_scales_with_depth():
    rng = random.Random(1)
    shallow = random_loot(1, rng=rng)
    deep = random_loot(10, rng=rng)
    assert shallow.tier == 1
    assert deep.tier == 1 + min(5, 10 // 2)
