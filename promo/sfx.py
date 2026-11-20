"""Synthesised sound-design library (royalty-free) for the promo edit.

Every function returns a mono float array at SR. Kinds match edit.json "sfx" entries.
"""
import numpy as np

SR = 48000
rng = np.random.default_rng(21)


def _t(d):
    return np.arange(int(SR * d)) / SR


def _band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def _sweep_noise(d, f0, f1, up=True):
    n = int(SR * d)
    noise = rng.uniform(-1, 1, n)
    out = np.zeros(n)
    seg = 1024
    for i in range(0, n, seg):
        k = i / n
        fc = f0 + (f1 - f0) * (k if up else 1 - k)
        chunk = noise[i:i + seg]
        out[i:i + len(chunk)] = _band(chunk, fc * 0.5, fc * 2.0)
    return out


def _bell(freqs, decays, amps, d=1.2):
    t = _t(d)
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / dc) for f, dc, a in zip(freqs, decays, amps))
    return s * np.minimum(t / 0.002, 1)


def whoosh(d=0.5):
    t = np.linspace(0, 1, int(SR * d))
    return _sweep_noise(d, 400, 4500) * np.sin(np.pi * t) ** 2 * 0.9


def whoosh_in(d=0.5):
    t = np.linspace(0, 1, int(SR * d))
    return _sweep_noise(d, 300, 6000) * t ** 2.2


def swoosh_up(d=0.35):
    t = np.linspace(0, 1, int(SR * d))
    return _sweep_noise(d, 800, 7000) * np.sin(np.pi * t) ** 1.5 * 0.8


def impact_soft():
    t = _t(1.0)
    boom = np.sin(2 * np.pi * np.cumsum(48 + 70 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.35)
    hit = _band(rng.uniform(-1, 1, len(t)), 150, 3000) * np.exp(-t / 0.06)
    return np.tanh(1.4 * boom) * 0.9 + hit * 0.35


def cash_flutter():
    out = np.zeros(int(SR * 0.6))
    pos = 0.0
    for k in range(14):
        n = int(SR * 0.018)
        click = _band(rng.uniform(-1, 1, n), 1800, 7500) * np.exp(-np.arange(n) / (SR * 0.004))
        i = int(pos * SR)
        out[i:i + n] += click * (1 - k / 16)
        pos += rng.uniform(0.022, 0.04)
    return out * 0.9


def shimmer():
    t = _t(1.1)
    s = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (2093, 2637, 3136, 4186, 5274))
    return s / 5 * np.exp(-t / 0.35) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t)) * np.minimum(t / 0.03, 1)


def stamp():
    t = _t(0.5)
    thud = np.sin(2 * np.pi * np.cumsum(70 + 90 * np.exp(-t / 0.02)) / SR) * np.exp(-t / 0.09)
    slap = _band(rng.uniform(-1, 1, len(t)), 300, 4000) * np.exp(-t / 0.025)
    return np.tanh(1.6 * thud) + slap * 0.6


def sparkle():
    out = np.zeros(int(SR * 0.9))
    for k, f in enumerate((3520, 4699, 3951, 5274, 6272, 4435)):
        b = _bell([f, f * 2.01], [0.12, 0.06], [1, 0.3], d=0.4)
        i = int(k * 0.045 * SR)
        out[i:i + len(b)] += b * (0.8 - k * 0.08)
    return out * 0.5


def coin():
    f0 = rng.uniform(2900, 3400)
    return _bell([f0, f0 * 1.52, f0 * 2.13, f0 * 2.76], [0.09, 0.07, 0.05, 0.035], [1, 0.6, 0.4, 0.25], d=0.3) * 0.6


def chaching():
    t = _t(1.4)
    drawer = _band(rng.uniform(-1, 1, int(SR * 0.12)), 600, 5000) * np.exp(-np.arange(int(SR * 0.12)) / (SR * 0.03))
    bell = _bell([2217, 2794, 3322, 4435, 5588], [0.9, 0.7, 0.5, 0.35, 0.25], [1, .7, .5, .35, .2], d=1.4)
    out = np.zeros(len(t))
    out[:len(drawer)] += drawer * 0.9
    i = int(0.09 * SR)
    out[i:] += bell[:len(out) - i] * 0.8
    for k in range(3):                                   # a few coins dropping in the till
        c = coin()
        j = int((0.14 + 0.05 * k) * SR)
        out[j:j + len(c)] += c * 0.5
    return out


def rise():
    t = _t(0.7)
    f = 300 + 900 * (t / t[-1]) ** 2
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / t[-1]) ** 1.5 * 0.35 + whoosh_in(0.7) * 0.4


def pop():
    t = _t(0.09)
    return np.sin(2 * np.pi * np.cumsum(950 * np.exp(-t / 0.03) + 250) / SR) * np.exp(-t / 0.03)


def tick():
    t = _t(0.12)
    return np.sin(2 * np.pi * 1500 * t) * np.exp(-t / 0.018) + _band(rng.uniform(-1, 1, len(t)), 3000, 9000) * np.exp(-t / 0.004) * 0.5


def ding():
    return _bell([1568, 2349, 3136, 4699], [0.8, 0.55, 0.4, 0.25], [1, .5, .3, .15], d=1.3) * 0.8


def scan():
    t = _t(0.8)
    f = 700 + 500 * np.sin(np.pi * t / t[-1])
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * t)) * np.sin(np.pi * t / t[-1]) * 0.25


def page():
    t = np.linspace(0, 1, int(SR * 0.28))
    return _band(rng.uniform(-1, 1, len(t)), 900, 5000) * np.sin(np.pi * t) ** 2 * 0.8


def ping():
    a = _bell([1319, 2637], [0.25, 0.12], [1, 0.3], d=0.5)
    b = _bell([1760, 3520], [0.4, 0.18], [1, 0.3], d=0.7)
    out = np.zeros(int(SR * 0.85))
    out[:len(a)] += a
    out[int(0.12 * SR):int(0.12 * SR) + len(b)] += b
    return out * 0.6


def punch():
    t = _t(0.25)
    air = np.concatenate([whoosh(0.18) * 0.6, np.zeros(len(t) - int(SR * 0.18))])
    thump = np.sin(2 * np.pi * np.cumsum(60 + 80 * np.exp(-t / 0.02)) / SR) * np.exp(-t / 0.08) * 0.6
    return air + thump


KINDS = {k: v for k, v in globals().items() if callable(v) and not k.startswith("_")}


def render(events, duration, stereo=True):
    """events: [kind, time, gain] -> stereo float array."""
    n = int(SR * (duration + 2))
    L, R = np.zeros(n), np.zeros(n)
    for k, (kind, t, g) in enumerate(events):
        s = KINDS[kind]()
        s = s / (np.abs(s).max() + 1e-9)
        i = int(max(t, 0) * SR)
        s = s[: n - i]
        pan = ((k * 37) % 9 - 4) / 18                        # gentle spread across the stereo field
        L[i:i + len(s)] += s * g * np.sqrt(0.5 * (1 - pan))
        R[i:i + len(s)] += s * g * np.sqrt(0.5 * (1 + pan))
    return np.stack([L, R], 1)[: int(SR * duration)]
