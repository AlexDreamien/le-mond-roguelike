from collections import deque

from lemond_pygame.core.dungeon import (
    CHEST,
    ENTRY,
    EXIT,
    FLOOR,
    LOOT,
    MONSTER,
    WALL,
    Dungeon,
)

WALKABLE = {FLOOR, ENTRY, EXIT, CHEST, LOOT}


def _generated(depth=1):
    d = Dungeon(32, 20, depth)
    d.generate()
    return d


def test_generation_is_deterministic_for_a_depth():
    a = _generated(3)
    b = _generated(3)
    assert a.grid == b.grid
    assert a.entry == b.entry
    assert a.exit == b.exit
    assert a.monsters == b.monsters


def test_entry_and_exit_tiles_are_marked():
    d = _generated(2)
    ex, ey = d.entry
    xx, xy = d.exit
    assert d.grid[ey][ex] == ENTRY
    assert d.grid[xy][xx] == EXIT
    assert d.entry != d.exit


def test_exit_is_reachable_from_entry():
    d = _generated(4)
    seen = {d.entry}
    q = deque([d.entry])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if d.inside(nx, ny) and (nx, ny) not in seen and d.grid[ny][nx] != WALL:
                seen.add((nx, ny))
                q.append((nx, ny))
    assert d.exit in seen


def test_monsters_are_on_walkable_in_bounds_tiles():
    d = _generated(5)
    assert len(d.monsters) > 0
    for x, y in d.monsters:
        assert d.inside(x, y)
        assert d.grid[y][x] != WALL


def test_all_floor_is_reachable_from_entry():
    # No sealed-off rooms: every walkable cell must be reachable from the entry.
    for depth in range(1, 8):
        d = _generated(depth)
        reachable = {d.entry}
        q = deque([d.entry])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if d.inside(nx, ny) and (nx, ny) not in reachable and d.grid[ny][nx] != WALL:
                    reachable.add((nx, ny))
                    q.append((nx, ny))
        all_floor = {(x, y) for y in range(d.h) for x in range(d.w) if d.grid[y][x] != WALL}
        assert all_floor == reachable, f"depth {depth}: {len(all_floor - reachable)} sealed cells"


def test_monsters_are_tracked_in_the_list_not_the_grid():
    # Monster cells stay FLOOR; the game loop keys combat off d.monsters, so the
    # MONSTER tile id must never be written into the grid.
    d = _generated(3)
    assert all(MONSTER not in row for row in d.grid)
    for x, y in d.monsters:
        assert d.grid[y][x] == FLOOR


def test_different_depths_differ():
    assert _generated(1).grid != _generated(2).grid
