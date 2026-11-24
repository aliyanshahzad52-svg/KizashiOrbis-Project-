"""Original soundtrack for the unbranded serum commercial (fully synthesised, no samples, no voice).

Slow, airy luxury ambient in D major (Dmaj9 - Bm11 - Gmaj9 - Aadd9 feel): warm pads, soft felt-piano notes,
a low swell, plus sound design on the picture: water drops and ripples, the glass bottle touching stone,
the dropper lifting, the serum drop, floating droplets, and a soft resolving chord on the hero shot.

Usage: python3 music.py <out.wav> [duration]
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
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 16.77
SR = 48000
N = int(SR * (DUR + 3))
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(23)


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


def pad(notes, dur, att=1.6, rel=2.5, cut=1400):
    t = t_(dur + rel); out = np.zeros(len(t))
    for n in notes:
        f = midi(n)
        for d in (-7, 0, 6):
            ff = f * 2 ** (d / 1200)
            out += np.sin(2 * np.pi * ff * t) + 0.35 * np.sin(4 * np.pi * ff * t) + 0.12 * np.sin(6 * np.pi * ff * t)
    out = filt(out, hi=cut) / (len(notes) * 3)
    out *= 1 + 0.08 * np.sin(2 * np.pi * 0.25 * t)
    return out * np.minimum(t / att, 1) ** 2 * np.clip(1 - (t - dur) / rel, 0, 1)


def felt(note, dur=3.0, vel=1.0):
    """Soft felt-piano: few partials, slightly inharmonic, fast hammer + long decay, muffled."""
    t = t_(dur); f = midi(note); s = np.zeros(len(t))
    for k, a in enumerate([1, 0.45, 0.22, 0.12, 0.06], 1):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        s += a * np.sin(2 * np.pi * fk * t) * np.exp(-t * (0.9 + 0.7 * k))
    thump = filt(rng.uniform(-1, 1, len(t)), lo=80, hi=600) * np.exp(-t / 0.012) * 0.15
    return filt(s + thump, hi=2600) * np.minimum(t / 0.004, 1) * vel


def drop_plip(pitch=1.0):
    """Water drop: quick rising sine 'plip' with a tiny splash."""
    t = t_(0.25)
    f = (700 + 1500 * (1 - np.exp(-t / 0.012))) * pitch
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045)
    spl = filt(rng.uniform(-1, 1, len(t)), lo=2500, hi=9000) * np.exp(-t / 0.02) * 0.25
    return tone + spl


def glass_tap(f0=2400):
    t = t_(1.6)
    s = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t / d) for r, a, d in [(1, 1, 0.5), (2.71, 0.5, 0.25), (5.2, 0.25, 0.12), (0.5, 0.3, 0.4)])
    knock = filt(rng.uniform(-1, 1, len(t)), lo=200, hi=1800) * np.exp(-t / 0.01) * 0.6
    return s * 0.6 + knock


def ripple_wash(d=1.6):
    t = t_(d); x = t / d
    return filt(rng.uniform(-1, 1, len(t)), lo=300, hi=2400) * np.sin(np.pi * x) ** 2 * (1 - x) * 0.6


def air(d, lo=1500, hi=7000):
    t = t_(d); x = t / d
    return filt(rng.uniform(-1, 1, len(t)), lo=lo, hi=hi) * np.sin(np.pi * x) ** 1.5


def squeak(d=0.35):
    t = t_(d); x = t / d
    f = 900 + 300 * np.sin(np.pi * x)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x) ** 2 * 0.25 + filt(rng.uniform(-1, 1, len(t)), lo=1500, hi=5000) * np.sin(np.pi * x) * 0.15


# ------------------------------------------------------------------ music bed (no beat, breathing tempo)
CH = [(0.0, [50, 57, 62, 64, 66, 69]),        # D maj9
      (4.0, [47, 54, 62, 64, 66, 69]),        # Bm11
      (7.6, [43, 50, 59, 62, 66, 69]),        # G maj9 (lift into the macro)
      (11.2, [45, 52, 61, 64, 66, 71]),       # A add9 / sus
      (13.6, [38, 50, 57, 62, 66, 69, 74])]   # D - home, hero shot
for i, (t0, ch) in enumerate(CH):
    t1 = CH[i + 1][0] if i + 1 < len(CH) else DUR + 0.5
    add(pad(ch, t1 - t0 + 0.6, att=1.8 if i == 0 else 0.9, rel=2.2, cut=1100 if i == 0 else 1600), t0 - (0 if i == 0 else 0.5), 0.5)
    add(pad([ch[0] - 12], t1 - t0 + 0.6, att=1.2, rel=2.0, cut=300), t0 - (0 if i == 0 else 0.5), 0.55)
# felt piano melody - sparse, placed between events
MEL = [(1.2, 74, .7), (2.0, 76, .55), (2.8, 78, .6), (4.0, 81, .7), (5.2, 78, .5), (6.5, 74, .65),
       (7.6, 83, .7), (8.4, 81, .5), (9.2, 78, .55), (10.0, 76, .6), (11.2, 81, .6), (12.0, 85, .5),
       (12.8, 83, .5), (13.6, 86, .75), (13.62, 74, .45), (14.4, 81, .45), (15.2, 78, .4)]
for t0, n, v in MEL:
    add(felt(n, 3.2, v), t0, 0.26, 0.25 * np.sin(n))
    add(felt(n - 12, 3.2, v * 0.5), t0 + 0.01, 0.12, -0.2)

# ------------------------------------------------------------------ sound design (picture times)
add(air(3.0, 200, 1200), 0.0, 0.35)                                  # opening low air swell
t = t_(3.0); add(np.sin(2 * np.pi * 36.7 * t) * np.sin(np.pi * t / 3.0) ** 2, 0.0, 0.35)   # sub bloom
add(sfx.shimmer(), 0.65, 0.12, -0.4); add(sfx.shimmer(), 1.05, 0.12, 0.4)                 # rim lights catch the glass
for tt, p, pan in [(1.0, 1.0, -0.5), (2.67, 1.15, 0.6), (5.0, 0.9, -0.3), (5.83, 1.25, 0.6)]:
    add(drop_plip(p), tt, 0.32, pan); add(ripple_wash(1.4), tt + 0.03, 0.12, pan)
add(air(1.8, 600, 3000), 2.2, 0.12)                                  # bottle descending
add(glass_tap(2100), 3.95, 0.22); add(ripple_wash(2.2), 3.97, 0.26)   # touches the wet stone
# B macro: dropper lifts, drop forms, falls
add(squeak(0.5), 6.9, 0.35); add(air(1.4, 800, 4000), 6.95, 0.12)
add(glass_tap(3300), 8.45, 0.06, 0.2)
add(drop_plip(1.35), 9.72, 0.4, 0.05)
# C floating
add(air(2.6, 1200, 6000), 10.0, 0.16)
for k in range(6): add(drop_plip(1.6 + 0.15 * k) * 0.5, 10.3 + k * 0.42, 0.12, -0.6 + 0.24 * k)
add(sfx.sparkle(), 11.6, 0.08, 0.3)
# D hero
add(sfx.whoosh_in(0.6), 12.7, 0.1)
add(sfx.shimmer(), 13.6, 0.18)
add(glass_tap(2600), 13.62, 0.06)

# ------------------------------------------------------------------ bus: long hall reverb + fade
ir_len = int(3.2 * SR)
ir = rng.normal(0, 1, ir_len) * np.exp(-np.arange(ir_len) / SR / 0.95); ir = filt(ir, hi=6000); ir /= np.sqrt((ir ** 2).sum())
def conv(x, h):
    nf = 1 << (len(x) + len(h) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]
L, R = L + 0.45 * conv(L, ir), R + 0.45 * conv(R, np.roll(ir, 211))
end = int(DUR * SR); g = np.ones(N)
g[:int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR)); f = int(1.8 * SR)
g[end - f:end] = np.linspace(1, 0, f) ** 1.5; g[end:] = 0
mix = np.stack([L * g, R * g], 1)[:end]; mix /= np.abs(mix).max() + 1e-9
tmp = tempfile.mkdtemp()
w = wave.open(f"{tmp}/raw.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 0.9 * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{tmp}/raw.wav", "-af",
                "acompressor=threshold=-20dB:ratio=2:attack=15:release=200:makeup=2,loudnorm=I=-15:TP=-1.0:LRA=10",
                "-ar", str(SR), OUT], check=True)
print("wrote", OUT)
