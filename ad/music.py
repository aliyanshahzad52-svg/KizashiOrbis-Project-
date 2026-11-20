"""Original background music for the OrbisNexa followers ad (royalty-free, synthesized).

120 BPM, 1 bar = 2.0 s, key D major, progression D - A - Bm - G (I-V-vi-IV).
Arrangement is locked to the video timeline:
  bars 0-2   hook      : globe + flight paths; plucked arpeggio, claps, building riser
  bar  3     brand     : big impact + sub boom on the logo reveal
  bars 4-12  countries : full groove (one country per bar), whoosh into each bar
  bars 13-14 CTA       : groove continues, final chord rings out

Usage: python3 music.py out.wav [duration_seconds]
"""
import sys
import wave

import numpy as np

SR = 48000
OUT = sys.argv[1]
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
BEAT = 0.5
BAR = 2.0
N = int(SR * (DUR + 1.5))
rng = np.random.default_rng(3)

L = np.zeros(N)
R = np.zeros(N)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def add(sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[: N - i0]
    gl, gr = gain * np.sqrt(0.5 * (1 - pan)), gain * np.sqrt(0.5 * (1 + pan))
    L[i0:i0 + len(sig)] += sig * gl
    R[i0:i0 + len(sig)] += sig * gr


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def env(n, a, d, s=0.0, r=0.0, hold=None):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0)
    if hold is None:
        e *= np.exp(-np.maximum(t - a, 0) / max(d, 1e-4)) * (1 - s) + s
    else:
        rel = np.clip((t - hold) / max(r, 1e-4), 0, 1)
        e *= (1 - rel)
    return e


# ---------------------------------------------------------------- instruments
def pad(notes, dur, bright=0.5):
    n = int(SR * (dur + 1.2))
    t = np.arange(n) / SR
    out = np.zeros(n)
    for note in notes:
        f0 = midi(note)
        for det in (-0.09, 0.0, 0.11):
            f = f0 * 2 ** (det / 12)
            ph = rng.uniform(0, 2 * np.pi)
            for h in range(1, 14):
                amp = (1 / h) * np.exp(-h * (1.2 - bright) * 0.45)
                out += amp * np.sin(2 * np.pi * f * h * t + ph * h)
    a = 0.35
    e = np.minimum(t / a, 1) * np.clip(1 - (t - dur) / 1.2, 0, 1)
    return out * e / (len(notes) * 3 * 2.2)


def pluck(note, dur=0.6, bright=0.55):
    """Karplus-Strong plucked string."""
    f = midi(note)
    p = max(2, int(SR / f))
    n = int(SR * dur)
    buf = rng.uniform(-1, 1, p)
    buf = fft_filter(np.tile(buf, 4), hi=3000 + 6000 * bright)[:p]
    out = np.zeros(n)
    for i in range(n):
        v = buf[i % p]
        out[i] = v
        buf[i % p] = 0.5 * (v + buf[(i + 1) % p]) * 0.996
    return out * env(n, 0.002, dur * 0.45)


def bass(note, dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = midi(note)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return np.tanh(1.4 * s) * env(n, 0.006, dur * 0.6, hold=dur * 0.75, r=dur * 0.25)


def kick(gain=1.0):
    n = int(SR * 0.42)
    t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / 0.22)
    s[:120] += rng.uniform(-0.4, 0.4, 120) * np.linspace(1, 0, 120)
    return np.tanh(1.6 * s) * gain


def clap():
    n = int(SR * 0.3)
    noise = fft_filter(rng.uniform(-1, 1, n), lo=900, hi=7000)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for k, dt in enumerate((0.0, 0.011, 0.022)):
        e += np.exp(-np.maximum(t - dt, 0) / (0.012 if k < 2 else 0.09)) * (t >= dt)
    return noise * e * 0.9


def hat(open_=False):
    n = int(SR * (0.22 if open_ else 0.06))
    noise = fft_filter(rng.uniform(-1, 1, n), lo=7000)
    return noise * env(n, 0.001, 0.08 if open_ else 0.018) * 0.55


def impact(big=True):
    n = int(SR * 2.6)
    t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.9 if big else 0.4))
    hit = fft_filter(rng.uniform(-1, 1, n), lo=200, hi=9000) * np.exp(-t / 0.35)
    return np.tanh(1.3 * boom) * 0.9 + hit * (0.35 if big else 0.18)


def whoosh(length=0.45, up=True):
    n = int(SR * length)
    t = np.linspace(0, 1, n)
    noise = rng.uniform(-1, 1, n)
    out = np.zeros(n)
    seg = 1024
    for i in range(0, n, seg):
        k = t[i] if up else 1 - t[i]
        out[i:i + seg] = fft_filter(noise[i:i + seg] if i + seg <= n else noise[i:], lo=300 + 3500 * k, hi=1200 + 9000 * k)[: len(out[i:i + seg])]
    e = np.sin(np.pi * t) ** 2
    return out * e * 0.5


def riser(length):
    n = int(SR * length)
    t = np.linspace(0, 1, n)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * t ** 2) / SR) * 0.15
    noise = whoosh(length, up=True) * 1.2
    return (tone + noise) * t ** 1.6


# ----------------------------------------------------------------- harmony
# chord tones (MIDI) per bar: D, A, Bm, G
CHORDS = [[62, 66, 69, 74], [61, 64, 69, 73], [62, 66, 71, 74], [62, 67, 71, 74]]
ROOTS = [38, 45, 47, 43]
ARP = [[74, 78, 81, 86], [73, 76, 81, 85], [74, 78, 83, 86], [74, 79, 83, 86]]
NBARS = int(np.ceil(DUR / BAR))

pads = np.zeros(N)
drums_l, drums_r = np.zeros(N), np.zeros(N)


def add_mono(buf, sig, t0, gain=1.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[: N - i0]
    buf[i0:i0 + len(sig)] += sig * gain


kick_times = []
for b in range(NBARS):
    t0 = b * BAR
    ch = CHORDS[b % 4]
    full = 4 <= b <= 13
    # pad
    p = pad(ch, BAR + 0.05, bright=0.35 if b < 3 else 0.55)
    add_mono(pads, p, t0, 0.55 if b >= 3 else 0.35)
    # arpeggio plucks (16ths in hook + groove, 8ths in outro)
    step = 0.25 if b <= 13 else 0.5
    k = 0
    tt = 0.0
    while tt < BAR - 1e-6:
        if b == NBARS - 1 and tt >= 1.0:
            break
        note = ARP[b % 4][k % 4] + (12 if (k % 8 == 7 and full) else 0)
        add(pluck(note, 0.55), t0 + tt, 0.16 if b >= 3 else 0.2, pan=(-0.35 if k % 2 else 0.35))
        k += 1
        tt += step
    # bass (offbeat 8ths from bar 2)
    if 3 <= b <= 13:
        for e in range(4):
            add(bass(ROOTS[b % 4], 0.24), t0 + e * BEAT + 0.25, 0.42)
        add(bass(ROOTS[b % 4] , 0.2), t0, 0.3)
    # drums
    for beat in range(4):
        tb = t0 + beat * BEAT
        if (3 <= b <= 13) or (b == 2 and beat >= 2):
            add_mono(drums_l, kick(0.95), tb)
            add_mono(drums_r, kick(0.95), tb)
            kick_times.append(tb)
        if b <= 13 and beat in (1, 3) and not (b == 3 and beat == 1) and b >= 1:
            c = clap()
            add_mono(drums_l, c, tb, 0.5)
            add_mono(drums_r, c, tb + 0.004, 0.5)
        if full:
            h = hat(open_=(beat % 2 == 1))
            add_mono(drums_l, h, tb + 0.25, 0.32)
            add_mono(drums_r, h, tb + 0.25, 0.42)
            for q in (0.125, 0.375):
                hh = hat()
                add_mono(drums_l, hh, tb + q, 0.12)
                add_mono(drums_r, hh, tb + q, 0.16)

# final chord ring-out on the last bar
last = (NBARS - 1) * BAR
add_mono(pads, pad(CHORDS[0] + [50], 2.6, bright=0.6), last + 1.0, 0.6)
add(pluck(86, 1.6), last + 1.0, 0.25, -0.2)
add(pluck(81, 1.6), last + 1.0, 0.22, 0.2)

# sidechain duck for pads / bass from the kick
duck = np.ones(N)
for tk in kick_times:
    i0 = int(tk * SR)
    n = int(0.28 * SR)
    seg = 1 - 0.55 * np.exp(-np.arange(n) / (0.08 * SR))
    j = min(N, i0 + n)
    duck[i0:j] = np.minimum(duck[i0:j], seg[: j - i0])
pads *= duck
L *= duck ** 0.6
R *= duck ** 0.6
L += pads * 0.95 + drums_l
R += pads * 1.0 + drums_r

# FX: impacts, whooshes, risers
add(impact(False), 0.0, 0.55)                       # hook opener
add(riser(2.4), 3.6, 0.55)                          # build into the logo
add(impact(True), 6.0, 0.95)                        # brand reveal
for k in range(9):                                  # into each country
    t = 8.0 + 2 * k
    add(whoosh(0.5), t - 0.38, 0.32, pan=-0.3 if k % 2 else 0.3)
add(riser(1.6), 24.3, 0.45)                         # into the CTA
add(impact(False), 26.0, 0.55)
for k, tw in enumerate((0.35, 1.95, 2.45, 3.0, 3.5)):   # soft swish as each route launches
    add(whoosh(0.55), tw, 0.16, pan=(-0.4 + 0.2 * k))

# simple stereo reverb (exponential noise IR)
ir_n = int(SR * 1.8)
tt = np.arange(ir_n) / SR
irl = rng.normal(0, 1, ir_n) * np.exp(-tt / 0.45)
irr = rng.normal(0, 1, ir_n) * np.exp(-tt / 0.45)
irl, irr = fft_filter(irl, hi=6000), fft_filter(irr, hi=6000)
irl /= np.sqrt((irl ** 2).sum())
irr /= np.sqrt((irr ** 2).sum())


def conv(x, h):
    n = len(x) + len(h)
    nf = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[: len(x)]


wetL, wetR = conv(L, irl), conv(R, irr)
L = L + 0.22 * wetL
R = R + 0.22 * wetR

# master: gentle low-cut, soft clip, fade tail, normalise
L, R = fft_filter(L, lo=28), fft_filter(R, lo=28)
end = int(DUR * SR)
fade = int(1.2 * SR)
g = np.ones(N)
g[end - fade:end] = np.linspace(1, 0, fade) ** 1.5
g[end:] = 0
L, R = L * g, R * g
L, R = L[:end], R[:end]
rms = np.sqrt(np.mean(np.concatenate([L, R]) ** 2))
target = 10 ** (-15.5 / 20)
L, R = L * target / rms, R * target / rms
L, R = np.tanh(L * 1.1) / 1.1, np.tanh(R * 1.1) / 1.1
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = L * min(1, 0.93 / peak), R * min(1, 0.93 / peak)

pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", OUT, f"{DUR:.1f}s", "rms dBFS", round(20 * np.log10(np.sqrt(np.mean(pcm.astype(float) ** 2)) / 32767), 1))
