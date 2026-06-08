"""Combat math and monster generation. Deterministic given the RNG state."""

from __future__ import annotations

import random

from .entities import Creature

# kind -> stat -> (base, numerator, denominator); value = base + depth * num // den.
# ``kind`` doubles as the sprite/glyph key and the localization key
# (see locales/*.json -> "monster.<kind>").
MONSTER_KINDS = [
    (
        "goblin",
        {
            "str": (3, 1, 1),
            "dex": (7, 2, 1),
            "int": (2, 0, 1),
            "hp": (10, 2, 1),
            "armor": (0, 0, 1),
        },
    ),
    (
        "orc",
        {
            "str": (8, 2, 1),
            "dex": (3, 1, 2),
            "int": (2, 0, 1),
            "hp": (18, 3, 1),
            "armor": (1, 1, 3),
        },
    ),
    (
        "bat",
        {
            "str": (2, 1, 2),
            "dex": (10, 2, 1),
            "int": (2, 0, 1),
            "hp": (6, 1, 1),
            "armor": (0, 0, 1),
        },
    ),
    (
        "ogre",
        {
            "str": (12, 3, 1),
            "dex": (2, 1, 3),
            "int": (2, 0, 1),
            "hp": (28, 4, 1),
            "armor": (2, 1, 2),
        },
    ),
    (
        "armor",
        {
            "str": (6, 2, 1),
            "dex": (3, 1, 2),
            "int": (2, 0, 1),
            "hp": (22, 3, 1),
            "armor": (4, 1, 2),
        },
    ),
    (
        "vampire",
        {
            "str": (3, 1, 1),
            "dex": (11, 2, 1),
            "int": (4, 1, 2),
            "hp": (8, 2, 1),
            "armor": (1, 1, 4),
        },
    ),
    (
        "ghost",
        {
            "str": (2, 0, 1),  # weak melee; a fragile, evasive ranged caster
            "dex": (9, 2, 1),  # high dex -> dodges the hero's arrows well
            "int": (5, 1, 1),
            "hp": (7, 1, 1),  # squishy: dies fast to one solid hit
            "armor": (0, 0, 1),
        },
    ),
]
MONSTER_WEIGHTS = [3, 3, 2, 1, 2, 1, 1]  # ..., vampire, ghost

# Heavy hitters are suppressed on the first floors so a depth-1 hero never faces
# an ogre or living armor in the opening room. Index order matches MONSTER_KINDS:
# goblin, orc, bat, ogre, armor, vampire, ghost.
_GATES = {
    3: ("ogre", "armor"),  # appear only from depth 3
    2: ("vampire", "ghost"),  # appear only from depth 2
}

# Caster monsters fire at the hero from range on a periodic tick when the hero is
# on a clear cardinal line within reach. ``dmg`` is (base, num, den): the rolled
# damage centre = base + depth*num//den. The hero may dodge (DODGE skill) and
# armour halves the hit, like melee. The vampire heals itself by damage dealt.
CASTERS = {
    "bat": {"range": 3, "dmg": (2, 1, 2), "effect": "ultrasound"},
    "ghost": {"range": 5, "dmg": (3, 1, 1), "effect": "magic_arrow"},
    "vampire": {"range": 4, "dmg": (2, 1, 1), "effect": "drain"},
}
MONSTER_TURN_INTERVAL = 1.2  # seconds between caster volleys


def caster_spec(kind: str):
    return CASTERS.get(kind)


def caster_damage(kind: str, depth: int) -> tuple[int, int] | None:
    """Damage range for a caster monster's ranged attack at ``depth``."""
    spec = CASTERS.get(kind)
    if not spec:
        return None
    centre = _stat(spec["dmg"], depth)
    return (max(1, centre - 1), centre + 1)


def _stat(spec: tuple[int, int, int], depth: int) -> int:
    base, num, den = spec
    return base + depth * num // den


def weights_for_depth(depth: int) -> list[int]:
    """Spawn weights with shallow-depth elites gated out (set to weight 0)."""
    weights = list(MONSTER_WEIGHTS)
    index = {kind: i for i, (kind, _) in enumerate(MONSTER_KINDS)}
    for min_depth, kinds in _GATES.items():
        if depth < min_depth:
            for kind in kinds:
                weights[index[kind]] = 0
    return weights


def generate_monster(depth: int, rng: random.Random | None = None) -> Creature:
    r = rng or random
    kind, spec = r.choices(MONSTER_KINDS, weights=weights_for_depth(depth), k=1)[0]
    base_hp = _stat(spec["hp"], depth)
    hp = base_hp + r.randint(0, max(1, base_hp // 4))
    return Creature(
        kind=kind,
        max_hp=hp,
        hp=hp,
        str_=_stat(spec["str"], depth),
        dex=_stat(spec["dex"], depth),
        int_=_stat(spec["int"], depth),
        glyph=kind,
        hostile=True,
        xp_reward=6 + depth * 3,
        armor=_stat(spec["armor"], depth),
    )


def dodge_chance(entity, dodge_skill: int = 0) -> float:
    base = min(40, entity.dex) * 0.01
    base += dodge_skill * 0.03
    return min(0.6, base)


def extra_attack_chance(entity) -> float:
    return min(0.30, entity.dex * 0.015)


def try_attack(attacker, defender, defender_armor, defender_dodge_skill=0, rng=None, damage=None):
    """Resolve one swing. Returns (damage, defender_dead, dodged).

    ``damage`` overrides the attacker's melee range with an explicit (min, max),
    used for ranged shots and caster monster attacks so the same dodge/armour
    resolution covers every kind of hit.
    """
    r = rng or random
    if r.random() < dodge_chance(defender, defender_dodge_skill):
        return 0, False, True
    base_min, base_max = damage if damage is not None else attacker.melee_damage()
    dmg = r.randint(base_min, base_max)
    dmg = max(1, dmg - defender_armor // 2)
    defender.hp -= dmg
    return dmg, defender.hp <= 0, False
