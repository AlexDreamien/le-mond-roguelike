"""Game-wide constants: display geometry, balance, and audio format."""

# Display geometry
TILE = 32
MAP_W, MAP_H = 32, 20
HUD_H = 116  # four rows: bars, stats, status message, hotkey hints
SCREEN_W, SCREEN_H = MAP_W * TILE, MAP_H * TILE + HUD_H
FPS = 60
FOV_RADIUS = 8

# Palette
C_BG = (5, 5, 8)
C_TEXT = (220, 220, 220)
C_PANEL = (18, 18, 26)
C_PANEL_BORDER = (70, 70, 90)
C_HP_BG = (60, 20, 20)
C_HP_FG = (40, 200, 90)

# Audio mixer format
SND_RATE = 22050
SND_SIZE = -16
SND_CHAN = 1

MONSTER_TYPES = ["goblin", "orc", "bat", "ogre", "armor", "vampire"]
