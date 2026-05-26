import sys, random, math
import pygame as pg
from typing import Dict, Tuple, List, Set
from . import config as cfg
from .dungeon import Dungeon, WALL, FLOOR, ENTRY, EXIT, CHEST, MONSTER, LOOT, DIRS
from .entities import Hero, Creature, Item, random_loot, EQUIP_SLOTS
from .drawing import build_tiles, build_animsets_from_atlas
from .ui_common import line, panel, message_box, prompt_yes_no
from .ui_inventory import inventory_screen
from .ui_stats import stats_window, skills_window
from .ui_options import options_screen
from .ui_pause import pause_screen
from .magic import do_cast
from .particles import ParticleSystem
from .audio import make_sounds
from .storage import save_hero

class AnimState:
    def __init__(self, sheets:dict, fps=8, speed_scale=1.0):
        self.sheets = sheets; self.state='idle'; self.frame=0; self.timer=0.0
        self.fps=fps; self.one_shot=False; self._queued=None; self.speed_scale=speed_scale; self.facing='right'
    def set_speed(self, scale:float): self.speed_scale = max(0.2, min(3.0, scale))
    def set_facing(self, facing:str):
        if facing in ('left','right'): self.facing=facing
    def set(self, state, one_shot=False, queue_to='idle'):
        if self.state != state: self.state = state; self.frame=0; self.timer=0.0
        self.one_shot = one_shot; self._queued = queue_to if one_shot else None
    def _frames_for_state(self):
        key = f"{self.state}_{self.facing}"
        return self.sheets.get(key) or self.sheets.get(self.state) or self.sheets.get('idle_right') or self.sheets.get('idle_left')
    def update(self, dt):
        frames = self._frames_for_state()
        if not frames: return
        self.timer += dt; spf = 1.0/max(1,self.fps) / self.speed_scale
        while self.timer >= spf:
            self.timer -= spf; self.frame = (self.frame + 1) % len(frames)
            if self.one_shot and self.frame == 0:
                self.one_shot = False
                if self._queued: self.state = self._queued; self._queued=None
    def get_frame(self):
        frames = self._frames_for_state()
        if not frames: return None
        return frames[self.frame % len(frames)]

class SlideFX:
    def __init__(self): self.t=0.0; self.dur=0.0; self.dir=(0.0,0.0); self.dist=0.0; self.mode='dash'; self.ox=0.0; self.oy=0.0
    def trigger(self, dx,dy, dist=0.25, dur=0.12, mode='dash'):
        n=math.hypot(dx,dy) or 1.0; self.dir=(dx/n,dy/n); self.dist=dist; self.dur=max(0.05,dur); self.t=0.0; self.mode=mode
    def update(self, dt):
        if self.t>=self.dur: self.ox=self.oy=0.0; return
        self.t+=dt; phase=min(1.0,self.t/self.dur)
        amp = math.sin(math.pi*phase) if self.mode=='dash' else (1.0-phase)
        self.ox = self.dir[0]*self.dist*amp; self.oy=self.dir[1]*self.dist*amp

def generate_monster(depth:int) -> Creature:
    kinds = [
        ("Гоблин", 'goblin', {"str": 3 + depth, "dex": 7 + depth*2, "int": 2, "hp": 10 + depth*2, "armor":0}),
        ("Орк", 'orc', {"str": 8 + depth*2, "dex": 3 + depth//2, "int": 2, "hp": 18 + depth*3, "armor":0}),
        ("Летучая мышь", 'bat', {"str": 2 + depth//2, "dex": 10 + depth*2, "int": 2, "hp": 6 + depth, "armor":0}),
        ("Огр", 'ogre', {"str": 12 + depth*3, "dex": 2 + depth//3, "int": 2, "hp": 28 + depth*4, "armor":0}),
        ("Живой доспех", 'armor', {"str": 6 + depth*2, "dex": 3 + depth//2, "int": 2, "hp": 22 + depth*3, "armor":4 + depth//2}),
        ("Вампир", 'vampire', {"str": 3 + depth, "dex": 11 + depth*2, "int": 4 + depth//2, "hp": 8 + depth*2, "armor":1}),
    ]
    weights = [3,3,2,1,2,1]
    name, glyph, st = random.choices(kinds, weights=weights, k=1)[0]
    base_hp = st["hp"]; hp = base_hp + random.randint(0, max(1, base_hp//4))
    return Creature(name=name, max_hp=hp, hp=hp, str_=st["str"], dex=st["dex"], int_=st["int"], glyph=glyph, hostile=True, xp_reward=6+depth*3, armor=st["armor"])

def bresenham_line(x0,y0,x1,y1):
    dx = abs(x1-x0); dy = -abs(y1-y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx + dy; x,y=x0,y0
    while True:
        yield x,y
        if x==x1 and y==y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x += sx
        if e2 <= dx: err += dx; y += sy

def compute_fov(d:Dungeon, px:int, py:int, radius:int) -> Set[Tuple[int,int]]:
    vis=set(); vis.add((px,py))
    for y in range(py-radius, py+radius+1):
        for x in range(px-radius, px+radius+1):
            if not d.inside(x,y): continue
            if (x-px)**2 + (y-py)**2 > radius*radius: continue
            blocked=False
            for (lx,ly) in bresenham_line(px,py,x,y):
                vis.add((lx,ly))
                if d.grid[ly][lx] == WALL and not (lx==x and ly==y):
                    blocked=True; break
            if blocked: continue
    return vis

def dodge_chance(entity, dodge_skill=0):
    base = min(40, entity.dex) * 0.01; base += dodge_skill * 0.03
    return min(0.6, base)
def extra_attack_chance(entity): return min(0.30, entity.dex * 0.015)

def try_attack(attacker, defender, defender_armor, defender_dodge_skill=0):
    if random.random() < dodge_chance(defender, defender_dodge_skill): return 0, False, True
    base_min, base_max = attacker.melee_damage(); dmg = random.randint(base_min, base_max); dmg = max(1, dmg - defender_armor//2)
    defender.hp -= dmg; return dmg, defender.hp <= 0, False

def draw_hp_bar(surface, x,y,w,h, cur, maxv):
    pg.draw.rect(surface, cfg.C_HP_BG, (x,y,w,h), border_radius=3)
    if maxv <= 0: return
    frac = max(0.0, min(1.0, cur/maxv)); pg.draw.rect(surface, cfg.C_HP_FG, (x+2, y+2, int((w-4)*frac), h-4), border_radius=3)

def draw_hud(screen, hero:Hero):
    pg.draw.rect(screen, cfg.C_PANEL, (0, cfg.MAP_H*cfg.TILE, cfg.SCREEN_W, cfg.HUD_H)); pg.draw.rect(screen, cfg.C_PANEL_BORDER, (0, cfg.MAP_H*cfg.TILE, cfg.SCREEN_W, cfg.HUD_H), 2)
    font = pg.font.SysFont(None, 20)
    draw_hp_bar(screen, 10, cfg.MAP_H*cfg.TILE + 10, 260, 18, hero.hp, hero.max_hp); line(screen, font, f"HP: {hero.hp}/{hero.max_hp}", 16, cfg.MAP_H*cfg.TILE + 11, (0,0,0))
    dmg_min,dmg_max = hero.weapon_damage()
    hud = f"Lv{hero.level}  STR:{hero.str_} DEX:{hero.dex} INT:{hero.int_}  ARM:{hero.total_armor()}  DMG:{dmg_min}-{dmg_max}  DODGE:{int(dodge_chance(hero, hero.skills['DODGE'])*100)}%  XP:{hero.xp}/{hero.xp_to_next()}  Зелья:{hero.potions}"
    line(screen, font, hud, 10, cfg.MAP_H*cfg.TILE + 36, cfg.C_TEXT)

def draw_msg(screen, text:str):
    font = pg.font.SysFont(None, 20); line(screen, font, text, 10, cfg.MAP_H*cfg.TILE + 64, (200,200,160))

def draw_map(screen, tiles, hero_anim:AnimState, monsters_anim:dict, d:Dungeon, hero:Hero, render_px:float, render_py:float, monsters:dict, visible:Set[Tuple[int,int]], mon_slide:dict):
    for y in range(d.h):
        for x in range(d.w):
            r = pg.Rect(x*cfg.TILE, y*cfg.TILE, cfg.TILE, cfg.TILE)
            screen.blit(tiles['floor'], r)
            t = d.grid[y][x]
            if t == WALL: screen.blit(tiles['wall'], r)
            elif t == CHEST: screen.blit(tiles['chest'], r)
            elif t == EXIT: screen.blit(tiles['exit'], r)
            if (x,y) not in visible: screen.blit(tiles['shadow_hard'] if not d.seen[y][x] else tiles['shadow_soft'], r)
            else: d.seen[y][x] = True
    for (x,y), m in list(monsters.items()):
        if (x,y) in visible:
            a = monsters_anim.get(id(m)); frame = a.get_frame() if a else None
            fx = mon_slide.get(id(m)); offx = int((fx.ox if fx else 0.0) * cfg.TILE); offy = int((fx.oy if fx else 0.0) * cfg.TILE)
            r = pg.Rect(x*cfg.TILE + offx, y*cfg.TILE + offy, cfg.TILE, cfg.TILE)
            if frame: screen.blit(frame, r)
    r = pg.Rect(int(render_px*cfg.TILE), int(render_py*cfg.TILE), cfg.TILE, cfg.TILE)
    screen.blit(hero_anim.get_frame(), r)

def run_level(screen, tiles, animsets, hero:Hero, sounds, options, current_slot:int) -> bool:
    d = Dungeon(cfg.MAP_W, cfg.MAP_H, hero.depth); d.generate()
    monsters = {pos: generate_monster(d.depth) for pos in d.monsters}
    hero_anim = AnimState(animsets['hero'], fps=8, speed_scale=options['anim_speed'])
    monsters_anim = {}
    for m in monsters.values():
        sheets = animsets.get(m.glyph) or animsets.get('goblin')
        monsters_anim[id(m)] = AnimState(sheets, fps=6, speed_scale=options['anim_speed'])
    for a in monsters_anim.values(): a.set_facing('right')
    hero_anim.set_facing('right')
    mon_slide = { id(m): SlideFX() for m in monsters.values() }
    ps = ParticleSystem()

    hx,hy = d.entry; rx,ry = float(hx), float(hy)
    moving=False; move_from=(hx,hy); move_to=(hx,hy); move_t=0.0
    msg = f"Уровень {hero.depth}. Найдите выход."; event_log=[]

    def set_msg(t:str):
        nonlocal msg; msg=t; event_log.append(t)
        if len(event_log)>400: del event_log[:len(event_log)-400]

    def update_animations(dt):
        hero_anim.set_speed(options['anim_speed'])
        for a in monsters_anim.values(): a.set_speed(options['anim_speed'])
        for fx in mon_slide.values(): fx.update(dt)
        ps.update(dt)

    def spawn_scaled(func, tx,ty, n, **kw):
        k = max(0.0, options['particles']); count = max(0, int(n * k))
        if count <= 0: return
        getattr(ps, func)(tx,ty, n=count, **kw)

    def try_start_move(dx,dy):
        nonlocal moving, move_from, move_to, move_t, hx,hy, rx,ry
        if dx<0: hero_anim.set_facing('left')
        if dx>0: hero_anim.set_facing('right')
        nx,ny = hx+dx, hy+dy
        if not d.inside(nx,ny): return
        tile = d.grid[ny][nx]
        if tile == WALL: set_msg("Стена."); return
        if tile in (FLOOR, ENTRY, LOOT, CHEST, EXIT):
            moving=True; move_from=(hx,hy); move_to=(nx,ny); move_t=0.0
            hero_anim.set('walk', one_shot=True, queue_to='idle'); sounds['step'].play(); return
        if tile == MONSTER:
            m = monsters[(nx,ny)]; a = monsters_anim[id(m)]
            if nx < hx: hero_anim.set_facing('left')
            if nx > hx: hero_anim.set_facing('right')
            hero_anim.set('attack', one_shot=True, queue_to='idle'); a.set('hurt', one_shot=True, queue_to='idle')
            kx,ky = (nx-hx, ny-hy); mon_slide[id(m)].trigger(kx,ky, dist=0.22, dur=0.12, mode='knock')
            swings = 1 + (1 if random.random() < min(0.30, hero.dex * 0.015) else 0)
            total=0
            for _ in range(swings):
                dd, dead, dodged = try_attack(hero, m, m.armor + m.dex//2, 0)
                if dodged: set_msg(f"{m.name} уклонился!"); continue
                total += dd; spawn_scaled('spawn_hit', nx,ny, n=8, col=(255,255,180))
            sounds['hit'].play()
            if m.hp <= 0:
                set_msg(f"Вы убили {m.name} и получили {m.xp_reward} XP.")
                prev = hero.level; hero.gain_xp(m.xp_reward)
                if hero.level>prev: spawn_scaled('spawn_levelup', hx,hy, n=36); sounds['levelup'].play()
                spawn_scaled('spawn_burst', nx,ny, n=22, base_col=(200,60,60))
                d.grid[ny][nx] = FLOOR; del monsters[(nx,ny)]; del monsters_anim[id(m)]; del mon_slide[id(m)]
                if random.random() < 0.4: d.grid[ny][nx] = LOOT
            else:
                a.set('attack', one_shot=True, queue_to='idle')
                if hx < nx: a.set_facing('left')
                elif hx > nx: a.set_facing('right')
                dxm, dym = (hx-nx), (hy-ny); dash_dist = min(0.40, 0.15 + m.dex/50.0)
                mon_slide[id(m)].trigger(dxm, dym, dist=dash_dist, dur=0.10, mode='dash')
                md_total=0; mswings = 1 + (1 if random.random() < min(0.30, m.dex * 0.015) else 0)
                for _ in range(mswings):
                    md, dead, dodged = try_attack(m, hero, hero.total_armor(), hero.skills['DODGE'])
                    if dodged: continue
                    md_total += md; spawn_scaled('spawn_hit', hx,hy, n=6, col=(255,200,200))
                    if hero.hp <= 0: break
                if md_total>0: sounds['hurt'].play(); spawn_scaled('spawn_burst', hx,hy, n=10, base_col=(200,70,70))
                set_msg(f"Вы ударили {m.name} на {total}. " + ("Вы уклонились!" if md_total==0 else f"{m.name} ответил на {md_total}."))
                if hero.hp <= 0:
                    message_box(screen, ["Вы погибли, но сила Ле-Монда возвращает вас к началу уровня."]); return 'dead'
            return

    clock = pg.time.Clock()
    while True:
        dt = clock.tick(cfg.FPS) / 1000.0; update_animations(dt)
        if moving:
            move_t = min(1.0, (dt/0.12) + getattr(run_level, '_acc', 0.0))
            setattr(run_level, '_acc', move_t if move_t<1.0 else 0.0)
            t = move_t
            rx = move_from[0] + (move_to[0]-move_from[0]) * t; ry = move_from[1] + (move_to[1]-move_from[1]) * t
            if t >= 1.0:
                moving=False; setattr(run_level, '_acc', 0.0)
                hx,hy=move_to; rx,ry=float(hx),float(hy)
                tile = d.grid[hy][hx]
                if tile == LOOT:
                    if random.random()<0.4:
                        hero.potions += 1; 
                        d.grid[hy][hx]=FLOOR; sounds['pickup'].play()
                        msg_txt="Подобрано: зелье лечения (+1)."
                        set_msg(msg_txt)
                    else:
                        it = random_loot(hero.depth); 
                        if hero.equipment.get(it.slot) is None:
                            msg = hero.equip(it, to_slot=it.slot); set_msg(msg + " (авто)")
                        else:
                            if len(hero.inventory)<9: hero.inventory.append(it); set_msg(f"Взято в инвентарь: {it.describe()}")
                            else: set_msg("Инвентарь полон (9).")
                        d.grid[hy][hx]=FLOOR; sounds['pickup'].play()
                elif tile == CHEST:
                    if random.random()<0.4:
                        hero.potions += 1; d.grid[hy][hx]=FLOOR; sounds['pickup'].play(); set_msg("Сундук: зелье лечения (+1).")
                    else:
                        it = random_loot(hero.depth); 
                        if hero.equipment.get(it.slot) is None:
                            msg = hero.equip(it, to_slot=it.slot); set_msg(msg + " (авто)")
                        else:
                            if len(hero.inventory)<9: hero.inventory.append(it); set_msg(f"Взято в инвентарь: {it.describe()}")
                            else: set_msg("Инвентарь полон (9).")
                        d.grid[hy][hx]=FLOOR; sounds['pickup'].play()
                elif tile == EXIT:
                    sounds['open'].play(); hero.depth += 1; hero.unlocked_depth=max(hero.unlocked_depth, hero.depth); hero.hp=hero.max_hp; return True
        visible = compute_fov(d, hx, hy, cfg.FOV_RADIUS)
        screen.fill(cfg.C_BG); draw_map(screen, tiles, hero_anim, monsters_anim, d, hero, rx, ry, monsters, visible, mon_slide)
        ps.draw(screen); draw_hud(screen, hero); draw_msg(screen, msg); pg.display.flip()
        for e in pg.event.get():
            if e.type == pg.QUIT: save_hero(current_slot, hero, options); pg.quit(); sys.exit(0)
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_q: save_hero(current_slot, hero, options); pg.quit(); sys.exit(0)
                if e.key in (pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT) and not moving:
                    dx,dy = {pg.K_UP:(0,-1), pg.K_DOWN:(0,1), pg.K_LEFT:(-1,0), pg.K_RIGHT:(1,0)}[e.key]
                    hero.last_dir = (dx,dy); res = try_start_move(dx,dy)
                    if res == 'dead': return False
                elif e.key == pg.K_g and not moving:
                    if d.grid[hy][hx] == LOOT:
                        if random.random()<0.4:
                            hero.potions += 1; d.grid[hy][hx]=FLOOR; sounds['pickup'].play(); set_msg("Подобрано: зелье лечения (+1).")
                        else:
                            it = random_loot(hero.depth); 
                            if hero.equipment.get(it.slot) is None:
                                msg = hero.equip(it, to_slot=it.slot); set_msg(msg + " (авто)")
                            else:
                                if len(hero.inventory)<9: hero.inventory.append(it); set_msg(f"Взято в инвентарь: {it.describe()}")
                                else: set_msg("Инвентарь полон (9).")
                            d.grid[hy][hx]=FLOOR; sounds['pickup'].play()
                elif e.key == pg.K_i: set_msg(inventory_screen(screen, hero))
                elif e.key == pg.K_s: set_msg(stats_window(screen, hero))
                elif e.key == pg.K_k: set_msg(skills_window(screen, hero))
                elif e.key == pg.K_o:
                    def apply_opts(opts): 
                        for v in sounds.values(): v.set_volume(opts['volume'])
                    options_screen(screen, options, apply_opts); save_hero(current_slot, hero, options)
                elif e.key == pg.K_z:
                    if hero.potions<=0: set_msg("Зелий нет.")
                    else:
                        heal = 10 + 5*hero.level; healed = min(hero.max_hp - hero.hp, heal + hero.skills['MAGIC']*2)
                        hero.hp += healed; hero.potions -= 1; set_msg(f"Выпито зелье: +{healed} HP. Осталось: {hero.potions}."); sounds['potion'].play()
                elif e.key == pg.K_f:
                    def draw_map_with_current(vis): draw_map(screen, tiles, hero_anim, monsters_anim, d, hero, rx, ry, monsters, vis, mon_slide)
                    def draw_hud_with_current(): draw_hud(screen, hero)
                    set_msg(do_cast(screen, draw_map_with_current, draw_hud_with_current, d, hero, hx, hy, monsters, visible)); sounds['magic'].play()
                elif e.key == pg.K_p:
                    def _save_cb(): save_hero(current_slot, hero, options)
                    pause_screen(screen, d, hero, (hx,hy), monsters, msg, event_log, on_save=_save_cb)

def run():
    import os
    import pygame as pg
    from . import config as cfg

    drivers = ['wasapi', 'directsound', 'winmm', 'dummy']
    audio_driver = None

    for drv in drivers:
        try:
            os.environ['SDL_AUDIODRIVER'] = drv
            pg.mixer.pre_init(cfg.SND_RATE, cfg.SND_SIZE, cfg.SND_CHAN)
            pg.init()
            pg.mixer.init()  # если драйвер "dummy", звука не будет, но ошибки тоже
            audio_driver = drv
            break
        except Exception:
            try:
                pg.quit()  # корректно закрыть SDL перед сменой драйвера
            except Exception:
                pass
            continue

    if audio_driver is None:
        # Последняя попытка: хоть видео поднять
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        pg.init()
        audio_driver = 'dummy'

    
    screen = pg.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H)); 
    pg.display.set_caption("Le-Mond Roguelike (PyGame latest)")
    tiles = build_tiles(); 
    animsets = build_animsets_from_atlas(); 
    sounds = make_sounds(master_volume=0.7)
    
    from .ui_start import start_menu
    current_slot, hero, options = start_menu(screen, sounds)
    for v in sounds.values(): v.set_volume(options.get('volume', 0.7))
    while True:
        survived = run_level(screen, tiles, animsets, hero, sounds, options, current_slot)
        if not survived:
            hero.hp = hero.max_hp
            message_box(screen, ["Вы возродились на входе текущего уровня.", "Нажмите ENTER..."])
