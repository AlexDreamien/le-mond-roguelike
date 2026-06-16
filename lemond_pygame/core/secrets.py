"""Placement of bump-to-read wall inscriptions on corridor walls.

Pure (no pygame): operates on a :class:`Dungeon` grid. Inscriptions go on walls
lining single-width corridors so the hero passes them and cannot miss them.
(Secret rooms are reserved by the generator itself; see ``Dungeon.generate``.)
"""

from __future__ import annotations

import random

from .dungeon import WALL

_DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def corridor_wall(d, used, rng=None):
    """A wall tile lining a single-width straight corridor, for an inscription.
    Returns a (x, y) not in ``used``, or None if none qualify."""
    r = rng or random
    cands = []
    for y in range(1, d.h - 1):
        for x in range(1, d.w - 1):
            if d.grid[y][x] != WALL or (x, y) in used:
                continue
            for dx, dy in _DIRS4:
                fx, fy = x + dx, y + dy
                if not d.walkable(fx, fy) or d.walkable_neighbors(fx, fy) != 2:
                    continue
                wn = [(fx + ax, fy + ay) for ax, ay in _DIRS4 if d.walkable(fx + ax, fy + ay)]
                if wn[0][0] == wn[1][0] or wn[0][1] == wn[1][1]:  # straight corridor
                    cands.append((x, y))
                    break
    return r.choice(cands) if cands else None
