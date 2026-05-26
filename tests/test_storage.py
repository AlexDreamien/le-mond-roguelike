from lemond_pygame.storage import _item_from_dict


def test_new_format_round_trips():
    it = _item_from_dict({"kind": "sword", "slot": "MAIN", "tier": 2, "power": 3})
    assert (it.kind, it.tier, it.slot, it.power) == ("sword", 2, "MAIN", 3)


def test_legacy_russian_name_migrates_to_kind_and_tier():
    it = _item_from_dict({"name": "Меч 2", "slot": "MAIN", "power": 1, "two_handed": False})
    assert it.kind == "sword"
    assert it.tier == 2


def test_legacy_roman_numeral_name_keeps_tier_one():
    it = _item_from_dict({"name": "Посох I", "slot": "MAIN", "power": 1})
    assert it.kind == "staff"
    assert it.tier == 1


def test_legacy_unknown_name_falls_back_to_slot_default():
    it = _item_from_dict({"name": "Бубен 3", "slot": "OFF", "power": 1})
    assert it.kind == "shield"  # OFF slot default
    assert it.tier == 3


def test_legacy_missing_name_uses_slot_default():
    it = _item_from_dict({"slot": "BODY", "power": 2})
    assert it.kind == "armor"
    assert it.tier == 1
