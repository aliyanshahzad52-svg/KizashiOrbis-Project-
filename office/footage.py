"""Footage stage: reframe (slow push-ins), grade, person matte.

Writes  <out>/plate.mkv  graded 1920x1080 frames (FFV1)
        <out>/matte.mkv  person matte (FFV1 gray) used to put the background text behind people
Frames run to the end of the edit (the last shot continues under the end card).

Grade (natural, bright, clean - no skin smoothing):
  * per-shot exposure: face/person brightness brought to a common target (consistent across clips)
  * partial white balance from the cream wall (removes the yellow cast, keeps warmth)
  * gentle filmic tone curve with lifted shadows, soft highlight shoulder (no clipping on faces)
  * skin: a little extra light on the people (matte), slightly calmer orange saturation
  * clarity + fine sharpening; very light vignette

Usage: python3 footage.py <modnet.onnx> <out_dir> [--stills t1,t2,...]
"""
import json
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

MODNET, OUT = sys.argv[1:3]
STILLS = [float(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[3] == "--stills" else None
E = json.load(open("edit.json"))
W, H, FPS = 1920, 1080, E["fps"]
N = int(round(E["duration"] * FPS))
so = ort.SessionOptions()
so.intra_op_num_threads = 4
mod = ort.InferenceSession(MODNET, so, providers=["CPUExecutionProvider"])


def matte(f):
    x = cv2.resize(f, (896, 512), interpolation=cv2.INTER_AREA)[:, :, ::-1].astype(np.float32) / 255
    m = mod.run(None, {"input": ((x - 0.5) / 0.5).transpose(2, 0, 1)[None]})[0][0, 0]
    return np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_CUBIC), 0, 1)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def reframe(img, z, fx, fy):
    """Zoom z about focus (fx, fy) (kept at the same screen spot), sub-pixel accurate."""
    M = np.float32([[z, 0, fx - z * fx], [0, z, fy - z * fy]])
    # keep the frame covered
    tx = min(0, max(W - z * W, M[0, 2])); ty = min(0, max(H - z * H, M[1, 2]))
    M[0, 2], M[1, 2] = tx, ty
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ grade
def tone_lut():
    # input -> output (sRGB, 0..1): lifted shadows, bright mids, soft shoulder
    pts = np.array([[0, .025], [.08, .09], [.25, .28], [.45, .50], [.65, .70], [.80, .82], [.92, .905], [1.1, .965], [1.4, .985]])
    x = np.linspace(0, 1.4, 1024)
    return np.interp(x, pts[:, 0], pts[:, 1]).astype(np.float32)


TONE = tone_lut()
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - 0.06 * np.clip(((xx - W / 2) / (W * .62)) ** 2 + ((yy - H / 2) / (H * .7)) ** 2, 0, 1.6))[..., None]


def shot_params(s):
    """Exposure gain + white balance per shot, measured on its middle frame."""
    cap = cv2.VideoCapture(s["src"])
    cap.set(cv2.CAP_PROP_POS_MSEC, (s["a"] + (s["b"] - s["a"]) / 2) * 1000)
    ok, f = cap.read()
    m = matte(f)
    f = f.astype(np.float32) / 255
    lum = f @ np.array([0.114, 0.587, 0.299], np.float32)
    # skin pixels on the people (face + hands)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    skin = (m > 0.6) & (hsv[..., 0] > 6) & (hsv[..., 0] < 26) & (hsv[..., 1] > 0.28) & (hsv[..., 1] < 0.75) & (lum > 0.12) & (lum < 0.85)
    face_l = float(np.median(lum[skin])) if skin.sum() > 500 else float(np.median(lum[m > 0.5]))
    gain = float(np.clip(0.46 / max(face_l, 1e-3), 1.0, 1.2))           # overall exposure (walls must keep their texture)
    lift = float(np.clip(0.50 / max(face_l * gain, 1e-3), 1.0, 1.18))    # remaining brightening applied to the people only
    # wall / background: neutralise 55% of its cast (cream stays slightly warm)
    bg = (m < 0.1) & (lum > 0.45) & (lum < 0.95)
    mean = f[bg].mean(0) if bg.sum() > 1000 else f.reshape(-1, 3).mean(0)
    g = mean.mean()
    wb = (g / mean) ** 0.55
    wb = wb / wb[1]
    return dict(gain=gain, lift=lift, wb=wb.astype(np.float32), face=face_l)


def grade(img, m, P):
    f = img.astype(np.float32) / 255
    f = f * P["wb"] * P["gain"]
    m3 = cv2.GaussianBlur(m, (0, 0), 6)[..., None]
    f = f * (1 + (P["lift"] - 1 + 0.04) * m3)                            # light the people (faces) to a common level
    f = TONE[np.clip((f / 1.4 * 1023).astype(np.int32), 0, 1023)]
    hsv = cv2.cvtColor(np.clip(f, 0, 1), cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0], hsv[..., 1]
    skin = np.clip(1 - np.abs(h - 22) / 18, 0, 1) * m3[..., 0]
    hsv[..., 1] = np.clip(s * (1.06 - 0.12 * skin), 0, 1)                # gentle vibrance, calmer skin orange
    f = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    f = f + 0.16 * (f - cv2.GaussianBlur(f, (0, 0), 16))                # clarity
    f = f + 0.38 * (f - cv2.GaussianBlur(f, (0, 0), 1.1))               # fine sharpening (texture kept)
    return np.clip(f * VIGN, 0, 1)


# ------------------------------------------------------------------ main
def shot_at(t):
    for k, s in enumerate(E["shots"]):
        if t < s["t1"] or k == len(E["shots"]) - 1:
            return k, s


params = []
for s in E["shots"]:
    params.append(shot_params(s))
    print(f"shot {s['t0']:5.2f}  face {params[-1]['face']:.2f}  gain {params[-1]['gain']:.2f} lift {params[-1]['lift']:.2f}  wb {np.round(params[-1]['wb'], 3)}", flush=True)

caps = {}


def frame_at(s, t):
    src_t = s["a"] + (t - s["t0"])
    key = s["src"]
    if key not in caps:
        caps[key] = [cv2.VideoCapture(key), -1, None]
    cap = caps[key]
    idx = int(round(src_t * FPS))
    if idx < cap[1] or idx > cap[1] + 48:
        cap[0].set(cv2.CAP_PROP_POS_FRAMES, idx)
        cap[1] = idx - 1
    while cap[1] < idx:
        ok, fr = cap[0].read()
        if not ok:
            break
        cap[2] = fr
        cap[1] += 1
    return cap[2]


def render(i, prev_m):
    t = i / FPS
    k, s = shot_at(t)
    raw = frame_at(s, t)
    span = s["t1"] - s["t0"] + (E["end"] if k == len(E["shots"]) - 1 else 0)
    p = ease((t - s["t0"]) / span) * 0.6 + 0.4 * (t - s["t0"]) / span
    z = s["z"][0] + (s["z"][1] - s["z"][0]) * p
    img = reframe(raw, z, *s["f"])
    m = matte(img)
    if prev_m is not None and prev_m[0] == k:                           # temporal smoothing within a shot
        d = np.abs(m - prev_m[1])
        m = prev_m[1] + (m - prev_m[1]) * np.clip(d * 4, 0.45, 1)
    g = grade(img, m, params[k])
    return (g * 255 + 0.5).astype(np.uint8), m, k


if STILLS:
    import os
    os.makedirs(OUT, exist_ok=True)
    for t in STILLS:
        g, m, k = render(int(round(t * FPS)), None)
        k_, s = shot_at(t)
        raw = frame_at(s, t)
        cv2.imwrite(f"{OUT}/st_{t}.png", np.hstack([cv2.resize(raw, (960, 540)), cv2.resize(g, (960, 540))]))
        cv2.imwrite(f"{OUT}/g_{t}.png", g)
        cv2.imwrite(f"{OUT}/m_{t}.png", (m * 255).astype(np.uint8))
    sys.exit()

enc_p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", "24000/1001", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", f"{OUT}/plate.mkv"], stdin=subprocess.PIPE)
enc_m = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                          "-r", "24000/1001", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", f"{OUT}/matte.mkv"], stdin=subprocess.PIPE)
prev = None
for i in range(N):
    g, m, k = render(i, prev)
    prev = (k, m)
    enc_p.stdin.write(g.tobytes())
    enc_m.stdin.write((m * 255 + 0.5).astype(np.uint8).tobytes())
    if i % 48 == 0:
        print("frame", i, "/", N, flush=True)
for e in (enc_p, enc_m):
    e.stdin.close(); e.wait()
print("done footage", N)
