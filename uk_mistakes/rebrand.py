"""Faithful OrbisNexa re-brand of the 'UK arrival mistakes' reference reel (720x1280 @25 -> 1080x1920).

Kept: every frame of the footage, all text, timing and transitions.
Changed:
  * orange graphics (headings, highlight pills, bottom chevrons) -> OrbisNexa blue. Only the flat, highly
    saturated overlay orange is recoloured; footage colours (e.g. the aircraft livery) are left alone.
  * the OEC logo (top-left) is removed with LaMa inpainting; the OrbisNexa logo is placed there with a soft glow.
  * from frame END0 the reference's end card is replaced by the OrbisNexa end card (endcard.mkv).

Usage: python3 rebrand.py <reference.mp4> <lama.onnx> <endcard.mkv|none> <logo.png> <out.mkv> [--stills f1,f2]
"""
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

REF, LAMA, END, LOGO, OUT = sys.argv[1:6]
STILLS = [int(x) for x in sys.argv[7].split(",")] if len(sys.argv) > 7 else None
W, H = 1080, 1920
END0 = 1490
sess = ort.InferenceSession(LAMA, providers=["CPUExecutionProvider"])


def recolor(f, i):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (h >= 3) & (h <= 19) & (s > 140) & (v > 95)
    if i < 116:                                   # opening shot: aircraft livery stays orange
        m[:600] = False
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
    # soft edge: include anti-aliased rim around solid overlay pixels
    rim = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (h <= 24) & (s > 60)
    mm = m | rim
    h[mm] = 108
    s[mm] = np.minimum(s[mm] * 1.04, 255)
    v[mm] = v[mm] * 0.93
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)


# OEC logo: x 50-197, y 52-132 (720 px) -> inpaint in a 512 crop
LB = (44, 48, 204, 136)
lmask = np.zeros((512, 512), np.float32)
lmask[LB[1]:LB[3], LB[0]:LB[2]] = 1


def remove_logo(f):
    crop = f[:512, :512]
    xi = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255
    o = sess.run(None, {"image": xi, "mask": lmask[None, None]})[0][0].transpose(1, 2, 0)
    o = cv2.cvtColor(np.clip(o, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    soft = cv2.GaussianBlur(cv2.dilate(lmask, np.ones((5, 5), np.uint8)), (0, 0), 2)[..., None]
    f = f.copy()
    f[:512, :512] = (o * soft + crop * (1 - soft)).astype(np.uint8)
    return f


logo = cv2.imread(LOGO, cv2.IMREAD_UNCHANGED)
LW = 200
LH = int(round(logo.shape[0] * LW / logo.shape[1]))
PAD = 34
lg = cv2.copyMakeBorder(cv2.resize(logo, (LW, LH), interpolation=cv2.INTER_AREA), PAD, PAD, PAD, PAD,
                        cv2.BORDER_CONSTANT, value=(0, 0, 0, 0)).astype(np.float32)
la = lg[..., 3:4] / 255
halo = np.clip(cv2.GaussianBlur(cv2.dilate(la[..., 0], np.ones((13, 13), np.uint8)), (0, 0), 12)[..., None] * 1.7, 0, 1) * 0.6
LX, LY = 62 - PAD, 52 - PAD


def place_logo(f):
    hh, ww = lg.shape[:2]
    roi = f[LY:LY + hh, LX:LX + ww].astype(np.float32)
    roi = roi * (1 - halo) + 255 * halo
    roi = roi * (1 - la) + lg[..., :3] * la
    f[LY:LY + hh, LX:LX + ww] = np.clip(roi + .5, 0, 255).astype(np.uint8)
    return f


def up(f):
    g = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    g = g + 0.3 * (g - cv2.GaussianBlur(g, (0, 0), 1.1))
    return np.clip(g + .5, 0, 255).astype(np.uint8)


def process(i, f):
    return place_logo(up(remove_logo(recolor(f, i))))


cap = cv2.VideoCapture(REF)
if STILLS:
    for i in STILLS:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read()
        cv2.imwrite(f"{OUT}_{i}.png", process(i, f))
    sys.exit()

enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "25", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", OUT], stdin=subprocess.PIPE)
for i in range(END0):
    ok, f = cap.read()
    if not ok:
        break
    enc.stdin.write(process(i, f).tobytes())
    if i % 100 == 0:
        print("frame", i, "/", END0, flush=True)
if END != "none":
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", END, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        enc.stdin.write(b)
enc.stdin.close(); enc.wait()
print("done")
