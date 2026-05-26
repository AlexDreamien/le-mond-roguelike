import pygame as pg
from .ui_common import panel, line
from . import config as cfg
def stats_window(screen, hero):
    font = pg.font.SysFont(None, 22)
    rect = pg.Rect(80, 80, cfg.SCREEN_W-160, cfg.SCREEN_H-180)
    while True:
        screen.fill(cfg.C_BG); panel(screen, rect, "Характеристики")
        y = rect.y+50
        for s in [
            f"Уровень: {hero.level} (XP {hero.xp}/{hero.xp_to_next()})",
            f"Сила: {hero.str_}",
            f"Ловкость: {hero.dex}",
            f"Интеллект: {hero.int_}",
            f"Здоровье: {hero.hp}/{hero.max_hp}",
            f"Навыки: Ближний бой {hero.skills['MELEE']}, Уворот {hero.skills['DODGE']}, Магия {hero.skills['MAGIC']}",
        ]:
            line(screen, font, s, rect.x+20, y); y+=28
        line(screen, font, "Esc/Enter — закрыть", rect.x+20, rect.bottom-40, (160,160,200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type==pg.QUIT: pg.quit(); raise SystemExit
            if e.type==pg.KEYDOWN and e.key in (pg.K_ESCAPE, pg.K_RETURN): return "OK"
def skills_window(screen, hero):  # simplified stub
    return "Навыки пока изменяются автоматически при уровне."
