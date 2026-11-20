"""Audio for the Italy promo: cleaned voice (edited with the EDL) + original ducked music bed.

  1. voice : source audio cut with the edit list (10 ms crossfades at every jump cut),
             then high-pass, de-noise, de-mud, presence lift, compression, loudness.
  2. music : original royalty-free bed (100 BPM, F - C - Dm - Bb), soft groove under the
             talk, a lift into the end card and a clean final chord.
  3. mix   : music side-chain ducked under the voice, final loudness -14 LUFS (Meta/IG).

Usage: python3 audio.py <source.mov> <out.wav>
"""
import json
import subprocess
import sys
import tempfile
import wave

import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
E = json.load(open("edit.json"))
SR = 48000
DUR = E["duration"]
V = E["video_len"]
tmp = tempfile.mkdtemp()


def run(*a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *a], check=True)


def read(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, w.getnchannels())


def write(path, x):
    x = np.clip(x, -1, 1)
    w = wave.open(path, "wb"); w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype(np.int16).tobytes()); w.close()


# ------------------------------------------------------------------ 1. voice
run("-i", SRC, "-vn", "-ac", "2", "-ar", str(SR), f"{tmp}/src.wav")
src = read(f"{tmp}/src.wav")
xf = int(0.010 * SR)
parts = []
for a, b in E["edl"]:
    seg = src[int(a * SR):int(b * SR)].copy()
    ramp = np.linspace(0, 1, xf)[:, None]
    seg[:xf] *= ramp
    seg[-xf:] *= ramp[::-1]
    parts.append(seg)
voice = np.concatenate(parts)
voice = np.concatenate([voice, np.zeros((int(DUR * SR) - len(voice), 2))]) if len(voice) < DUR * SR else voice[:int(DUR * SR)]
write(f"{tmp}/voice_raw.wav", voice)
run("-i", f"{tmp}/voice_raw.wav", "-af",
    "highpass=f=85,lowpass=f=15000,afftdn=nr=10:nf=-32:tn=1,"
    "equalizer=f=220:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.0:g=2.5,equalizer=f=9000:t=q:w=1:g=1.2,"
    "acompressor=threshold=-22dB:ratio=3:attack=6:release=140:makeup=3,"
    "loudnorm=I=-16:TP=-1.5:LRA=7,aformat=channel_layouts=stereo",
    "-ar", str(SR), f"{tmp}/voice.wav")

# ------------------------------------------------------------------ 2. music
rng = np.random.default_rng(9)
N = int(SR * (DUR + 2))
L = np.zeros(N); R = np.zeros(N)
BPM = 100; BEAT = 60 / BPM; BAR = 4 * BEAT


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def add(sig, t0, g=1.0, pan=0.0):
    i0 = int(t0 * SR)
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


def pad(notes, dur, att=0.6):
    n = int(SR * (dur + 1.5)); t = np.arange(n) / SR; out = np.zeros(n)
    for note in notes:
        for det in (-0.07, 0.0, 0.08):
            f = midi(note) * 2 ** (det / 12); ph = rng.uniform(0, 6.28)
            for h in range(1, 10):
                out += np.sin(2 * np.pi * f * h * t + ph * h) / h * np.exp(-h * 0.35)
    e = np.minimum(t / att, 1) * np.clip(1 - (t - dur) / 1.5, 0, 1)
    return out * e / (len(notes) * 6)


def pluck(note, dur=0.9):
    f = midi(note); p = max(2, int(SR / f)); n = int(SR * dur)
    buf = lp(rng.uniform(-1, 1, p * 4), 4500)[:p]; out = np.zeros(n)
    for i in range(n):
        v = buf[i % p]; out[i] = v; buf[i % p] = 0.5 * (v + buf[(i + 1) % p]) * 0.997
    return out * np.exp(-np.arange(n) / SR / (dur * 0.4))


def kick():
    n = int(SR * 0.35); t = np.arange(n) / SR
    return np.tanh(1.5 * np.sin(2 * np.pi * np.cumsum(44 + 90 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.18))


def hat():
    n = int(SR * 0.05)
    return hp(rng.uniform(-1, 1, n), 7500) * np.exp(-np.arange(n) / SR / 0.012)


def bass(note, dur):
    n = int(SR * dur); t = np.arange(n) / SR; f = midi(note)
    return np.tanh(1.2 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t))) * np.minimum(t / 0.01, 1) * np.exp(-t / (dur * 0.7))


CH = [[65, 69, 72], [64, 67, 72], [65, 69, 74], [65, 70, 74]]          # F, C/E, Dm, Bb
RT = [41, 36, 38, 34]
ARP = [[77, 81, 84, 81], [76, 79, 84, 79], [77, 81, 86, 81], [77, 82, 86, 82]]
nb = int(np.ceil(V / BAR))
kicks = []
for b in range(nb):
    t0 = b * BAR; c = b % 4
    add(pad(CH[c], BAR), t0, 0.9)
    for k in range(8):                                         # 8th-note arpeggio
        add(pluck(ARP[c][k % 4], 0.7), t0 + k * BEAT / 2, 0.10 if b else 0.07, pan=(-0.3 if k % 2 else 0.3))
    if b >= 1:
        for q in range(4):
            add(bass(RT[c], BEAT * 0.9), t0 + q * BEAT, 0.20)
        for q in (0, 2):
            add(kick(), t0 + q * BEAT, 0.55); kicks.append(t0 + q * BEAT)
        for q in range(8):
            add(hat(), t0 + q * BEAT / 2 + (BEAT / 4 if q % 2 else 0), 0.10 if q % 2 else 0.06)
# end card: lift + resolving chord
swell = int(1.2 * SR); n = np.arange(swell) / swell
add(hp(rng.uniform(-1, 1, swell), 2500) * n ** 2 * 0.25, V - 1.2, 1.0)
add(pad([53, 65, 69, 72, 77], 3.6, att=0.25), V, 1.25)
for k, nt in enumerate([77, 81, 84, 89]):
    add(pluck(nt, 2.2), V + 0.25 + k * 0.12, 0.16, pan=(-0.25 + 0.17 * k))
tt = np.arange(int(2.4 * SR)) / SR
add(np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-tt / 0.08)) / SR) * np.exp(-tt / 0.7), V + 0.2, 0.35)

# sidechain from kick, gentle reverb, fades
duck = np.ones(N)
for tk in kicks:
    i0 = int(tk * SR); m = int(0.25 * SR); j = min(N, i0 + m)
    duck[i0:j] = np.minimum(duck[i0:j], (1 - 0.4 * np.exp(-np.arange(m) / (0.07 * SR)))[:j - i0])
L *= duck; R *= duck
ir = rng.normal(0, 1, int(1.6 * SR)) * np.exp(-np.arange(int(1.6 * SR)) / SR / 0.5); ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
def conv(x, h):
    nf = 1 << (len(x) + len(h) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]
L, R = L + 0.25 * conv(L, ir), R + 0.25 * conv(R, np.roll(ir, 211))
end = int(DUR * SR); g = np.ones(N); fi = int(0.6 * SR)
g[:fi] = np.linspace(0, 1, fi); g[end - int(1.3 * SR):end] = np.linspace(1, 0, int(1.3 * SR)) ** 1.4; g[end:] = 0
music = np.stack([L * g, R * g], 1)[:end]
music /= np.abs(music).max() + 1e-9
write(f"{tmp}/music.wav", music * 0.9)

# ------------------------------------------------------------------ 3. mix
# music sits ~-26 LUFS under the talk (ducked further by the voice), rises for the end card
run("-i", f"{tmp}/voice.wav", "-i", f"{tmp}/music.wav", "-filter_complex",
    f"[1:a]loudnorm=I=-27:TP=-3,volume='if(gte(t,{V - 0.3:.2f}),3.2,1)':eval=frame[m];"
    "[0:a]asplit=2[v][sc];"
    "[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=350:makeup=1[md];"
    "[v][md]amix=inputs=2:duration=first:normalize=0,"
    "loudnorm=I=-14:TP=-1.0:LRA=9", "-ar", str(SR), "-ac", "2", OUT)
print("wrote", OUT)
