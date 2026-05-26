import pygame as pg
from .dungeon import WALL
from .ui_common import panel, line
from . import config as cfg
def do_cast(screen, draw_map_cb, draw_hud_cb, d, hero, hx, hy, monsters, visible):
    font = pg.font.SysFont(None, 20); rect = pg.Rect(80, 80, cfg.SCREEN_W-160, 120)
    while True:
        draw_map_cb(visible); draw_hud_cb()
        panel(screen, rect, "Магия: Выберите направление")
        line(screen, font, "Стрелки: направление, Esc — отмена", rect.x+20, rect.y+50); pg.display.flip()
        for e in pg.event.get():
            if e.type==pg.QUIT: pg.quit(); raise SystemExit
            if e.type==pg.KEYDOWN:
                if e.key==pg.K_ESCAPE: return "Отмена."
                if e.key in (pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT):
                    dx,dy={pg.K_UP:(0,-1), pg.K_DOWN:(0,1), pg.K_LEFT:(-1,0), pg.K_RIGHT:(1,0)}[e.key]
                    rng = 3 + hero.int_//3; dmg = 3 + hero.int_ + hero.skills['MAGIC']*2
                    for i in range(1, rng+1):
                        x,y=hx+dx*i, hy+dy*i
                        if not d.inside(x,y): break
                        if d.grid[y][x]==WALL: break
                        if (x,y) in monsters:
                            m = monsters[(x,y)]; m.hp -= dmg
                            if m.hp<=0: return f"Заклинание поразило {m.name} на {dmg} и убило."
                            else: return f"Заклинание поразило {m.name} на {dmg}."
                    return "Заклинание ушло в пустоту."
