"""Original soundtrack for the OrbisNexa office promo (synthesised, royalty-free).

Warm, uplifting 96 BPM bed in D major (D - A - Bm - G): soft pads, plucked arpeggio, light percussion
that builds through the packing and lifts into the brand reveal. Sound effects are placed on the exact
animation times of pack.html (latches, lid, every item landing, flip, reveal, final screen).

Usage: python3 pack_music.py <out.wav>
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "promo"))
import sfx  # noqa: E402

OUT = sys.argv[1]
SR = 48000
import json
E = json.load(open("edit.json"))
DUR = E["duration"]
N = int(SR * (DUR + 2))
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(5)
BEAT = 60 / 100
BAR = 4 * BEAT


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def t_(d): return np.arange(int(SR * d)) / SR


def add(sig, t0, g=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N or i0 < 0: return
    sig = sig[:N - i0]
    L[i0:i0 + len(sig)] += sig * g * np.sqrt(0.5 * (1 - pan))
    R[i0:i0 + len(sig)] += sig * g * np.sqrt(0.5 * (1 + pan))


def lp(x, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / hi) ** 4), len(x))


def hp(x, lo):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (lo / np.maximum(f, 1)) ** 4), len(x))


def saw(f, t):
    out = np.zeros_like(t)
    for h in range(1, 20):
        if f * h > 14000: break
        out += np.sin(2 * np.pi * f * h * t) / h
    return out * 0.6


def pad(notes, dur, att=0.6, rel=1.4):
    t = t_(dur + rel); out = np.zeros(len(t))
    for n in notes:
        for d in (-8, 0, 9):
            out += saw(midi(n) * 2 ** (d / 1200), t)
    out = lp(out, 1800) / (len(notes) * 3)
    return out * np.minimum(t / att, 1) * np.clip(1 - (t - dur) / rel, 0, 1)


def keys(note, dur=1.6):
    """Soft electric-piano-like tone."""
    t = t_(dur); f = midi(note)
    s = np.sin(2 * np.pi * f * t + 0.8 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.4))
    s += 0.25 * np.sin(2 * np.pi * f * 3 * t) * np.exp(-t / 0.25)
    return s * np.exp(-t / 0.9) * np.minimum(t / 0.004, 1)


def pluck(note, dur=0.5):
    t = t_(dur); f = midi(note)
    s = lp(saw(f, t) * np.exp(-t / 0.1) + 0.2 * saw(f, t) * np.exp(-t / 0.4), 3600)
    return s * np.minimum(t / 0.003, 1)


def kick():
    t = t_(0.35)
    return np.tanh(1.4 * np.sin(2 * np.pi * np.cumsum(48 + 80 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.2))


def shaker():
    t = t_(0.09)
    return hp(rng.uniform(-1, 1, len(t)), 6000) * np.sin(np.pi * t / t[-1]) ** 2


def snap():
    t = t_(0.2)
    return hp(lp(rng.uniform(-1, 1, len(t)), 7000), 1200) * np.exp(-t / 0.04)


def latch_click():
    t = t_(0.12)
    a = np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.006)
    b = hp(rng.uniform(-1, 1, len(t)), 2500) * np.exp(-t / 0.01) * 0.6
    c = np.zeros(len(t)); j = int(0.035 * SR)
    c[j:] = (np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.008))[:len(t) - j] * 0.7
    return a + b + c


def thud(weight=1.0):
    t = t_(0.5)
    body = np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t / 0.02)) / SR) * np.exp(-t / (0.08 * weight))
    tap = lp(rng.uniform(-1, 1, len(t)), 2200) * np.exp(-t / 0.015)
    return body * 0.9 + tap * 0.5


def paper():
    t = np.linspace(0, 1, int(SR * 0.35))
    return hp(lp(rng.uniform(-1, 1, len(t)), 6000), 1500) * np.sin(np.pi * t) ** 3 * 0.7


# ------------------------------------------------------------------ music
# warm, confident corporate bed, 100 BPM, C major: C - G/B - Am - F ; builds through the edit
CH = [[60, 64, 67], [59, 62, 67], [57, 60, 64], [53, 57, 60]]
RT = [36, 35, 33, 29]
ARP = [[72, 76, 79, 76], [71, 74, 79, 74], [69, 72, 76, 72], [65, 69, 72, 69]]
V = E["video"]
nb = int(np.ceil(V / BAR))
for b in range(nb):
    t0 = b * BAR; c = b % 4
    if t0 >= V: break
    add(pad(CH[c], BAR, att=0.5, rel=0.8), t0, 0.45)
    add(keys(CH[c][0] - 12, BAR), t0, 0.2)
    add(keys(CH[c][1], BAR * 0.9), t0, 0.1)
    for k in range(8):
        t = t0 + k * BEAT / 2
        if t >= V - 0.05: break
        add(pluck(ARP[c][k % 4], 0.45), t, 0.10 if b < 2 else 0.14, -0.35 if k % 2 else 0.35)
    if b >= 2:                                           # groove enters after the opening
        for q in range(4):
            tq = t0 + q * BEAT
            if tq >= V: break
            if q in (0, 2): add(kick(), tq, 0.42)
            if q in (1, 3): add(snap(), tq, 0.15, 0.1)
            add(shaker(), tq + BEAT / 2, 0.05 + (0.02 if b >= 6 else 0), 0.4)
            if b >= 4: add(keys(RT[c] + 12, BEAT * 0.9), tq, 0.08)
# subtle accents: soft whoosh as each message appears, lift into flash cuts
for k, s in enumerate(E["shots"]):
    a = s["t0"] + (0.35 if k == 0 else 0.12)
    add(sfx.whoosh(0.38), a - 0.05, 0.06, 0.25 if k % 2 else -0.25)
    if s["tr"] == "flash" and k:
        n = int(0.6 * SR); x = np.arange(n) / n
        add(hp(rng.uniform(-1, 1, n), 3000) * x ** 2.5 * 0.2, s["t0"] - 0.6)
# end card: rise, resolving chord, logo shimmer
rs = int(1.2 * SR); x = np.arange(rs) / rs
add(hp(rng.uniform(-1, 1, rs), 2500) * x ** 2.2 * 0.18, V - 1.2)
add(pad([48, 60, 64, 67, 72], E["end"] - 0.4, att=0.25, rel=1.6), V, 0.95)
for k, nt in enumerate([72, 76, 79, 84]):
    add(keys(nt, 2.6), V + 0.1 + k * 0.12, 0.18, -0.3 + 0.2 * k)
tt = t_(2.4)
add(np.sin(2 * np.pi * np.cumsum(36 + 50 * np.exp(-tt / 0.1)) / SR) * np.exp(-tt / 0.8), V, 0.35)
add(sfx.shimmer(), V + 1.0, 0.12)
add(sfx.pop(), V + 1.6, 0.06, -0.2); add(sfx.pop(), V + 1.76, 0.06, 0.2); add(sfx.pop(), V + 2.05, 0.05)

# ------------------------------------------------------------------ bus
ir = rng.normal(0, 1, int(1.6 * SR)) * np.exp(-np.arange(int(1.6 * SR)) / SR / 0.5); ir = lp(ir, 5500); ir /= np.sqrt((ir ** 2).sum())
def conv(x, h):
    nf = 1 << (len(x) + len(h) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]
L, R = L + 0.22 * conv(L, ir), R + 0.22 * conv(R, np.roll(ir, 151))
end = int(DUR * SR); g = np.ones(N)
g[:int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR)); f = int(1.6 * SR)
g[end - f:end] = np.linspace(1, 0, f) ** 1.5; g[end:] = 0
mix = np.stack([L * g, R * g], 1)[:end]; mix /= np.abs(mix).max() + 1e-9
tmp = tempfile.mkdtemp()
w = wave.open(f"{tmp}/raw.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 0.9 * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{tmp}/raw.wav", "-af",
                "acompressor=threshold=-18dB:ratio=2.2:attack=10:release=150:makeup=2,loudnorm=I=-14:TP=-1.0:LRA=9",
                "-ar", str(SR), OUT], check=True)
print("wrote", OUT)
