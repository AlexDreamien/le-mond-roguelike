"""Procedural dungeon generation: rooms, a maze, connectors, and loops.

Deterministic: a given (size, depth) always produces the same layout because the
RNG is seeded from ``depth``.
"""

from __future__ import annotations

import random
from collections import deque

WALL, FLOOR, ENTRY, EXIT, CHEST, MONSTER, LOOT, POTION = 1, 0, 2, 3, 4, 5, 6, 7
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


class Dungeon:
    def __init__(self, w: int, h: int, depth: int = 1):
        self.w, self.h, self.depth = w, h, depth
        self.grid = [[WALL for _ in range(w)] for _ in range(h)]
        self.seen = [[False for _ in range(w)] for _ in range(h)]
        self.entry = (1, 1)
        self.exit = (w - 2, h - 2)
        self.monsters: list[tuple[int, int]] = []
        self.rng = random.Random(depth * 1337)

    def inside(self, x, y) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def generate(self) -> None:
        w, h = self.w, self.h
        rng = self.rng

        # 1) Start with solid walls everywhere.
        self.grid = [[WALL for _ in range(w)] for _ in range(h)]
        self.seen = [[False for _ in range(w)] for _ in range(h)]

        def carve_rect(x0, y0, x1, y1, tile=FLOOR):
            for y in range(max(1, y0), min(h - 1, y1)):
                for x in range(max(1, x0), min(w - 1, x1)):
                    self.grid[y][x] = tile

        def rect_overlaps(r, rooms, margin=1):
            x, y, wid, hei = r
            for rx, ry, rw, rh in rooms:
                if not (
                    x + wid + margin <= rx
                    or rx + rw + margin <= x
                    or y + hei + margin <= ry
                    or ry + rh + margin <= y
                ):
                    return True
            return False

        # 2) Random non-overlapping rooms (odd sizes tile nicely with corridors).
        rooms = []
        room_tries = 80
        for _ in range(room_tries):
            rw = rng.randrange(5, 10, 2)
            rh = rng.randrange(5, 9, 2)
            rx = rng.randrange(1, w - rw - 1)
            ry = rng.randrange(1, h - rh - 1)
            r = (rx, ry, rw, rh)
            if not rect_overlaps(r, rooms, margin=2):
                rooms.append(r)
                carve_rect(rx, ry, rx + rw, ry + rh, FLOOR)

        # 3) Flood the empty space with a maze (DFS on odd coordinates).
        visited = [[False] * w for _ in range(h)]

        def neighbors_cells(x, y):
            out = []
            for dx, dy in DIRS:
                nx, ny = x + dx * 2, y + dy * 2
                if 1 <= nx < w - 1 and 1 <= ny < h - 1:
                    out.append((dx, dy, nx, ny))
            rng.shuffle(out)
            return out

        starts = []
        for _ in range(10):
            sx, sy = rng.randrange(1, w - 1, 2), rng.randrange(1, h - 1, 2)
            starts.append((sx, sy))

        for sx, sy in starts:
            if visited[sy][sx] or self.grid[sy][sx] == FLOOR:
                continue
            stack = [(sx, sy)]
            visited[sy][sx] = True
            self.grid[sy][sx] = FLOOR
            while stack:
                x, y = stack[-1]
                nbrs = []
                for dx, dy, nx, ny in neighbors_cells(x, y):
                    if visited[ny][nx]:
                        continue
                    # Do not punch through existing rooms.
                    if self.grid[ny][nx] == FLOOR:
                        continue
                    nbrs.append((dx, dy, nx, ny))
                if nbrs:
                    dx, dy, nx, ny = rng.choice(nbrs)
                    self.grid[y + dy][x + dx] = FLOOR
                    self.grid[ny][nx] = FLOOR
                    visited[ny][nx] = True
                    stack.append((nx, ny))
                else:
                    stack.pop()

        # 4) Connect each room to nearby corridors with 1-2 tunnels.
        for rx, ry, rw, rh in rooms:
            connectors = []
            for x in range(rx, rx + rw):
                for y in [ry - 1, ry + rh]:
                    if 1 <= x < w - 1 and 1 <= y < h - 1:
                        connectors.append((x, y))
            for y in range(ry, ry + rh):
                for x in [rx - 1, rx + rw]:
                    if 1 <= x < w - 1 and 1 <= y < h - 1:
                        connectors.append((x, y))
            rng.shuffle(connectors)
            add = rng.randint(1, 2)
            built = 0
            for cx, cy in connectors:
                # Skip if floor is already adjacent.
                if any(
                    self.grid[cy + dy][cx + dx] == FLOOR
                    for dx, dy in DIRS
                    if 0 <= cx + dx < w and 0 <= cy + dy < h
                ):
                    continue
                # Dig a straight tunnel until it reaches existing floor.
                dirs = DIRS[:]
                rng.shuffle(dirs)
                dug = False
                for dx, dy in dirs:
                    x, y = cx, cy
                    for _ in range(12):
                        if not (1 <= x < w - 1 and 1 <= y < h - 1):
                            break
                        if self.grid[y][x] == FLOOR:
                            dug = True
                            break
                        self.grid[y][x] = FLOOR
                        x += dx
                        y += dy
                    if dug:
                        break
                if dug:
                    built += 1
                if built >= add:
                    break

        # 5) Add loops by knocking out occasional walls between two corridors.
        loops = int((w * h) * 0.02)
        for _ in range(loops):
            x = rng.randrange(2, w - 2)
            y = rng.randrange(2, h - 2)
            if self.grid[y][x] != WALL:
                continue
            if (self.grid[y][x - 1] == FLOOR and self.grid[y][x + 1] == FLOOR) or (
                self.grid[y - 1][x] == FLOOR and self.grid[y + 1][x] == FLOOR
            ):
                self.grid[y][x] = FLOOR

        # 5b) Guarantee every carved area is reachable: connect stray pockets to
        # the main region so no room is ever sealed off.
        self._ensure_connected()

        # 6) Place entry and exit as far apart as possible.
        floors = [
            (x, y) for y in range(1, h - 1) for x in range(1, w - 1) if self.grid[y][x] == FLOOR
        ]
        if not floors:
            cx, cy = w // 2, h // 2
            self.grid[cy][cx] = FLOOR
            floors = [(cx, cy)]

        def farthest_from(src):
            dist = {src: 0}
            q = deque([src])
            best = src
            while q:
                x, y = q.popleft()
                for dx, dy in DIRS:
                    nx, ny = x + dx, y + dy
                    if (
                        0 <= nx < w
                        and 0 <= ny < h
                        and self.grid[ny][nx] == FLOOR
                        and (nx, ny) not in dist
                    ):
                        dist[(nx, ny)] = dist[(x, y)] + 1
                        q.append((nx, ny))
                        if dist[(nx, ny)] > dist[best]:
                            best = (nx, ny)
            return best

        entry = rng.choice(floors)
        exit_ = farthest_from(farthest_from(entry))

        self.entry = entry
        self.exit = exit_
        self.grid[entry[1]][entry[0]] = ENTRY
        self.grid[exit_[1]][exit_[0]] = EXIT

        # 7) Scatter chests and loot.
        free_floors = [(x, y) for (x, y) in floors if (x, y) not in (entry, exit_)]
        rng.shuffle(free_floors)
        ch_cnt = max(3, (w * h) // 160)
        lt_cnt = max(5, (w * h) // 120)
        for x, y in free_floors[:ch_cnt]:
            self.grid[y][x] = CHEST
        for x, y in free_floors[ch_cnt : ch_cnt + lt_cnt]:
            self.grid[y][x] = LOOT if rng.random() < 0.5 else POTION  # coins vs potion

        # 8) Place monsters away from the entry. Their tiles stay FLOOR; the game
        # loop tracks positions in a dict keyed by coordinate.
        self.monsters = []
        # Population grows with depth so deeper floors get more crowded instead
        # of staying at a fixed count; capped to avoid absurd density.
        mons_cnt = min(28, max(7, 5 + self.depth))
        keep = [
            (x, y)
            for (x, y) in free_floors[ch_cnt + lt_cnt :]
            if abs(x - entry[0]) + abs(y - entry[1]) >= 6
        ]
        rng.shuffle(keep)
        for x, y in keep[:mons_cnt]:
            self.monsters.append((x, y))

    def _components(self) -> list[list[tuple[int, int]]]:
        w, h = self.w, self.h
        seen = [[False] * w for _ in range(h)]
        comps = []
        for sy in range(h):
            for sx in range(w):
                if self.grid[sy][sx] != FLOOR or seen[sy][sx]:
                    continue
                cells = []
                stack = [(sx, sy)]
                seen[sy][sx] = True
                while stack:
                    x, y = stack.pop()
                    cells.append((x, y))
                    for dx, dy in DIRS:
                        nx, ny = x + dx, y + dy
                        if (
                            0 <= nx < w
                            and 0 <= ny < h
                            and self.grid[ny][nx] == FLOOR
                            and not seen[ny][nx]
                        ):
                            seen[ny][nx] = True
                            stack.append((nx, ny))
                comps.append(cells)
        return comps

    def _carve_corridor(self, x0, y0, x1, y1) -> None:
        x = x0
        sx = 1 if x1 >= x0 else -1
        while x != x1:
            self.grid[y0][x] = FLOOR
            x += sx
        y = y0
        sy = 1 if y1 >= y0 else -1
        while y != y1:
            self.grid[y][x1] = FLOOR
            y += sy
        self.grid[y1][x1] = FLOOR

    def _ensure_connected(self) -> None:
        comps = self._components()
        if len(comps) <= 1:
            return
        main_idx = max(range(len(comps)), key=lambda i: len(comps[i]))
        main = set(comps[main_idx])
        for i, cells in enumerate(comps):
            if i == main_idx:
                continue
            ax, ay = cells[0]
            bx, by = min(main, key=lambda c: abs(c[0] - ax) + abs(c[1] - ay))
            self._carve_corridor(ax, ay, bx, by)
            main.update(cells)
