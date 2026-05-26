"""Game loop and bootstrap: input handling and orchestration of core + render."""

from __future__ import annotations

import contextlib
import os
import random
import sys

import pygame as pg

from . import i18n
from .audio import make_sounds
from .core import config as cfg
from .core.combat import extra_attack_chance, generate_monster, try_attack
from .core.dungeon import CHEST, ENTRY, EXIT, FLOOR, LOOT, MONSTER, WALL, Dungeon
from .core.fov import compute_fov
from .core.loot import INVENTORY_LIMIT, resolve_pickup
from .drawing import build_animsets_from_atlas, build_tiles
from .magic import do_cast
from .particles import ParticleSystem
from .render import AnimState, SlideFX, draw_hud, draw_map, draw_msg
from .storage import save_hero
from .ui_common import message_box
from .ui_inventory import inventory_screen
from .ui_options import options_screen
from .ui_pause import pause_screen
from .ui_stats import skills_window, stats_window

MOVE_DURATION = 0.12  # seconds to slide between two tiles

_DIR_KEYS = {
    pg.K_UP: (0, -1),
    pg.K_DOWN: (0, 1),
    pg.K_LEFT: (-1, 0),
    pg.K_RIGHT: (1, 0),
}


def run_level(screen, tiles, animsets, hero, sounds, options, current_slot) -> bool:
    d = Dungeon(cfg.MAP_W, cfg.MAP_H, hero.depth)
    d.generate()
    monsters = {pos: generate_monster(d.depth) for pos in d.monsters}
    hero_anim = AnimState(animsets["hero"], fps=8, speed_scale=options["anim_speed"])
    monsters_anim = {}
    for m in monsters.values():
        sheets = animsets.get(m.glyph) or animsets.get("goblin")
        monsters_anim[id(m)] = AnimState(sheets, fps=6, speed_scale=options["anim_speed"])
    for a in monsters_anim.values():
        a.set_facing("right")
    hero_anim.set_facing("right")
    mon_slide = {id(m): SlideFX() for m in monsters.values()}
    ps = ParticleSystem()

    hx, hy = d.entry
    rx, ry = float(hx), float(hy)
    moving = False
    move_from = (hx, hy)
    move_to = (hx, hy)
    move_acc = 0.0
    msg = i18n.t("msg.level_intro", depth=hero.depth)
    event_log = []

    def set_msg(text: str):
        nonlocal msg
        msg = text
        event_log.append(text)
        if len(event_log) > 400:
            del event_log[: len(event_log) - 400]

    def update_animations(dt):
        hero_anim.set_speed(options["anim_speed"])
        for a in monsters_anim.values():
            a.set_speed(options["anim_speed"])
        for fx in mon_slide.values():
            fx.update(dt)
        ps.update(dt)

    def spawn_scaled(func, tx, ty, n, **kw):
        k = max(0.0, options["particles"])
        count = max(0, int(n * k))
        if count <= 0:
            return
        getattr(ps, func)(tx, ty, n=count, **kw)

    def apply_pickup(from_chest=False):
        result = resolve_pickup(hero, hero.depth)
        sounds["pickup"].play()
        if result.outcome == "potion":
            set_msg(i18n.t("pickup.chest_potion" if from_chest else "pickup.potion"))
        elif result.outcome == "equipped":
            status = i18n.t(result.equip_status, item=i18n.item_name(result.item))
            set_msg(i18n.t("pickup.equipped", status=status))
        elif result.outcome == "stored":
            set_msg(i18n.t("pickup.stored", item=i18n.item_describe(result.item)))
        else:
            set_msg(i18n.t("pickup.inventory_full", limit=INVENTORY_LIMIT))

    def try_start_move(dx, dy):
        nonlocal moving, move_from, move_to, move_acc, hx, hy, rx, ry
        if dx < 0:
            hero_anim.set_facing("left")
        if dx > 0:
            hero_anim.set_facing("right")
        nx, ny = hx + dx, hy + dy
        if not d.inside(nx, ny):
            return None
        tile = d.grid[ny][nx]
        if tile == WALL:
            set_msg(i18n.t("msg.wall"))
            return None
        if tile in (FLOOR, ENTRY, LOOT, CHEST, EXIT):
            moving = True
            move_from = (hx, hy)
            move_to = (nx, ny)
            move_acc = 0.0
            hero_anim.set("walk", one_shot=True, queue_to="idle")
            sounds["step"].play()
            return None
        if tile == MONSTER:
            return _attack(nx, ny)
        return None

    def _attack(nx, ny):
        m = monsters[(nx, ny)]
        a = monsters_anim[id(m)]
        if nx < hx:
            hero_anim.set_facing("left")
        if nx > hx:
            hero_anim.set_facing("right")
        hero_anim.set("attack", one_shot=True, queue_to="idle")
        a.set("hurt", one_shot=True, queue_to="idle")
        mon_slide[id(m)].trigger(nx - hx, ny - hy, dist=0.22, dur=0.12, mode="knock")
        swings = 1 + (1 if random.random() < extra_attack_chance(hero) else 0)
        total = 0
        for _ in range(swings):
            dd, _dead, dodged = try_attack(hero, m, m.armor + m.dex // 2, 0)
            if dodged:
                set_msg(i18n.t("msg.monster_dodged", name=i18n.monster_name(m)))
                continue
            total += dd
            spawn_scaled("spawn_hit", nx, ny, n=8, col=(255, 255, 180))
        sounds["hit"].play()
        if m.hp <= 0:
            set_msg(i18n.t("msg.killed", name=i18n.monster_name(m), xp=m.xp_reward))
            prev = hero.level
            hero.gain_xp(m.xp_reward)
            if hero.level > prev:
                spawn_scaled("spawn_levelup", hx, hy, n=36)
                sounds["levelup"].play()
            spawn_scaled("spawn_burst", nx, ny, n=22, base_col=(200, 60, 60))
            d.grid[ny][nx] = FLOOR
            del monsters[(nx, ny)]
            del monsters_anim[id(m)]
            del mon_slide[id(m)]
            if random.random() < 0.4:
                d.grid[ny][nx] = LOOT
            return None
        a.set("attack", one_shot=True, queue_to="idle")
        if hx < nx:
            a.set_facing("left")
        elif hx > nx:
            a.set_facing("right")
        dash_dist = min(0.40, 0.15 + m.dex / 50.0)
        mon_slide[id(m)].trigger(hx - nx, hy - ny, dist=dash_dist, dur=0.10, mode="dash")
        md_total = 0
        mswings = 1 + (1 if random.random() < extra_attack_chance(m) else 0)
        for _ in range(mswings):
            md, _dead, dodged = try_attack(m, hero, hero.total_armor(), hero.skills["DODGE"])
            if dodged:
                continue
            md_total += md
            spawn_scaled("spawn_hit", hx, hy, n=6, col=(255, 200, 200))
            if hero.hp <= 0:
                break
        if md_total > 0:
            sounds["hurt"].play()
            spawn_scaled("spawn_burst", hx, hy, n=10, base_col=(200, 70, 70))
        hit_part = i18n.t("msg.you_hit", name=i18n.monster_name(m), total=total)
        tail = (
            i18n.t("msg.you_dodged")
            if md_total == 0
            else i18n.t("msg.monster_hit_back", name=i18n.monster_name(m), dmg=md_total)
        )
        set_msg(hit_part + tail)
        if hero.hp <= 0:
            message_box(screen, [i18n.t("msg.death_box")])
            return "dead"
        return None

    def on_arrival():
        nonlocal hx, hy, rx, ry
        tile = d.grid[hy][hx]
        if tile in (LOOT, CHEST):
            apply_pickup(from_chest=(tile == CHEST))
            d.grid[hy][hx] = FLOOR
        elif tile == EXIT:
            sounds["open"].play()
            hero.depth += 1
            hero.unlocked_depth = max(hero.unlocked_depth, hero.depth)
            hero.hp = hero.max_hp
            return True
        return False

    clock = pg.time.Clock()
    while True:
        dt = clock.tick(cfg.FPS) / 1000.0
        update_animations(dt)
        if moving:
            move_acc = min(1.0, move_acc + dt / MOVE_DURATION)
            t = move_acc
            rx = move_from[0] + (move_to[0] - move_from[0]) * t
            ry = move_from[1] + (move_to[1] - move_from[1]) * t
            if t >= 1.0:
                moving = False
                move_acc = 0.0
                hx, hy = move_to
                rx, ry = float(hx), float(hy)
                if on_arrival():
                    return True

        visible = compute_fov(d, hx, hy, cfg.FOV_RADIUS)
        screen.fill(cfg.C_BG)
        draw_map(
            screen, tiles, hero_anim, monsters_anim, d, hero, rx, ry, monsters, visible, mon_slide
        )
        ps.draw(screen)
        draw_hud(screen, hero)
        draw_msg(screen, msg)
        pg.display.flip()

        for e in pg.event.get():
            if e.type == pg.QUIT:
                save_hero(current_slot, hero, options)
                pg.quit()
                sys.exit(0)
            if e.type != pg.KEYDOWN:
                continue
            if e.key == pg.K_q:
                save_hero(current_slot, hero, options)
                pg.quit()
                sys.exit(0)
            if e.key in _DIR_KEYS and not moving:
                dx, dy = _DIR_KEYS[e.key]
                hero.last_dir = (dx, dy)
                if try_start_move(dx, dy) == "dead":
                    return False
            elif e.key == pg.K_g and not moving:
                if d.grid[hy][hx] == LOOT:
                    apply_pickup(from_chest=False)
                    d.grid[hy][hx] = FLOOR
            elif e.key == pg.K_i:
                set_msg(inventory_screen(screen, hero))
            elif e.key == pg.K_s:
                set_msg(stats_window(screen, hero))
            elif e.key == pg.K_k:
                set_msg(skills_window(screen, hero))
            elif e.key == pg.K_o:

                def apply_opts(opts):
                    for v in sounds.values():
                        v.set_volume(opts["volume"])

                options_screen(screen, options, apply_opts)
                save_hero(current_slot, hero, options)
            elif e.key == pg.K_z:
                if hero.potions <= 0:
                    set_msg(i18n.t("msg.no_potions"))
                else:
                    heal = 10 + 5 * hero.level
                    healed = min(hero.max_hp - hero.hp, heal + hero.skills["MAGIC"] * 2)
                    hero.hp += healed
                    hero.potions -= 1
                    set_msg(i18n.t("msg.potion_used", healed=healed, potions=hero.potions))
                    sounds["potion"].play()
            elif e.key == pg.K_f:

                def draw_map_cb(vis, rx=rx, ry=ry):
                    draw_map(
                        screen,
                        tiles,
                        hero_anim,
                        monsters_anim,
                        d,
                        hero,
                        rx,
                        ry,
                        monsters,
                        vis,
                        mon_slide,
                    )

                def draw_hud_cb():
                    draw_hud(screen, hero)

                set_msg(
                    do_cast(screen, draw_map_cb, draw_hud_cb, d, hero, hx, hy, monsters, visible)
                )
                sounds["magic"].play()
            elif e.key == pg.K_p:

                def _save_cb():
                    save_hero(current_slot, hero, options)

                pause_screen(screen, d, hero, (hx, hy), monsters, msg, event_log, on_save=_save_cb)


def _init_pygame() -> str:
    drivers = ["wasapi", "directsound", "winmm", "dummy"]
    for drv in drivers:
        try:
            os.environ["SDL_AUDIODRIVER"] = drv
            pg.mixer.pre_init(cfg.SND_RATE, cfg.SND_SIZE, cfg.SND_CHAN)
            pg.init()
            pg.mixer.init()  # a "dummy" driver yields no sound but does not error
            return drv
        except Exception:
            with contextlib.suppress(Exception):
                pg.quit()
            continue
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pg.init()
    return "dummy"


def run() -> None:
    _init_pygame()
    i18n.load_locales()

    screen = pg.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
    pg.display.set_caption(i18n.t("app.title"))
    tiles = build_tiles()
    animsets = build_animsets_from_atlas()
    sounds = make_sounds(master_volume=0.7)

    from .ui_start import start_menu

    current_slot, hero, options = start_menu(screen, sounds)
    i18n.set_locale(options.get("language", i18n.get_locale()))
    for v in sounds.values():
        v.set_volume(options.get("volume", 0.7))

    while True:
        survived = run_level(screen, tiles, animsets, hero, sounds, options, current_slot)
        if not survived:
            hero.hp = hero.max_hp
            message_box(screen, [i18n.t("msg.respawn_1"), i18n.t("msg.respawn_2")])
