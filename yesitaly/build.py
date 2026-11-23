"""OrbisNexa re-brand of the 'Italy is Calling' course reel.

Keeps the reference footage, cuts, typography and animation timing, and changes only:
  * theme      : the red accent pills become OrbisNexa blue, white-pill text becomes OrbisNexa navy;
  * course     : 'Luxury Brand Management' -> 'MBBS & Nursing' (old pill removed with LaMa inpainting,
                 new pill drawn in the same style, same hard-cut timing);
  * CTA        : 'Apply with YES Italy' -> 'Apply with OrbisNexa', with the original spring / motion-blur
                 pop animation re-created frame by frame from the measured pill size;
  * ending     : OrbisNexa closing screen (rendered separately by endcard.html) appended.

All work is done at 1080x1920 (the 720x1280 reference is Lanczos-upscaled first).

Usage: python3 build.py <reference.mp4> <lama.onnx> <out_frames.mkv>     (video only, FFV1)
       python3 build.py --test <reference.mp4> <lama.onnx> <outdir> <frame> [frame ...]
"""
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw, ImageFont

TEST = sys.argv[1] == "--test"
args = sys.argv[2:] if TEST else sys.argv[1:]
REF, LAMA, OUT = args[:3]
FRAMES = [int(a) for a in args[3:]] if TEST else None

W, H, K = 1080, 1920, 1.5                       # output size, scale from reference coordinates
BLUE = np.array([179, 79, 11], np.float32)      # OrbisNexa blue  #0b4fb3 (BGR)
RED = np.array([1, 0, 189], np.float32)         # reference red   #bd0001 (BGR)
NAVY = np.array([61, 27, 12], np.float32)       # OrbisNexa navy  #0c1b3d (BGR)
FONT = "assets/InterDisplay-Medium.otf"
FS, TRACK = 72, -2.6                            # 48 px / -1.7 px at reference scale (SF-like tracking)

# pill rectangles in reference (720x1280) coordinates: x0, x1, y0, y1
AI = (144, 572, 374, 450)
FAS = (150, 567, 490, 573)
LUX = (51, 666, 606, 689)
BUS = (72, 645, 720, 805)
ENG = (63, 656, 836, 919)
APP_REST_W, APP_REST_H, APP_CY = 463, 83, 793.5

sess = ort.InferenceSession(LAMA, providers=["CPUExecutionProvider"])


# ------------------------------------------------------------------ text / pill rendering
def text_img(text, size=FS, track=TRACK, color=(255, 255, 255)):
    f = ImageFont.truetype(FONT, size)
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + track * (len(text) - 1)) + 4
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (tw, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 0.0
    for c, w in zip(text, widths):
        d.text((x, 0), c, font=f, fill=color + (255,))
        x += w + track
    bb = im.getbbox()
    return im, bb


def pill(text, fill, tcolor, pad, h):
    """Rounded pill with centred text; returns RGBA numpy (BGRA) at output scale."""
    tim, bb = text_img(text, color=tcolor)
    tw = bb[2] - bb[0]
    w = int(round(tw + 2 * pad))
    im = Image.new("RGBA", (w * 4, h * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=h * 2, fill=fill + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    # vertical placement: cap height centred like the reference (cap-top to baseline centred)
    f = ImageFont.truetype(FONT, FS)
    cap_top = f.getbbox("H")[1]
    base = f.getmetrics()[0]
    y = int(round(h / 2 - (cap_top + base) / 2))
    im.alpha_composite(tim, (int(round((w - tw) / 2 - bb[0])), y))
    a = np.array(im)
    return cv2.cvtColor(a, cv2.COLOR_RGBA2BGRA)


def over(dst, src, x, y):
    """Alpha-composite BGRA src onto float BGR dst at integer x, y (clipped)."""
    h, w = src.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = s[..., 3:4] / 255
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + s[..., :3] * a


LUX_H = int(round((LUX[3] - LUX[2] + 1) * K))
MBBS = pill("MBBS & Nursing", (255, 255, 255), (12, 27, 61), 36 * K, LUX_H)
APPLY = pill("Apply with OrbisNexa", (11, 79, 179), (255, 255, 255), 34 * K, int(round(APP_REST_H * K)))
APPLY = cv2.resize(APPLY, (max(APPLY.shape[1], int(APP_REST_W * K) + 6), APPLY.shape[0]), interpolation=cv2.INTER_AREA) \
    if APPLY.shape[1] < APP_REST_W * K else APPLY


# ------------------------------------------------------------------ helpers
def rect(r, m=0):
    x0, x1, y0, y1 = r
    return int((x0 - m) * K), int((x1 + 1 + m) * K), int((y0 - m) * K), int((y1 + 1 + m) * K)


def present(f720, r, thr, kind):
    x0, x1, y0, y1 = r
    a = f720[y0:y1, x0:x1].astype(np.int16)
    if kind == "white":
        m = (a > 225).all(2)
    else:
        m = (a[..., 2] - np.maximum(a[..., 0], a[..., 1])) > 110
    return m.sum() > thr * (x1 - x0) * (y1 - y0)


def recolor_red(f, r):
    """Red -> OrbisNexa blue inside rect r (output coords), keeping anti-aliasing and white text."""
    x0, x1, y0, y1 = r
    x0, y0 = max(x0, 0), max(y0, 0)
    reg = f[y0:y1, x0:x1]
    redness = reg[..., 2] - np.maximum(reg[..., 0], reg[..., 1])
    a = np.clip(redness / 188.0, 0, 1)[..., None]
    f[y0:y1, x0:x1] = reg + a * (BLUE - RED)


def navy_text(f, r):
    """Dark text inside a white pill -> OrbisNexa navy (interior only)."""
    x0, x1, y0, y1 = r
    h = y1 - y0
    x0, x1 = x0 + h // 2, x1 - h // 2
    y0, y1 = y0 + 6, y1 - 6
    reg = f[y0:y1, x0:x1]
    d = np.clip((255 - reg.min(2)) / (255 - 14), 0, 1)[..., None]
    f[y0:y1, x0:x1] = 255 * (1 - d) + NAVY * d


def lama(img_bgr, mask):
    """LaMa on a 512x512 crop (uint8 BGR, mask 0/1)."""
    x = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255
    m = mask.astype(np.float32)[None, None]
    out = sess.run(None, {"image": x, "mask": m})[0][0].transpose(1, 2, 0)
    if out.max() <= 1.5:
        out = out * 255
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)


LX0, LX1, LY0, LY1 = rect(LUX)
NX0 = (LX0 + LX1) // 2 - MBBS.shape[1] // 2
NX1 = NX0 + MBBS.shape[1]
prev_fill = None


def remove_lux(f):
    """Inpaint the parts of the old pill that the narrower new pill does not cover."""
    global prev_fill
    u8 = np.clip(f, 0, 255).astype(np.uint8)
    mask = np.zeros((H, W), np.uint8)
    cv2.rectangle(mask, (LX0 - 5, LY0 - 5), (LX1 + 5, LY1 + 5), 1, -1)
    # the whole old pill is a hole (so LaMa never extends white pill from the context); the new
    # pill is drawn over the middle afterwards, only the side strips of the fill remain visible
    cy = (LY0 + LY1) // 2
    ys = min(max(cy - 256, 0), H - 512)
    out = u8.copy()
    for xs in (0, W - 512):
        crop = u8[ys:ys + 512, xs:xs + 512]
        mk = mask[ys:ys + 512, xs:xs + 512].copy()
        res = lama(crop, mk)
        soft = cv2.GaussianBlur(cv2.dilate(mk, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 2)[..., None]
        if xs == 0:
            soft[:, W // 2 - xs:] = 0
        else:
            soft[:, :max(W // 2 - xs, 0)] = 0
        out[ys:ys + 512, xs:xs + 512] = (res * soft + out[ys:ys + 512, xs:xs + 512] * (1 - soft)).astype(np.uint8)
    fill = out.astype(np.float32)
    # light temporal smoothing of the filled water/buildings (reduces inpainting shimmer)
    m3 = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 3)[..., None]
    if prev_fill is not None:
        fill = fill * (1 - 0.35 * m3) + prev_fill * 0.35 * m3
    prev_fill = fill
    return fill


def motion_blur_h(img, n):
    n = int(n)
    if n < 2:
        return img
    k = np.zeros((1, n), np.float32)
    k[0, :] = 1 / n
    return cv2.filter2D(img, -1, k, borderType=cv2.BORDER_CONSTANT)


# ------------------------------------------------------------------ per frame
prev_app_w = None


def process(i, f720):
    global prev_app_w
    t = i / 30
    f = cv2.resize(f720, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    f = f + 0.35 * (f - cv2.GaussianBlur(f, (0, 0), 1.0))                # crisp after upscale

    if 5.5 <= t <= 9.0:                                                   # course pills scene
        if present(f720, LUX, 0.6, "white"):
            f = remove_lux(f)
            over(f, MBBS, NX0, LY0)
        for r in (AI, ENG):
            if present(f720, r, 0.4, "white"):
                navy_text(f, rect(r))
        for r in (FAS, BUS):
            if present(f720, r, 0.3, "red"):
                recolor_red(f, rect(r, 8))

    if t >= 13.5:                                                         # CTA pill
        a = f720[730:860, 30:690].astype(np.int16)
        m = (a[..., 2] - np.maximum(a[..., 0], a[..., 1])) > 110
        cols = np.where(m.sum(0) > 4)[0]
        if len(cols) > 10:
            w_old = cols[-1] - cols[0] + 1
            cx = 30 + (cols[0] + cols[-1]) / 2
            s = w_old / APP_REST_W
            recolor_red(f, (0, W, int(720 * K), int(870 * K)))
            pw, ph = int(round(APPLY.shape[1] * s)), int(round(APPLY.shape[0] * s))
            p = cv2.resize(APPLY, (pw, ph), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            if prev_app_w is not None:
                p = motion_blur_h(p, abs(w_old - prev_app_w) * K * 0.9)
            over(f, p, int(round(cx * K - pw / 2)), int(round(APP_CY * K - ph / 2)))
            prev_app_w = w_old
    return np.clip(f + 0.5, 0, 255).astype(np.uint8)


cap = cv2.VideoCapture(REF)
if TEST:
    import os
    os.makedirs(OUT, exist_ok=True)
    want = set(FRAMES)
    i = 0
    while want:
        ok, fr = cap.read()
        if not ok:
            break
        if i >= min(want) - 3:              # warm up the temporal state with the preceding frames
            res = process(i, fr)
            if i in want:
                cv2.imwrite(f"{OUT}/f{i:03d}.png", res)
                want.discard(i)
        i += 1
    sys.exit()

enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "30", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", OUT], stdin=subprocess.PIPE)
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    enc.stdin.write(process(i, fr).tobytes())
    if i % 60 == 0:
        print("frame", i, flush=True)
    i += 1
enc.stdin.close()
enc.wait()
print("done", i, "frames")
