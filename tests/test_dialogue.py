import json
from pathlib import Path

from lemond_pygame.core import dialogue as dlg
from lemond_pygame.core import endings
from lemond_pygame.core.artifacts import make_artifact
from lemond_pygame.core.entities import Hero

LOCALES = Path(__file__).resolve().parents[1] / "lemond_pygame" / "locales"


def _load(code):
    with open(LOCALES / f"{code}.json", encoding="utf-8") as f:
        return json.load(f)


def hero():
    return Hero(kind="hero", max_hp=20, hp=20, str_=5, dex=5, int_=5)


def test_will_relic_options_hidden_without_relics():
    h = hero()
    node = dlg.ROSMUND["n2"]
    opts = dlg.visible_options(node, h)
    assert all(o.get("ending") != "redeem" for o in opts)  # E5 hidden
    h.inventory += [make_artifact("unwritten_blade", 4), make_artifact("scholars_eye", 4)]
    opts = dlg.visible_options(node, h)
    assert any(o.get("ending") == "redeem" for o in opts)  # E5 now offered


def test_apply_effects_changes_favor_and_grants():
    h = hero()
    grant = dlg.apply_effects(h, {"effects": {"cult_favor": 1, "grant": "open_eye"}})
    assert h.flags["cult_favor"] == 1
    assert grant == "open_eye"
    dlg.apply_effects(h, {"effects": {"inq_favor": 1}})
    assert h.flags["inq_favor"] == 1


def test_endings_resolve_destroy_split():
    h = hero()
    assert endings.resolve("destroy", h) == endings.DESTROY  # low favor -> unwrite
    h.flags["inq_favor"] = 2
    assert endings.resolve("destroy", h) == endings.SEAL  # high favor -> seal
    assert endings.resolve("seize", h) == endings.SEIZE  # others pass through
    assert endings.resolve("cult", h) == endings.CULT
    assert endings.resolve("redeem", h) == endings.REDEEM


def test_met_flags_mapping():
    assert dlg.MET_FLAG == {"gildar": "gildar_met", "sando": "sando_met"}
    assert "rosmund" not in dlg.MET_FLAG  # Rosmund is the finale, not a one-off


def test_every_dialogue_and_ending_key_is_localized():
    en, ru = _load("en"), _load("ru")
    keys = {"dlg.ok", "ui.dialogue.hint", "ending.close"}
    for who, convo in dlg.CONVERSATIONS.items():
        keys.add("dlg." + who + ".name")
        for node in convo.values():
            keys.add(node["text"])
            for opt in node["options"]:
                keys.add(opt["text"])
    for eid in endings.ALL:
        keys.add("ending." + eid + ".title")
        keys.add("ending." + eid + ".body")
    missing_en = sorted(k for k in keys if k not in en)
    missing_ru = sorted(k for k in keys if k not in ru)
    assert not missing_en, f"missing in en: {missing_en}"
    assert not missing_ru, f"missing in ru: {missing_ru}"
