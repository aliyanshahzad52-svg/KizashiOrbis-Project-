"""Render the graded, re-framed base video (no overlays) for the Italy promo.

Reads edit.json (EDL + shot plan) and the source clip, then for every output frame:
  * picks the source frame through the edit list (jump cuts),
  * frames the shot: zoom about the speaker's face with cinematic punch-ins / eased moves,
  * resamples once from the 512x910 source to 1080x1920 (Lanczos) + gentle sharpening,
  * applies the colour grade (cooler, cleaner whites, soft S-curve, vignette).
During the end card the last frame is held and softly blurred behind the brand screen.

Usage: python3 render_base.py <source.mov> <out.mp4> [still_time]
"""
import json
import subprocess
import sys

import cv2
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
STILL = float(sys.argv[3]) if len(sys.argv) > 3 else None
E = json.load(open("edit.json"))
W, H, FPS = 1080, 1920, 30
SW, SH = 512, 910
BASE = W / SW                                   # 2.109: source -> full-frame scale
FACE = (225 * BASE, 400 * BASE)                 # face centre in full-frame coords
EDL = E["edl"]


def out_to_src(t):
    acc = 0.0
    for a, b in EDL:
        if t < acc + (b - a):
            return a + (t - acc)
        acc += b - a
    return EDL[-1][1]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def zoom_at(t):
    shots = E["shots"]
    for k, s in enumerate(shots):
        if s["t0"] <= t < s["t1"] or k == len(shots) - 1:
            prog = (t - s["t0"]) / max(s["t1"] - s["t0"], 1e-3)
            z = s["zoom"] * (1 + 0.035 * min(prog, 1))          # slow push within every shot
            if s["trans"] == "ease" and k > 0:
                prev = shots[k - 1]["zoom"] * 1.035
                z = prev + (z - prev) * ease((t - s["t0"]) / 0.7)
            return z
    return 1.0


def framing(z):
    """Affine matrix (source -> output) for zoom z, keeping the face well placed."""
    k = ease((z - 1.0) / 0.22)
    sx = FACE[0] + (540 - FACE[0]) * k                       # centre the face as we push in
    sy = FACE[1] + (806 - FACE[1]) * k                       # eyes on the upper third
    x0 = min(max(FACE[0] - sx / z, 0), W - W / z)
    y0 = min(max(FACE[1] - sy / z, 0), H - H / z)
    a = BASE * z
    return np.float32([[a, 0, -x0 * z], [0, a, -y0 * z]])


# ------------------------------------------------------------------ colour grade
def build_luts():
    x = np.arange(256) / 255.0
    curve = x + 0.10 * np.sin(2 * np.pi * x) * (1 - x) * 0.9      # gentle S: deeper shadows, brighter mids
    curve = np.clip(curve * 0.985 + 0.012, 0, 1)                    # soft black lift / highlight roll-off
    wb = {0: 1.035, 1: 1.0, 2: 0.965}                               # BGR: cool the warm wall slightly
    return [np.clip(np.clip(x * wb[c], 0, 1) ** 0.98 * 0 + curve[np.clip((x * wb[c] * 255).astype(int), 0, 255)], 0, 1) * 255
            for c in range(3)]


LUTS = [l.astype(np.uint8) for l in build_luts()]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - 0.16 * np.clip(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2, 0, 1.4))[..., None]
rng = np.random.default_rng(5)
GRAIN = [rng.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(6)]


def grade(img, i):
    img = cv2.merge([cv2.LUT(img[..., c], LUTS[c]) for c in range(3)])
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s = hsv[..., 0], hsv[..., 1]
    skin = np.clip(1 - np.abs(h - 12) / 14, 0, 1)                  # protect skin tones
    hsv[..., 1] = np.clip(s * (1.08 - 0.06 * skin), 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    blur = cv2.GaussianBlur(img, (0, 0), 1.6)
    img = img + 0.55 * (img - blur)                                  # restore crispness after upscale
    img = img * VIGN + GRAIN[i % len(GRAIN)]
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ frames
cap = cv2.VideoCapture(SRC)
src_frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    src_frames.append(f)
NSRC = len(src_frames)


def frame_at(t, i):
    st = out_to_src(min(t, E["video_len"] - 1 / FPS))
    f = src_frames[min(int(round(st * FPS)), NSRC - 1)]
    z = zoom_at(min(t, E["video_len"] - 1 / FPS))
    img = cv2.warpAffine(f, framing(z), (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    img = grade(img, i)
    if t >= E["video_len"]:                                          # behind the end card
        k = ease((t - E["video_len"]) / 0.8)
        img = cv2.GaussianBlur(img, (0, 0), 1 + 24 * k)
    return img


if STILL is not None:
    cv2.imwrite(OUT, frame_at(STILL, 0))
    sys.exit()

N = int(round(E["duration"] * FPS))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "12", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
hold = None
for i in range(N):
    t = i / FPS
    img = frame_at(t, i)
    enc.stdin.write(img.tobytes())
    if i % 150 == 0:
        print("base frame", i, "/", N, flush=True)
enc.stdin.close()
enc.wait()
print("done", OUT)
