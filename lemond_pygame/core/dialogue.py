"""Branching dialogue for the named characters: Gildar, Sando, Rosmund's Shade.

Pure data + helpers; the pygame runner lives in ``ui_dialogue.py``. A conversation
is a dict of ``node_id -> Node``. Each option may apply effects to the hero
(faction favor, flags, a granted artifact), then either go to another node, end
the talk (``goto=None``), or — only at Rosmund — trigger an ending.

Option fields:
  text   : i18n key for the choice line
  goto   : next node id, or None to end the conversation
  effects: dict applied on selection (see ``apply_effects``)
  ending : ending token for Rosmund's hinge ("seize"/"destroy"/"cult"/"redeem");
           "destroy" resolves to seal-vs-destroy by inquisition favor (endings.py)
  cond   : a predicate name that must hold for the option to appear ("will_relics")

See docs/STORY.md section 4.5; text is written there and lives in the locales.
"""

from __future__ import annotations

START = "n1"

GILDAR = {
    "n1": {
        "text": "dlg.gildar.n1",
        "options": [
            {"text": "dlg.gildar.n1.opt1", "goto": "n2"},
            {"text": "dlg.gildar.n1.opt2", "goto": "n3"},
            {"text": "dlg.gildar.n1.opt3", "goto": "n4", "effects": {"cult_favor": 1}},
        ],
    },
    "n2": {
        "text": "dlg.gildar.n2",
        "options": [
            {"text": "dlg.gildar.n2.opt1", "goto": None, "effects": {"inq_favor": 1}},
            {"text": "dlg.gildar.n2.opt2", "goto": "n3"},
        ],
    },
    "n3": {
        "text": "dlg.gildar.n3",
        "options": [
            {"text": "dlg.gildar.n3.opt1", "goto": None},
            {"text": "dlg.gildar.n3.opt2", "goto": None, "effects": {"inq_favor": 1}},
        ],
    },
    "n4": {"text": "dlg.gildar.n4", "options": [{"text": "dlg.ok", "goto": None}]},
}

SANDO = {
    "n1": {
        "text": "dlg.sando.n1",
        "options": [
            {"text": "dlg.sando.n1.opt1", "goto": "n2"},
            {"text": "dlg.sando.n1.opt2", "goto": "n3"},
            {"text": "dlg.sando.n1.opt3", "goto": "n4", "effects": {"inq_favor": 1}},
        ],
    },
    "n2": {
        "text": "dlg.sando.n2",
        "options": [
            {"text": "dlg.sando.n2.opt1", "goto": None, "effects": {"inq_favor": 1}},
            {"text": "dlg.sando.n2.opt2", "goto": "n3", "effects": {"cult_favor": 1}},
        ],
    },
    "n3": {
        "text": "dlg.sando.n3",
        "options": [
            {
                "text": "dlg.sando.n3.opt1",
                "goto": None,
                "effects": {"cult_favor": 1, "grant": "open_eye"},
            },
            {"text": "dlg.sando.n3.opt2", "goto": None, "effects": {"inq_favor": 1}},
        ],
    },
    "n4": {"text": "dlg.sando.n4", "options": [{"text": "dlg.ok", "goto": None}]},
}

ROSMUND = {
    "n1": {
        "text": "dlg.rosmund.n1",
        "options": [
            {"text": "dlg.rosmund.n1.opt1", "goto": "n2"},
            {"text": "dlg.rosmund.n1.opt2", "goto": "n3"},
        ],
    },
    "n2": {
        "text": "dlg.rosmund.n2",
        "options": [
            {"text": "dlg.rosmund.n2.opt1", "ending": "seize"},
            {"text": "dlg.rosmund.n2.opt2", "ending": "destroy"},
            {"text": "dlg.rosmund.n2.opt3", "ending": "redeem", "cond": "will_relics"},
        ],
    },
    "n3": {
        "text": "dlg.rosmund.n3",
        "options": [
            {"text": "dlg.rosmund.n3.opt1", "ending": "destroy"},
            {"text": "dlg.rosmund.n3.opt2", "ending": "cult"},
            {"text": "dlg.rosmund.n3.opt3", "ending": "redeem", "cond": "will_relics"},
        ],
    },
}

CONVERSATIONS = {"gildar": GILDAR, "sando": SANDO, "rosmund": ROSMUND}
MET_FLAG = {"gildar": "gildar_met", "sando": "sando_met"}


def _cond_ok(cond: str | None, hero) -> bool:
    if cond is None:
        return True
    if cond == "will_relics":
        return hero.artifacts_of_will() >= 2
    return True


def visible_options(node: dict, hero) -> list[dict]:
    """Options whose condition is satisfied for this hero."""
    return [o for o in node["options"] if _cond_ok(o.get("cond"), hero)]


def apply_effects(hero, option: dict) -> str | None:
    """Apply an option's effects to the hero. Returns a granted artifact id, if any."""
    eff = option.get("effects", {})
    for k in ("inq_favor", "cult_favor"):
        if k in eff:
            hero.flags[k] = hero.flags.get(k, 0) + eff[k]
    return eff.get("grant")
