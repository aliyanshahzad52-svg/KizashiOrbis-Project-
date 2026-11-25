"""Original soundtrack for the KizashiOrbis crow & fish-bowl animation (fully synthesised, no samples, no voice).

Light, witty, modern: muted plucks and a soft kick/clap groove in F major at 100 bpm, with sound design on the
picture - headline whooshes, icon pops, pebbles plopping into the bowl, bubbles, straw sips, the logo spin and a
resolving chime on the contact card.

Usage: python3 music.py <out.wav>
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "promo"))
import sfx  # noqa: E402

OUT = sys.argv[1]
DUR = 20.0
SR = 48000
N = int(SR * (DUR + 3))
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)
HITS = [3.21, 6.31, 9.41, 12.21]          # pebble impacts measured from the animation
E0 = 13.6                                  # ending starts


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def t_(d): return np.arange(int(SR * d)) / SR


def add(sig, t0, g=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if i0 < 0: sig = sig[-i0:]; i0 = 0
    if i0 >= N: return
    sig = sig[:N - i0]
    L[i0:i0 + len(sig)] += sig * g * np.sqrt(0.5 * (1 - pan))
    R[i0:i0 + len(sig)] += sig * g * np.sqrt(0.5 * (1 + pan))


def filt(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); H = np.ones_like(f)
    if hi: H /= 1 + (f / hi) ** 4
    if lo: H /= 1 + (lo / np.maximum(f, 1)) ** 4
    return np.fft.irfft(X * H, len(x))


def pluck(note, dur=0.9, bright=3000):
    """Muted marimba-ish pluck."""
    t = t_(dur); f = midi(note)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 6) + 0.35 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 22) \
        + 0.18 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 10)
    return filt(s, hi=bright) * np.minimum(t / 0.003, 1)


def pad(notes, dur, att=0.8, rel=1.2, cut=1500):
    t = t_(dur + rel); out = np.zeros(len(t))
    for n in notes:
        for d in (-6, 0, 5):
            ff = midi(n) * 2 ** (d / 1200)
            out += np.sin(2 * np.pi * ff * t) + 0.3 * np.sin(4 * np.pi * ff * t)
    out = filt(out, hi=cut) / (len(notes) * 3)
    return out * np.minimum(t / att, 1) ** 2 * np.clip(1 - (t - dur) / rel, 0, 1)


def kick():
    t = t_(0.35); f = 48 + 90 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)


def clap():
    t = t_(0.25); n = filt(rng.uniform(-1, 1, len(t)), lo=900, hi=6000)
    env = sum(np.exp(-np.maximum(t - d, 0) / 0.012) * (t >= d) for d in (0, 0.011, 0.022)) * 0.5 + np.exp(-t / 0.08) * 0.5
    return n * env


def hat(open_=False):
    t = t_(0.2 if open_ else 0.06)
    return filt(rng.uniform(-1, 1, len(t)), lo=7000) * np.exp(-t / (0.06 if open_ else 0.015))


def plop(pitch=1.0):
    """Pebble into water: deep 'bloop' (falling-then-rising cavity tone) plus a splashy spray."""
    t = t_(0.5)
    f = (380 + 520 * (1 - np.exp(-t / 0.03))) * pitch
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.07)
    thump = np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.05) * 0.6
    spray = filt(rng.uniform(-1, 1, len(t)), lo=1800, hi=9000) * (np.exp(-t / 0.05) * 0.5 + np.exp(-t / 0.25) * 0.12)
    return tone * 0.9 + thump + spray


def bubbles(d=1.4, n=9):
    out = np.zeros(int(SR * d))
    for k in range(n):
        tt = t_(0.08); f = (900 + 900 * rng.random()) * (1 + 1.5 * tt / 0.08)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.02)
        i = int(SR * (0.08 + rng.random() * (d - 0.2))); out[i:i + len(b)] += b * (0.35 + 0.4 * rng.random())
    return out


def sip(d=0.45):
    t = t_(d); x = t / d
    n = filt(rng.uniform(-1, 1, len(t)), lo=700, hi=3200) * np.sin(np.pi * x) ** 2
    gurg = np.sin(2 * np.pi * (180 + 60 * np.sin(2 * np.pi * 18 * t)) * t) * np.sin(np.pi * x) * 0.25
    return n * 0.6 + gurg


def pop():
    t = t_(0.09); f = 900 * np.exp(-t / 0.02) + 500
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)


def swish(d=0.4, lo=600, hi=7000, rise=True):
    t = t_(d); x = t / d
    env = (x ** 2 if rise else (1 - x) ** 2) * np.sin(np.pi * x)
    return filt(rng.uniform(-1, 1, len(t)), lo=lo, hi=hi) * env


def chime(notes, d=3.0):
    t = t_(d); s = np.zeros(len(t))
    for n in notes:
        f = midi(n)
        s += (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3)) * np.exp(-t * 1.4)
    return s / len(notes)


# ------------------------------------------------------------------ groove (100 bpm), F major: F - Dm - Bb - C
BPM = 100; B = 60 / BPM
CH = [[53, 57, 60, 65], [50, 57, 62, 65], [46, 58, 62, 65], [48, 55, 60, 64]]
ARP = [[65, 69, 72, 69], [62, 65, 69, 65], [62, 65, 70, 65], [64, 67, 72, 67]]
bar = 4 * B
t = 0.0; k = 0
while t < E0 - 0.05:
    ch = CH[k % 4]
    add(pad(ch, bar, att=0.5, rel=0.9, cut=1300), t, 0.30)
    add(pad([ch[0] - 12], bar, att=0.05, rel=0.4, cut=260), t, 0.55)           # warm sub bass
    for i in range(8):                                                           # 8th-note plucks
        tt = t + i * B / 2
        if tt > E0 - 0.1: break
        add(pluck(ARP[k % 4][i % 4] + (12 if i in (3, 7) else 0)), tt, 0.16 if i % 2 == 0 else 0.11, 0.35 * np.sin(i))
    if t >= 2 * B:                                                               # groove enters after the headline
        for i in range(4):
            tt = t + i * B
            if tt > E0 - 0.1: break
            if i in (0, 2): add(kick(), tt, 0.55)
            if i in (1, 3): add(clap(), tt, 0.16, 0.1)
            add(hat(), tt + B / 2, 0.07, -0.3); add(hat(), tt, 0.04, 0.3)
    t += bar; k += 1
# ending: brand moment - wide pad and resolving chime, no drums
add(pad([41, 53, 57, 60, 65, 69, 72], 6.0, att=0.6, rel=1.5, cut=2200), E0 + 0.1, 0.42)
add(pad([29], 6.0, att=0.4, rel=1.2, cut=200), E0 + 0.1, 0.5)

# ------------------------------------------------------------------ sound design on picture
add(swish(0.35, 800, 6000), 0.12, 0.18); add(swish(0.45, 400, 5000), 0.32, 0.22)       # We / Build
add(swish(0.6, 1500, 9000, rise=False), 0.95, 0.12, 0.3)                               # script writes on
add(swish(0.35, 2000, 9000, rise=False), 1.5, 0.08, 0.2)                               # underline
for i in range(5): add(pop(), 1.92 + i * 0.09, 0.12, -0.6 + 0.3 * i)                    # service icons
for i in range(6): add(pop() * 0.8, 2.52 + i * 0.06, 0.09, -0.5 + 0.2 * i)               # social icons
for i, h in enumerate(HITS):
    add(swish(0.45, 1500, 6000), h - 0.5, 0.06, -0.3)                                     # pebble falling
    add(plop(1.0 + 0.06 * i), h, 0.42, -0.15); add(bubbles(1.4), h + 0.1, 0.10, -0.1)
for s in (4.6, 7.7, 10.7):
    add(sip(), s, 0.16, 0.45)                                                             # straw sips
# ending
add(sfx.whoosh_in(0.9), E0 - 0.1, 0.22)
add(swish(1.5, 500, 8000), E0 + 0.3, 0.12)
add(sfx.shimmer(), E0 + 1.0, 0.16)
add(chime([77, 81, 84, 89], 3.5), E0 + 1.9, 0.22)
add(pop(), E0 + 2.1, 0.12, -0.2); add(pop(), E0 + 2.3, 0.12, 0.2)

# ------------------------------------------------------------------ bus
ir_len = int(2.0 * SR)
ir = rng.normal(0, 1, ir_len) * np.exp(-np.arange(ir_len) / SR / 0.5); ir = filt(ir, hi=7000); ir /= np.sqrt((ir ** 2).sum())
def conv(x, h):
    nf = 1 << (len(x) + len(h) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]
L, R = L + 0.25 * conv(L, ir), R + 0.25 * conv(R, np.roll(ir, 173))
end = int(DUR * SR); g = np.ones(N)
g[:int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR)); f = int(1.2 * SR)
g[end - f:end] = np.linspace(1, 0, f) ** 1.5; g[end:] = 0
mix = np.stack([L * g, R * g], 1)[:end]; mix /= np.abs(mix).max() + 1e-9
tmp = tempfile.mkdtemp()
w = wave.open(f"{tmp}/raw.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 0.9 * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{tmp}/raw.wav", "-af",
                "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=150:makeup=2,loudnorm=I=-14:TP=-1.0:LRA=9",
                "-ar", str(SR), OUT], check=True)
print("wrote", OUT)
