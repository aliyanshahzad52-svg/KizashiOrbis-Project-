"""Original soundtrack for the OrbisNexa IELTS reel (synthesised, royalty-free).

120 BPM, A minor (Am - F - C - G). Driving four-on-the-floor groove under the four scenes, the groove
drops out for each stripe transition (digital glitch + riser) and slams back on the cut. The end card
switches to a warm pad + pluck arpeggio with sparkle / pop accents on the logo and contact reveals.

Usage: python3 ielts_music.py <out.wav>
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "promo"))
import sfx  # noqa: E402  (shared synthesised sound-design library)

OUT = sys.argv[1]
SR = 48000
DUR = 19.0
N = int(SR * (DUR + 1.5))
L = np.zeros(N)
R = np.zeros(N)
rng = np.random.default_rng(42)
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT

# PROFILE=ref: timings measured frame-by-frame on the reference edit (used by the faithful re-brand)
REF = os.environ.get("PROFILE") == "ref"
TRANS = [2.54, 5.54, 8.51, 12.58] if REF else [2.5, 5.45, 8.45, 12.45]      # stripe transitions start
CUTS = [t + (0.46 if REF else 0.44) for t in TRANS]                          # shot changes under full cover
# end-card events: logo build, light/frame, sparkle ticks, contact lines, socials
EV = (dict(logo=13.25, logo_dt=0.12, shine=14.85, spark=15.5, swoosh=16.25, nums=16.34, addr=16.48, soc=[16.75, 16.95, 17.15])
      if REF else
      dict(logo=13.2, logo_dt=0.13, shine=14.15, spark=14.62, swoosh=15.2, nums=15.25, addr=15.62, soc=[15.95, 16.11]))
END = CUTS[-1]                              # end card from here


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def add(sig, t0, g=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N or i0 < 0:
        return
    sig = sig[:N - i0]
    L[i0:i0 + len(sig)] += sig * g * np.sqrt(0.5 * (1 - pan))
    R[i0:i0 + len(sig)] += sig * g * np.sqrt(0.5 * (1 + pan))


def lp(x, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / hi) ** 4), len(x))


def hp(x, lo):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (lo / np.maximum(f, 1)) ** 4), len(x))


def t_(d):
    return np.arange(int(SR * d)) / SR


# ------------------------------------------------------------------ instruments
def kick():
    t = t_(0.4)
    body = np.sin(2 * np.pi * np.cumsum(46 + 110 * np.exp(-t / 0.035)) / SR) * np.exp(-t / 0.22)
    click = hp(rng.uniform(-1, 1, len(t)), 2500) * np.exp(-t / 0.004) * 0.4
    return np.tanh(1.8 * body) + click


def clap():
    t = t_(0.35)
    n = hp(lp(rng.uniform(-1, 1, len(t)), 6000), 900)
    env = np.zeros(len(t))
    for k, d in enumerate((0, 0.011, 0.022)):
        i = int(d * SR)
        env[i:] += np.exp(-(t[:len(t) - i]) / (0.008 if k < 2 else 0.11))
    return n * env * 0.8


def hat(open_=False):
    t = t_(0.25 if open_ else 0.06)
    return hp(rng.uniform(-1, 1, len(t)), 8000) * np.exp(-t / (0.08 if open_ else 0.014))


def saw(f, t):
    out = np.zeros_like(t)
    for h in range(1, 24):
        if f * h > 16000:
            break
        out += np.sin(2 * np.pi * f * h * t) / h
    return out * 0.6


def bass(note, dur):
    t = t_(dur)
    f = midi(note)
    s = np.sin(2 * np.pi * f * t) + 0.35 * lp(saw(f, t), 700)
    return np.tanh(1.4 * s) * np.minimum(t / 0.006, 1) * np.exp(-t / (dur * 0.9))


def pluck(note, dur=0.45, bright=4200):
    t = t_(dur)
    f = midi(note)
    s = sum(saw(f * 2 ** (d / 1200), t) for d in (-9, 0, 9)) / 3
    s = lp(s * np.exp(-t / 0.09) + 0.25 * s * np.exp(-t / 0.4), bright)
    return s * np.minimum(t / 0.003, 1)


def pad(notes, dur, att=0.5, rel=1.2):
    t = t_(dur + rel)
    out = np.zeros(len(t))
    for n in notes:
        for d in (-11, 0, 12):
            out += saw(midi(n) * 2 ** (d / 1200), t)
    out = lp(out, 2400) / (len(notes) * 3)
    env = np.minimum(t / att, 1) * np.clip(1 - (t - dur) / rel, 0, 1)
    return out * env


def glitch(d=0.44):
    """Digital stutter for the stripe transition: gated, bit-crushed noise + pitch-stepped blips."""
    n = int(SR * d)
    out = np.zeros(n)
    pos = 0
    while pos < n:
        seg = int(SR * rng.uniform(0.018, 0.05))
        kind = rng.integers(3)
        t = np.arange(min(seg, n - pos)) / SR
        if kind == 0:
            s = np.sign(np.sin(2 * np.pi * rng.uniform(300, 1800) * t)) * 0.5
        elif kind == 1:
            s = np.round(rng.uniform(-1, 1, len(t)) * 4) / 4 * 0.6
        else:
            s = np.zeros(len(t))
        out[pos:pos + len(t)] = s * np.exp(-t / 0.03)
        pos += seg
    return hp(lp(out, 9000), 200) * np.linspace(0.5, 1, n)


# ------------------------------------------------------------------ arrangement
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]       # Am F C G (triads)
RT = [33, 29, 36, 31]
ARP = [[69, 72, 76, 72, 81, 76, 72, 76], [65, 69, 72, 69, 77, 72, 69, 72],
       [64, 67, 72, 67, 76, 72, 67, 72], [67, 71, 74, 71, 79, 74, 71, 74]]


def in_gap(t):
    """True while the groove is muted for a transition (stripes cover the screen)."""
    return any(a - 0.02 <= t < c for a, c in zip(TRANS, CUTS))


nbars = int(np.ceil(END / BAR))
for b in range(nbars):
    t0 = b * BAR
    c = b % 4
    if t0 < END:
        add(pad(CH[c], BAR, att=0.25, rel=0.6), t0, 0.55)
    for k in range(16):                                   # 16th grid
        t = t0 + k * BEAT / 4
        if t >= END or in_gap(t):
            continue
        if k % 4 == 0:
            add(kick(), t, 0.95)
        if k in (4, 12):
            add(clap(), t, 0.5, 0.05)
        add(hat(open_=(k % 4 == 2)), t, 0.16 if k % 4 == 2 else (0.10 if k % 2 else 0.07), 0.3 if k % 2 else -0.2)
        if k % 2 == 0:
            add(pluck(ARP[c][(k // 2) % 8], 0.4), t, 0.20, -0.35 if (k // 2) % 2 else 0.35)
        if k % 4 in (0, 3):
            add(bass(RT[c], BEAT * 0.45), t, 0.5)

# transitions: riser into the glitch, stutter, impact + reverse-cymbal feel on the cut
for a, cut in zip(TRANS, CUTS):
    add(sfx.whoosh_in(0.5) * 0.6, a - 0.5, 0.35)
    add(glitch(cut - a), a, 0.32, 0.0)
    add(sfx.impact_soft(), cut, 0.55)
    add(kick(), cut, 0.9)
    add(sfx.whoosh(0.45), cut - 0.05, 0.25, 0.2)

# scene accents: band sweep + text slide
for a, dt in zip([0.0] + CUTS[:3], [0.45, 0.2, 0.2, 0.2] if REF else [0.35, 0.2, 0.2, 0.2]):
    add(sfx.swoosh_up(), a + dt - 0.05, 0.22, -0.3)
    add(sfx.whoosh(0.32), a + dt + 0.12, 0.18, 0.3)
add(sfx.impact_soft(), 0.45 if REF else 0.35, 0.45)                         # opening downbeat with the first band sweep

# ------------------------------------------------------------------ end card (logo + contacts)
ENDC = [[57, 64, 69, 72], [53, 60, 65, 69], [48, 55, 60, 64], [55, 62, 67, 71]]
for k in range(4):
    add(pad(ENDC[k], 1.45, att=0.35, rel=1.6 if k == 3 else 0.5), END + 0.1 + k * 1.45, 1.1)
for k in range(24):                                        # soft pluck arpeggio, 8ths
    t = END + 0.3 + k * BEAT / 2
    if t > DUR - 1.0:
        break
    c = min(int((t - END - 0.1) / 1.45), 3)
    add(pluck(ENDC[c][k % 4] + 12, 0.6, 3000), t, 0.18, -0.4 if k % 2 else 0.4)
for k in range(3 if REF else 5):                           # logo pieces building
    add(sfx.pop(), EV["logo"] + k * EV["logo_dt"], 0.12, -0.5 + k * 0.25)
add(sfx.shimmer(), EV["shine"], 0.3)                       # light sweep / frame drawing round the logo
add(sfx.sparkle(), EV["spark"], 0.25, 0.4)                 # sparkle ticks
add(sfx.swoosh_up(), EV["swoosh"], 0.18)
for k in range(2):
    add(sfx.pop(), EV["nums"] + k * 0.14, 0.16, -0.2 + 0.4 * k)   # phone numbers
add(sfx.pop(), EV["addr"], 0.14)                           # address
for k, t in enumerate(EV["soc"]):
    add(sfx.tick(), t, 0.12, -0.3 + 0.3 * k)               # socials
add(sfx.ding(), DUR - 1.6, 0.18)
tt = t_(2.5)
add(np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-tt / 0.1)) / SR) * np.exp(-tt / 0.8), END, 0.4)

# ------------------------------------------------------------------ mix bus: sidechain, glue reverb, fades
duck = np.ones(N)
for b in range(nbars * 4):
    t = b * BEAT
    if t >= END or in_gap(t):
        continue
    i0 = int(t * SR)
    m = int(0.22 * SR)
    j = min(N, i0 + m)
    duck[i0:j] = np.minimum(duck[i0:j], (1 - 0.35 * np.exp(-np.arange(m) / (0.06 * SR)))[:j - i0])
L *= duck
R *= duck
ir = rng.normal(0, 1, int(1.2 * SR)) * np.exp(-np.arange(int(1.2 * SR)) / SR / 0.35)
ir = lp(ir, 6000)
ir /= np.sqrt((ir ** 2).sum())


def conv(x, h):
    nf = 1 << (len(x) + len(h) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]


L, R = L + 0.18 * conv(L, ir), R + 0.18 * conv(R, np.roll(ir, 173))
end = int(DUR * SR)
g = np.ones(N)
g[:int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
f = int(1.4 * SR)
g[end - f:end] = np.linspace(1, 0, f) ** 1.6
g[end:] = 0
mix = np.stack([L * g, R * g], 1)[:end]
mix /= np.abs(mix).max() + 1e-9

tmp = tempfile.mkdtemp()
w = wave.open(f"{tmp}/raw.wav", "wb")
w.setnchannels(2)
w.setsampwidth(2)
w.setframerate(SR)
w.writeframes((mix * 0.9 * 32767).astype(np.int16).tobytes())
w.close()
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{tmp}/raw.wav", "-af",
                "acompressor=threshold=-16dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-14:TP=-1.0:LRA=8",
                "-ar", str(SR), OUT], check=True)
print("wrote", OUT)
