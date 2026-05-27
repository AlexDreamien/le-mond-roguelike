import array
import io
import math
import struct

import pygame as pg

from .core import config as cfg


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
    return pg.mixer.Sound(file=_wav_bytes(arr))


def make_sounds(master_volume=0.7):
    s = {}
    s["step"] = synth_tone(520, 40, 0.25, "sine")
    s["hit"] = synth_tone(220, 60, 0.6, "square")
    s["hurt"] = synth_tone(120, 120, 0.6, "square")
    s["pickup"] = synth_tone(880, 80, 0.5, "sine")
    s["potion"] = synth_tone(660, 140, 0.5, "sine")
    s["levelup"] = synth_tone(990, 180, 0.6, "sine")
    s["magic"] = synth_tone(440, 120, 0.5, "sine")
    s["open"] = synth_tone(350, 100, 0.5, "sine")
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
    return pg.mixer.Sound(file=_wav_bytes(arr))


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
