import pygame as pg
from .ui_common import panel, line
from . import config as cfg
from .entities import EQUIP_SLOTS
def inventory_screen(screen, hero):
    font = pg.font.SysFont(None, 20)
    rect = pg.Rect(60, 60, cfg.SCREEN_W-120, cfg.SCREEN_H-140); sel = 0
    def redraw():
        screen.fill(cfg.C_BG); panel(screen, rect, "Инвентарь")
        x=rect.x+16; y=rect.y+46
        line(screen, font, "Экипировка:", x, y, (200,210,240)); y+=22
        for slot in EQUIP_SLOTS:
            it = hero.equipment.get(slot); text = f"{slot:>4}: {it.name if it else '-'}"
            line(screen, font, text, x, y); y+=20
        y+=8; line(screen, font, "Предметы (Enter — экипировать, Del — выбросить):", x, y, (200,210,240)); y+=24
        for i,it in enumerate(hero.inventory):
            pre = "→ " if i==sel else "  "
            line(screen, font, pre + it.describe(), x, y, (220,240,220) if i==sel else (220,220,220)); y+=20
        line(screen, font, "Esc — закрыть", x, rect.bottom-36, (160,160,200)); pg.display.flip()
    redraw()
    while True:
        for e in pg.event.get():
            if e.type==pg.QUIT: pg.quit(); raise SystemExit
            if e.type==pg.KEYDOWN:
                if e.key==pg.K_ESCAPE: return "Закрыто."
                if e.key==pg.K_UP: sel=max(0,sel-1); redraw()
                if e.key==pg.K_DOWN: sel=min(max(0,len(hero.inventory)-1), sel+1); redraw()
                if e.key in (pg.K_RETURN, pg.K_KP_ENTER):
                    if 0<=sel<len(hero.inventory):
                        it=hero.inventory.pop(sel); msg=hero.equip(it, to_slot=it.slot)
                        redraw(); return msg
                if e.key in (pg.K_DELETE, pg.K_BACKSPACE):
                    if 0<=sel<len(hero.inventory):
                        hero.inventory.pop(sel); redraw(); return "Выброшено."
