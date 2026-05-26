import pytest

from lemond_pygame import i18n
from lemond_pygame.core.entities import Creature, Item


@pytest.fixture(autouse=True)
def _fresh_locale():
    i18n.load_locales()
    i18n.set_locale("en")
    yield
    i18n.set_locale("en")


def test_locales_load_with_matching_keys():
    en = set(i18n._locales["en"])
    ru = set(i18n._locales["ru"])
    assert en == ru
    assert len(en) > 0


def test_t_formats_placeholders():
    assert i18n.t("msg.level_intro", depth=3) == "Level 3. Find the exit."


def test_t_falls_back_to_key_when_missing():
    assert i18n.t("totally.missing.key") == "totally.missing.key"


def test_set_and_get_locale():
    i18n.set_locale("ru")
    assert i18n.get_locale() == "ru"
    assert i18n.t("msg.wall") == "Стена."


def test_unknown_locale_is_ignored():
    i18n.set_locale("ru")
    i18n.set_locale("xx")  # not available
    assert i18n.get_locale() == "ru"


def test_next_locale_cycles():
    assert i18n.next_locale("en") == "ru"
    assert i18n.next_locale("ru") == "en"


def test_display_helpers_use_kind_keys():
    it = Item(kind="sword", slot="MAIN", tier=2, power=3)
    assert i18n.item_name(it) == "Sword 2"
    assert i18n.item_describe(it) == "Sword 2 (MAIN, +3)"
    monster = Creature(kind="goblin", max_hp=1, hp=1, str_=1, dex=1, int_=1)
    assert i18n.monster_name(monster) == "Goblin"
    assert i18n.class_name("warrior") == "Warrior"
