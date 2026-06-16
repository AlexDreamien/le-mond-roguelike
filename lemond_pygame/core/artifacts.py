"""Unique gold artifacts: a legendary tier above ordinary affixed gear.

Each artifact is a normal equipment kind carrying a fixed, strong affix loadout, a
unique name (gold rarity), and flavor — so it reuses the whole affix pipeline
(damage / armour / dodge / lifesteal / value / tooltip) while reading as a named
legend. Two are Rosmund's *will-relics*, flagged for the future "Rosmund's
Redemption" ending (``Hero.artifacts_of_will``). Bespoke non-stat powers from the
design (floor reveal, corruption pause, conditional burst) are deferred to the
Darkness/endings phase; here the legend lives in the fixed roll + name + flavor.

Pure rules; no pygame. Display strings live under ``artifact.<id>.name`` /
``.flavor`` in the locale files. See ``docs/STORY.md`` section 4.4.
"""

from __future__ import annotations

import random

from .entities import Item

# id -> (base kind, slot, affixes that all function in that slot, will_relic).
# Affixes are chosen so each one actually applies where the item is worn.
ARTIFACTS = {
    "unwritten_blade": ("sword", "MAIN", ["vampiric", "sharp"], True),
    "scholars_eye": ("helmet", "HEAD", ["sturdy", "swift"], True),
    "first_draft": ("armor", "BODY", ["sturdy", "swift"], False),
    "sealbearers_ward": ("shield", "OFF", ["sturdy", "swift"], False),
    "concordance_quill": ("wand", "MAIN", ["arcane", "swift"], False),
    "huntsmans_mark": ("bow", "MAIN", ["sharp", "swift"], False),
    "open_eye": ("staff", "MAIN", ["arcane", "swift"], False),
}

WILL_RELICS = {a for a, spec in ARTIFACTS.items() if spec[3]}

ARTIFACT_BASE_CHANCE = 0.04  # base chance a chest yields an artifact instead of loot
ARTIFACT_DEPTH_CHANCE = 0.006  # added per depth, so deeper runs see more legends


def is_artifact(item) -> bool:
    return bool(getattr(item, "unique", ""))


def make_artifact(artifact_id: str, tier: int) -> Item:
    """Build the named artifact at the given tier."""
    kind, slot, affixes, _will = ARTIFACTS[artifact_id]
    two_handed = kind in ("bow", "crossbow", "staff", "axe")
    return Item(
        kind=kind,
        slot=slot,
        tier=tier,
        power=tier,
        two_handed=two_handed,
        affixes=list(affixes),
        unique=artifact_id,
    )


def artifact_chance(depth: int) -> float:
    return min(0.12, ARTIFACT_BASE_CHANCE + depth * ARTIFACT_DEPTH_CHANCE)


def maybe_artifact(depth: int, tier: int, rng=None) -> Item | None:
    """With a small depth-scaled chance, roll a random unique artifact."""
    r = rng or random
    if r.random() >= artifact_chance(depth):
        return None
    return make_artifact(r.choice(list(ARTIFACTS)), tier)
