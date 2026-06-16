import json
import random
from pathlib import Path

from lemond_pygame.core import lore

LOCALES = Path(__file__).resolve().parents[1] / "lemond_pygame" / "locales"


def _load(code):
    with open(LOCALES / f"{code}.json", encoding="utf-8") as f:
        return json.load(f)


def test_band_for_depth_maps_acts():
    assert lore.band_for_depth(1) == lore.ACT1
    assert lore.band_for_depth(3) == lore.ACT1
    assert lore.band_for_depth(4) == lore.ACT2
    assert lore.band_for_depth(7) == lore.ACT2
    assert lore.band_for_depth(8) == lore.ACT3
    assert lore.band_for_depth(12) == lore.ACT4
    assert lore.band_for_depth(99) == lore.ACT4


def test_pick_lore_prefers_current_band_and_skips_seen():
    # At depth 1 only act-1 lore is eligible.
    keys = lore.pick_lore_keys(1, 5, exclude=set(), rng=random.Random(0))
    assert keys and all(lore.NOTES.get(k, lore.INSCRIPTIONS.get(k)) == lore.ACT1 for k in keys)
    # Seen keys are never re-picked.
    seen = set(keys)
    more = lore.pick_lore_keys(1, 5, exclude=seen, rng=random.Random(0))
    assert not (set(more) & seen)


def test_deep_floor_can_surface_earlier_lore():
    keys = lore.pick_lore_keys(12, 40, exclude=set(), rng=random.Random(1))
    bands = {lore.NOTES.get(k, lore.INSCRIPTIONS.get(k)) for k in keys}
    assert lore.ACT4 in bands  # current band present
    assert len(bands) > 1  # but earlier bands can show too


def test_musings_for_trigger():
    assert set(lore.musings_for_trigger("gold")) == {"muse.gold.a", "muse.gold.b"}
    assert lore.musings_for_trigger("band:act4") == ["muse.band.act4"]
    assert lore.musings_for_trigger("respawn") == ["muse.respawn.reveal"]


def test_every_lore_key_is_localized_in_both_languages():
    en, ru = _load("en"), _load("ru")
    keys = set(lore.NOTES) | set(lore.INSCRIPTIONS) | set(lore.MUSINGS)
    keys |= {"ui.note.title", "ui.note.found", "ui.note.inscription", "ui.note.close"}
    missing_en = sorted(k for k in keys if k not in en)
    missing_ru = sorted(k for k in keys if k not in ru)
    assert not missing_en, f"missing in en: {missing_en}"
    assert not missing_ru, f"missing in ru: {missing_ru}"


def test_inscription_classifier():
    assert lore.is_inscription("inscr.04")
    assert not lore.is_inscription("note.04")
