import random

import pygame as pg

from .core import config as cfg

_glow_cache: dict[int, pg.Surface] = {}


def _glow(radius: int) -> pg.Surface:
    """A cached white radial-falloff sprite, blitted additively for a glow."""
    surf = _glow_cache.get(radius)
    if surf is None:
        size = radius * 2
        surf = pg.Surface((size, size), pg.SRCALPHA)
        for y in range(size):
            for x in range(size):
                d = ((x - radius + 0.5) ** 2 + (y - radius + 0.5) ** 2) ** 0.5
                v = max(0, 255 - int(255 * (d / radius)))
                surf.set_at((x, y), (v, v, v, v))
        _glow_cache[radius] = surf
    return surf


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "t", "col", "size", "grav")

    def __init__(self, x, y, vx, vy, life, col, size=2, grav=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.t = 0.0
        self.col = col
        self.size = size
        self.grav = grav


class ParticleSystem:
    def __init__(self):
        self.p = []

    def spawn_burst(self, tx, ty, n=18, base_col=(200, 60, 60)):
        cx = tx * cfg.TILE + cfg.TILE // 2
        cy = ty * cfg.TILE + cfg.TILE // 2
        for _ in range(n):
            ang = random.random() * 6.283
            sp = random.uniform(20, 60)
            vx, vy = sp * pg.math.Vector2(1, 0).rotate_rad(ang)
            life = random.uniform(0.25, 0.5)
            self.p.append(Particle(cx, cy, vx, vy, life, base_col, size=2, grav=200))

    def spawn_sparkles(self, tx, ty, n=14, col=(230, 200, 90)):
        cx = tx * cfg.TILE + cfg.TILE // 2
        cy = ty * cfg.TILE + cfg.TILE // 2
        for _ in range(n):
            vx = random.uniform(-40, 40)
            vy = random.uniform(-40, 0)
            life = random.uniform(0.3, 0.6)
            self.p.append(Particle(cx, cy, vx, vy, life, col, size=2, grav=120))

    def spawn_heal(self, tx, ty, n=14, col=(120, 220, 140)):
        cx = tx * cfg.TILE + cfg.TILE // 2
        cy = ty * cfg.TILE + cfg.TILE // 2
        for _ in range(n):
            vx = random.uniform(-20, 20)
            vy = random.uniform(-50, -10)
            life = random.uniform(0.4, 0.7)
            self.p.append(Particle(cx, cy, vx, vy, life, col, size=2, grav=-30))

    def spawn_levelup(self, tx, ty, n=24):
        cx = tx * cfg.TILE + cfg.TILE // 2
        cy = ty * cfg.TILE + cfg.TILE // 2
        for _ in range(n):
            vx = random.uniform(-30, 30)
            vy = random.uniform(-60, -20)
            life = random.uniform(0.5, 0.9)
            self.p.append(Particle(cx, cy, vx, vy, life, (240, 220, 120), size=3, grav=10))

    def spawn_hit(self, tx, ty, n=8, col=(255, 255, 180)):
        cx = tx * cfg.TILE + cfg.TILE // 2
        cy = ty * cfg.TILE + cfg.TILE // 2
        for _ in range(n):
            vx = (random.random() - 0.5) * 40
            vy = (random.random() - 0.5) * 40
            life = 0.15 + random.random() * 0.20
            self.p.append(Particle(cx, cy, vx, vy, life, col, size=2, grav=0.0))

    def update(self, dt):
        alive = []
        for p in self.p:
            p.t += dt
            if p.t >= p.life:
                continue
            p.vy += p.grav * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.p = alive

    def draw(self, screen):
        for p in self.p:
            fade = max(0.0, 1.0 - p.t / p.life)
            radius = max(2, int(p.size * 3))
            glow = _glow(radius).copy()
            tint = (int(p.col[0] * fade), int(p.col[1] * fade), int(p.col[2] * fade), 255)
            glow.fill(tint, special_flags=pg.BLEND_RGB_MULT)
            screen.blit(
                glow, (int(p.x) - radius, int(p.y) - radius), special_flags=pg.BLEND_RGB_ADD
            )
