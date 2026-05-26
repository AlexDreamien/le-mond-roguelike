"""Field-of-view computation via Bresenham line-of-sight casting."""

from __future__ import annotations

from .dungeon import WALL, Dungeon


def bresenham_line(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        yield x, y
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def compute_fov(d: Dungeon, px: int, py: int, radius: int) -> set[tuple[int, int]]:
    visible: set[tuple[int, int]] = {(px, py)}
    for y in range(py - radius, py + radius + 1):
        for x in range(px - radius, px + radius + 1):
            if not d.inside(x, y):
                continue
            if (x - px) ** 2 + (y - py) ** 2 > radius * radius:
                continue
            for lx, ly in bresenham_line(px, py, x, y):
                visible.add((lx, ly))
                if d.grid[ly][lx] == WALL and not (lx == x and ly == y):
                    break
    return visible
