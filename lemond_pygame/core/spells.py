"""Spell definitions and pure resolution for the hero's directional magic.

No pygame here. This module decides which spells are unlocked (by the magic
skill), how hard they hit (scaling with intellect and the magic skill), and
which monsters a cast strikes given the dungeon geometry. The presentation
layer turns the returned :class:`CastResult` into a projectile animation.

``shape`` describes how a spell resolves against the world:

* ``bolt``   - a single bolt that stops at the first monster or wall
* ``pierce`` - travels the whole range, hitting every monster in the line
* ``aoe``    - bursts at the impact tile, hitting it and tiles within ``radius``
* ``chain``  - hits the first monster, then arcs to nearby ones (decaying)
* ``meteor`` - like ``aoe`` but with a wider blast radius
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Spell:
    key: str  # i18n + identification, e.g. "magic_arrow"
    min_skill: int  # MAGIC skill required to unlock the spell
    shape: str
    color: tuple[int, int, int]  # projectile/impact tint used by the render layer
    mana_cost: int = 0  # mana spent per cast
    radius: int = 0  # aoe/meteor blast radius (Chebyshev distance)
    max_chains: int = 0  # chain: number of extra targets after the first
    chain_radius: int = 0  # chain: search radius for the next arc
    falloff: int = 100  # chain: percent of damage kept on each jump


# Ordered by power / unlock depth. Index also drives the menu order.
SPELLS: list[Spell] = [
    Spell("magic_arrow", 0, "bolt", (150, 200, 255), mana_cost=3),
    Spell("frost_spike", 2, "pierce", (150, 225, 245), mana_cost=5),
    Spell("fireball", 4, "aoe", (255, 140, 60), mana_cost=8, radius=1),
    Spell(
        "lightning_chain",
        6,
        "chain",
        (245, 235, 130),
        mana_cost=7,
        max_chains=3,
        chain_radius=3,
        falloff=70,
    ),
    Spell("meteor", 9, "meteor", (255, 95, 50), mana_cost=14, radius=2),
]
SPELL_BY_KEY = {s.key: s for s in SPELLS}

# Per-spell base range; the divisor controls how fast intellect extends it.
_RANGE_BASE = {
    "magic_arrow": 4,
    "frost_spike": 5,
    "fireball": 5,
    "lightning_chain": 5,
    "meteor": 6,
}


def available_spells(magic_skill: int) -> list[Spell]:
    """Spells the hero can currently cast, in menu order."""
    return [s for s in SPELLS if magic_skill >= s.min_skill]


def is_unlocked(spell: Spell, magic_skill: int) -> bool:
    return magic_skill >= spell.min_skill


def next_locked(magic_skill: int) -> Spell | None:
    """The next spell that will unlock as the magic skill grows, if any."""
    locked = [s for s in SPELLS if magic_skill < s.min_skill]
    return min(locked, key=lambda s: s.min_skill) if locked else None


def spell_range(spell: Spell, int_: int) -> int:
    """Reach in tiles. Direct attacks reach further per point of intellect than
    the heavy area spells."""
    div = 3 if spell.shape in ("bolt", "pierce", "chain") else 4
    return _RANGE_BASE[spell.key] + int_ // div


def spell_damage(spell: Spell, int_: int, magic_skill: int) -> int:
    """Hit for this much. Power scales primarily with intellect, and secondarily
    with the magic skill. The single-target bolt rewards investment the most;
    the area spells trade per-target damage for coverage."""
    table = {
        "magic_arrow": 4 + int_ + 2 * magic_skill,
        "frost_spike": 3 + int_ + magic_skill,
        "fireball": 5 + int_ + magic_skill,
        "lightning_chain": 4 + int_ + magic_skill,
        "meteor": 8 + 2 * int_ + 2 * magic_skill,
    }
    return max(1, table[spell.key])


@dataclass
class Hit:
    pos: tuple[int, int]
    damage: int


@dataclass
class CastResult:
    spell: Spell
    path: list[tuple[int, int]]  # tiles the projectile flies through (origin excluded)
    impact: tuple[int, int]  # tile where the spell bursts
    hits: list[Hit] = field(default_factory=list)

    @property
    def hit_count(self) -> int:
        return len(self.hits)


def _square(center: tuple[int, int], radius: int) -> list[tuple[int, int]]:
    cx, cy = center
    return [
        (x, y)
        for y in range(cy - radius, cy + radius + 1)
        for x in range(cx - radius, cx + radius + 1)
    ]


def resolve(
    spell: Spell,
    origin: tuple[int, int],
    direction: tuple[int, int],
    blocked,
    monsters,
    int_: int,
    magic_skill: int,
) -> CastResult:
    """Resolve a cast without mutating anything.

    ``blocked(x, y)`` returns True for walls and out-of-bounds tiles.
    ``monsters`` is an iterable of tiles currently occupied by a monster.
    """
    dx, dy = direction
    ox, oy = origin
    reach = spell_range(spell, int_)
    dmg = spell_damage(spell, int_, magic_skill)
    monster_set = set(monsters)

    path: list[tuple[int, int]] = []
    impact = origin
    first_monster: tuple[int, int] | None = None
    for i in range(1, reach + 1):
        x, y = ox + dx * i, oy + dy * i
        if blocked(x, y):
            break
        path.append((x, y))
        impact = (x, y)
        if (x, y) in monster_set:
            if first_monster is None:
                first_monster = (x, y)
            if spell.shape != "pierce":  # pierce flies through everything
                break

    hits: list[Hit] = []
    if spell.shape == "bolt":
        if first_monster is not None:
            hits.append(Hit(first_monster, dmg))
    elif spell.shape == "pierce":
        hits.extend(Hit(cell, dmg) for cell in path if cell in monster_set)
    elif spell.shape in ("aoe", "meteor"):
        hits.extend(Hit(cell, dmg) for cell in _square(impact, spell.radius) if cell in monster_set)
    elif spell.shape == "chain" and first_monster is not None:
        hits.append(Hit(first_monster, dmg))
        struck = {first_monster}
        cur = first_monster
        cur_dmg = dmg
        for _ in range(spell.max_chains):
            cur_dmg = max(1, cur_dmg * spell.falloff // 100)
            candidates = [
                p
                for p in monster_set
                if p not in struck
                and abs(p[0] - cur[0]) <= spell.chain_radius
                and abs(p[1] - cur[1]) <= spell.chain_radius
            ]
            if not candidates:
                break
            nxt = min(
                candidates,
                key=lambda p: (abs(p[0] - cur[0]) + abs(p[1] - cur[1]), p),
            )
            hits.append(Hit(nxt, cur_dmg))
            struck.add(nxt)
            cur = nxt

    return CastResult(spell=spell, path=path, impact=impact, hits=hits)
