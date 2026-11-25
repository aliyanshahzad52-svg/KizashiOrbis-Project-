"""Faithful OrbisNexa re-brand of the 'Why Germany' reference reel (720x1280 -> 1080x1920, 30 fps).

Kept from the reference: every frame of footage, all text, timing, wipes and transitions.
Changed:
  * yellow graphics (headline words, section headings, wipe bands) -> OrbisNexa sky blue
    red graphics (title line, wipe bands)                         -> OrbisNexa royal blue
    The German flag inside the footage is left untouched (recolour is limited to the text areas and to
    full-width wipe bands).
  * the 'admitdot' logo (bottom centre) is removed with LaMa inpainting and the OrbisNexa logo is placed
    in the same spot (with a soft white halo so the navy wordmark reads on dark footage).
  * from 25.37 s the reference's white end card is replaced by the OrbisNexa end card (endcard.mkv),
    revealed through the reference's own white wipe.

Usage: python3 rebrand.py <reference.mp4> <lama.onnx> <endcard.mkv> <logo.png> <out.mkv> [--stills f1,f2,..]
"""
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

REF, LAMA, END, LOGO, OUT = sys.argv[1:6]
STILLS = [int(x) for x in sys.argv[7].split(",")] if len(sys.argv) > 7 else None
W, H, K = 1080, 1920, 1.5
END0 = 761                                       # first frame of the white wipe into the end card
sess = ort.InferenceSession(LAMA, providers=["CPUExecutionProvider"])

SKY_H, ROYAL_H = 104, 109                         # OpenCV hue (0-180)

# text areas (720-px reference coordinates): (t0, t1, x0, y0, x1, y1)
TEXT_ZONES = [
    (0.3, 3.4, 330, 580, 720, 740),               # "WHY GERMANY?"
    (3.0, 9.6, 0, 180, 720, 450),                 # "BENEFITS OF STUDYING IN GERMANY"
    (6.0, 25.4, 0, 430, 720, 760),                # section headings
]
LOGO_BOX = (232, 1082, 494, 1158)                 # admitdot logo incl. (R) mark


def remap(f, mask, red_too):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    yel = (h >= 15) & (h <= 38) & (s > 90) & (v > 150) & mask
    red = ((h <= 8) | (h >= 168)) & (s > 110) & (v > 90) & mask & red_too
    h[yel] = SKY_H; s[yel] *= 0.82
    h[red] = ROYAL_H; v[red] *= 0.92
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)


def wipe_rows(f):
    """Rows that are a full-width flat band of wipe colour (yellow / red)."""
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    yel = (h >= 15) & (h <= 38) & (s > 150) & (v > 180)
    red = ((h <= 8) | (h >= 168)) & (s > 160) & (v > 120)
    ry = yel.mean(1) > 0.9
    rr = red.mean(1) > 0.9
    return ry, rr


def process(i, f):
    t = i / 30
    m = np.zeros(f.shape[:2], bool)
    red_ok = np.zeros(f.shape[:2], bool)
    for t0, t1, x0, y0, x1, y1 in TEXT_ZONES:
        if t0 <= t < t1:
            m[y0:y1, x0:x1] = True
            if y0 == 180:
                red_ok[y0:y1, x0:x1] = True        # red title line
    ry, rr = wipe_rows(f)
    if ry.any() or rr.any():
        band = np.zeros_like(m); band[ry | rr] = True
        band = cv2.dilate(band.astype(np.uint8), np.ones((5, 1), np.uint8)).astype(bool)
        m |= band; red_ok |= band
    out = remap(f, m, red_ok) if m.any() else f
    return out


# ------------------------------------------------------------------ logo removal + new logo
x0, y0, x1, y1 = LOGO_BOX
CX, CY = 104, 768                                 # 512x512 crop origin (covers the logo)
lmask = np.zeros((512, 512), np.uint8)
lmask[y0 - CY - 4:y1 - CY + 4, x0 - CX - 4:x1 - CX + 4] = 1


def remove_logo(f):
    crop = f[CY:CY + 512, CX:CX + 512]
    xi = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255
    o = sess.run(None, {"image": xi, "mask": lmask.astype(np.float32)[None, None]})[0][0].transpose(1, 2, 0)
    o = cv2.cvtColor(np.clip(o, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    soft = cv2.GaussianBlur(cv2.dilate(lmask, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)[..., None]
    f = f.copy()
    f[CY:CY + 512, CX:CX + 512] = (o * soft + crop * (1 - soft)).astype(np.uint8)
    return f


logo = cv2.imread(LOGO, cv2.IMREAD_UNCHANGED)
LW = 300                                          # output px (reference logo is 262 px wide at 1080)
LH = int(round(logo.shape[0] * LW / logo.shape[1]))
lg = cv2.resize(logo, (LW, LH), interpolation=cv2.INTER_AREA)
PAD = 30
lg = cv2.copyMakeBorder(lg, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0)).astype(np.float32)
la = lg[..., 3:4] / 255
halo = cv2.GaussianBlur(cv2.dilate(la[..., 0], np.ones((11, 11), np.uint8)), (0, 0), 10)[..., None]
halo = np.clip(halo * 1.6, 0, 1) * 0.62
LX = 540 - LW // 2 - PAD
LY = int(1158 * K) - LH + 6 - PAD                 # bottom aligned with the reference logo's baseline


def place_logo(f):
    roi = f[LY:LY + LH + 2 * PAD, LX:LX + LW + 2 * PAD].astype(np.float32)
    roi = roi * (1 - halo) + 255 * halo
    roi = roi * (1 - la) + lg[..., :3] * la
    f[LY:LY + LH + 2 * PAD, LX:LX + LW + 2 * PAD] = np.clip(roi + .5, 0, 255).astype(np.uint8)
    return f


def up(f):
    g = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    g = g + 0.35 * (g - cv2.GaussianBlur(g, (0, 0), 1.1))
    return np.clip(g + .5, 0, 255).astype(np.uint8)


def end_reader():
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", END, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            return
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


cap = cv2.VideoCapture(REF)
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
import os
KEEP = os.environ.get("KEEP")                     # reuse already-rendered frames before END0 from this file
if STILLS:
    for i in STILLS:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read()
        g = place_logo(up(remove_logo(process(i, f))))
        cv2.imwrite(f"{OUT}_{i}.png", g)
    sys.exit()

enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "30", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", OUT], stdin=subprocess.PIPE)
ends = end_reader()
if KEEP:
    kp = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", KEEP, "-frames:v", str(END0), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
for i in range(N):
    ok, f = cap.read()
    if not ok:
        break
    if KEEP and i < END0:
        g = np.frombuffer(kp.stdout.read(W * H * 3), np.uint8).reshape(H, W, 3)
    elif i < END0:
        g = place_logo(up(remove_logo(process(i, f))))
    else:
        card = next(ends)
        # reveal the end card through the reference's own white wipe (row by row: rows the wipe has
        # covered come entirely from our card, so nothing of the reference's own end card shows through)
        rows = ((f.min(2) > 225).mean(1) > 0.5).astype(np.float32)
        rows = cv2.resize(rows[:, None], (1, H), interpolation=cv2.INTER_LINEAR)[:, 0][:, None, None]
        if rows.mean() > 0.995:
            g = card
        else:
            base = place_logo(up(remove_logo(process(i, f))))
            g = np.clip(base * (1 - rows) + card * rows + .5, 0, 255).astype(np.uint8)
    enc.stdin.write(g.tobytes())
    if i % 60 == 0:
        print("frame", i, "/", N, flush=True)
enc.stdin.close(); enc.wait()
print("done", N)
