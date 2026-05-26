import io, math, struct, array
import pygame as pg
from . import config as cfg
def _wav_bytes(samples, rate=cfg.SND_RATE, nch=1, sampwidth=2):
    nframes = len(samples); data_bytes = samples.tobytes()
    byte_rate = rate * nch * sampwidth; block_align = nch * sampwidth
    buf = io.BytesIO()
    buf.write(b'RIFF'); buf.write(struct.pack('<I', 36 + len(data_bytes))); buf.write(b'WAVE')
    buf.write(b'fmt '); buf.write(struct.pack('<IHHIIHH', 16, 1, nch, rate, byte_rate, block_align, sampwidth*8))
    buf.write(b'data'); buf.write(struct.pack('<I', len(data_bytes))); buf.write(data_bytes); buf.seek(0); return buf
def synth_tone(freq=440.0, ms=120, volume=0.5, shape='sine'):
    rate = cfg.SND_RATE; n = int(rate * ms / 1000); arr = array.array('h'); amp = int(32767 * max(0.0, min(1.0, volume)))
    for i in range(n):
        t = i / rate
        if shape == 'sine': v = int(amp * math.sin(2*math.pi*freq*t))
        elif shape == 'square': v = int(amp * (1 if math.sin(2*math.pi*freq*t) >= 0 else -1))
        else: v = int(amp * math.sin(2*math.pi*freq*t))
        arr.append(v)
    return pg.mixer.Sound(file=_wav_bytes(arr))
def make_sounds(master_volume=0.7):
    s = {}
    s['step'] = synth_tone(520, 40, 0.25, 'sine')
    s['hit'] = synth_tone(220, 60, 0.6, 'square')
    s['hurt'] = synth_tone(120, 120, 0.6, 'square')
    s['pickup'] = synth_tone(880, 80, 0.5, 'sine')
    s['potion'] = synth_tone(660, 140, 0.5, 'sine')
    s['levelup'] = synth_tone(990, 180, 0.6, 'sine')
    s['magic'] = synth_tone(440, 120, 0.5, 'sine')
    s['open'] = synth_tone(350, 100, 0.5, 'sine')
    for v in s.values(): v.set_volume(master_volume)
    return s
