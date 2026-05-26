import pygame as pg
from . import config as cfg
from .ui_common import line, panel
def options_screen(screen, options:dict, apply_fn):
    font = pg.font.SysFont(None, 20)
    rect = pg.Rect(70, 70, cfg.SCREEN_W-140, cfg.SCREEN_H-180); idx = 0
    items = [("Скорость анимаций", "anim_speed", 0.5, 2.0, 0.1), ("Интенсивность партиклов", "particles", 0.0, 2.0, 0.1), ("Громкость звука", "volume", 0.0, 1.0, 0.05)]
    def value_bar(x, y, w, h, v, vmin, vmax):
        pg.draw.rect(screen, (30,30,40), (x,y,w,h), border_radius=4); t = (v - vmin) / (vmax - vmin)
        pg.draw.rect(screen, (90,140,200), (x+2,y+2,int((w-4)*t),h-4), border_radius=4)
    while True:
        screen.fill(cfg.C_BG); panel(screen, rect, "Настройки (O)")
        y = rect.y + 60; rows=[]
        for i,(label, key, vmin, vmax, step) in enumerate(items):
            r = pg.Rect(rect.x+30, y, rect.w-60, 46)
            pg.draw.rect(screen, (26,26,34), r, border_radius=6); pg.draw.rect(screen, (70,70,90), r, 1, border_radius=6)
            color = (220,220,220) if i!=idx else (200,240,200); line(screen, font, f"{label}: {options[key]:.2f}", r.x+10, r.y+8, color)
            value_bar(r.x+10, r.y+24, r.w-20, 12, options[key], vmin, vmax); rows.append((r, key, vmin, vmax, step)); y += 54
        line(screen, font, "←/→ — изменить, ↑/↓ — выбрать, R — сброс, ENTER/ESC — закрыть", rect.x+30, rect.bottom-40, (160,160,200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT: pg.quit(); raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_KP_ENTER): return "Готово."
                if e.key == pg.K_UP: idx = (idx - 1) % len(items)
                if e.key == pg.K_DOWN: idx = (idx + 1) % len(items)
                if e.key == pg.K_LEFT:
                    key = items[idx][1]; vmin = items[idx][2]; step = items[idx][4]
                    options[key] = max(vmin, round(options[key]-step, 2)); apply_fn(options)
                if e.key == pg.K_RIGHT:
                    key = items[idx][1]; vmax = items[idx][3]; step = items[idx][4]
                    options[key] = min(vmax, round(options[key]+step, 2)); apply_fn(options)
                if e.key == pg.K_r:
                    options['anim_speed']=1.0; options['particles']=1.0; options['volume']=0.7; apply_fn(options)
