"""Story lore: explorer notes, wall inscriptions, and hero musings.

Pure data + deterministic selection. The display text lives in the locale files
under ``note.*`` / ``inscr.*`` / ``muse.*``; this module holds the pools, the
depth-band gating, and the musing triggers. See ``docs/STORY.md`` for the canon.

Lore is placed using the *global* RNG (not the depth-seeded dungeon RNG), so the
pieces a player finds vary across runs and the story accretes rather than
repeating floor-for-floor.
"""

from __future__ import annotations

import random

ACT1, ACT2, ACT3, ACT4 = "act1", "act2", "act3", "act4"


def band_for_depth(depth: int) -> str:
    """Which narrative act a depth belongs to."""
    if depth <= 3:
        return ACT1
    if depth <= 7:
        return ACT2
    if depth <= 11:
        return ACT3
    return ACT4


# Explorer note id -> the act band it may appear in. Together the notes tell
# Rosmund's thread and foreshadow the twist; see docs/STORY.md section 4.1.
NOTES: dict[str, str] = {
    "note.01": ACT1, "note.02": ACT1, "note.03": ACT1, "note.04": ACT1, "note.05": ACT1,
    "note.06": ACT2, "note.07": ACT2, "note.08": ACT2, "note.09": ACT2, "note.10": ACT2,
    "note.11": ACT2,
    "note.12": ACT3, "note.13": ACT3, "note.14": ACT3, "note.15": ACT3, "note.16": ACT3,
    "note.17": ACT3,
    "note.18": ACT4, "note.19": ACT4, "note.20": ACT4, "note.21": ACT4, "note.22": ACT4,
}  # fmt: skip

# Wall inscription id -> band (terser, ominous; some in the dead tongue).
INSCRIPTIONS: dict[str, str] = {
    "inscr.01": ACT1, "inscr.02": ACT1,
    "inscr.03": ACT2, "inscr.04": ACT2,
    "inscr.05": ACT3, "inscr.06": ACT3, "inscr.07": ACT3,
    "inscr.08": ACT4, "inscr.09": ACT4,
}  # fmt: skip

# Hero musing id -> the trigger that fires it. Triggers available in the MVP:
# "band:<act>" (first time the hero enters that act), "gold" (gold artifact found),
# "lowhp", "slaughter" (kill streak), "respawn" (after several deaths). The "dark.*"
# musings wait for the Darkness mechanic (later phase).
MUSINGS: dict[str, str] = {
    "muse.band.act1": "band:act1",
    "muse.band.act2": "band:act2",
    "muse.band.act3": "band:act3",
    "muse.band.act4": "band:act4",
    "muse.gold.a": "gold",
    "muse.gold.b": "gold",
    "muse.lowhp.a": "lowhp",
    "muse.lowhp.b": "lowhp",
    "muse.slaughter.a": "slaughter",
    "muse.slaughter.b": "slaughter",
    "muse.dark.first": "dark",
    "muse.dark.engulf": "dark",
    "muse.respawn.reveal": "respawn",
    "muse.ending.inq": "ending",
    "muse.ending.cult": "ending",
    "muse.ending.self": "ending",
}

RESPAWN_REVEAL_DEATHS = 5  # the respawn-reveal musing fires once at this death count


def _band_at_or_before(depth: int) -> list[str]:
    """The bands appropriate at ``depth`` (current band plus earlier ones), so a
    deep floor can still surface earlier lore the player missed."""
    order = [ACT1, ACT2, ACT3, ACT4]
    return order[: order.index(band_for_depth(depth)) + 1]


def pick_lore_keys(depth: int, count: int, exclude: set[str], rng=None) -> list[str]:
    """Pick up to ``count`` distinct note/inscription keys to place on a floor.

    Favours the current act band but may surface earlier, unseen lore. Already
    seen keys in ``exclude`` are skipped so the player keeps finding new pieces.
    """
    r = rng or random
    bands = set(_band_at_or_before(depth))
    pool = [k for k, b in NOTES.items() if b in bands and k not in exclude]
    pool += [k for k, b in INSCRIPTIONS.items() if b in bands and k not in exclude]
    if not pool:
        return []
    r.shuffle(pool)
    # Weight toward the current band by sorting current-band entries first.
    cur = band_for_depth(depth)
    pool.sort(key=lambda k: 0 if NOTES.get(k, INSCRIPTIONS.get(k)) == cur else 1)
    return pool[:count]


def is_inscription(key: str) -> bool:
    return key in INSCRIPTIONS


def musings_for_trigger(trigger: str) -> list[str]:
    """Musing keys registered for a trigger, e.g. 'gold' or 'band:act2'."""
    return [k for k, t in MUSINGS.items() if t == trigger]
