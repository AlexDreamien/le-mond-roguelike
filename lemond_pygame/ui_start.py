import pygame as pg
from .ui_common import panel, line, prompt_yes_no
from . import config as cfg
from .storage import list_saves, load_hero, save_hero, delete_save
from .entities import Hero, Item
DEFAULT_OPTIONS = {"anim_speed":1.0,"particles":1.0,"volume":0.7}
def _slot_rect(i): return pg.Rect(60, 60 + (i-1)*90, cfg.SCREEN_W-120, 72)
def _del_rect(r): return pg.Rect(r.right-120, r.y+18, 100, 36)
def _draw_slot(screen, font, info):
    r = _slot_rect(info['slot'])
    pg.draw.rect(screen, (30,30,40), r, border_radius=8); pg.draw.rect(screen, (70,70,90), r, 1, border_radius=8)
    if info['exists']:
        line(screen, font, f"Слот {info['slot']}: {info['name']} — {info['class']} — Ур.{info['level']} — Подземелье {info['depth']}", r.x+12, r.y+12)
        dr = _del_rect(r)
        pg.draw.rect(screen, (120,60,60), dr, border_radius=6); pg.draw.rect(screen, (200,120,120), dr, 1, border_radius=6)
        line(screen, font, "Удалить", dr.x+16, dr.y+10, (250,230,230))
    else:
        line(screen, font, f"Слот {info['slot']}: Новая игра", r.x+12, r.y+22, (200,220,200))
def class_select(screen):
    font = pg.font.SysFont(None, 24); rect = pg.Rect(60, 60, cfg.SCREEN_W-120, cfg.SCREEN_H-160)
    while True:
        screen.fill(cfg.C_BG); panel(screen, rect, "Выбор класса")
        w = (rect.w - 40) // 3
        data = [("Воин", {"STR":10,"DEX":4,"INT":1}, "Ближний бой +1", "меч 1 ур."),
                ("Вор", {"STR":5,"DEX":10,"INT":5}, "Уворот +1", "кинжал 1 ур."),
                ("Маг", {"STR":3,"DEX":2,"INT":10}, "Магия +1", "посох 1 ур.")]
        cards=[]
        for i,(name, stats, skill, item) in enumerate(data):
            r = pg.Rect(rect.x+20+i*w, rect.y+60, w-20, 180); cards.append((r,name))
            pg.draw.rect(screen, (26,26,34), r, border_radius=8); pg.draw.rect(screen, (70,70,90), r, 1, border_radius=8)
            line(screen, font, name, r.x+12, r.y+10, (220,220,240))
            line(screen, font, f"Сила: {stats['STR']}", r.x+12, r.y+44)
            line(screen, font, f"Ловк.: {stats['DEX']}", r.x+12, r.y+68)
            line(screen, font, f"Интел.: {stats['INT']}", r.x+12, r.y+92)
            line(screen, font, skill, r.x+12, r.y+124, (200,210,200))
            line(screen, font, f"Старт: {item} + зелье", r.x+12, r.y+148, (200,210,200))
        line(screen, font, "Клик на карточке. Esc — назад", rect.x+20, rect.bottom-36, (160,160,200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT: pg.quit(); raise SystemExit
            if e.type == pg.KEYDOWN and e.key==pg.K_ESCAPE: return None
            if e.type == pg.MOUSEBUTTONDOWN and e.button==1:
                mx,my = e.pos
                for r,name in cards:
                    if r.collidepoint(mx,my): return name
def create_hero_for_class(cls:str)->Hero:
    from .entities import Hero, Item
    if cls=="Воин":
        h=Hero(name="Густав", max_hp=20, hp=20, str_=10, dex=4, int_=1, glyph='hero'); h.skills['MELEE']=1; it=Item("Меч I","MAIN",1,False)
    elif cls=="Вор":
        h=Hero(name="Густав", max_hp=18, hp=18, str_=5, dex=10, int_=5, glyph='hero'); h.skills['DODGE']=1; it=Item("Кинжал I","MAIN",1,False)
    else:
        h=Hero(name="Густав", max_hp=16, hp=16, str_=3, dex=2, int_=10, glyph='hero'); h.skills['MAGIC']=1; it=Item("Посох I","MAIN",1,False)
    h.class_name=cls; h.recompute_max_hp(); h.hp=h.max_hp; h.depth=1; h.unlocked_depth=1; h.potions=1
    h.equip(it, to_slot="MAIN"); return h
def start_menu(screen, sounds):
    font = pg.font.SysFont(None, 24); title_font = pg.font.SysFont(None, 36)
    while True:
        screen.fill(cfg.C_BG); line(screen, title_font, "Le-Mond — Рогалик", 60, 16, (210,210,240))
        panel(screen, pg.Rect(40, 40, cfg.SCREEN_W-80, cfg.SCREEN_H-120), "Стартовое меню (5 слотов)")
        infos=list_saves(); rects=[]
        for info in infos:
            _draw_slot(screen, font, info); rects.append((_slot_rect(info['slot']), info))
        line(screen, font, "Клик по слоту — загрузить/создать. 'Удалить' — стереть сейв. ESC — выйти.", 60, cfg.SCREEN_H-60, (160,160,200))
        pg.display.flip()
        for e in pg.event.get():
            if e.type==pg.QUIT: pg.quit(); raise SystemExit
            if e.type==pg.KEYDOWN and e.key==pg.K_ESCAPE: pg.quit(); raise SystemExit
            if e.type==pg.MOUSEBUTTONDOWN and e.button==1:
                mx,my=e.pos
                for r,info in rects:
                    if r.collidepoint(mx,my):
                        if info.get('exists') and _del_rect(r).collidepoint(mx,my):
                            if prompt_yes_no(screen, f"Удалить слот {info['slot']}?"): delete_save(info['slot'])
                            break
                        if info.get('exists'):
                            hero,opts=load_hero(info['slot']); 
                            if hero is None: break
                            sounds['open'].play(); return info['slot'], hero, opts
                        else:
                            cls=class_select(screen); 
                            if not cls: break
                            hero=create_hero_for_class(cls); opts=DEFAULT_OPTIONS.copy(); save_hero(info['slot'], hero, opts)
                            sounds['open'].play(); return info['slot'], hero, opts
