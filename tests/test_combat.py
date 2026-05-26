import random

from lemond_pygame.core.combat import (
    MONSTER_KINDS,
    _stat,
    dodge_chance,
    extra_attack_chance,
    generate_monster,
    try_attack,
)
from lemond_pygame.core.entities import Creature


def make(dex=0, str_=10, hp=20, armor=0):
    return Creature(kind="dummy", max_hp=hp, hp=hp, str_=str_, dex=dex, int_=0, armor=armor)


def test_stat_uses_integer_floor_division():
    # base + depth * num // den, matching the original integer arithmetic.
    assert _stat((2, 1, 3), 3) == 3  # ogre dex: 2 + 3//3
    assert _stat((2, 1, 3), 2) == 2  # 2 + 2//3 -> 2 + 0
    assert _stat((3, 1, 2), 5) == 5  # 3 + 5//2
    assert _stat((12, 3, 1), 3) == 21  # 12 + 3*3


def test_dodge_chance_is_bounded():
    assert dodge_chance(make(dex=0)) == 0.0
    assert dodge_chance(make(dex=10_000), dodge_skill=10_000) <= 0.6


def test_extra_attack_chance_is_bounded():
    assert extra_attack_chance(make(dex=0)) == 0.0
    assert extra_attack_chance(make(dex=10_000)) <= 0.30


def test_try_attack_can_be_forced_to_dodge():
    attacker = make(str_=10)
    defender = make(dex=40)  # high dex -> dodge chance is at its max
    rng = random.Random()
    rng.random = lambda: 0.0  # below any dodge chance
    dmg, dead, dodged = try_attack(attacker, defender, defender_armor=0, rng=rng)
    assert dodged is True
    assert dmg == 0
    assert defender.hp == defender.max_hp  # unchanged


def test_try_attack_applies_armor_and_damage():
    attacker = make(str_=10)  # melee_damage -> (5, 7)
    defender = make(dex=0, hp=20, armor=4)
    rng = random.Random()
    rng.random = lambda: 0.99  # never dodge
    rng.randint = lambda a, b: b  # max roll = 7
    dmg, dead, dodged = try_attack(attacker, defender, defender_armor=4, rng=rng)
    assert dodged is False
    assert dmg == 7 - 4 // 2  # armor halved
    assert defender.hp == 20 - dmg
    assert dead is False


def test_try_attack_reports_death():
    attacker = make(str_=10)
    defender = make(dex=0, hp=1, armor=0)
    rng = random.Random()
    rng.random = lambda: 0.99
    rng.randint = lambda a, b: b
    _dmg, dead, _dodged = try_attack(attacker, defender, defender_armor=0, rng=rng)
    assert dead is True
    assert defender.hp <= 0


def test_generate_monster_is_deterministic_and_valid():
    a = generate_monster(5, rng=random.Random(123))
    b = generate_monster(5, rng=random.Random(123))
    assert (a.kind, a.hp, a.str_, a.dex, a.armor) == (b.kind, b.hp, b.str_, b.dex, b.armor)
    assert a.kind in {k for k, _ in MONSTER_KINDS}
    assert a.glyph == a.kind
    assert a.hostile is True
    assert a.hp >= a.max_hp - a.max_hp  # hp positive and >= 0
    assert a.hp > 0
