"""Premium OrbisNexa edit of the "Why Choose Italy for study?" reel (v2).

Design rules (client brief):
  * Logo only in its original form: no panel, tile or shape behind it.
  * Every element appears once. One logo instance runs through the whole film:
    it enters over the map, stays as the header of the contact screen and
    finally glides to centre as the closing shot. Contact details appear only
    on the contact screen.
  * Clean, light, modern look; original content and animation timing kept.

Pipeline
  1. Map section (0-419): original badge removed with a tracked clean plate
     (map_cleanplate.py), light grade, logo fades up at the top.
  2. Zoom-dissolve into a full-bleed light contact screen. Each element pops in
     with the scale/opacity measured from the original's own pop animation.
  3. Outro: details ease out, the logo glides to centre; audio fades out.

Usage: python3 italy_premium_edit.py <reference.mp4> <logo.jpg> <out.mp4>
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from map_cleanplate import build_cleaner  # noqa: E402

SRC, LOGO, OUT = sys.argv[1:4]
W, H, FPS = 720, 1280, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_BOLD = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
F_TEXT = os.path.join(HERE, "fonts", "OpenSans-ExtraBold.ttf")

PHONES = ["+92 370 0035896", "+92 312 4222204"]
ADDRESS = ["Iqbal, 8 Allama,", "Raza Block Town, Lahore, Pakistan"]
NAVY = (12, 27, 61)                  # RGB, from the logo
BLUE = (0, 102, 214)
SLATE = (66, 80, 110)

# timeline (frames)
UI_OUT1 = 361                        # original UI finished fading out
XFADE0, CARD_START, CARD_REF = 408, 420, 569
OUTRO0 = 606                         # details start to leave
GLIDE0, GLIDE1 = 618, 664            # logo glides to centre
END = 720                            # 24.0 s
AUDIO_FADE = 1.2

LOGO_TOP_C = (360, 168)              # logo centre: map + contact screen
LOGO_TOP_H = 236
LOGO_END_C = (360, 610)
LOGO_END_SCALE = 1.55


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)       # smootherstep


# ------------------------------------------------------------------ frames
frames = []
cap = cv2.VideoCapture(SRC)
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
frames = np.array(frames)
CARD_BG = frames[CARD_REF][640, 30].astype(np.float32)
card_ref = frames[CARD_REF].astype(np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# --------------------------------------------------------------- logo art
logo_src = cv2.cvtColor(cv2.imread(LOGO), cv2.COLOR_BGR2RGB).astype(np.float32)


def keyed_logo():
    """The original logo with its white background removed (true transparency)."""
    c = logo_src[150:1075, 118:1134]
    a = np.clip((250 - c.min(-1)) / 42, 0, 1)
    rgb = (c - 255 * (1 - a[..., None])) / np.maximum(a[..., None], 1e-3)
    rgb = np.where(a[..., None] > 0.02, rgb, 255)
    # globe interior is white in the artwork: keep it white, not see-through
    disc = np.zeros(a.shape, np.uint8)
    cv2.circle(disc, (523 - 118, 495 - 150), 150, 1, -1)       # globe centre/radius in source
    inner = (disc > 0) & (a < 0.98)
    rgb[inner] = rgb[inner] * a[inner][..., None] + 255 * (1 - a[inner][..., None])
    a[inner] = 1.0
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


LOGO_IMG = keyed_logo()


def fit(img, max_w, max_h):
    s = min(max_w / img.width, max_h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def scaled_img(img, s):
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


LOGO_BASE = fit(LOGO_IMG, 10_000, LOGO_TOP_H)
LOGO_BIG = fit(LOGO_IMG, 10_000, round(LOGO_TOP_H * LOGO_END_SCALE))   # crisp end size


def soft_shadow(img, blur, strength, dy):
    pad = blur * 3
    sh = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad))
    blk = Image.new("RGBA", img.size, (8, 20, 48, 255))
    blk.putalpha(img.getchannel("A").point(lambda v: int(v * strength)))
    sh.alpha_composite(blk, (pad, pad + dy))
    return sh.filter(ImageFilter.GaussianBlur(blur)), pad


def sheen(img, t, width=0.14, strength=0.5):
    if t <= 0 or t >= 1:
        return img
    w, h = img.size
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    pos = (gx + gy * 0.55) / (w + h * 0.55)
    band = np.clip(1 - np.abs(pos - (-0.15 + 1.3 * t)) / width, 0, 1) ** 2 * strength
    arr = np.array(img).astype(np.float32)
    k = band[..., None] * (arr[..., 3:4] / 255)
    arr[..., :3] = arr[..., :3] * (1 - k) + 255 * k
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def paste(dst, img, cx, cy, alpha=1.0):
    """Composite RGBA `img` centred at (cx, cy) onto float BGR `dst`."""
    if alpha <= 0.001:
        return
    a = np.array(img).astype(np.float32)
    a[..., 3] *= alpha
    h, w = a.shape[:2]
    x, y = int(round(cx - w / 2)), int(round(cy - h / 2))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
    k = sub[..., 3:4] / 255
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - k) + sub[..., 2::-1] * k


def draw_logo(f, i, on_map):
    """The single logo instance, wherever it is in the film."""
    if i < CARD_START:
        p = ease((i - 2) / 22)
        cy = LOGO_TOP_C[1] + 22 * (1 - p)
        s = 0.965 + 0.035 * p
        alpha = p
    else:
        p, alpha = 1.0, 1.0
        g = ease_io((i - GLIDE0) / (GLIDE1 - GLIDE0))
        cy = LOGO_TOP_C[1] + (LOGO_END_C[1] - LOGO_TOP_C[1]) * g
        s = 1 + (LOGO_END_SCALE - 1) * g
    if alpha <= 0.001:
        return
    if s > 1.001:
        img = scaled_img(LOGO_BIG, s / LOGO_END_SCALE)
    else:
        img = scaled_img(LOGO_BASE, s) if abs(s - 1) > 1e-3 else LOGO_BASE
    sweep = (i - 40) / 34 if i < CARD_START else (i - (GLIDE1 + 12)) / 36
    img = sheen(img, sweep)
    sh, _ = soft_shadow(img, 12 if on_map else 16, 0.30 if on_map else 0.16, 6)
    paste(f, sh, LOGO_TOP_C[0], cy + 0, alpha)
    paste(f, img, LOGO_TOP_C[0], cy, alpha)


# -------------------------------------------------------------- map section
vign = (1 - 0.14 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2, 0, 1))[..., None]


def grade(f):
    hsv = cv2.cvtColor(np.clip(f, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.10, 0, 255)
    f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    f = (f - 128) * 1.05 + 130
    return np.clip(f * vign, 0, 255)


print("tracking map for clean plate ...", flush=True)
clean = build_cleaner(frames)


def map_frame(i):
    f = clean(i) if i <= UI_OUT1 + 2 else frames[i].astype(np.float32)
    return grade(f)


# ------------------------------------------------------- light contact screen
_rng = np.random.default_rng(11)
GRAIN = [_rng.normal(0, 1.0, (H, W, 1)).astype(np.float32) for _ in range(4)]
BG_TOP = np.array((255, 255, 255), np.float32)          # BGR
BG_BOT = np.array((250, 240, 229), np.float32)          # very light blue
BG_BASE = BG_TOP[None, None] * (1 - (yy / H)[..., None] ** 1.3) + BG_BOT[None, None] * (yy / H)[..., None] ** 1.3
GLOW = np.array((255, 214, 170), np.float32) - 255      # pale blue tint (negative offset)


def light_bg(i):
    """Clean white -> pale-blue backdrop with one broad, slowly drifting light."""
    t = (i - CARD_START) / 300
    g = np.exp(-((xx - (520 - 160 * t)) ** 2 + (yy - (980 - 240 * t)) ** 2) / (2 * 640 ** 2))[..., None]
    return np.clip(BG_BASE + GLOW * 0.22 * g + GRAIN[i % 4], 0, 255)


def icon_from_card(y0, y1, x0, x1):
    """Original card icons (white disc, blue glyph) -> brand blue disc, white glyph."""
    D = np.array([255, 255, 255], np.float32) - CARD_BG
    c = card_ref[y0:y1, x0:x1]
    t = np.clip(((c - CARD_BG) * D).sum(-1) / (D * D).sum(), 0, 1)
    disc = (t > 0.5).astype(np.uint8)
    ff = disc.copy()
    cv2.floodFill(ff, np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8), (0, 0), 2)
    filled = cv2.GaussianBlur((ff != 2).astype(np.float32), (0, 0), 0.6)
    glyph = (1 - t) * (filled > 0.5)
    rgb = np.array(BLUE, np.float32)[None, None] * (1 - glyph[..., None]) + 255 * glyph[..., None]
    return Image.fromarray(np.dstack([rgb, filled * 255]).astype(np.uint8), "RGBA")


def text_img(lines, font, size, color, line_gap=1.32):
    f = ImageFont.truetype(font, size)
    widths = [f.getbbox(t)[2] - f.getbbox(t)[0] for t in lines]
    lh = round(size * line_gap)
    im = Image.new("RGBA", (max(widths) + 20, lh * len(lines) + 16))
    d = ImageDraw.Draw(im)
    for k, t in enumerate(lines):
        d.text((im.width / 2, 8 + lh * k + lh / 2), t, font=f, fill=color, anchor="mm")
    return im


def heading(text, size):
    f = ImageFont.truetype(F_BOLD, size)
    bb = f.getbbox(text)
    w = bb[2] - bb[0] + 20
    im = Image.new("RGBA", (w, size + 40))
    d = ImageDraw.Draw(im)
    d.text((w / 2, size * 0.62), text, font=f, fill=NAVY, anchor="mm")
    bar_w, bar_y = 58, size + 22
    bar = np.zeros((5, bar_w, 4), np.uint8)
    for x in range(bar_w):
        k = x / (bar_w - 1)
        bar[:, x, :3] = [round(NAVY[c] * (1 - k) + BLUE[c] * k) for c in range(3)]
        bar[:, x, 3] = 255
    b = Image.fromarray(bar, "RGBA")
    m = Image.new("L", (bar_w, 5))
    ImageDraw.Draw(m).rounded_rectangle([0, 0, bar_w - 1, 4], radius=2, fill=255)
    b.putalpha(m)
    im.alpha_composite(b, ((w - bar_w) // 2, bar_y))
    return im


ICON_PHONE = fit(icon_from_card(396, 462, 326, 394), 60, 60)
ICON_PIN = fit(icon_from_card(736, 812, 322, 398), 64, 64)
SOCIALS = icon_from_card(1096, 1160, 222, 498)

# element: (name, zone y0, y1 in the original, centre y, image)
# (name, zone y0, y1 + centre y in the original [for timing], target y, image)
# One phone icon serves both numbers (the original's second icon is dropped).
ELEMENTS = [
    ("contact", 284, 372, 328.0, 402, heading("Contact Us", 46)),
    ("icon1", 384, 472, 429.0, 514, ICON_PHONE),
    ("phone1", 478, 552, 514.5, 578, text_img([PHONES[0]], F_BOLD, 36, NAVY)),
    ("phone2", 652, 724, 685.5, 626, text_img([PHONES[1]], F_BOLD, 36, NAVY)),
    ("pin", 728, 822, 773.5, 742, ICON_PIN),
    ("address", 846, 930, 889.0, 812, text_img(ADDRESS, F_TEXT, 24, SLATE, 1.42)),
    ("follow", 1000, 1090, 1045.5, 952, text_img(["Follow Us"], F_BOLD, 30, NAVY)),
    ("socials", 1092, 1166, 1127.5, 1022, SOCIALS),
]

# fit each element's pop animation (scale, opacity) from the original
X0, X1 = 80, 639
SCALES = np.round(np.arange(0.05, 1.501, 0.025), 3)
flat = np.empty_like(card_ref)
flat[:] = CARD_BG


def zone_layer(y0, y1):
    out = flat.copy()
    out[y0:y1, X0:X1] = card_ref[y0:y1, X0:X1]
    return out


def fit_pop(frame, y0, y1, cy, old):
    fz = frame[y0:y1, X0:X1].astype(np.float32) - CARD_BG
    if np.abs(fz).max() < 25:
        return 0.0, 1.0
    best = (np.inf, 0.0, 1.0)
    for s in SCALES:
        M = np.float32([[s, 0, 360 * (1 - s)], [0, s, cy * (1 - s)]])
        t = cv2.warpAffine(old, M, (W, H), borderValue=CARD_BG.tolist())[y0:y1, X0:X1] - CARD_BG
        den = (t * t).sum()
        if den < 1:
            continue
        a = float(np.clip((fz * t).sum() / den, 0, 1))
        err = ((fz - a * t) ** 2).sum()
        if err < best[0]:
            best = (err, a, s)
    return best[1], best[2]


print("measuring original pop animations ...", flush=True)
POPS = {}
for name, y0, y1, cy, _, _ in ELEMENTS:
    old = zone_layer(y0, y1)
    for i in range(CARD_START, CARD_REF + 1):
        a, s = fit_pop(frames[i], y0, y1, cy, old)
        POPS[(name, i)] = (1.0 if a > 0.85 else a, s)


def contact_frame(i):
    f = light_bg(i)
    for k, (name, y0, y1, cy, ty, img) in enumerate(ELEMENTS):
        a, s = POPS.get((name, min(i, CARD_REF)), (1.0, 1.0))
        dy = 0.0
        if i >= OUTRO0:                                    # staggered, bottom first
            o = ease_io((i - OUTRO0 - (len(ELEMENTS) - 1 - k) * 1.6) / 12)
            a *= 1 - o
            dy = -14 * o
        if a <= 0.01:
            continue
        im = img if abs(s - 1) < 1e-3 else scaled_img(img, s)
        paste(f, im, 360, ty + dy, a)
    return f


# ------------------------------------------------------------------ render
enc = subprocess.Popen([
    "ffmpeg", "-loglevel", "error", "-y",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-map", "0:v", "-map", "1:a",
    "-af", f"afade=t=out:st={END / FPS - AUDIO_FADE:.2f}:d={AUDIO_FADE}",
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
    "-t", f"{END / FPS:.3f}", OUT], stdin=subprocess.PIPE)

print("rendering ...", flush=True)
card_first = None
for i in range(END):
    if i < CARD_START:
        f = map_frame(i)
        if i >= XFADE0:                                      # zoom-dissolve
            k = ease_io((i - XFADE0 + 1) / (CARD_START - XFADE0 + 1))
            M = cv2.getRotationMatrix2D((360, 640), 0, 1 + 0.10 * k)
            f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            if card_first is None:
                card_first = light_bg(CARD_START)
            f = f * (1 - k) + card_first * k
        draw_logo(f, i, on_map=True)
    else:
        f = contact_frame(i)
        draw_logo(f, i, on_map=False)
    enc.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    if i % 60 == 0:
        print(" frame", i, flush=True)

enc.stdin.close()
enc.wait()
print("done", OUT)
