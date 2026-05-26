import random
WALL, FLOOR, ENTRY, EXIT, CHEST, MONSTER, LOOT = 1, 0, 2, 3, 4, 5, 6
DIRS = [(1,0),(-1,0),(0,1),(0,-1)]
class Dungeon:
    def __init__(self, w:int, h:int, depth:int=1):
        self.w, self.h, self.depth = w, h, depth
        self.grid = [[WALL for _ in range(w)] for _ in range(h)]
        self.seen = [[False for _ in range(w)] for _ in range(h)]
        self.entry = (1,1); self.exit = (w-2,h-2); self.monsters=[]
        self.rng = random.Random(depth*1337)
    def inside(self, x,y): return 0<=x<self.w and 0<=y<self.h
    def generate(self):
        w, h = self.w, self.h
        rng = self.rng
    
        # 1) Стены везде
        self.grid = [[WALL for _ in range(w)] for _ in range(h)]
        self.seen = [[False for _ in range(w)] for _ in range(h)]
    
        # --- вспомогательные ---
        def carve_rect(x0, y0, x1, y1, tile=FLOOR):
            for y in range(max(1, y0), min(h-1, y1)):
                for x in range(max(1, x0), min(w-1, x1)):
                    self.grid[y][x] = tile
    
        def rect_overlaps(r, rooms, margin=1):
            x,y,wid,hei = r
            for (rx,ry,rw,rh) in rooms:
                if not (x+wid+margin <= rx or rx+rw+margin <= x or
                        y+hei+margin <= ry or ry+rh+margin <= y):
                    return True
            return False
    
        # 2) Случайные комнаты (3–7 клеток высота/ширина, не пересекаются)
        rooms = []
        ROOM_TRIES = 80
        for _ in range(ROOM_TRIES):
            rw = rng.randrange(5, 10, 2)  # нечётные, чтобы красивее стыковались с коридорами
            rh = rng.randrange(5, 9, 2)
            rx = rng.randrange(1, w - rw - 1)
            ry = rng.randrange(1, h - rh - 1)
            r = (rx, ry, rw, rh)
            if not rect_overlaps(r, rooms, margin=2):
                rooms.append(r)
                carve_rect(rx, ry, rx + rw, ry + rh, FLOOR)
    
        # 3) Лабиринтом заполняем свободные зоны (DFS по нечётным координатам)
        visited = [[False]*w for _ in range(h)]
        def neighbors_cells(x, y):
            out = []
            for dx,dy in DIRS:
                nx, ny = x + dx*2, y + dy*2
                if 1 <= nx < w-1 and 1 <= ny < h-1:
                    out.append((dx,dy,nx,ny))
            rng.shuffle(out)
            return out
    
        # стартовые точки — несколько случайных
        starts = []
        for _ in range(10):
            sx, sy = rng.randrange(1, w-1, 2), rng.randrange(1, h-1, 2)
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
                for dx,dy,nx,ny in neighbors_cells(x,y):
                    if visited[ny][nx]:
                        continue
                    # не «ломаем» комнаты
                    if self.grid[ny][nx] == FLOOR:
                        continue
                    nbrs.append((dx,dy,nx,ny))
                if nbrs:
                    dx,dy,nx,ny = rng.choice(nbrs)
                    self.grid[y+dy][x+dx] = FLOOR
                    self.grid[ny][nx] = FLOOR
                    visited[ny][nx] = True
                    stack.append((nx,ny))
                else:
                    stack.pop()
    
        # 4) Соединяем комнаты с ближайшими коридорами (1–2 точки на комнату)
        for (rx,ry,rw,rh) in rooms:
            connectors = []
            # собираем возможные точки на периметре
            for x in range(rx, rx+rw):
                for y in [ry-1, ry+rh]:
                    if 1 <= x < w-1 and 1 <= y < h-1:
                        connectors.append((x,y))
            for y in range(ry, ry+rh):
                for x in [rx-1, rx+rw]:
                    if 1 <= x < w-1 and 1 <= y < h-1:
                        connectors.append((x,y))
            rng.shuffle(connectors)
            add = rng.randint(1, 2)
            built = 0
            for (cx, cy) in connectors:
                # если рядом уже пол — пропускаем
                if any(self.grid[cy+dy][cx+dx] == FLOOR for dx,dy in DIRS if 0 <= cx+dx < w and 0 <= cy+dy < h):
                    continue
                # копаем прямой тоннель в случайном направлении, пока не встретим пол
                dirs = DIRS[:]
                rng.shuffle(dirs)
                dug = False
                for dx, dy in dirs:
                    x, y = cx, cy
                    for _ in range(12):
                        if not (1 <= x < w-1 and 1 <= y < h-1):
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
                
        # 5) Добавляем «петли» — местами ломаем стены между двумя этажами
        LOOPS = int((w*h) * 0.02)
        for _ in range(LOOPS):
            x = rng.randrange(2, w-2)
            y = rng.randrange(2, h-2)
            if self.grid[y][x] != WALL:
                continue
            # если по соседству два пола не по диагонали — можно продолбить и сделать ответвление
            if ((self.grid[y][x-1] == FLOOR and self.grid[y][x+1] == FLOOR) or
                (self.grid[y-1][x] == FLOOR and self.grid[y+1][x] == FLOOR)):
                self.grid[y][x] = FLOOR
    
        # 6) Точки входа/выхода — максимально далекие друг от друга
        floors = [(x,y) for y in range(1,h-1) for x in range(1,w-1) if self.grid[y][x] == FLOOR]
        if not floors:
            # запасной вариант: открыть центр
            cx, cy = w//2, h//2
            self.grid[cy][cx] = FLOOR
            floors = [(cx,cy)]
    
        def farthest_from(src):
            from collections import deque
            dist = {src: 0}
            q = deque([src])
            best = src
            while q:
                x,y = q.popleft()
                for dx,dy in DIRS:
                    nx,ny = x+dx, y+dy
                    if 0<=nx<w and 0<=ny<h and self.grid[ny][nx]==FLOOR and (nx,ny) not in dist:
                        dist[(nx,ny)] = dist[(x,y)] + 1
                        q.append((nx,ny))
                        if dist[(nx,ny)] > dist[best]:
                            best = (nx,ny)
            return best
    
        entry = rng.choice(floors)
        exit_ = farthest_from(farthest_from(entry))
    
        self.entry = entry
        self.exit = exit_
        self.grid[entry[1]][entry[0]] = ENTRY
        self.grid[exit_[1]][exit_[0]] = EXIT
    
        # 7) Сундуки/лут
        import math
        free_floors = [(x,y) for (x,y) in floors if (x,y) not in (entry, exit_)]
        rng.shuffle(free_floors)
        ch_cnt = max(3, (w*h)//160)
        lt_cnt = max(5, (w*h)//120)
        for (x,y) in free_floors[:ch_cnt]:
            self.grid[y][x] = CHEST
        for (x,y) in free_floors[ch_cnt:ch_cnt+lt_cnt]:
            self.grid[y][x] = LOOT
    
        # 8) Монстры — подальше от входа
        self.monsters = []
        mons_cnt = max(6, (w*h)//90)
        keep = [(x,y) for (x,y) in free_floors[ch_cnt+lt_cnt:] if abs(x-entry[0]) + abs(y-entry[1]) >= 6]
        rng.shuffle(keep)
        for (x,y) in keep[:mons_cnt]:
            # можно оставить клетку как FLOOR и хранить только список позиций —
            # дальше логика боя опирается на словарь monsters в game.py
            self.monsters.append((x,y))