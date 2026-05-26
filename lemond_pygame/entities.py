from dataclasses import dataclass, field
import random
EQUIP_SLOTS = ["MAIN","OFF","HEAD","BODY","HANDS","FEET"]
@dataclass
class Item:
    name:str
    slot:str|None
    power:int=0
    two_handed:bool=False
    def describe(self): return f"{self.name} ({self.slot or 'прочее'}, +{self.power})"
@dataclass
class Creature:
    name:str
    max_hp:int
    hp:int
    str_:int
    dex:int
    int_:int
    glyph:str='?'
    hostile:bool=True
    xp_reward:int=5
    armor:int=0
    def melee_damage(self):
        base = max(1, self.str_//2)
        return (base, base+2)
@dataclass
class Hero(Creature):
    inventory:list=field(default_factory=list)
    equipment:dict=field(default_factory=lambda:{s:None for s in EQUIP_SLOTS})
    level:int=1
    xp:int=0
    stat_points:int=0
    skill_points:int=0
    skills:dict=field(default_factory=lambda:{"MELEE":0,"DODGE":0,"MAGIC":0})
    potions:int=0
    depth:int=1
    unlocked_depth:int=1
    last_dir:tuple[int,int]=(1,0)
    def total_armor(self):
        val = 0
        for it in self.equipment.values():
            if it and it.slot in ("OFF","HEAD","BODY","HANDS","FEET"):
                val += max(0, it.power)
        return val + (self.str_//5)
    def weapon_damage(self):
        wep = self.equipment.get("MAIN")
        base = 1 + self.str_//2 + self.skills["MELEE"]
        if wep: base += wep.power
        return (max(1,base-1), base+1)
    def melee_damage(self): return self.weapon_damage()
    def recompute_max_hp(self): self.max_hp = 16 + self.str_*2
    def xp_to_next(self): return 20 + (self.level-1)*15
    def gain_xp(self, v:int):
        self.xp += v
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1; self.stat_points += 2; self.skill_points += 1
    def equip(self, item:Item, to_slot:str|None=None):
        slot = to_slot or item.slot
        if not slot: return "Нельзя экипировать."
        if slot=="MAIN" and item.two_handed and self.equipment.get("OFF") is not None:
            return "Нельзя: двуручное оружие и щит вместе."
        if slot=="OFF":
            main=self.equipment.get("MAIN")
            if main and getattr(main, "two_handed", False):
                return "Нельзя: щит с двуручным оружием."
        self.equipment[slot] = item
        return f"Экипировано: {item.name}"
def random_loot(depth:int) -> Item:
    roll = random.random()
    tier = 1 + min(5, depth//2)
    if roll < 0.25:
        return Item(f"Меч {tier}", "MAIN", power=tier, two_handed=False)
    elif roll < 0.40:
        return Item(f"Топор {tier}", "MAIN", power=tier+1, two_handed=True)
    elif roll < 0.55:
        return Item(f"Посох {tier}", "MAIN", power=tier, two_handed=False)
    elif roll < 0.70:
        return Item(f"Щит {tier}", "OFF", power=tier)
    elif roll < 0.80:
        return Item(f"Шлем {tier}", "HEAD", power=tier)
    elif roll < 0.90:
        return Item(f"Броня {tier}", "BODY", power=tier+1)
    elif roll < 0.95:
        return Item(f"Перчатки {tier}", "HANDS", power=tier)
    else:
        return Item(f"Сапоги {tier}", "FEET", power=tier)
