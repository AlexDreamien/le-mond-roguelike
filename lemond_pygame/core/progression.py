"""Spending stat and skill points, manually or auto-distributed by class."""

from __future__ import annotations

from .entities import Hero

# class_kind -> (favored stat, favored skill) used for auto-distribution.
PRIMARY_STAT = {"warrior": "str", "thief": "dex", "mage": "int"}
PRIMARY_SKILL = {"warrior": "MELEE", "thief": "DODGE", "mage": "MAGIC"}

STATS = ("str", "dex", "int")
SKILLS = ("MELEE", "DODGE", "MAGIC")


def add_stat(hero: Hero, stat: str) -> bool:
    """Spend one stat point on ``stat``. Returns False if none available."""
    if hero.stat_points <= 0 or stat not in STATS:
        return False
    hero.stat_points -= 1
    if stat == "str":
        before = hero.max_hp
        hero.str_ += 1
        hero.recompute_max_hp()
        hero.hp += hero.max_hp - before  # gaining toughness heals the new margin
    elif stat == "dex":
        hero.dex += 1
    else:
        hero.int_ += 1
    return True


def add_skill(hero: Hero, skill: str) -> bool:
    """Spend one skill point on ``skill``. Returns False if none available."""
    if hero.skill_points <= 0 or skill not in SKILLS:
        return False
    hero.skill_points -= 1
    hero.skills[skill] += 1
    return True


def auto_assign(hero: Hero, do_stats: bool = True, do_skills: bool = True) -> None:
    """Spend pending points into the hero's class-favored stat/skill."""
    if do_stats:
        stat = PRIMARY_STAT.get(hero.class_kind, "str")
        while add_stat(hero, stat):
            pass
    if do_skills:
        skill = PRIMARY_SKILL.get(hero.class_kind, "MELEE")
        while add_skill(hero, skill):
            pass
