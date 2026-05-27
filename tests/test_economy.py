from lemond_pygame.core import economy
from lemond_pygame.core.entities import Hero, Item


def test_drop_and_shop_tiers():
    assert economy.drop_tier(1) == 1
    assert economy.drop_tier(4) == 3
    assert economy.shop_tier(4) == 4  # one above the drop tier
    assert economy.shop_tier(20) == 6  # capped


def test_buy_price_exceeds_sell_price():
    it = Item(kind="sword", slot="MAIN", tier=3, power=3)
    assert economy.buy_price(it) > economy.sell_price(it)
    assert economy.sell_price(it) >= 1


def test_value_scales_with_tier_and_power():
    cheap = Item(kind="sword", slot="MAIN", tier=1, power=1)
    rich = Item(kind="sword", slot="MAIN", tier=5, power=6)
    assert economy.item_value(rich) > economy.item_value(cheap)


def test_training_costs_rise_with_level():
    h1 = Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5)
    h1.level = 1
    h9 = Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5)
    h9.level = 9
    assert economy.stat_point_cost(h9) > economy.stat_point_cost(h1)
    assert economy.skill_point_cost(h1) > economy.stat_point_cost(h1)  # skills cost more
    # Pinned values after the economy rebalance (gold income was trimmed to match).
    assert economy.stat_point_cost(h1) == 75 + 35
    assert economy.skill_point_cost(h1) == 130 + 60
