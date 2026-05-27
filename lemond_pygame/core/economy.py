"""Prices for the merchant and the trainer. Pure and tunable in one place."""

from __future__ import annotations

from .entities import Item


def drop_tier(depth: int) -> int:
    """Tier of loot that drops on a given depth."""
    return 1 + min(5, depth // 2)


def shop_tier(depth: int) -> int:
    """Merchant stock is one tier above what drops on the current depth."""
    return min(6, drop_tier(depth) + 1)


def item_value(item: Item) -> int:
    return item.tier * 8 + item.power * 6


def buy_price(item: Item) -> int:
    return item_value(item) * 2  # merchant markup


def sell_price(item: Item) -> int:
    return max(1, item_value(item) // 2)


def stat_point_cost(hero) -> int:
    return 75 + hero.level * 35


def skill_point_cost(hero) -> int:
    return 130 + hero.level * 60
