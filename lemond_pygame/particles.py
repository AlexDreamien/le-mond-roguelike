import random, pygame as pg
from . import config as cfg
class Particle:
    __slots__ = ("x","y","vx","vy","life","t","col","size","grav")
    def __init__(self, x,y,vx,vy, life, col, size=2, grav=0.0):
        self.x,self.y=x,y; self.vx,self.vy=vx,vy; self.life=life; self.t=0.0
        self.col=col; self.size=size; self.grav=grav
class ParticleSystem:
    def __init__(self): self.p=[]
    def spawn_burst(self, tx,ty, n=18, base_col=(200,60,60)):
        cx = tx*cfg.TILE + cfg.TILE//2; cy = ty*cfg.TILE + cfg.TILE//2
        for _ in range(n):
            ang = random.random()*6.283; sp = random.uniform(20,60)
            vx,vy = sp*pg.math.Vector2(1,0).rotate_rad(ang); life = random.uniform(0.25,0.5)
            self.p.append(Particle(cx,cy,vx,vy,life, base_col, size=2, grav=200))
    def spawn_sparkles(self, tx,ty, n=14, col=(230,200,90)):
        cx = tx*cfg.TILE + cfg.TILE//2; cy = ty*cfg.TILE + cfg.TILE//2
        for _ in range(n):
            vx = random.uniform(-40,40); vy = random.uniform(-40,0); life = random.uniform(0.3,0.6)
            self.p.append(Particle(cx,cy,vx,vy,life,col,size=2,grav=120))
    def spawn_heal(self, tx,ty, n=14, col=(120,220,140)):
        cx = tx*cfg.TILE + cfg.TILE//2; cy = ty*cfg.TILE + cfg.TILE//2
        for _ in range(n):
            vx = random.uniform(-20,20); vy = random.uniform(-50,-10); life = random.uniform(0.4,0.7)
            self.p.append(Particle(cx,cy,vx,vy,life,col,size=2,grav=-30))
    def spawn_levelup(self, tx,ty, n=24):
        cx = tx*cfg.TILE + cfg.TILE//2; cy = ty*cfg.TILE + cfg.TILE//2
        for _ in range(n):
            vx = random.uniform(-30,30); vy = random.uniform(-60,-20); life = random.uniform(0.5,0.9)
            self.p.append(Particle(cx,cy,vx,vy,life,(240,220,120),size=3,grav=10))
    def spawn_hit(self, tx,ty, n=8, col=(255,255,180)):
        cx = tx*cfg.TILE + cfg.TILE//2; cy = ty*cfg.TILE + cfg.TILE//2
        for _ in range(n):
            vx = (random.random()-0.5)*40; vy = (random.random()-0.5)*40; life = 0.15 + random.random()*0.20
            self.p.append(Particle(cx,cy,vx,vy,life,col, size=2, grav=0.0))
    def update(self, dt):
        alive=[]
        for p in self.p:
            p.t += dt
            if p.t >= p.life: continue
            p.vy += p.grav*dt; p.x += p.vx*dt; p.y += p.vy*dt; alive.append(p)
        self.p = alive
    def draw(self, screen):
        for p in self.p:
            a = max(0, 255 - int(255*(p.t/p.life)))
            col = (p.col[0], p.col[1], p.col[2], a)
            s = pg.Surface((p.size,p.size), pg.SRCALPHA); s.fill(col); screen.blit(s, (int(p.x), int(p.y)))
