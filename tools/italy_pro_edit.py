"""Polished OrbisNexa edit of the "Why Choose Italy for study?" reel.

Builds on the straight rebrand (rebrand_video3.py) with a creative pass:
  * Map section: OrbisNexa horizontal logo on a clean white panel (slides in,
    light sweep, exits with the rest of the UI), light colour grade + vignette.
  * Smooth zoom-dissolve from the map into the contact card.
  * Contact card: animated navy->blue gradient instead of flat blue, logo on a
    white tile, OrbisNexa numbers + address; original pop timings kept.
  * The original 6.7 s plain-white tail becomes a branded outro: iris wipe to
    white, full-colour logo reveal with light sweep, contact strip.

Usage: python3 italy_pro_edit.py <reference.mp4> <logo.jpg> <out.mp4>
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, LOGO, OUT = sys.argv[1:4]
W, H, FPS = 720, 1280, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_NUM = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
F_ADDR = os.path.join(HERE, "fonts", "OpenSans-ExtraBold.ttf")

PHONES = ["+92 370 0035896", "+92 312 4222204"]
ADDRESS = ["Iqbal, 8 Allama,", "Raza Block Town, Lahore, Pakistan"]
NAVY = (12, 27, 61)          # RGB
BLUE = (0, 102, 214)

# timeline (frames) measured from the reference
MAP_END = 420
BADGE_IN_END, UI_OUT0, UI_OUT1 = 16, 345, 361
XFADE0 = 410
CARD_START, CARD_REF = 420, 569
WIPE0, WIPE1 = 596, 626
CARD_X0, CARD_X1, CARD_Y0, CARD_Y1 = 80, 639, 56, 1224


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


frames = []
cap = cv2.VideoCapture(SRC)
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
N = len(frames)
CARD_BG = frames[CARD_REF][640, 30].astype(np.float32)   # flat blue (BGR)


# ------------------------------------------------------------------ logo art
logo_src = cv2.cvtColor(cv2.imread(LOGO), cv2.COLOR_BGR2RGB).astype(np.float32)


def rgba_crop(y0, y1, x0, x1):
    """Logo crop as RGBA with the white background keyed out."""
    c = logo_src[y0:y1, x0:x1]
    a = np.clip((248 - c.min(-1)) / 45, 0, 1)
    # un-premultiply against white so edges stay clean
    rgb = np.where(a[..., None] > 0.01, (c - 255 * (1 - a[..., None])) / np.maximum(a[..., None], 0.01), 255)
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def fit(img, max_w, max_h):
    s = min(max_w / img.width, max_h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def horizontal_lockup(height):
    icon = rgba_crop(150, 745, 216, 1024)
    text = rgba_crop(760, 1072, 118, 1134)
    icon = fit(icon, 10_000, height)
    text = fit(text, 10_000, round(height * 0.74))
    gap = round(height * 0.12)
    out = Image.new("RGBA", (icon.width + gap + text.width, height))
    out.alpha_composite(icon, (0, 0))
    out.alpha_composite(text, (icon.width + gap, (height - text.height) // 2 + 2))
    return out


VERTICAL = rgba_crop(150, 1075, 118, 1134)


def shadow_of(img, blur, strength, dy=6):
    pad = blur * 3
    sh = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad))
    a = img.getchannel("A").point(lambda v: int(v * strength))
    blk = Image.new("RGBA", img.size, (5, 15, 40, 255))
    blk.putalpha(a)
    sh.alpha_composite(blk, (pad, pad + dy))
    return sh.filter(ImageFilter.GaussianBlur(blur)), pad


def rounded(w, h, r, fill):
    im = Image.new("RGBA", (w, h))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=fill)
    return im


def sheen(img, t, width=0.18, strength=0.55):
    """Diagonal light band sweeping across img's opaque pixels; t in [0, 1]."""
    if t <= 0 or t >= 1:
        return img
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pos = (xx + yy * 0.6) / (w + h * 0.6)
    c = -0.2 + 1.4 * t
    band = np.clip(1 - np.abs(pos - c) / width, 0, 1) ** 2 * strength
    arr = np.array(img).astype(np.float32)
    k = band[..., None] * (arr[..., 3:4] / 255)
    arr[..., :3] = arr[..., :3] * (1 - k) + 255 * k
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# top panel for the map section
PANEL_W, PANEL_H = 600, 210
panel = rounded(PANEL_W, PANEL_H, 34, (255, 255, 255, 246))
accent = Image.new("RGBA", (PANEL_W - 120, 5))
acc = np.zeros((5, PANEL_W - 120, 4), np.uint8)
for x in range(PANEL_W - 120):
    k = x / (PANEL_W - 121)
    acc[:, x, :3] = [round(NAVY[i] * (1 - k) + BLUE[i] * k) for i in range(3)]
    acc[:, x, 3] = round(255 * np.sin(np.pi * k) ** 0.6)
panel.alpha_composite(Image.fromarray(acc, "RGBA"), (60, PANEL_H - 16))
lock = horizontal_lockup(138)
lock = fit(lock, PANEL_W - 70, 140)
panel.alpha_composite(lock, ((PANEL_W - lock.width) // 2, (PANEL_H - 10 - lock.height) // 2))
panel_shadow, panel_pad = shadow_of(panel, 16, 0.35, dy=8)
PANEL_X, PANEL_Y = (W - PANEL_W) // 2, 54

# white logo tile for the contact card
TILE_W, TILE_H = 470, 150
tile = rounded(TILE_W, TILE_H, 30, (255, 255, 255, 255))
lk = fit(horizontal_lockup(110), TILE_W - 56, 112)
tile.alpha_composite(lk, ((TILE_W - lk.width) // 2, (TILE_H - lk.height) // 2))
tile_shadow, tile_pad = shadow_of(tile, 14, 0.45, dy=8)
TILE_C = (360, 165)


def paste(dst_bgr, img, x, y, alpha=1.0):
    """Alpha-composite RGBA PIL image onto a float BGR frame at (x, y)."""
    a = np.array(img).astype(np.float32)
    if alpha < 1:
        a[..., 3] *= alpha
    h, w = a.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
    k = sub[..., 3:4] / 255
    dst_bgr[y0:y1, x0:x1] = dst_bgr[y0:y1, x0:x1] * (1 - k) + sub[..., 2::-1] * k


def scaled_img(img, s):
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


# ------------------------------------------------------------- map section
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vign = 1 - 0.16 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2, 0, 1)
vign = vign[..., None]
badge_m = np.clip(104 - np.sqrt((xx - 358.9) ** 2 + (yy - 158.7) ** 2), 0, 6)[..., None] / 6
BG_IN, BG_OUT = frames[0].astype(np.float32), frames[362].astype(np.float32)


def grade(f):
    hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.12, 0, 255)
    f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    f = (f - 128) * 1.06 + 128
    return np.clip(f * vign, 0, 255)


def map_frame(i):
    f = frames[i].astype(np.float32)
    # remove the old badge where the panel is not fully covering it
    if i <= BADGE_IN_END:
        f = f * (1 - badge_m) + BG_IN * badge_m
    elif UI_OUT0 - 2 <= i <= UI_OUT1 + 2:
        f = f * (1 - badge_m) + BG_OUT * badge_m
    f = grade(f)
    # panel animation
    if i < UI_OUT0:
        p = ease((i - 1) / 15)
        dy = -36 * (1 - p)
    else:
        p = 1 - ease_io((i - UI_OUT0) / (UI_OUT1 - UI_OUT0))
        dy = -24 * (1 - p)
    if p > 0.001:
        pan = sheen(panel, (i - 34) / 30)
        paste(f, panel_shadow, PANEL_X - panel_pad, PANEL_Y - panel_pad + dy, p)
        paste(f, pan, PANEL_X, PANEL_Y + dy, p)
    return f


# ----------------------------------------------------------- card section
def text_layer(lines, font, size, centers_y):
    img = Image.new("RGB", (W, H), tuple(int(v) for v in CARD_BG[::-1]))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font, size)
    for t, cy in zip(lines, centers_y):
        d.text((360, cy), t, font=f, fill="white", anchor="mm")
    return np.array(img)[..., ::-1].astype(np.float32)


card_ref = frames[CARD_REF].astype(np.float32)
flat = np.empty_like(card_ref)
flat[:] = CARD_BG


def zone_copy(src, y0, y1, dst_y=None):
    out = flat.copy()
    h = y1 - y0
    dy = y0 if dst_y is None else dst_y
    out[dy:dy + h, CARD_X0:CARD_X1] = src[y0:y1, CARD_X0:CARD_X1]
    return out


phone_rows, globe_c = (396, 462), 604.5
icon_y = round(globe_c - (phone_rows[1] - phone_rows[0]) / 2)
ELEMENTS = [
    ("badge", 74, 256, 164.8, zone_copy(card_ref, 74, 256), flat),
    ("phone1", 478, 552, 514.5, zone_copy(card_ref, 478, 552), text_layer([PHONES[0]], F_NUM, 38, [514.5])),
    ("icon2", 560, 652, globe_c, zone_copy(card_ref, 560, 652), zone_copy(card_ref, *phone_rows, dst_y=icon_y)),
    ("phone2", 652, 724, 685.5, zone_copy(card_ref, 652, 724), text_layer([PHONES[1]], F_NUM, 38, [685.5])),
    ("address", 846, 930, 889.5, zone_copy(card_ref, 846, 930), text_layer(ADDRESS, F_ADDR, 20, [874.5, 903.5])),
]
SCALES = np.round(np.arange(0.05, 1.501, 0.025), 3)


def scaled(layer, y0, y1, cy, s):
    M = np.float32([[s, 0, 360 * (1 - s)], [0, s, cy * (1 - s)]])
    out = cv2.warpAffine(layer, M, (W, H), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=CARD_BG.tolist())
    return out[y0:y1, CARD_X0:CARD_X1]


def fit_card(frame, el):
    _, y0, y1, cy, old, _ = el
    fz = frame[y0:y1, CARD_X0:CARD_X1].astype(np.float32) - CARD_BG
    if np.abs(fz).max() < 25:
        return 0.0, 1.0
    best = (np.inf, 0.0, 1.0)
    for s in SCALES:
        t = scaled(old, y0, y1, cy, s) - CARD_BG
        den = (t * t).sum()
        if den < 1:
            continue
        a = float(np.clip((fz * t).sum() / den, 0, 1))
        err = ((fz - a * t) ** 2).sum()
        if err < best[0]:
            best = (err, a, s)
    return best[1], best[2]


# animated gradient that replaces the flat card blue
def lerp(c1, c2, k):
    return c1[None, None, :] * (1 - k) + c2[None, None, :] * k


diag = np.clip((xx * 0.55 + yy) / (W * 0.55 + H), 0, 1)[..., None]
G_TOP = np.array(NAVY[::-1], np.float32)            # BGR
G_BOT = np.array((10, 96, 196)[::-1], np.float32)
G_BASE = lerp(G_TOP, G_BOT, diag ** 0.9)
inside = ((xx >= 78) & (xx <= 641) & (yy >= 55) & (yy <= 1224)).astype(np.float32)
inside = cv2.GaussianBlur(inside, (0, 0), 2)[..., None]
GLOW_COL = np.array((255, 170, 60), np.float32)      # BGR light blue


_rng = np.random.default_rng(7)
_GRAIN = [_rng.normal(0, 1.1, (H, W, 1)).astype(np.float32) for _ in range(4)]


def grain(i):
    """Fine animated grain: dithers soft gradients so they don't band."""
    return _GRAIN[i % 4]


def gradient(i):
    t = (i - CARD_START) / 200
    gx, gy = 120 + 480 * t, 260 + 640 * np.sin(t * 1.4)
    g1 = np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * 260 ** 2))[..., None]
    g2 = np.exp(-((xx - (620 - 300 * t)) ** 2 + (yy - (1150 - 200 * t)) ** 2) / (2 * 300 ** 2))[..., None]
    g = G_BASE + GLOW_COL * (0.16 * g1 + 0.12 * g2)
    g = g * (0.80 + 0.20 * inside) + 255 * 0.05 * inside      # glass card, darker margin
    return np.clip(g + grain(i), 0, 255)


WHITE = np.array([255, 255, 255], np.float32)
D = WHITE - CARD_BG
DD = (D * D).sum()


def swap_background(f, g):
    v = f - CARD_BG
    t = np.clip((v * D).sum(-1, keepdims=True) / DD, 0, 1)
    resid = np.sqrt(((v - t * D) ** 2).sum(-1, keepdims=True))
    w = np.clip((42 - resid) / 18, 0, 1)        # 1 = pixel lies on the blue->white line
    on_line = g * (1 - t) + WHITE * t
    return f * (1 - w) + on_line * w


fits = {}


def card_frame(i):
    src = frames[min(i, CARD_REF)]
    f = src.astype(np.float32)
    badge = (0.0, 1.0)
    for el in ELEMENTS:
        name, y0, y1, cy, old, new = el
        if (i, name) not in fits:
            fits[(i, name)] = (1.0, 1.0) if i >= CARD_REF else fit_card(src, el)
        a, s = fits[(i, name)]
        a = 1.0 if a > 0.85 else a
        if name == "badge":
            badge = (a, s)
        z = np.empty((y1 - y0, CARD_X1 - CARD_X0, 3), np.float32)
        z[:] = CARD_BG
        if a > 0.01 and name != "badge":
            z += a * (scaled(new, y0, y1, cy, s) - CARD_BG)
        f[y0:y1, CARD_X0:CARD_X1] = z
        for c0, c1 in ((66, CARD_X0), (CARD_X1, 654)):
            f[y0:y1, c0:c1] = card_ref[y0:y1, c0:c1]
    f = swap_background(f, gradient(i))
    a, s = badge
    if a > 0.01:
        s = s * 1.0
        ti, sh = scaled_img(tile, s), scaled_img(tile_shadow, s)
        tt = sheen(ti, (i - 470) / 28, strength=0.45)
        paste(f, sh, TILE_C[0] - sh.width / 2, TILE_C[1] - sh.height / 2 + 4 * s, a)
        paste(f, tt, TILE_C[0] - ti.width / 2, TILE_C[1] - ti.height / 2, a)
    if i > CARD_REF:                                   # gentle push-in while holding
        z = 1 + 0.025 * ease_io((i - CARD_REF) / (WIPE1 - CARD_REF))
        M = cv2.getRotationMatrix2D((360, 640), 0, z)
        f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
    return f


# ---------------------------------------------------------------- outro
_glow = np.exp(-((xx - 360) ** 2 + (yy - 560) ** 2) / (2 * 360 ** 2))[..., None]
END_BG = np.clip(255 - _glow * np.array([0, 10, 22], np.float32)                 # BGR: cool tint
                 - (yy / H)[..., None] ** 2 * np.array([0, 8, 16], np.float32), 0, 255)
# note: subtle cool glow behind the logo on an otherwise white page

end_logo = fit(VERTICAL, 470, 450)
END_LOGO_C = (360, 520)


def icon_from_card(y0, y1, x0, x1):
    """Card icon (white disc, blue glyph) -> blue disc with white glyph, RGBA."""
    c = card_ref[y0:y1, x0:x1]
    v = c - CARD_BG
    t = np.clip((v * D).sum(-1) / DD, 0, 1)
    disc = (t > 0.5).astype(np.uint8)
    ff = disc.copy()
    mask = np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    filled = (ff != 2).astype(np.float32)
    filled = cv2.GaussianBlur(filled, (0, 0), 0.7)
    glyph = (1 - t) * (filled > 0.5)
    rgb = np.array(BLUE, np.float32)[None, None] * (1 - glyph[..., None]) + 255 * glyph[..., None]
    return Image.fromarray(np.dstack([rgb, filled * 255]).astype(np.uint8), "RGBA")


ICON_PHONE = icon_from_card(396, 462, 326, 394)
ICON_PIN = icon_from_card(736, 812, 322, 398)


def contact_strip():
    w, h = 620, 236
    im = rounded(w, h, 30, (243, 247, 253, 255))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=30, outline=(214, 226, 243), width=2)
    d = ImageDraw.Draw(im)
    f_addr = ImageFont.truetype(F_ADDR, 23)
    f_ph = ImageFont.truetype(F_NUM, 30)
    pin = fit(ICON_PIN, 60, 60)
    ph = fit(ICON_PHONE, 60, 60)
    im.alpha_composite(pin, (34, 30))
    d.text((112, 30), ADDRESS[0], font=f_addr, fill=NAVY)
    d.text((112, 62), ADDRESS[1], font=f_addr, fill=NAVY)
    d.line([(34, 118), (w - 34, 118)], fill=(205, 218, 238), width=2)
    im.alpha_composite(ph, (34, 144))
    d.text((112, 132), PHONES[0], font=f_ph, fill=NAVY)
    d.text((112, 172), PHONES[1], font=f_ph, fill=NAVY)
    return im


strip = contact_strip()
strip_shadow, strip_pad = shadow_of(strip, 18, 0.18, dy=10)
STRIP_Y = 850


def outro_frame(i):
    f = END_BG + grain(i)
    t = (i - WIPE1 + 6) / FPS
    p = ease(t / 0.9)
    if p > 0:
        s = 0.9 + 0.1 * p
        lg = scaled_img(end_logo, s)
        lg = sheen(lg, (i - 668) / 34, width=0.16, strength=0.6)
        paste(f, lg, END_LOGO_C[0] - lg.width / 2, END_LOGO_C[1] - lg.height / 2 + 30 * (1 - p), p)
    q = ease((t - 0.7) / 0.7)
    if q > 0:
        y = STRIP_Y + 50 * (1 - q)
        paste(f, strip_shadow, (W - strip.width) / 2 - strip_pad, y - strip_pad, q)
        paste(f, strip, (W - strip.width) / 2, y, q)
    return f


# ---------------------------------------------------------------- render
enc = subprocess.Popen([
    "ffmpeg", "-loglevel", "error", "-y",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow",
    "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)

card_first = None
for i in range(N):
    if i < MAP_END:
        f = map_frame(i)
        if i >= XFADE0:                      # zoom-dissolve into the card
            k = ease_io((i - XFADE0 + 1) / (MAP_END - XFADE0 + 1))
            M = cv2.getRotationMatrix2D((360, 640), 0, 1 + 0.12 * k)
            f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
            if card_first is None:
                card_first = card_frame(CARD_START)
            Mc = cv2.getRotationMatrix2D((360, 640), 0, 0.94 + 0.06 * k)
            c = cv2.warpAffine(card_first, Mc, (W, H), borderMode=cv2.BORDER_REPLICATE)
            f = f * (1 - k) + c * k
    elif i < WIPE0:
        f = card_frame(i)
    elif i < WIPE1:
        c = card_frame(i)
        o = outro_frame(i)
        r = 1500 * ease_io((i - WIPE0 + 1) / (WIPE1 - WIPE0))
        m = np.clip((r - np.sqrt((xx - 360) ** 2 + (yy - 640) ** 2)) / 3, 0, 1)[..., None]
        f = c * (1 - m) + o * m
    else:
        f = outro_frame(i)
    enc.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())

enc.stdin.close()
enc.wait()
print("frames", N)
