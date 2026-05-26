import pygame as pg
from . import config as cfg
def line(screen, font, text, x, y, col=(220,220,220)):
    surf = font.render(text, True, col); screen.blit(surf, (x,y))
def panel(screen, rect, title=None):
    pg.draw.rect(screen, cfg.C_PANEL, rect, border_radius=8); pg.draw.rect(screen, cfg.C_PANEL_BORDER, rect, 1, border_radius=8)
    if title:
        font = pg.font.SysFont(None, 22); line(screen, font, title, rect.x+10, rect.y+8, (200,200,240))
def message_box(screen, lines):
    font = pg.font.SysFont(None, 22)
    w = max(400, max(font.size(s)[0] for s in lines)+40); h = 60 + 26*len(lines)
    rect = pg.Rect((cfg.SCREEN_W-w)//2, (cfg.SCREEN_H-h)//2, w, h); panel(screen, rect, "Сообщение")
    y = rect.y+40
    for s in lines: line(screen, font, s, rect.x+20, y); y+=26
    line(screen, font, "Enter/Esc — закрыть", rect.x+20, rect.bottom-28, (160,160,200)); pg.display.flip()
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT: pg.quit(); raise SystemExit
            if e.type == pg.KEYDOWN and e.key in (pg.K_RETURN, pg.K_ESCAPE): return
def prompt_yes_no(screen, text:str):
    font = pg.font.SysFont(None, 22)
    w = max(420, font.size(text)[0]+60); h = 140
    rect = pg.Rect((cfg.SCREEN_W-w)//2, (cfg.SCREEN_H-h)//2, w, h); panel(screen, rect, "Подтвердите")
    line(screen, font, text, rect.x+20, rect.y+48); line(screen, font, "Y — да, N — нет", rect.x+20, rect.bottom-30, (160,160,200))
    pg.display.flip()
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT: pg.quit(); raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_y, pg.K_RETURN): return True
                if e.key in (pg.K_n, pg.K_ESCAPE): return False
