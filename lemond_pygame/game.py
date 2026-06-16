"""Game loop and bootstrap: input handling and orchestration of core + render."""

from __future__ import annotations

import asyncio
import contextlib
import os
import random
import sys

import pygame as pg

from . import fonts, i18n
from .audio import Music, make_ambient, make_sounds
from .core import config as cfg
from .core import endings, lore, secrets
from .core import spells as sp
from .core import weapons as wp
from .core.combat import (
    MONSTER_TURN_INTERVAL,
    caster_damage,
    caster_spec,
    extra_attack_chance,
    generate_monster,
    try_attack,
)
from .core.dungeon import CHEST, ENTRY, EXIT, FLOOR, LOOT, NOTE, POTION, SECRET, WALL, Dungeon
from .core.fov import compute_fov
from .core.loot import INVENTORY_LIMIT, floor_gold_amount, resolve_chest
from .core.progression import auto_assign
from .drawing import (
    build_animsets_from_atlas,
    build_creature_animsets,
    build_ghost_animset,
    build_hero_animset,
    build_tiles,
)
from .magic import animate_cast, animate_shot, choose_direction
from .particles import ParticleSystem
from .render import AnimState, Shake, SlideFX, draw_damage_flash, draw_hud, draw_map, draw_msg
from .storage import save_hero
from .ui_common import message_box, prompt_yes_no
from .ui_dialogue import dialogue_screen
from .ui_ending import ending_screen
from .ui_help import help_screen
from .ui_inventory import inventory_screen
from .ui_note import note_screen
from .ui_options import options_screen
from .ui_pause import pause_screen
from .ui_shop import shop_screen
from .ui_spellbook import spellbook_screen
from .ui_stats import skills_window, stats_window
from .ui_trainer import trainer_screen

MOVE_DURATION = 0.12  # seconds to slide between two tiles
FLASH_DURATION = 0.22  # seconds the red damage flash lingers
ATTACK_COOLDOWN = 0.16  # min seconds between attacks (so holding into a foe is paced)
MERCHANT_CHANCE = 0.35  # chance a merchant appears on a level
TRAINER_CHANCE = 0.25  # chance a trainer appears on a level

_DIR_KEYS = {
    pg.K_UP: (0, -1),
    pg.K_DOWN: (0, 1),
    pg.K_LEFT: (-1, 0),
    pg.K_RIGHT: (1, 0),
}


def _facing(dx, dy) -> str:
    if dy < 0:
        return "north"
    if dy > 0:
        return "south"
    return "west" if dx < 0 else "east"


async def run_level(
    screen, tiles, animsets, hero, sounds, options, current_slot, music=None
) -> bool:
    d = Dungeon(cfg.MAP_W, cfg.MAP_H, hero.depth)
    d.generate()
    monsters = {pos: generate_monster(d.depth) for pos in d.monsters}
    hero_anim = AnimState(animsets["hero"], fps=8, speed_scale=options["anim_speed"])
    monsters_anim = {}
    for m in monsters.values():
        sheets = animsets.get(m.glyph) or animsets.get("goblin")
        monsters_anim[id(m)] = AnimState(sheets, fps=6, speed_scale=options["anim_speed"])
    for a in monsters_anim.values():
        a.set_facing("south")  # monsters use a single south-facing idle
    hero_anim.set_facing("south")  # hero uses 4-directional art
    mon_slide = {id(m): SlideFX() for m in monsters.values()}
    ps = ParticleSystem()

    npcs = {}  # pos -> kind; collide to talk (not attack). Talk-NPCs block their tile.
    free = [
        (x, y)
        for y in range(d.h)
        for x in range(d.w)
        if d.grid[y][x] == FLOOR and (x, y) not in monsters and (x, y) != d.entry
    ]
    random.shuffle(free)

    def place_npc(kind: str) -> bool:
        # Talk-NPCs can't be killed or walked through, so only place them on an
        # open tile (room/junction: >=3 walkable neighbours) that keeps the exit
        # reachable when every NPC tile is blocked -- never sealing the only path.
        for pos in free:
            if d.walkable_neighbors(*pos) >= 3 and d.exit_reachable(set(npcs) | {pos}):
                free.remove(pos)
                npcs[pos] = kind
                return True
        return False

    if random.random() < MERCHANT_CHANCE:
        place_npc("merchant")
    if random.random() < TRAINER_CHANCE:
        place_npc("trainer")
    # Named story characters appear in their act band: Gildar parleys in the
    # Reading Halls, Sando recruits in the Unwritten Depths, and Rosmund's Shade
    # waits at the Heart (always) to resolve the endings.
    band = lore.band_for_depth(hero.depth)
    if band == lore.ACT2 and not hero.flags["gildar_met"] and random.random() < 0.5:
        place_npc("gildar")
    if band == lore.ACT3 and not hero.flags["sando_met"] and random.random() < 0.5:
        place_npc("sando")
    if band == lore.ACT4:
        place_npc("rosmund")

    npc_anim = {}
    for pos, kind in npcs.items():
        sheets = animsets.get(kind)
        if sheets:
            anim = AnimState(sheets, fps=5, speed_scale=options["anim_speed"])
            anim.set_facing("south")
            npc_anim[pos] = anim

    # --- Story lore placement ------------------------------------------------
    # Notes lie on the floor and inside secret rooms (read on arrival). Wall
    # inscriptions are carved on single-width corridor walls and read by bumping
    # them. Secret rooms are niches hidden behind a bumpable secret door.
    # lore_tiles: floor pos -> note key; wall_lore: wall pos -> (kind, key) where
    # kind is "inscr" (a carved inscription) or "secret" (a hidden door).
    lore_tiles: dict[tuple[int, int], str] = {}
    wall_lore: dict[tuple[int, int], tuple[str, str | None]] = {}
    seen = set(hero.lore_seen)
    for key in lore.pick_notes(hero.depth, random.randint(1, 2), seen):
        if not free:
            break
        pos = free.pop()
        d.grid[pos[1]][pos[0]] = NOTE
        lore_tiles[pos] = key
        seen.add(key)
    for key in lore.pick_inscriptions(hero.depth, random.randint(1, 2), seen):
        pos = secrets.corridor_wall(d, set(wall_lore))
        if pos is None:
            break
        wall_lore[pos] = ("inscr", key)
        seen.add(key)
    # The generator reserved a sealed secret room (if any). Drop a note inside,
    # sometimes a chest, and register its hidden door so bumping it opens the room.
    if d.secret_doors and d.secret_cells:
        note_keys = lore.pick_notes(hero.depth, 1, seen)
        if note_keys:
            cells = sorted(d.secret_cells)
            npos = cells[len(cells) // 2]
            d.grid[npos[1]][npos[0]] = NOTE
            lore_tiles[npos] = note_keys[0]
            seen.add(note_keys[0])
            if len(cells) > 2 and random.random() < 0.5:
                cx, cy = cells[0]
                d.grid[cy][cx] = CHEST
            wall_lore[d.secret_doors[0]] = ("secret", note_keys[0])

    hx, hy = d.entry
    rx, ry = float(hx), float(hy)
    moving = False
    move_from = (hx, hy)
    move_to = (hx, hy)
    move_acc = 0.0
    msg = i18n.t("msg.level_intro", depth=hero.depth)
    event_log = []

    world = pg.Surface((cfg.SCREEN_W, cfg.MAP_H * cfg.TILE))
    shake = Shake()
    flash_t = 0.0
    attack_cd = 0.0
    npc_block = False  # set after opening an NPC; cleared when no direction is held
    cast_block = False  # set after a cast so the aim key does not also step the hero
    crossbow_loaded = True  # a crossbow fires, then needs a reload press
    monster_turn_acc = 0.0  # accumulates dt; caster monsters fire each interval
    pending_ending = None  # set when Rosmund's dialogue resolves an ending

    def set_status(text: str):
        """Show a message at the bottom without recording it in the event log."""
        nonlocal msg
        msg = text

    muse_shown = set()  # run-local: each musing trigger fires at most once per level
    level_kills = [0]  # boxed for the kill-streak musing

    def note_muse(trigger: str):
        """Voice a one-off hero musing (shown in the status line, not a popup)."""
        avail = [k for k in lore.musings_for_trigger(trigger) if k not in hero.lore_seen]
        if not avail or trigger in muse_shown:
            return
        key = random.choice(avail)
        hero.lore_seen.append(key)
        muse_shown.add(trigger)
        set_msg(i18n.t(key))

    def set_msg(text: str):
        set_status(text)
        event_log.append(text)
        if len(event_log) > 400:
            del event_log[: len(event_log) - 400]

    def update_animations(dt):
        hero_anim.set_speed(options["anim_speed"])
        hero_anim.update(dt)
        for a in monsters_anim.values():
            a.set_speed(options["anim_speed"])
            a.update(dt)
        for a in npc_anim.values():
            a.set_speed(options["anim_speed"])
            a.update(dt)
        for fx in mon_slide.values():
            fx.update(dt)
        ps.update(dt)

    def spawn_scaled(func, tx, ty, n, **kw):
        k = max(0.0, options["particles"])
        count = max(0, int(n * k))
        if count <= 0:
            return
        getattr(ps, func)(tx, ty, n=count, **kw)

    def take_floor(tile) -> None:
        """Pick up a floor reward: coins (LOOT) give gold, POTION gives a potion."""
        sounds["pickup"].play()
        hero_anim.set("pickup", one_shot=True, queue_to="idle")
        if tile == POTION:
            if random.random() < 0.5:  # floor potions split between health and mana
                hero.mana_potions += 1
                set_msg(i18n.t("pickup.mana_potion"))
            else:
                hero.potions += 1
                set_msg(i18n.t("pickup.potion"))
        else:
            amount = floor_gold_amount(hero.depth)
            hero.gold += amount
            set_msg(i18n.t("pickup.gold", gold=amount))

    def open_chest() -> bool:
        """Open a chest. Returns False (leaves it) when the inventory is full."""
        result = resolve_chest(hero, hero.depth)
        if result.outcome == "inventory_full":
            set_msg(i18n.t("pickup.inventory_full", limit=INVENTORY_LIMIT))
            return False
        sounds["pickup"].play()
        hero_anim.set("pickup", one_shot=True, queue_to="idle")
        if result.outcome == "potion":
            set_msg(i18n.t("pickup.chest_potion"))
        elif result.outcome == "mana_potion":
            set_msg(i18n.t("pickup.chest_mana_potion"))
        elif result.outcome == "equipped":
            status = i18n.t(result.equip_status, item=i18n.item_name(result.item))
            set_msg(i18n.t("pickup.equipped", status=status))
        elif result.outcome == "stored":
            set_msg(i18n.t("pickup.stored", item=i18n.item_describe(result.item)))
        if result.item is not None and getattr(result.item, "unique", ""):
            note_muse("gold")  # a hero musing on finding a legendary gold artifact
        return True

    async def _open_npc(nx, ny):
        nonlocal pending_ending
        kind = npcs[(nx, ny)]
        if kind == "merchant":
            await shop_screen(screen, hero, hero.depth)
        elif kind == "trainer":
            await trainer_screen(screen, hero, options)
        else:  # a named story character: run their dialogue
            choice = await dialogue_screen(screen, kind, hero)
            if choice:  # only Rosmund's hinge returns an ending token
                pending_ending = endings.resolve(choice, hero)
            elif kind in ("gildar", "sando"):
                del npcs[(nx, ny)]  # they have said their piece and move on
        save_hero(current_slot, hero, options)

    async def try_start_move(dx, dy):
        nonlocal moving, move_from, move_to, move_acc, hx, hy, rx, ry, npc_block
        hero_anim.set_facing(_facing(dx, dy))
        nx, ny = hx + dx, hy + dy
        if not d.inside(nx, ny):
            return None
        if (nx, ny) in npcs:  # talk, do not attack or step onto them
            if not npc_block:
                npc_block = True
                await _open_npc(nx, ny)
            return None
        if (nx, ny) in monsters:  # monsters live in this dict, not on the grid
            if attack_cd > 0:
                return None
            return await _attack(nx, ny)
        tile = d.grid[ny][nx]
        if tile == WALL:
            mark = wall_lore.get((nx, ny))
            if mark is not None:  # an inscribed or secret-door wall: bump to use it
                kind, key = mark
                if kind == "inscr":
                    if key not in hero.lore_seen:
                        hero.lore_seen.append(key)
                    sounds["open"].play()
                    await note_screen(screen, "", i18n.t(key), inscription=True)
                else:  # secret door: open it, revealing the hidden room behind
                    d.grid[ny][nx] = FLOOR
                    del wall_lore[(nx, ny)]
                    sounds["open"].play()
                    set_msg(i18n.t("msg.secret_found"))
                return None
            set_status(i18n.t("msg.wall"))  # shown at the bottom, not logged
            sounds["wall"].play()
            return None
        if tile in (FLOOR, ENTRY, LOOT, POTION, CHEST, EXIT, NOTE, SECRET):
            moving = True
            move_from = (hx, hy)
            move_to = (nx, ny)
            move_acc = 0.0
            sounds["step"].play()
            return None
        return None

    def kill_monster(pos):
        """Award XP, drop loot, and remove a dead monster. Shared by melee and
        magic so both kill paths grant the same rewards and clean-up."""
        m = monsters[pos]
        nx, ny = pos
        prev = hero.level
        hero.gain_xp(m.xp_reward)
        if hero.level > prev:
            spawn_scaled("spawn_levelup", hx, hy, n=36)
            sounds["levelup"].play()
            auto_assign(hero, options["auto_stats"], options["auto_skills"])
        spawn_scaled("spawn_burst", nx, ny, n=22, base_col=(200, 60, 60))
        d.grid[ny][nx] = FLOOR
        del monsters[pos]
        del monsters_anim[id(m)]
        del mon_slide[id(m)]
        if random.random() < 0.4:
            d.grid[ny][nx] = LOOT if random.random() < 0.5 else POTION
        level_kills[0] += 1
        if level_kills[0] >= 5:  # a grim reflection after a string of kills
            note_muse("slaughter")

    def _lifesteal(damage_dealt):
        """A vampiric weapon heals its wielder for a third of damage dealt."""
        weapon = hero.equipment.get("MAIN")
        if weapon and "vampiric" in getattr(weapon, "affixes", ()) and damage_dealt >= 3:
            healed = min(hero.max_hp - hero.hp, damage_dealt // 3)
            if healed > 0:
                hero.hp += healed
                spawn_scaled("spawn_heal", hx, hy, n=6)

    async def _attack(nx, ny):
        nonlocal flash_t, attack_cd
        attack_cd = ATTACK_COOLDOWN
        m = monsters[(nx, ny)]
        a = monsters_anim[id(m)]
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
        if total > 0:
            shake.trigger(mag=3.0, dur=0.10)  # light shake when the hero lands a blow
            _lifesteal(total)
        if m.hp <= 0:
            set_msg(i18n.t("msg.killed", name=i18n.monster_name(m), xp=m.xp_reward))
            kill_monster((nx, ny))
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
        hero_dodge = hero.skills["DODGE"] + hero.dodge_bonus()
        for _ in range(mswings):
            md, _dead, dodged = try_attack(m, hero, hero.total_armor(), hero_dodge)
            if dodged:
                continue
            md_total += md
            spawn_scaled("spawn_hit", hx, hy, n=6, col=(255, 200, 200))
            if hero.hp <= 0:
                break
        if md_total > 0:
            sounds["hurt"].play()
            spawn_scaled("spawn_burst", hx, hy, n=10, base_col=(200, 70, 70))
            shake.trigger(mag=7.0, dur=0.20)  # stronger shake + red flash on taking damage
            flash_t = FLASH_DURATION
        hit_part = i18n.t("msg.you_hit", name=i18n.monster_name(m), total=total)
        tail = (
            i18n.t("msg.you_dodged")
            if md_total == 0
            else i18n.t("msg.monster_hit_back", name=i18n.monster_name(m), dmg=md_total)
        )
        set_msg(hit_part + tail)
        if 0 < hero.hp <= hero.max_hp // 4:
            note_muse("lowhp")
        if hero.hp <= 0:
            await message_box(screen, [i18n.t("msg.death_box")])
            return "dead"
        return None

    async def on_arrival():
        nonlocal hx, hy, rx, ry
        tile = d.grid[hy][hx]
        if tile == CHEST:
            if open_chest():
                d.grid[hy][hx] = FLOOR
        elif tile in (LOOT, POTION):
            take_floor(tile)
            d.grid[hy][hx] = FLOOR
        elif tile == NOTE:
            key = lore_tiles.pop((hx, hy), None)
            d.grid[hy][hx] = FLOOR
            if key:
                if key not in hero.lore_seen:
                    hero.lore_seen.append(key)
                inscr = lore.is_inscription(key)
                title = "" if inscr else i18n.t("ui.note.found")
                await note_screen(screen, title, i18n.t(key), inscription=inscr)
        elif tile == EXIT:
            sounds["open"].play()
            hero.depth += 1
            hero.unlocked_depth = max(hero.unlocked_depth, hero.depth)
            # Descending grants a partial recovery (~40%), not a full reset, so
            # potions and attrition still matter between floors.
            hero.hp = min(hero.max_hp, hero.hp + (hero.max_hp * 2) // 5)
            hero.mana = min(hero.max_mana, hero.mana + (hero.max_mana * 2) // 5)
            return True
        return False

    def render_world_frame(dt, overlay=None):
        """Draw one full world+HUD frame to the screen without flipping.

        Used by the spellcasting overlays so the dungeon keeps animating behind
        their menus and the projectile can be painted onto the world (under the
        screen-shake offset) via the ``overlay(world_surface)`` hook.
        """
        update_animations(dt)
        shake.update(dt)
        vis = compute_fov(d, hx, hy, cfg.FOV_RADIUS)
        world.fill(cfg.C_BG)
        draw_map(
            world,
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
            npcs,
            npc_anim,
            wall_lore,
        )
        ps.draw(world)
        if overlay:
            overlay(world)
        sx, sy = shake.offset()
        screen.fill((0, 0, 0))
        screen.blit(world, (sx, sy))
        draw_hud(screen, hero)
        draw_msg(screen, msg)

    def active_spell():
        """The spell bound to F (chosen in the spellbook), clamped to unlocked."""
        spell = sp.SPELL_BY_KEY.get(hero.active_spell)
        if spell is None or not sp.is_unlocked(spell, hero.skills["MAGIC"]):
            avail = sp.available_spells(hero.skills["MAGIC"])
            spell = avail[-1] if avail else sp.SPELLS[0]
            hero.active_spell = spell.key
        return spell

    async def cast_spell():
        """Cast the active spell: check mana, aim it, fly the projectile, apply it."""
        spell = active_spell()
        spell_name = i18n.t("magic.spell." + spell.key)
        if hero.mana < spell.mana_cost:
            set_status(i18n.t("magic.no_mana", spell=spell_name))
            return
        cast_clock = pg.time.Clock()
        reach = sp.spell_range(spell, hero.int_)
        direction = await choose_direction(
            screen,
            render_world_frame,
            cast_clock,
            d,
            (hx, hy),
            reach,
            i18n.t("ui.magic.dir_title", spell=spell_name),
        )
        if direction is None:
            return
        hero.mana -= spell.mana_cost  # spend only once the cast is committed
        hero.last_dir = direction
        hero_anim.set_facing(_facing(*direction))
        result = sp.resolve(
            spell,
            (hx, hy),
            direction,
            lambda x, y: (not d.inside(x, y)) or d.grid[y][x] == WALL,
            monsters.keys(),
            hero.int_,
            hero.skills["MAGIC"],
            wp.magic_power(hero.equipment.get("MAIN")),
        )
        hero_anim.set("cast", one_shot=True, queue_to="idle")
        await animate_cast(
            screen,
            render_world_frame,
            cast_clock,
            (hx, hy),
            result,
            ps,
            shake,
            sounds,
            options["particles"],
        )
        # Apply damage, capturing names before any monster is removed.
        applied = []  # (name, damage, killed)
        for h in result.hits:
            if h.pos not in monsters:
                continue
            m = monsters[h.pos]
            name = i18n.monster_name(m)
            m.hp -= h.damage
            dead = m.hp <= 0
            applied.append((name, h.damage, dead))
            if dead:
                kill_monster(h.pos)
        if not applied:
            set_msg(i18n.t("magic.spell_miss", spell=spell_name))
        elif len(applied) == 1:
            name, dmg, dead = applied[0]
            key = "magic.spell_killed" if dead else "magic.spell_hit"
            set_msg(i18n.t(key, name=name, dmg=dmg))
        else:
            slain = sum(1 for _, _, dead in applied if dead)
            set_msg(i18n.t("magic.spell_multi", spell=spell_name, count=len(applied), killed=slain))

    async def ranged_attack():
        """Fire the equipped bow/crossbow: aim, fly the bolt, resolve the hit."""
        nonlocal crossbow_loaded
        weapon = hero.equipment.get("MAIN")
        if not weapon or wp.category(weapon.kind) != "ranged":
            set_status(i18n.t("msg.no_ranged"))
            return
        if weapon.kind == "crossbow" and not crossbow_loaded:
            crossbow_loaded = True  # second press reloads instead of firing
            set_status(i18n.t("msg.crossbow_reload"))
            sounds["open"].play()
            return
        reach = wp.weapon_range(hero, weapon)
        shot_clock = pg.time.Clock()
        direction = await choose_direction(
            screen,
            render_world_frame,
            shot_clock,
            d,
            (hx, hy),
            reach,
            i18n.t("ui.ranged.dir_title", weapon=i18n.item_name(weapon)),
        )
        if direction is None:
            return
        if weapon.kind == "crossbow":
            crossbow_loaded = False
        hero.last_dir = direction
        hero_anim.set_facing(_facing(*direction))
        hero_anim.set("attack", one_shot=True, queue_to="idle")
        # Trace the bolt: stop at the first monster or wall within range.
        dx, dy = direction
        target = None
        end = (hx, hy)
        for i in range(1, reach + 1):
            x, y = hx + dx * i, hy + dy * i
            if not d.inside(x, y) or d.grid[y][x] == WALL:
                break
            end = (x, y)
            if (x, y) in monsters:
                target = (x, y)
                break
        await animate_shot(screen, render_world_frame, shot_clock, (hx, hy), end, sounds)
        if target is None:
            set_msg(i18n.t("msg.ranged_miss"))
            return
        m = monsters[target]
        name = i18n.monster_name(m)
        dmg_range = wp.ranged_damage(hero, weapon)
        dd, dead, dodged = try_attack(hero, m, m.armor + m.dex // 2, 0, damage=dmg_range)
        if dodged:
            set_msg(i18n.t("msg.monster_dodged", name=name))
            return
        spawn_scaled("spawn_hit", target[0], target[1], n=8, col=(255, 255, 180))
        sounds["hit"].play()
        _lifesteal(dd)
        if dead:
            set_msg(i18n.t("msg.ranged_killed", name=name, dmg=dd))
            kill_monster(target)
        else:
            set_msg(i18n.t("msg.ranged_hit", name=name, dmg=dd))

    def _caster_dir(mx, my, reach):
        """Return True if the hero is on a clear cardinal line from (mx,my) within
        ``reach`` (no walls between), so a caster monster can fire."""
        if mx == hx and my != hy and abs(my - hy) <= reach:
            step = 1 if hy > my else -1
            return all(d.grid[my + step * k][mx] != WALL for k in range(1, abs(my - hy)))
        if my == hy and mx != hx and abs(mx - hx) <= reach:
            step = 1 if hx > mx else -1
            return all(d.grid[my][mx + step * k] != WALL for k in range(1, abs(mx - hx)))
        return False

    _EFFECT_COLOR = {
        "ultrasound": (200, 130, 235),
        "magic_arrow": (150, 200, 255),
        "drain": (220, 70, 90),
    }

    def monster_casts(visible):
        """Caster monsters fire at the hero from range. Real-time, non-blocking:
        the hit shows as a coloured burst and flash rather than a flown bolt."""
        nonlocal flash_t
        for pos, m in list(monsters.items()):
            spec = caster_spec(m.kind)
            if not spec or pos not in visible or not _caster_dir(pos[0], pos[1], spec["range"]):
                continue
            dd, _dead, dodged = try_attack(
                m,
                hero,
                hero.total_armor(),
                hero.skills["DODGE"] + hero.dodge_bonus(),
                damage=caster_damage(m.kind, d.depth),
            )
            name = i18n.monster_name(m)
            if dodged:
                set_msg(i18n.t("msg.you_dodged_ranged", name=name))
                continue
            color = _EFFECT_COLOR.get(spec["effect"], (220, 120, 120))
            spawn_scaled("spawn_burst", hx, hy, n=10, base_col=color)
            shake.trigger(mag=5.0, dur=0.16)
            flash_t = FLASH_DURATION
            if spec["effect"] == "drain":
                m.hp = min(m.max_hp, m.hp + dd)  # vampire heals by damage dealt
            set_msg(i18n.t("msg.caster_hit", name=name, dmg=dd))
            if 0 < hero.hp <= hero.max_hp // 4:
                note_muse("lowhp")
            if hero.hp <= 0:
                return True
        return False

    # On entering the floor, voice the act-band musing (once ever); once the hero
    # has respawned enough times, the respawn-reveal musing seeds the twist.
    if hero.deaths >= lore.RESPAWN_REVEAL_DEATHS:
        note_muse("respawn")
    note_muse("band:" + lore.band_for_depth(hero.depth))

    clock = pg.time.Clock()
    while True:
        if pending_ending:  # Rosmund's choice resolved -> show it and end the run
            await ending_screen(screen, pending_ending)
            return "ending"
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
                if await on_arrival():
                    return True

        if attack_cd > 0:
            attack_cd = max(0.0, attack_cd - dt)
        if not moving:  # hold a direction to keep stepping that way
            pressed = pg.key.get_pressed()
            if not any(pressed[k] for k in _DIR_KEYS):
                npc_block = False  # released: allow re-opening an NPC on the next press
                cast_block = False  # released: the aim key no longer suppresses stepping
            elif not cast_block:  # an arrow held over from aiming must not step the hero
                for key, (dx, dy) in _DIR_KEYS.items():
                    if pressed[key]:
                        hero.last_dir = (dx, dy)
                        if await try_start_move(dx, dy) == "dead":
                            return False
                        break

        # Base hero pose: walk while sliding, idle when stopped. One-shot actions
        # (attack/cast/pickup/drink) keep priority until they finish.
        if not hero_anim.one_shot:
            hero_anim.set("walk" if moving else "idle")

        shake.update(dt)
        if flash_t > 0:
            flash_t = max(0.0, flash_t - dt)

        visible = compute_fov(d, hx, hy, cfg.FOV_RADIUS)

        # Caster monsters take a turn on a fixed interval, firing at the hero.
        monster_turn_acc += dt
        if monster_turn_acc >= MONSTER_TURN_INTERVAL:
            monster_turn_acc = 0.0
            if monster_casts(visible):
                await message_box(screen, [i18n.t("msg.death_box")])
                return False

        world.fill(cfg.C_BG)
        draw_map(
            world,
            tiles,
            hero_anim,
            monsters_anim,
            d,
            hero,
            rx,
            ry,
            monsters,
            visible,
            mon_slide,
            npcs,
            npc_anim,
            wall_lore,
        )
        ps.draw(world)
        sx, sy = shake.offset()
        screen.fill((0, 0, 0))
        screen.blit(world, (sx, sy))
        draw_hud(screen, hero)
        draw_msg(screen, msg)
        if flash_t > 0:
            draw_damage_flash(screen, flash_t / FLASH_DURATION)
        pg.display.flip()
        await asyncio.sleep(0)  # yield to the browser each frame (no-op on desktop)

        for e in pg.event.get():
            if e.type == pg.QUIT:
                save_hero(current_slot, hero, options)
                pg.quit()
                sys.exit(0)
            if e.type != pg.KEYDOWN:
                continue
            if e.key == pg.K_q:
                if await prompt_yes_no(screen, i18n.t("ui.quit_confirm")):
                    save_hero(current_slot, hero, options)
                    pg.quit()
                    sys.exit(0)
                continue
            if e.key == pg.K_g and not moving:
                if d.grid[hy][hx] in (LOOT, POTION):
                    take_floor(d.grid[hy][hx])
                    d.grid[hy][hx] = FLOOR
            elif e.key == pg.K_i:
                set_msg(await inventory_screen(screen, hero))
            elif e.key == pg.K_s:
                await stats_window(screen, hero, options)
            elif e.key == pg.K_k:
                await skills_window(screen, hero, options)
            elif e.key == pg.K_h:
                await help_screen(screen)
            elif e.key == pg.K_o:

                def apply_opts(opts):
                    for v in sounds.values():
                        v.set_volume(opts["volume"])

                await options_screen(screen, options, apply_opts)
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
                    hero_anim.set("drink", one_shot=True, queue_to="idle")
            elif e.key == pg.K_x:
                if hero.mana_potions <= 0:
                    set_msg(i18n.t("msg.no_mana_potions"))
                elif hero.mana >= hero.max_mana:
                    set_msg(i18n.t("msg.mana_full"))
                else:
                    gain = 8 + 4 * hero.level
                    restored = min(hero.max_mana - hero.mana, gain)
                    hero.mana += restored
                    hero.mana_potions -= 1
                    set_msg(
                        i18n.t("msg.mana_potion_used", restored=restored, potions=hero.mana_potions)
                    )
                    sounds["potion"].play()
                    hero_anim.set("drink", one_shot=True, queue_to="idle")
            elif e.key == pg.K_b:
                await spellbook_screen(screen, hero)
            elif e.key == pg.K_f and not moving:
                await cast_spell()
                cast_block = True  # don't let the aim key also step the hero
            elif e.key == pg.K_r and not moving:
                await ranged_attack()
                cast_block = True  # don't let the aim key also step the hero
            elif e.key == pg.K_p:

                def _save_cb():
                    save_hero(current_slot, hero, options)

                await pause_screen(
                    screen,
                    d,
                    hero,
                    (hx, hy),
                    monsters,
                    msg,
                    event_log,
                    on_save=_save_cb,
                    options=options,
                    music=music,
                )


def _init_pygame() -> str:
    """Init pygame and force the mixer to signed-16 mono at SND_RATE.

    pre_init's format is only a *request*. Browsers (pygbag/WASM) typically open
    the device as float32 stereo at 44.1/48 kHz; our raw int16 mono buffers then
    play back as noise and crackle. ``allowedchanges=0`` pins the obtained format
    to what we ask for (SDL converts to the hardware internally), so the buffers
    are interpreted correctly.

    On the web the audio pump shares the main thread with the game (no
    SharedArrayBuffer on GitHub Pages), so a slow frame starves it and crackles.
    A much larger mixer buffer (~190 ms) rides over multi-frame hitches; the
    extra latency is acceptable for ambience and short effects. Desktop keeps
    the snappy default. Falls back to a relaxed init (the buffer builder then
    adapts to whatever format the device reports), then to a silent dummy
    driver. SDL still picks the platform audio driver (coreaudio/wasapi)."""
    buffer = 4096 if sys.platform == "emscripten" else 512
    pg.mixer.pre_init(cfg.SND_RATE, cfg.SND_SIZE, cfg.SND_CHAN, buffer, allowedchanges=0)
    pg.init()
    try:
        pg.mixer.init(cfg.SND_RATE, cfg.SND_SIZE, cfg.SND_CHAN, buffer, allowedchanges=0)
    except pg.error:
        try:
            pg.mixer.init()  # relaxed: accept whatever the device offers
        except pg.error:
            os.environ["SDL_AUDIODRIVER"] = "dummy"
            with contextlib.suppress(pg.error):
                pg.mixer.init()
    return os.environ.get("SDL_AUDIODRIVER", "default")


async def run() -> None:
    _init_pygame()
    i18n.load_locales()

    screen = pg.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
    pg.display.set_caption(i18n.t("app.title"))

    async def loading(label):
        """Paint a status frame and yield, so the browser canvas isn't blank
        while assets and audio are synthesized (slow under WASM)."""
        screen.fill(cfg.C_BG)
        font = fonts.get_font(28, bold=True)
        surf = font.render(label, True, (210, 210, 240))
        screen.blit(surf, surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H // 2)))
        pg.display.flip()
        await asyncio.sleep(0)

    await loading(i18n.t("app.title"))
    tiles = build_tiles()
    animsets = build_animsets_from_atlas()
    hero_art = build_hero_animset()
    if hero_art:
        animsets["hero"] = hero_art  # PixelLab 4-directional hero, falls back to atlas
    animsets.update(build_creature_animsets("monsters"))  # override atlas monsters
    animsets.update(build_creature_animsets("npc"))  # "merchant", "trainer"
    animsets.setdefault("ghost", build_ghost_animset())  # procedural placeholder
    await loading(i18n.t("app.title"))
    sounds = make_sounds(master_volume=0.7)

    from .ui_start import start_menu

    await loading(i18n.t("app.title"))
    ambient = make_ambient()
    ambient.set_volume(0.5)

    while True:  # one iteration per campaign; an ending sends us back to the menu
        current_slot, hero, options = await start_menu(screen, sounds)
        i18n.set_locale(options.get("language", i18n.get_locale()))
        for v in sounds.values():
            v.set_volume(options.get("volume", 0.7))
        music = Music(ambient, enabled=options.get("music", True))

        while True:
            result = await run_level(
                screen, tiles, animsets, hero, sounds, options, current_slot, music
            )
            if result == "ending":
                save_hero(current_slot, hero, options)
                break  # campaign complete -> return to the start menu
            if not result:
                hero.hp = hero.max_hp
                hero.deaths += 1  # the city keeps a checkpoint of you (the story canon)
                await message_box(screen, [i18n.t("msg.respawn_1"), i18n.t("msg.respawn_2")])
