import json, pygame as pg
from . import config as cfg
from .respath import resource_path
def build_tiles():
    wall = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA); wall.fill((70,70,80)); pg.draw.rect(wall,(110,110,120),(0,0,cfg.TILE,cfg.TILE),1)
    floor = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA); floor.fill((24,24,32))
    chest = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA); chest.fill((50,50,20)); pg.draw.rect(chest,(210,170,40),(4,6,cfg.TILE-8,cfg.TILE-10), border_radius=4)
    exit = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA); exit.fill((22,26,30)); pg.draw.rect(exit,(40,180,180),(2,2,cfg.TILE-4,cfg.TILE-4),2, border_radius=6)
    shadow_soft = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA); shadow_soft.fill((0,0,0,120))
    shadow_hard = pg.Surface((cfg.TILE, cfg.TILE), pg.SRCALPHA); shadow_hard.fill((0,0,0,200))
    return {"wall":wall,"floor":floor,"chest":chest,"exit":exit,"shadow_soft":shadow_soft,"shadow_hard":shadow_hard}
def build_animsets_from_atlas():
    png = ("assets/le_mond_sprite_atlas.png")
    jsn = ("assets/le_mond_sprite_atlas.json")
    atlas = pg.image.load(png).convert_alpha(); meta = json.load(open(jsn,"r",encoding="utf-8"))
    def slice_rect(r):
        x,y,w,h=r["x"],r["y"],r["w"],r["h"]; s = pg.Surface((w,h), pg.SRCALPHA); s.blit(atlas,(0,0),(x,y,w,h)); return s
    def load_ent(ent_key):
        return { k:[slice_rect(rc) for rc in rects] for k,rects in meta["entities"][ent_key].items() }
    animsets = {}
    for ent in ["hero","goblin","orc","bat","ogre","armor","vampire"]:
        animsets[ent] = load_ent(ent)
    return animsets
