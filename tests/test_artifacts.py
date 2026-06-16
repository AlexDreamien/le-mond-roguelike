import json
from pathlib import Path

from lemond_pygame.core import economy
from lemond_pygame.core.artifacts import (
    ARTIFACTS,
    WILL_RELICS,
    is_artifact,
    make_artifact,
    maybe_artifact,
)
from lemond_pygame.core.entities import Hero, Item

LOCALES = Path(__file__).resolve().parents[1] / "lemond_pygame" / "locales"


def test_make_artifact_carries_unique_and_affixes():
    art = make_artifact("unwritten_blade", tier=4)
    assert art.unique == "unwritten_blade"
    assert is_artifact(art)
    assert art.affixes == ["vampiric", "sharp"]
    assert art.kind == "sword" and art.slot == "MAIN"
    assert not is_artifact(Item(kind="sword", slot="MAIN", tier=4))


def test_two_handed_flag_matches_kind():
    assert make_artifact("huntsmans_mark", 3).two_handed  # bow
    assert not make_artifact("first_draft", 3).two_handed  # body armour


def test_maybe_artifact_respects_chance():
    class R:
        def __init__(self, v):
            self.v = v

        def random(self):
            return self.v

        def choice(self, seq):
            return seq[0]

    assert maybe_artifact(5, 3, rng=R(0.99)) is None  # above the chance -> nothing
    got = maybe_artifact(5, 3, rng=R(0.0))  # below -> an artifact
    assert got is not None and is_artifact(got)


def test_artifacts_are_far_more_valuable():
    plain = Item(kind="sword", slot="MAIN", tier=4, power=4)
    art = make_artifact("unwritten_blade", tier=4)
    assert economy.item_value(art) > economy.item_value(plain) + 50


def test_will_relics_count_for_the_ending():
    h = Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5)
    assert h.artifacts_of_will() == 0
    h.inventory.append(make_artifact("unwritten_blade", 4))  # will-relic
    h.equipment["HEAD"] = make_artifact("scholars_eye", 4)  # will-relic
    h.inventory.append(make_artifact("first_draft", 4))  # not a will-relic
    assert h.artifacts_of_will() == 2
    assert {"unwritten_blade", "scholars_eye"} == WILL_RELICS


def _load(code):
    with open(LOCALES / f"{code}.json", encoding="utf-8") as f:
        return json.load(f)


def test_every_artifact_is_localized():
    en, ru = _load("en"), _load("ru")
    for aid in ARTIFACTS:
        for suffix in (".name", ".flavor"):
            key = "artifact." + aid + suffix
            assert key in en, f"missing in en: {key}"
            assert key in ru, f"missing in ru: {key}"


def test_artifact_uses_its_own_name():
    from lemond_pygame import i18n

    i18n.load_locales()
    i18n.set_locale("en")
    art = make_artifact("unwritten_blade", 4)
    assert i18n.item_name(art) == "Rosmund's Unwritten Blade"  # not the affix suffix
