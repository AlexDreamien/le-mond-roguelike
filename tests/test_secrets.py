import random
from collections import deque

from lemond_pygame.core import secrets
from lemond_pygame.core.dungeon import FLOOR, SECRET, WALL, Dungeon


def _reachable(d, opened=None):
    """Walkable (non-WALL) tiles reachable from entry, optionally treating the
    ``opened`` positions (e.g. a bumped secret door) as passable."""
    opened = opened or set()
    seen = {d.entry}
    q = deque([d.entry])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen or not d.inside(nx, ny):
                continue
            if d.grid[ny][nx] != WALL or (nx, ny) in opened:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def test_exit_reachable_basic():
    d = Dungeon(32, 20, 3)
    d.generate()
    assert d.exit_reachable(set())
    assert not d.exit_reachable({d.exit})


def test_exit_reachable_detects_a_sealed_path():
    d = Dungeon(5, 3, 1)
    d.grid = [[WALL] * 5 for _ in range(3)]
    for x in (1, 2, 3):
        d.grid[1][x] = FLOOR
    d.entry, d.exit = (1, 1), (3, 1)
    assert d.exit_reachable(set())
    assert not d.exit_reachable({(2, 1)})  # the only middle tile blocks the path


def _generate_with_secret():
    for s in range(60):
        d = Dungeon(32, 20, 4)
        d.rng = random.Random(s * 7 + 1)
        d.generate()
        if d.secret_doors and d.secret_cells:
            return d
    raise AssertionError("no secret room generated across 60 seeds")


def test_secret_room_is_sealed_until_the_door_is_bumped():
    d = _generate_with_secret()
    (door,) = d.secret_doors
    assert d.grid[door[1]][door[0]] == WALL  # the door reads as a plain wall
    cells = d.secret_cells
    reachable = _reachable(d)
    assert not (cells & reachable)  # the room is unreachable while sealed
    # the door fronts both the hidden room and an outside (non-secret) corridor
    nbrs = [(door[0] + dx, door[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    assert any(n in cells for n in nbrs)
    assert any(d.inside(*n) and d.grid[n[1]][n[0]] != WALL and n not in cells for n in nbrs)
    # opening the door connects the room
    opened = _reachable(d, opened={door})
    assert cells & opened


def test_secret_cells_are_walkable_but_not_floor():
    d = _generate_with_secret()
    for x, y in d.secret_cells:
        assert d.grid[y][x] == SECRET
        assert d.walkable(x, y)  # passable once revealed
    assert d.entry not in d.secret_cells and d.exit not in d.secret_cells


def test_corridor_wall_borders_a_corridor():
    d = Dungeon(32, 20, 5)
    d.generate()
    pos = secrets.corridor_wall(d, set(), rng=random.Random(3))
    if pos is not None:
        x, y = pos
        assert d.grid[y][x] == WALL
        assert any(d.walkable(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
