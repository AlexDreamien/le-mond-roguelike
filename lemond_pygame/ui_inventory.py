"""Inventory screen: an equipment paper-doll on the left and an item grid on the
right. Hover for a tooltip, click to select (Enter equip / Del drop), or
drag an item from the grid onto a matching equipment slot.
"""

from __future__ import annotations

import asyncio

import pygame as pg

from . import fonts, i18n
from .core import config as cfg
from .core.entities import EQUIP_SLOTS
from .core.loot import INVENTORY_LIMIT
from .core.weapons import can_equip
from .drawing import object_icon
from .ui_common import line, panel

SLOT = 64
CELL = 78
GRID_COLS = 3

# Anatomical layout of equipment slots (box top-left positions).
_LCX = 250  # left-area centre x
_SLOT_POS = {
    "HEAD": (_LCX - SLOT // 2, 120),
    "MAIN": (_LCX - SLOT // 2 - 104, 220),
    "BODY": (_LCX - SLOT // 2, 220),
    "OFF": (_LCX - SLOT // 2 + 104, 220),
    "HANDS": (_LCX - SLOT // 2 - 104, 330),
    "FEET": (_LCX - SLOT // 2 + 104, 330),
}


def _slot_rect(slot):
    x, y = _SLOT_POS[slot]
    return pg.Rect(x, y, SLOT, SLOT)


def _cell_rect(i):
    col, row = i % GRID_COLS, i // GRID_COLS
    return pg.Rect(560 + col * (CELL + 10), 130 + row * (CELL + 10), CELL, CELL)


def _equip_from_inventory(hero, idx) -> str:
    """Equip inventory[idx] into its own slot, swapping any worn item back."""
    item = hero.inventory[idx]
    slot = item.slot
    if not slot:
        return "equip.not_equippable"
    ok, unmet = can_equip(hero, item)
    if not ok:  # stat/skill requirement not met -> a specific message, no equip
        return "equip.req_" + (unmet if unmet in ("str", "dex", "int") else "skill")
    worn = hero.equipment.get(slot)
    status = hero.equip(item, to_slot=slot)
    if status == "equip.ok":
        hero.inventory.pop(idx)
        if worn is not None:
            hero.inventory.append(worn)
    return status


def _unequip(hero, slot) -> bool:
    item = hero.equipment.get(slot)
    if item and len(hero.inventory) < INVENTORY_LIMIT:
        hero.equipment[slot] = None
        hero.inventory.append(item)
        return True
    return False


def _blit_centered(screen, icon, rect):
    screen.blit(icon, icon.get_rect(center=rect.center))


async def inventory_screen(screen, hero) -> str:
    font = fonts.get_font(20)
    small = fonts.get_font(18)
    panel_rect = pg.Rect(40, 40, cfg.SCREEN_W - 80, cfg.SCREEN_H - 100)
    equip_btn = pg.Rect(560, 470, 180, 44)
    drop_btn = pg.Rect(750, 470, 180, 44)

    selected = 0
    drag_idx = None
    dragging = False
    down_pos = (0, 0)
    status = ""
    clock = pg.time.Clock()

    def clamp():
        nonlocal selected
        selected = max(0, min(selected, max(0, len(hero.inventory) - 1)))

    def slot_under(pos):
        for slot in EQUIP_SLOTS:
            if _slot_rect(slot).collidepoint(pos):
                return slot
        return None

    def cell_under(pos):
        for i in range(len(hero.inventory)):
            if _cell_rect(i).collidepoint(pos):
                return i
        return None

    def equip_selected():
        nonlocal status
        if 0 <= selected < len(hero.inventory):
            item = hero.inventory[selected]
            status = i18n.t(_equip_from_inventory(hero, selected), item=i18n.item_name(item))
            clamp()

    def drop_selected():
        nonlocal status
        if 0 <= selected < len(hero.inventory):
            hero.inventory.pop(selected)
            status = i18n.t("msg.dropped")
            clamp()

    def draw_tooltip(item, pos):
        lines = [i18n.item_name(item), i18n.t("ui.item.power", power=item.power)]
        if item.two_handed:
            lines.append(i18n.t("ui.item.two_handed"))
        w = max(small.size(s)[0] for s in lines) + 20
        h = 8 + len(lines) * 20
        x = min(pos[0] + 14, cfg.SCREEN_W - w - 6)
        y = min(pos[1] + 14, cfg.SCREEN_H - h - 6)
        panel(screen, pg.Rect(x, y, w, h))
        for j, s in enumerate(lines):
            line(screen, small, s, x + 10, y + 6 + j * 20, (230, 230, 200))

    def redraw(mouse):
        screen.fill(cfg.C_BG)
        panel(screen, panel_rect, i18n.t("ui.inventory.title"), icon="icon.inventory")
        line(screen, font, i18n.t("ui.inventory.equipment"), 80, 86, (200, 210, 240))
        line(screen, font, i18n.t("ui.inventory.items"), 560, 96, (200, 210, 240))

        hover_slot = slot_under(mouse) if dragging else None
        for slot in EQUIP_SLOTS:
            r = _slot_rect(slot)
            valid_drop = (
                dragging
                and r.collidepoint(mouse)
                and 0 <= drag_idx < len(hero.inventory)
                and hero.inventory[drag_idx].slot == slot
            )
            bg = (40, 60, 40) if valid_drop else (26, 26, 34)
            pg.draw.rect(screen, bg, r, border_radius=8)
            pg.draw.rect(
                screen, (90, 110, 90) if hover_slot == slot else (70, 70, 90), r, 2, border_radius=8
            )
            item = hero.equipment.get(slot)
            if item:
                icon = object_icon(f"item.{item.kind}", SLOT - 16)
                if icon:
                    _blit_centered(screen, icon, r)
            else:
                icon = object_icon(f"slot.{slot}", SLOT - 16)
                if icon:
                    faded = icon.copy()
                    faded.set_alpha(110)
                    _blit_centered(screen, faded, r)

        for i in range(INVENTORY_LIMIT):
            r = _cell_rect(i)
            has = i < len(hero.inventory)
            pg.draw.rect(screen, (24, 24, 32), r, border_radius=6)
            border = (200, 220, 160) if (has and i == selected) else (70, 70, 90)
            pg.draw.rect(screen, border, r, 2, border_radius=6)
            if has and not (dragging and i == drag_idx):
                icon = object_icon(f"item.{hero.inventory[i].kind}", CELL - 22)
                if icon:
                    _blit_centered(screen, icon, r)

        # Buttons
        active = 0 <= selected < len(hero.inventory)
        for rect, key in ((equip_btn, "ui.inventory.equip"), (drop_btn, "ui.inventory.drop")):
            pg.draw.rect(screen, (40, 50, 64) if active else (28, 28, 36), rect, border_radius=6)
            pg.draw.rect(
                screen, (90, 110, 150) if active else (60, 60, 74), rect, 2, border_radius=6
            )
            col = (220, 230, 240) if active else (120, 120, 130)
            line(screen, font, i18n.t(key), rect.x + 14, rect.y + 12, col)

        if status:
            line(screen, small, status, 560, 530, (200, 200, 160))
        line(
            screen,
            small,
            i18n.t("ui.inventory.close_hint"),
            560,
            panel_rect.bottom - 30,
            (160, 160, 200),
        )

        # Tooltip (hover) and dragged item on top.
        if not dragging:
            hi = cell_under(mouse)
            if hi is not None:
                draw_tooltip(hero.inventory[hi], mouse)
            else:
                hs = slot_under(mouse)
                if hs and hero.equipment.get(hs):
                    draw_tooltip(hero.equipment[hs], mouse)
        elif 0 <= drag_idx < len(hero.inventory):
            icon = object_icon(f"item.{hero.inventory[drag_idx].kind}", CELL - 22)
            if icon:
                screen.blit(icon, icon.get_rect(center=mouse))
        pg.display.flip()

    while True:
        clock.tick(cfg.FPS)
        mouse = pg.mouse.get_pos()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_ESCAPE, pg.K_i):
                    return i18n.t("msg.closed")
                if e.key in (pg.K_RETURN, pg.K_KP_ENTER):
                    equip_selected()
                if e.key in (pg.K_DELETE, pg.K_BACKSPACE):
                    drop_selected()
                if e.key == pg.K_LEFT:
                    selected -= 1
                    clamp()
                if e.key == pg.K_RIGHT:
                    selected += 1
                    clamp()
                if e.key == pg.K_UP:
                    selected -= GRID_COLS
                    clamp()
                if e.key == pg.K_DOWN:
                    selected += GRID_COLS
                    clamp()
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if equip_btn.collidepoint(e.pos):
                    equip_selected()
                elif drop_btn.collidepoint(e.pos):
                    drop_selected()
                else:
                    idx = cell_under(e.pos)
                    if idx is not None:
                        selected = idx
                        drag_idx = idx
                        dragging = False
                        down_pos = e.pos
                    else:
                        slot = slot_under(e.pos)
                        if slot and hero.equipment.get(slot) and _unequip(hero, slot):
                            status = i18n.t("ui.inventory.unequipped")
            elif e.type == pg.MOUSEMOTION:
                moved = abs(e.pos[0] - down_pos[0]) + abs(e.pos[1] - down_pos[1])
                if drag_idx is not None and e.buttons[0] and moved > 6:
                    dragging = True
            elif e.type == pg.MOUSEBUTTONUP and e.button == 1:
                if dragging and drag_idx is not None and 0 <= drag_idx < len(hero.inventory):
                    slot = slot_under(e.pos)
                    if slot and hero.inventory[drag_idx].slot == slot:
                        item = hero.inventory[drag_idx]
                        status = i18n.t(
                            _equip_from_inventory(hero, drag_idx), item=i18n.item_name(item)
                        )
                        clamp()
                drag_idx = None
                dragging = False
        redraw(mouse)
        await asyncio.sleep(0)
