import array
import io
import math
import random
import struct

import pygame as pg

from .core import config as cfg


class _SilentSound:
    """No-op stand-in used when the platform can't create mixer Sounds.

    pygbag/WASM raises 'can't access resource on platform' for in-memory
    ``mixer.Sound`` buffers, so on the web we fall back to silence instead of
    crashing. The interface matches the bits of pygame.mixer.Sound the game
    uses (play/set_volume), and play() returns None so the Music wrapper just
    sees an idle channel."""

    def play(self, *args, **kwargs):
        return None

    def set_volume(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass


def _make_sound(samples):
    """Build a mixer Sound from raw 16-bit mono samples (an ``array('h')``).

    Uses an in-memory ``buffer`` matched to the mixer's actual rate/channels
    rather than a WAV ``file=`` object: pygbag/WASM raises 'can't access resource
    on platform' for file-like sources but accepts raw buffers. The samples are
    generated at ``cfg.SND_RATE`` mono, so resample (nearest) and duplicate
    across channels when the mixer opened with a different format. Falls back to
    the WAV path on desktop, then to silence, if the platform refuses."""
    try:
        init = pg.mixer.get_init()
        rate = init[0] if init else cfg.SND_RATE
        channels = init[2] if init else 1
        data = samples
        if rate != cfg.SND_RATE:  # nearest-neighbour resample to the mixer rate
            ratio = rate / cfg.SND_RATE
            count = int(len(data) * ratio)
            last = len(data) - 1
            data = array.array("h", (data[min(last, int(i / ratio))] for i in range(count)))
        if channels >= 2:  # replicate the mono signal across channels, interleaved
            interleaved = array.array("h")
            for s in data:
                interleaved.extend((s,) * channels)
            data = interleaved
        return pg.mixer.Sound(buffer=data.tobytes())
    except Exception:
        try:
            return pg.mixer.Sound(file=_wav_bytes(samples))
        except Exception:
            return _SilentSound()


def _wav_bytes(samples, rate=cfg.SND_RATE, nch=1, sampwidth=2):
    data_bytes = samples.tobytes()
    byte_rate = rate * nch * sampwidth
    block_align = nch * sampwidth
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(data_bytes)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, nch, rate, byte_rate, block_align, sampwidth * 8))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(data_bytes)))
    buf.write(data_bytes)
    buf.seek(0)
    return buf


def synth_tone(freq=440.0, ms=120, volume=0.5, shape="sine"):
    rate = cfg.SND_RATE
    n = int(rate * ms / 1000)
    arr = array.array("h")
    amp = int(32767 * max(0.0, min(1.0, volume)))
    for i in range(n):
        t = i / rate
        if shape == "sine":
            v = int(amp * math.sin(2 * math.pi * freq * t))
        elif shape == "square":
            v = int(amp * (1 if math.sin(2 * math.pi * freq * t) >= 0 else -1))
        else:
            v = int(amp * math.sin(2 * math.pi * freq * t))
        arr.append(v)
    return _make_sound(arr)


def _render(samples, volume=0.6) -> pg.mixer.Sound:
    amp = 32767 * max(0.0, min(1.0, volume))
    arr = array.array("h", (int(max(-1.0, min(1.0, s)) * amp) for s in samples))
    return _make_sound(arr)


def _footstep(volume=0.3) -> pg.mixer.Sound:
    """A soft, dull noise burst — a foot landing on stone."""
    n = int(cfg.SND_RATE * 0.09)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / cfg.SND_RATE
        lp = lp * 0.82 + random.uniform(-1, 1) * 0.18  # low-pass for a muffled thud
        out.append(lp * math.exp(-t * 45))
    return _render(out, volume)


def _thud(freq=95, ms=150, volume=0.5) -> pg.mixer.Sound:
    """A low damped thump with a little noise — bumping a wall."""
    n = int(cfg.SND_RATE * ms / 1000)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / cfg.SND_RATE
        env = math.exp(-t * 22)
        lp = lp * 0.9 + random.uniform(-1, 1) * 0.1
        out.append(env * (0.6 * math.sin(2 * math.pi * freq * t) + 0.4 * lp))
    return _render(out, volume)


def _impact(volume=0.55) -> pg.mixer.Sound:
    """A sharp whack plus a low thump — a melee hit."""
    n = int(cfg.SND_RATE * 0.13)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / cfg.SND_RATE
        lp = lp * 0.5 + random.uniform(-1, 1) * 0.5  # brighter noise
        crack = lp * math.exp(-t * 32)
        thump = math.sin(2 * math.pi * 70 * t) * math.exp(-t * 42)
        out.append(0.7 * crack + 0.55 * thump)
    return _render(out, volume)


def _chest(volume=0.5) -> pg.mixer.Sound:
    """A wooden creak followed by a latch click — opening a chest."""
    n = int(cfg.SND_RATE * 0.45)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / cfg.SND_RATE
        wobble = 0.5 + 0.5 * math.sin(2 * math.pi * 6 * t)  # creak
        lp = lp * 0.7 + random.uniform(-1, 1) * 0.3
        out.append(lp * wobble * max(0.0, 1.0 - t / 0.45) * 0.5)
    click = int(cfg.SND_RATE * 0.30)
    for i in range(click, min(n, click + int(cfg.SND_RATE * 0.03))):
        out[i] += random.uniform(-1, 1) * math.exp(-(i - click) / cfg.SND_RATE * 120) * 0.6
    return _render(out, volume)


def make_sounds(master_volume=0.7):
    s = {}
    s["step"] = _footstep(0.30)
    s["hit"] = _impact(0.55)
    s["wall"] = _thud(95, 150, 0.5)
    s["open"] = _chest(0.5)
    s["hurt"] = synth_tone(120, 120, 0.6, "square")
    s["pickup"] = synth_tone(880, 80, 0.5, "sine")
    s["potion"] = synth_tone(660, 140, 0.5, "sine")
    s["levelup"] = synth_tone(990, 180, 0.6, "sine")
    s["magic"] = synth_tone(440, 120, 0.5, "sine")
    for v in s.values():
        v.set_volume(master_volume)
    return s


def make_ambient(volume: float = 0.45) -> pg.mixer.Sound:
    """Synthesize a quiet, seamlessly looping ambient dungeon drone.

    The low drones are snapped to a whole number of cycles over the loop length
    so the buffer loops without a click; the sparse melody fades to silence at
    both ends, so it never crosses the loop boundary.
    """
    rate = cfg.SND_RATE
    length = 8.0
    n = int(rate * length)
    two_pi = 2 * math.pi

    def cycles(freq):
        return round(freq * length) / length

    breath = cycles(0.125)
    drones = [(cycles(110.0), 0.50), (cycles(164.81), 0.30), (cycles(220.0), 0.16)]  # A2, E3, A3
    samples = [0.0] * n
    for i in range(n):
        t = i / rate
        env = 0.7 + 0.3 * math.sin(two_pi * breath * t)
        acc = 0.0
        for freq, amp in drones:
            acc += amp * math.sin(two_pi * freq * t)
        samples[i] = acc * env

    # Sparse A-minor-pentatonic shimmer; each note fades in and out (zero at edges).
    motif = [(220.0, 0.4, 1.6), (261.63, 2.3, 1.4), (329.63, 4.2, 1.3), (196.0, 6.0, 1.6)]
    for freq, start, dur in motif:
        s0 = int(start * rate)
        s1 = min(n, int((start + dur) * rate))
        span = max(1, s1 - s0)
        for i in range(s0, s1):
            fade = math.sin(math.pi * (i - s0) / span)
            samples[i] += 0.16 * fade * math.sin(two_pi * freq * (i / rate))

    peak = max(1e-6, max(abs(v) for v in samples))
    amp = int(32767 * max(0.0, min(1.0, volume)))
    arr = array.array("h", (int(amp * (v / peak)) for v in samples))
    return _make_sound(arr)


class Music:
    """Loops a single ambient track on its own channel, with on/off control."""

    def __init__(self, sound: pg.mixer.Sound, enabled: bool = True):
        self.sound = sound
        self.enabled = enabled
        self.channel = None
        if enabled:
            self._start()

    def _start(self):
        self.channel = self.sound.play(loops=-1)

    def set_enabled(self, on: bool) -> None:
        self.enabled = bool(on)
        if self.enabled:
            if self.channel is None or not self.channel.get_busy():
                self._start()
        elif self.channel is not None:
            self.channel.stop()
            self.channel = None
