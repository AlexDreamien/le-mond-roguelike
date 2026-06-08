from lemond_pygame.core.spells import (
    SPELL_BY_KEY,
    SPELLS,
    available_spells,
    is_unlocked,
    next_locked,
    resolve,
    spell_damage,
    spell_range,
)


def test_every_spell_has_a_positive_mana_cost():
    assert all(s.mana_cost > 0 for s in SPELLS)
    # Costlier spells hit harder: meteor (biggest) costs the most.
    assert SPELL_BY_KEY["meteor"].mana_cost == max(s.mana_cost for s in SPELLS)
    assert SPELL_BY_KEY["magic_arrow"].mana_cost < SPELL_BY_KEY["meteor"].mana_cost


def test_next_locked_tracks_the_upcoming_unlock():
    assert next_locked(0).key == "frost_spike"  # first spell above the starter
    assert next_locked(4).key == "lightning_chain"
    assert next_locked(9) is None  # everything unlocked


def _blocked_from(walls, w=20, h=20):
    wall_set = set(walls)

    def blocked(x, y):
        return not (0 <= x < w and 0 <= y < h) or (x, y) in wall_set

    return blocked


def test_availability_grows_with_magic_skill():
    assert [s.key for s in available_spells(0)] == ["magic_arrow"]
    assert [s.key for s in available_spells(4)] == ["magic_arrow", "frost_spike", "fireball"]
    assert len(available_spells(9)) == len(SPELLS)  # everything unlocked
    assert is_unlocked(SPELL_BY_KEY["meteor"], 9)
    assert not is_unlocked(SPELL_BY_KEY["meteor"], 8)


def test_damage_scales_with_intellect_and_skill():
    arrow = SPELL_BY_KEY["magic_arrow"]
    assert spell_damage(arrow, 0, 0) >= 1
    assert spell_damage(arrow, 10, 0) > spell_damage(arrow, 0, 0)
    assert spell_damage(arrow, 0, 5) > spell_damage(arrow, 0, 0)
    # Meteor scales the hardest with intellect (2x term).
    meteor = SPELL_BY_KEY["meteor"]
    assert spell_damage(meteor, 10, 0) - spell_damage(meteor, 0, 0) == 20


def test_range_scales_with_intellect():
    arrow = SPELL_BY_KEY["magic_arrow"]
    assert spell_range(arrow, 9) > spell_range(arrow, 0)


def test_bolt_stops_at_first_monster():
    arrow = SPELL_BY_KEY["magic_arrow"]
    res = resolve(arrow, (5, 5), (1, 0), _blocked_from([]), {(7, 5), (9, 5)}, int_=6, magic_skill=0)
    assert [h.pos for h in res.hits] == [(7, 5)]  # only the nearest
    assert res.impact == (7, 5)


def test_bolt_misses_into_a_wall():
    arrow = SPELL_BY_KEY["magic_arrow"]
    res = resolve(arrow, (5, 5), (1, 0), _blocked_from([(7, 5)]), {(9, 5)}, int_=6, magic_skill=0)
    assert res.hits == []  # wall at (7,5) blocks before the monster at (9,5)
    assert res.impact == (6, 5)  # last open tile


def test_pierce_hits_every_monster_in_the_line():
    frost = SPELL_BY_KEY["frost_spike"]
    res = resolve(frost, (5, 5), (1, 0), _blocked_from([]), {(6, 5), (8, 5)}, int_=6, magic_skill=2)
    assert {h.pos for h in res.hits} == {(6, 5), (8, 5)}


def test_pierce_stops_at_a_wall():
    frost = SPELL_BY_KEY["frost_spike"]
    res = resolve(frost, (5, 5), (1, 0), _blocked_from([(7, 5)]), {(6, 5), (8, 5)}, 6, 2)
    assert {h.pos for h in res.hits} == {(6, 5)}  # (8,5) is behind the wall


def test_aoe_hits_impact_and_neighbours():
    fire = SPELL_BY_KEY["fireball"]
    monsters = {(8, 5), (8, 6), (8, 4), (9, 5)}  # cluster around impact (8,5)
    res = resolve(fire, (5, 5), (1, 0), _blocked_from([]), monsters, int_=6, magic_skill=4)
    assert res.impact == (8, 5)
    assert {h.pos for h in res.hits} == monsters  # all within radius 1


def test_meteor_uses_a_wide_radius():
    meteor = SPELL_BY_KEY["meteor"]
    monsters = {(8, 5), (8, 7), (10, 5)}  # within Chebyshev radius 2 of (8,5)
    res = resolve(meteor, (5, 5), (1, 0), _blocked_from([]), monsters, int_=6, magic_skill=9)
    assert {h.pos for h in res.hits} == monsters


def test_chain_arcs_to_nearby_monsters_with_falloff():
    chain = SPELL_BY_KEY["lightning_chain"]
    monsters = {(7, 5), (8, 6), (9, 6)}  # primary then two within chain radius
    res = resolve(chain, (5, 5), (1, 0), _blocked_from([]), monsters, int_=6, magic_skill=6)
    assert res.hits[0].pos == (7, 5)  # primary is the first monster struck
    assert len(res.hits) == 3  # primary + 2 arcs (cap is max_chains=3)
    # Damage decays along the arc.
    assert res.hits[1].damage < res.hits[0].damage
    assert res.hits[2].damage <= res.hits[1].damage


def test_chain_is_capped_by_max_chains():
    chain = SPELL_BY_KEY["lightning_chain"]
    # A dense blob of adjacent monsters; only 1 + max_chains may be hit.
    blob = {(7, 5), (7, 6), (8, 5), (8, 6), (8, 7), (7, 7)}
    res = resolve(chain, (5, 5), (1, 0), _blocked_from([]), blob, int_=6, magic_skill=6)
    assert len(res.hits) == 1 + chain.max_chains
