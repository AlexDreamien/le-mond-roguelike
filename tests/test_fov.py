from lemond_pygame.core.dungeon import FLOOR, WALL, Dungeon
from lemond_pygame.core.fov import bresenham_line, compute_fov


def open_room(w=7, h=7):
    d = Dungeon(w, h)
    d.grid = [[FLOOR for _ in range(w)] for _ in range(h)]
    return d


def test_bresenham_includes_both_endpoints():
    points = list(bresenham_line(0, 0, 3, 0))
    assert points[0] == (0, 0)
    assert points[-1] == (3, 0)


def test_origin_is_always_visible():
    d = open_room()
    vis = compute_fov(d, 3, 3, radius=2)
    assert (3, 3) in vis


def test_tiles_outside_radius_are_not_visible():
    d = open_room(9, 9)
    vis = compute_fov(d, 4, 4, radius=2)
    assert (4, 6) in vis  # distance 2
    assert (4, 8) not in vis  # distance 4, outside the scan box


def test_walls_block_line_of_sight():
    d = open_room(7, 7)
    d.grid[3][4] = WALL  # east of the hero at (3, 3)
    vis = compute_fov(d, 3, 3, radius=3)
    assert (4, 3) in vis  # the wall itself is seen
    assert (5, 3) not in vis  # hidden behind the wall
    assert (6, 3) not in vis
