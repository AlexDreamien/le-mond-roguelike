import os, json
from pathlib import Path
from .entities import Hero, Item, EQUIP_SLOTS
def _folder():
    base = os.getenv('LOCALAPPDATA') or os.path.expanduser(r'~\AppData\Local')
    p = Path(base) / 'Le-Mond Roguelike'; p.mkdir(parents=True, exist_ok=True); return p
def save_path(slot:int)->str: return str(_folder() / f"save_{slot}.json")
def _mk_item(d): return Item(name=d['name'], slot=d.get('slot'), power=d.get('power',0), two_handed=d.get('two_handed',False))
def save_hero(slot:int, hero:Hero, options:dict):
    data = {
        "name": hero.name, "class": getattr(hero, "class_name", "Герой"),
        "max_hp": hero.max_hp, "hp": hero.hp, "str_": hero.str_, "dex": hero.dex, "int_": hero.int_,
        "level": hero.level, "xp": hero.xp, "stat_points": hero.stat_points, "skill_points": hero.skill_points,
        "depth": hero.depth, "unlocked_depth": hero.unlocked_depth, "skills": hero.skills, "potions": hero.potions,
        "inventory": [{"name": it.name, "slot": it.slot, "power": it.power, "two_handed": it.two_handed} for it in hero.inventory],
        "equipment": {slot: (None if it is None else {"name": it.name, "slot": it.slot, "power": it.power, "two_handed": it.two_handed}) for slot,it in hero.equipment.items()},
        "options": options or {"anim_speed":1.0,"particles":1.0,"volume":0.7}
    }
    with open(save_path(slot), "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
def load_hero(slot:int):
    p = save_path(slot); opts = {"anim_speed":1.0,"particles":1.0,"volume":0.7}
    if not os.path.exists(p): return None, opts
    with open(p, "r", encoding="utf-8") as f: data = json.load(f)
    h = Hero(name=data.get("name","Густав"), max_hp=data.get("max_hp",20), hp=data.get("hp",20),
             str_=data.get("str_",5), dex=data.get("dex",5), int_=data.get("int_",5), glyph='hero')
    h.class_name = data.get("class","Герой")
    h.level = data.get("level",1); h.xp = data.get("xp",0)
    h.stat_points = data.get("stat_points",0); h.skill_points = data.get("skill_points",0)
    h.depth = data.get("depth",1); h.unlocked_depth = data.get("unlocked_depth", h.depth)
    h.skills = data.get("skills", {"MELEE":0,"DODGE":0,"MAGIC":0}); h.potions = data.get("potions", 0)
    h.inventory = [_mk_item(it) for it in data.get("inventory",[])]
    h.equipment = {s: None for s in EQUIP_SLOTS}
    for slot, it in data.get("equipment",{}).items():
        h.equipment[slot] = None if it is None else _mk_item(it)
    opts.update(data.get("options", {})); return h, opts
def list_saves():
    res=[]
    for i in range(1,6):
        p = save_path(i)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f: d=json.load(f)
                res.append({"slot":i,"name":d.get("name","Густав"),"class":d.get("class","Герой"),"level":d.get("level",1),"depth":d.get("depth",1),"exists":True})
            except Exception:
                res.append({"slot":i,"exists":False})
        else: res.append({"slot":i,"exists":False})
    return res
def delete_save(slot:int):
    try: os.remove(save_path(slot))
    except FileNotFoundError: pass
