"""Final compositor: graded plate + background text behind people (matte) + zoom-blur cut accents
+ end-card blur + front layer (logo, flashes, end card) + soundtrack.

Usage: python3 compose.py <plate.mkv> <matte.mkv> <back.mkv> <front.mkv> <music.wav> <out.mp4>
       python3 compose.py --still <g.png> <m.png> <back.png> <front.png> <t> <out.png>
"""
import json
import subprocess
import sys

import cv2
import numpy as np

E = json.load(open("edit.json"))
W, H, FPS = 1920, 1080, E["fps"]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def zoom_blur(f, amount, cx=960, cy=430):
    acc = f.copy(); n = 7
    for k in range(1, n + 1):
        M = cv2.getRotationMatrix2D((cx, cy), 0, 1 + amount * k / n)
        acc += cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / (n + 1)


HOLD = {}                      # shot index -> solid "keep in front" mask for people the matte misses in places


def build_holds(matte_path):
    """For shots with a 'hold' x-range: union of the person matte over the whole shot inside that range,
    filled to its convex hull and grown a little - a solid silhouette for that person (e.g. short dark hair
    against a dark frame edge, where the per-frame matte has holes)."""
    want = {k: s for k, s in enumerate(E["shots"]) if s.get("hold")}
    if not want:
        return
    acc = {k: np.zeros((H, W), np.uint8) for k in want}
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", matte_path, "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        t = i / FPS
        for k, s in want.items():
            if s["t0"] <= t < s["t1"]:
                acc[k] = np.maximum(acc[k], np.frombuffer(b, np.uint8).reshape(H, W))
        i += 1
    for k, s in want.items():
        x0, x1 = s["hold"]
        m = (acc[k] > 110).astype(np.uint8)
        m[:, :x0] = 0; m[:, x1:] = 0
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        if n < 2:
            continue
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        pts = np.column_stack(np.where(lab == big)[::-1]).astype(np.int32)
        hull = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(pts), 255)
        hull = cv2.dilate(hull, np.ones((31, 31), np.uint8))
        HOLD[k] = cv2.GaussianBlur(hull.astype(np.float32) / 255, (0, 0), 6)


def compose(t, plate, m, back, front):
    f = plate.astype(np.float32) / 255
    m = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.4)
    m = np.clip((m - 0.08) / 0.84, 0, 1)
    for k, s in enumerate(E["shots"]):
        if k in HOLD and s["t0"] <= t < s["t1"]:
            m = np.maximum(m, HOLD[k])
    m = m[..., None]
    if back is not None:
        a = back[..., 3:4].astype(np.float32) / 255 * (1 - m)
        f = f * (1 - a) + back[..., :3].astype(np.float32) / 255 * a
    for s in E["shots"][1:]:
        if s["tr"] in ("punch", "flash"):
            d = t - s["t0"]
            if -0.08 <= d < 0.16:
                amt = 0.07 * (1 - abs(d - 0.0) / 0.16)
                f = zoom_blur(f, max(amt, 0.0))
    if t >= E["video"]:
        k = ease((t - E["video"]) / 0.9)
        f = cv2.GaussianBlur(f, (0, 0), 0.5 + 22 * k)
    if front is not None:
        a = front[..., 3:4].astype(np.float32) / 255
        f = f * (1 - a) + front[..., :3].astype(np.float32) / 255 * a
    return np.clip(f * 255 + 0.5, 0, 255).astype(np.uint8)


def rd(p):
    return p.stdout.read


if sys.argv[1] == "--still":
    g, m, bk, fr, t, out = sys.argv[2:8]
    cv2.imwrite(out, compose(float(t), cv2.imread(g), cv2.imread(m, 0), cv2.imread(bk, -1), cv2.imread(fr, -1)))
    sys.exit()

PL, MT, BK, FR, AUD, OUT = sys.argv[1:7]


def pipe(path, fmt):
    return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", fmt, "-"], stdout=subprocess.PIPE)


def get(p, ch):
    b = p.stdout.read(W * H * ch)
    return None if len(b) < W * H * ch else np.frombuffer(b, np.uint8).reshape(H, W, ch) if ch > 1 else np.frombuffer(b, np.uint8).reshape(H, W)


build_holds(MT)
print("hold-out masks:", sorted(HOLD), flush=True)
pp, pm, pb, pf = pipe(PL, "bgr24"), pipe(MT, "gray"), pipe(BK, "bgra"), pipe(FR, "bgra")
N = int(round(E["duration"] * FPS))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "24000/1001", "-i", "-", "-i", AUD, "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for i in range(N):
    pl, mt, bk, fr = get(pp, 3), get(pm, 1), get(pb, 4), get(pf, 4)
    if pl is None:
        break
    enc.stdin.write(compose(i / FPS, pl, mt, bk, fr).tobytes())
    if i % 96 == 0:
        print("compose", i, "/", N, flush=True)
enc.stdin.close(); enc.wait()
print("done", OUT)
