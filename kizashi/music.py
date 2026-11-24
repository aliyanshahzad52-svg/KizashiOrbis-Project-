"""Original soundtrack + sound design for the KizashiOrbis 3D brand promo (fully synthesised, no samples).

Dark, premium electronic bed in E minor at ~109 BPM (two bars per scene, so every scene change lands on a
downbeat): sub pulse, wide pads, glassy arpeggio, tight drums from scene 2, risers into each fly-through,
and sound effects placed on the exact animation times of kizashi.html.

Usage: python3 music.py <out.wav>
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "promo"))
import sfx  # noqa: E402  (generic synthesised whooshes / pops / shimmers)

OUT = sys.argv[1]
SR = 48000
DUR = 27.5
N = int(SR * (DUR + 2))
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(11)
BAR = 2.2                    # 4 beats
BEAT = BAR / 4
G0 = 4.3 - 2 * BAR           # grid origin so scene starts (4.3, 8.7, ...) are downbeats
SCENES = [4.3, 8.7, 13.1, 17.5, 21.7]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def t_(d): return np.arange(int(SR * d)) / SR


def add(sig, t0, g=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if i0 < 0: sig = sig[-i0:]; i0 = 0
    if i0 >= N: return
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
    for h in range(1, 24):
        if f * h > 15000: break
        out += np.sin(2 * np.pi * f * h * t) / h
    return out * 0.6


def pad(notes, dur, att=0.8, rel=1.5, cut=1500):
    t = t_(dur + rel); out = np.zeros(len(t))
    for n in notes:
        for d in (-10, 0, 11):
            out += saw(midi(n) * 2 ** (d / 1200), t)
    out = lp(out, cut) / (len(notes) * 3)
    return out * np.minimum(t / att, 1) * np.clip(1 - (t - dur) / rel, 0, 1)


def glass(note, dur=0.7):
    t = t_(dur); f = midi(note)
    s = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / 0.08))
    return s * np.exp(-t / 0.22) * np.minimum(t / 0.002, 1)


def sub(note, dur):
    t = t_(dur); f = midi(note)
    s = np.tanh(1.6 * np.sin(2 * np.pi * f * t)) * 0.8 + 0.3 * np.sin(4 * np.pi * f * t)
    return lp(s, 400) * np.minimum(t / 0.01, 1) * np.exp(-t / (dur * 0.8))


def kick():
    t = t_(0.45)
    return np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(42 + 110 * np.exp(-t / 0.025)) / SR) * np.exp(-t / 0.22))


def clap():
    t = t_(0.3); n = rng.uniform(-1, 1, len(t))
    env = sum(np.exp(-np.maximum(t - d, 0) / 0.012) * (t >= d) for d in (0, 0.011, 0.022)) + 0.6 * np.exp(-t / 0.09)
    return hp(lp(n, 6000), 900) * env * 0.5


def hat(open_=False):
    t = t_(0.25 if open_ else 0.06)
    return hp(rng.uniform(-1, 1, len(t)), 7500) * np.exp(-t / (0.08 if open_ else 0.015))


def riser(d):
    n = int(SR * d); x = np.arange(n) / n
    noise = hp(rng.uniform(-1, 1, n), 1800) * x ** 2.5
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * x ** 2) / SR) * x ** 3 * 0.25
    return noise * 0.6 + tone


def boom():
    t = t_(3.0)
    body = np.sin(2 * np.pi * np.cumsum(30 + 70 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 1.1)
    air = lp(rng.uniform(-1, 1, len(t)), 1500) * np.exp(-t / 0.25) * 0.4
    return np.tanh(1.5 * body) + air


def ping(note):
    t = t_(0.9); f = midi(note)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t / 0.1)) * np.exp(-t / 0.3) * np.minimum(t / 0.002, 1)


# ------------------------------------------------------------------ harmony (E minor: Em - C - G - D)
CH = [[52, 59, 64, 67], [48, 55, 60, 64], [55, 59, 62, 67], [50, 57, 62, 66]]
RT = [28, 24, 31, 26]
ARP = [[76, 79, 83, 79, 88, 83], [72, 76, 79, 76, 84, 79], [74, 79, 83, 79, 86, 83], [74, 78, 81, 78, 86, 81]]
nb = int(np.ceil((DUR - G0) / BAR))
for b in range(nb):
    t0 = G0 + b * BAR; c = b % 4
    if t0 > DUR: break
    intro = t0 < 4.3 - 1e-6
    if t0 + BAR > -0.5:
        add(pad(CH[c], BAR, att=0.9 if intro else 0.4, rel=1.0, cut=900 if intro else 1700), t0, 0.42)
    if t0 >= 21.7 - 1e-6: continue                         # finale has its own chord
    if not intro:
        for q in range(4):
            tq = t0 + q * BEAT
            add(sub(RT[c] + 12, BEAT * 0.9), tq, 0.38)
            add(kick(), tq, 0.55 if q in (0, 2) else 0.35)
            if q in (1, 3): add(clap(), tq, 0.22, 0.05)
            add(hat(), tq + BEAT / 2, 0.08, 0.35)
            if q == 3: add(hat(True), tq + BEAT / 2, 0.06, -0.3)
            for s in range(2):                                 # 16th glass arp
                k = q * 2 + s
                add(glass(ARP[c][k % 6]), tq + s * BEAT / 2, 0.075, 0.45 if k % 2 else -0.45)
    else:
        for k in range(4):
            tq = t0 + k * BEAT
            if tq > 0.2: add(glass(ARP[c][k * 2 % 6], 1.2), tq, 0.05, -0.4 if k % 2 else 0.4)

# risers + whoosh into every fly-through
for s in SCENES:
    add(riser(1.1), s - 1.1, 0.16)
    add(sfx.whoosh(0.8), s - 0.35, 0.3)
    add(kick(), s, 0.25); add(sub(28, 1.2), s, 0.25)

# ------------------------------------------------------------------ scene 1: intro
add(riser(2.0), 0.0, 0.08)
add(sfx.shimmer(), 0.5, 0.18)                             # core appears
add(boom(), 0.55, 0.25)
add(sfx.whoosh_in(0.6), 1.3, 0.14, -0.3)
add(sfx.shimmer(), 1.75, 0.26, 0.2)                       # logo forms
add(sfx.sparkle(), 2.3, 0.18, 0.3)                        # light sweep
# ------------------------------------------------------------------ scene 2
for i, tt in enumerate([4.4, 4.6, 4.8]): add(sfx.swoosh_up(), tt, 0.12, [-0.3, -0.5, 0.5][i])
for i in range(7): add(sfx.tick(), 4.3 + 0.8 + i * 0.2, 0.05, -0.4)
# ------------------------------------------------------------------ scene 3 (lead notifications)
for i, nt in enumerate([81, 83, 86, 88]):
    tt = 8.7 + 1.0 + i * 0.55
    add(sfx.swoosh_up(), tt - 0.05, 0.1, -0.4 if i % 2 == 0 else 0.4)
    add(ping(nt), tt + 0.18, 0.16, -0.3 if i % 2 == 0 else 0.3)
add(sfx.pop(), 8.7 + 1.9, 0.08)                           # "Learn more" button lights
# ------------------------------------------------------------------ scene 4 (assembly)
for i in range(4): add(sfx.whoosh_in(0.35), 13.1 + 0.6 + i * 0.18, 0.1, -0.5 + i * 0.33)
for i in range(5): add(sfx.pop(), 13.1 + 1.45 + i * 0.12, 0.08, -0.6 + i * 0.3)
add(sfx.page(), 13.6, 0.12)
# ------------------------------------------------------------------ scene 5 (growth)
add(sfx.pop(), 17.65, 0.12)                               # seed appears
add(sfx.swoosh_up(), 18.45, 0.12)                         # seed splits
for i, nt in enumerate([64, 67, 71, 74, 76, 79, 83]): add(glass(nt, 1.0), 17.5 + 1.25 + i * 0.2, 0.14, -0.5 + i * 0.16)
add(sfx.rise(), 19.1, 0.2)                                # growth line climbs
add(sfx.sparkle(), 20.8, 0.14, 0.4)                       # arrow peaks
# ------------------------------------------------------------------ scene 6 (final reveal)
add(pad([40, 52, 59, 64, 67, 71], 5.8, att=0.25, rel=1.6, cut=2200), 22.35, 0.75)
add(sub(28, 3.0), 22.4, 0.45)
add(boom(), 22.4, 0.55)
add(sfx.impact_soft(), 22.4, 0.4)
add(sfx.shimmer(), 22.5, 0.3)
add(sfx.sparkle(), 23.05, 0.2, 0.3)                       # light sweep
for k, nt in enumerate([76, 79, 83, 88]): add(glass(nt, 1.6), 23.6 + k * 0.09, 0.12, -0.3 + 0.2 * k)   # tagline
add(sfx.whoosh_in(0.4), 24.4, 0.12)
add(sfx.pop(), 24.85, 0.1)                                # website
for i in range(8): add(sfx.tick(), 25.4 + i * 0.1, 0.04, -0.5 + i * 0.14)
add(ping(88), 26.4, 0.08)

# ------------------------------------------------------------------ bus
ir = rng.normal(0, 1, int(2.2 * SR)) * np.exp(-np.arange(int(2.2 * SR)) / SR / 0.7); ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
def conv(x, h):
    nf = 1 << (len(x) + len(h) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]
L, R = L + 0.25 * conv(L, ir), R + 0.25 * conv(R, np.roll(ir, 173))
end = int(DUR * SR); g = np.ones(N)
g[:int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR)); f = int(1.4 * SR)
g[end - f:end] = np.linspace(1, 0, f) ** 1.6; g[end:] = 0
mix = np.stack([L * g, R * g], 1)[:end]; mix /= np.abs(mix).max() + 1e-9
tmp = tempfile.mkdtemp()
w = wave.open(f"{tmp}/raw.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 0.9 * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{tmp}/raw.wav", "-af",
                "acompressor=threshold=-18dB:ratio=2.5:attack=8:release=140:makeup=2,loudnorm=I=-14:TP=-1.0:LRA=9",
                "-ar", str(SR), OUT], check=True)
print("wrote", OUT)
