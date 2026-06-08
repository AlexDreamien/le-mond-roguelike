from lemond_pygame.core.entities import Hero
from lemond_pygame.core.progression import add_skill, add_stat, auto_assign


def make_hero(class_kind="warrior", stat_points=0, skill_points=0):
    h = Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5, class_kind=class_kind)
    h.recompute_max_hp()  # keep max_hp consistent with str, as the game does
    h.hp = h.max_hp
    h.stat_points = stat_points
    h.skill_points = skill_points
    return h


def test_add_stat_consumes_a_point_and_raises_the_stat():
    h = make_hero(stat_points=1)
    assert add_stat(h, "dex") is True
    assert h.dex == 6
    assert h.stat_points == 0


def test_add_strength_increases_max_hp_and_heals_the_margin():
    h = make_hero(stat_points=1)
    h.hp = 10
    before_max = h.max_hp
    add_stat(h, "str")
    assert h.max_hp == before_max + 2  # recompute_max_hp = 16 + str*2
    assert h.hp == 12  # healed by the new margin


def test_add_intellect_increases_max_mana_and_grants_the_margin():
    h = make_hero(stat_points=1)
    h.recompute_max_mana()  # 10 + int*5... actually 10 + int*4
    h.mana = 5
    before_max = h.max_mana
    add_stat(h, "int")
    assert h.max_mana == before_max + 4  # recompute_max_mana = 10 + int*4
    assert h.mana == 9  # granted the new mana margin


def test_add_stat_fails_without_points():
    h = make_hero(stat_points=0)
    assert add_stat(h, "str") is False
    assert h.str_ == 5


def test_add_skill_consumes_a_point():
    h = make_hero(skill_points=2)
    assert add_skill(h, "MAGIC") is True
    assert h.skills["MAGIC"] == 1
    assert h.skill_points == 1


def test_auto_assign_spends_into_class_favored_stat_and_skill():
    h = make_hero(class_kind="thief", stat_points=3, skill_points=2)
    auto_assign(h)
    assert h.dex == 8  # thief favors dexterity
    assert h.skills["DODGE"] == 2
    assert h.stat_points == 0
    assert h.skill_points == 0


def test_auto_assign_can_target_one_category():
    h = make_hero(class_kind="mage", stat_points=2, skill_points=2)
    auto_assign(h, do_stats=True, do_skills=False)
    assert h.int_ == 7
    assert h.stat_points == 0
    assert h.skill_points == 2  # skills untouched
