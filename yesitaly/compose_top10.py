"""Final compositor for the 'Top 10 universities' reel.

footage (logo removed, upscaled) + zoom-blur exit (as in the reference) + transparent overlay
(OrbisNexa logo top-left, its travel to the centre, white closing card with contacts) + music.

Usage: python3 compose_top10.py <reference.mp4> <foot.mkv> <overlay.mkv> <seconds> <out.mp4>
"""
import subprocess
import sys
import tempfile
import wave

import cv2
import numpy as np

REF, FOOT, OVL, SECS, OUT = sys.argv[1:6]
W, H, FPS = 1080, 1920, 30
DUR = float(SECS)
N = int(round(DUR * FPS))
T0 = 8.13                                   # exit transition starts (reference timing)
tmp = tempfile.mkdtemp()

# ------------------------------------------------------------------ audio: original track, extended
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", REF, "-vn", "-ac", "2", "-ar", "48000", f"{tmp}/a.wav"], check=True)
w = wave.open(f"{tmp}/a.wav")
SR = w.getframerate()
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
need = int(DUR * SR)
if need > len(a):
    # continue with the section that best follows on from the last half-second
    L, win = len(a), SR // 2
    tail = a[L - win:, 0]
    best, bc = 0, -1
    for s in range(SR, L - win - (need - L) - 1, SR // 200):
        seg = a[s:s + win, 0]
        c = float(seg @ tail / (np.linalg.norm(seg) * np.linalg.norm(tail) + 1e-9))
        if c > bc:
            best, bc = s, c
    cont = a[best + win: best + win + need - L]
    x = int(0.03 * SR)
    r = np.linspace(0, 1, x)[:, None]
    head = a[L - x:] * (1 - r) + cont[:x] * r
    a = np.concatenate([a[:L - x], head, cont[x:]])
    print(f"music extended from {best / SR:.2f}s (match {bc:.2f})")
a = a[:need]
f = int(1.2 * SR)
a[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.4
wo = wave.open(f"{tmp}/m.wav", "wb"); wo.setnchannels(2); wo.setsampwidth(2); wo.setframerate(SR)
wo.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes()); wo.close()


# ------------------------------------------------------------------ video
def reader(path, ch, fmt):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", fmt, "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * ch)
        if len(b) < W * H * ch:
            return
        yield np.frombuffer(b, np.uint8).reshape(H, W, ch)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def zoom_blur(img, amount, scale):
    """Radial zoom (scale) + zoom blur (amount) around the frame centre, like the reference exit."""
    acc = np.zeros_like(img)
    n = 8
    for k in range(n):
        s = scale * (1 + amount * k / (n - 1))
        M = cv2.getRotationMatrix2D((W / 2, H * 0.55), -2.5 * (scale - 1) * 10, s)
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / n


enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", f"{tmp}/m.wav", "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
fr, ov = reader(FOOT, 3, "bgr24"), reader(OVL, 4, "bgra")
last = None
for i in range(N):
    t = i / FPS
    f = next(fr, None)
    if f is None:
        f = last
    last = f
    img = f.astype(np.float32)
    if t >= T0:
        k = ease((t - T0) / 0.22)
        img = zoom_blur(img, 0.10 * k, 1 + 0.18 * k)
    o = next(ov).astype(np.float32)
    al = o[..., 3:4] / 255
    img = img * (1 - al) + o[..., :3] * al
    enc.stdin.write(np.clip(img + 0.5, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close()
enc.wait()
print("done", OUT)
