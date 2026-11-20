"""Rebrand the "Why Choose Italy for study?" reel.

Keeps every frame, animation, text, the white tail and the audio. Only changes:
  * Logo inside the round badge (map section and contact card) -> OrbisNexa logo.
  * Contact card: phone number, second line (was website) and address -> OrbisNexa.

Each replaced element follows the original element's own animation: for every
frame we fit the original element's scale / opacity / blur against its final
look, then swap it with the new element under the same transform:
    out = frame + a * (T(new) - T(old))
which is exact for fades over any background. On the flat-blue contact card
the row is simply cleared and the new element drawn with the fitted scale/opacity.

Usage: python3 rebrand_video3.py <reference.mp4> <logo.jpg> <out.mp4>
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC, LOGO, OUT = sys.argv[1:4]
W, H, FPS = 720, 1280, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_NUM = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
F_ADDR = os.path.join(HERE, "fonts", "OpenSans-ExtraBold.ttf")

PHONES = ["+92 370 0035896", "+92 312 4222204"]
ADDRESS = ["Iqbal, 8 Allama,", "Raza Block Town, Lahore, Pakistan"]

# Measured from the reference video.
MAP_REF, MAP_END = 30, 420            # badge over the map: frames [0, 420)
MAP_DISC = (358.9, 158.7, 91.0)       # inner white disc (cx, cy, r)
CARD_START, CARD_REF, CARD_END = 420, 569, 570
CARD_DISC = (359.2, 164.8, 73.2)
CARD_X0, CARD_X1 = 80, 639            # just inside the card border (72-77, 641-646)

frames = []
cap = cv2.VideoCapture(SRC)
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
frames = np.array(frames)
CARD_BG = frames[CARD_REF][640, 30].astype(np.float32)   # flat card blue


# --------------------------------------------------------------------- assets
def logo_on_white(max_w, max_h):
    """Full-colour logo (icon + OrbisNexa wordmark), white background."""
    im = cv2.imread(LOGO)[150:945]
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    cols = np.where((g < 200).any(0))[0]
    im = im[:, cols.min() - 6: cols.max() + 7]
    s = min(max_w / im.shape[1], max_h / im.shape[0])
    im = cv2.resize(im, (round(im.shape[1] * s), round(im.shape[0] * s)),
                    interpolation=cv2.INTER_AREA).astype(np.float32)
    # clean jpeg off-white to pure white so it melts into the disc
    a = np.clip((250 - im.min(-1)) / 40, 0, 1)[..., None]
    return im * a + 255 * (1 - a)


def badge_layer(ref, disc):
    """The reference badge with its inner disc replaced by our logo."""
    cx, cy, r = disc
    out = ref.astype(np.float32).copy()
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    m = np.clip(r - 1.5 - d, 0, 1)[..., None]
    white = np.full_like(out, 255)
    side = r * 2 * 0.80
    lg = logo_on_white(side, side * 0.92)
    lh, lw = lg.shape[:2]
    x0, y0 = round(cx - lw / 2), round(cy - lh / 2)
    white[y0:y0 + lh, x0:x0 + lw] = lg
    out = out * (1 - m) + white * m
    return out, (np.clip(r + 2 - d, 0, 1) > 0)


def text_layer(bg, lines, font, size, centers_y, spacing=None):
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)[..., ::-1])
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font, size)
    for t, cy in zip(lines, centers_y):
        d.text((360, cy), t, font=f, fill="white", anchor="mm")
    return np.array(img)[..., ::-1].astype(np.float32)


# ------------------------------------------------------------ card elements
card_ref = frames[CARD_REF].astype(np.float32)
flat = np.empty_like(card_ref)
flat[:] = CARD_BG


def zone_copy(src, y0, y1, dst_y=None):
    out = flat.copy()
    if dst_y is None:
        out[y0:y1, CARD_X0:CARD_X1] = src[y0:y1, CARD_X0:CARD_X1]
    else:
        h = y1 - y0
        out[dst_y:dst_y + h, CARD_X0:CARD_X1] = src[y0:y1, CARD_X0:CARD_X1]
    return out


badge_new_card, _ = badge_layer(frames[CARD_REF], CARD_DISC)
# globe icon row -> phone icon (copied from the card's own phone icon)
phone_icon_rows = (396, 462)          # phone icon y-range on the card
globe_center = 604.5
icon_y = round(globe_center - (phone_icon_rows[1] - phone_icon_rows[0]) / 2)

ELEMENTS = [
    # name, zone y0, y1, scale-centre y, old layer, new layer
    ("badge", 74, 256, 164.8, zone_copy(card_ref, 74, 256), zone_copy(badge_new_card, 74, 256)),
    ("phone1", 478, 552, 514.5, zone_copy(card_ref, 478, 552),
     text_layer(flat, [PHONES[0]], F_NUM, 38, [514.5])),
    ("icon2", 560, 652, globe_center, zone_copy(card_ref, 560, 652),
     zone_copy(card_ref, *phone_icon_rows, dst_y=icon_y)),
    ("phone2", 652, 724, 685.5, zone_copy(card_ref, 652, 724),
     text_layer(flat, [PHONES[1]], F_NUM, 38, [685.5])),
    ("address", 846, 930, 889.5, zone_copy(card_ref, 846, 930),
     text_layer(flat, ADDRESS, F_ADDR, 20, [874.5, 903.5])),
]


def scaled(layer, y0, y1, cy, s, bg):
    """Scale `layer` about (360, cy) and return rows [y0, y1)."""
    M = np.float32([[s, 0, 360 * (1 - s)], [0, s, cy * (1 - s)]])
    out = cv2.warpAffine(layer, M, (W, H), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=bg.tolist())
    return out[y0:y1, CARD_X0:CARD_X1]


SCALES = np.round(np.arange(0.05, 1.501, 0.025), 3)


def fit_card(frame, el):
    _, y0, y1, cy, old, _ = el
    fz = frame[y0:y1, CARD_X0:CARD_X1].astype(np.float32) - CARD_BG
    if np.abs(fz).max() < 25:
        return 0.0, 1.0
    best = (np.inf, 0.0, 1.0)
    for s in SCALES:
        t = scaled(old, y0, y1, cy, s, CARD_BG) - CARD_BG
        den = (t * t).sum()
        if den < 1:
            continue
        a = float(np.clip((fz * t).sum() / den, 0, 1))
        err = ((fz - a * t) ** 2).sum()
        if err < best[0]:
            best = (err, a, s)
    return best[1], best[2]


# ------------------------------------------------------------- map badge
badge_new_map, map_mask = badge_layer(frames[MAP_REF], MAP_DISC)
ys, xs = np.where(map_mask)
by0, by1, bx0, bx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
old_map = frames[MAP_REF][by0:by1, bx0:bx1].astype(np.float32)
new_map = badge_new_map[by0:by1, bx0:bx1]
mm = map_mask[by0:by1, bx0:bx1][..., None].astype(np.float32)
mm_soft = cv2.GaussianBlur(cv2.dilate(mm, np.ones((9, 9))), (0, 0), 3)[..., None]
BG_IN, BG_OUT = frames[0].astype(np.float32), frames[362].astype(np.float32)


def blur(x, s):
    return x if s == 0 else cv2.GaussianBlur(x, (0, 0), s)


def fit_map(i):
    f = frames[i][by0:by1, bx0:bx1].astype(np.float32)
    bg = (BG_IN if i < 200 else BG_OUT)[by0:by1, bx0:bx1]
    fz = (f - bg) * mm_soft
    best = (np.inf, 0.0, 0)
    for s in (0, 1, 2, 3, 4, 6, 8, 11):
        t = (blur(old_map * mm, s) + bg * (1 - blur(mm, s)[..., None]) - bg) * mm_soft
        den = (t * t).sum()
        a = float(np.clip((fz * t).sum() / den, 0, 1))
        err = ((fz - a * t) ** 2).sum()
        if err < best[0]:
            best = (err, a, s)
    return best[1], best[2]


# ---------------------------------------------------------------- render
enc = subprocess.Popen([
    "ffmpeg", "-loglevel", "error", "-y",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow",
    "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)

log = []
for i, fr in enumerate(frames):
    out = fr.astype(np.float32)
    if i < MAP_END:
        if 16 <= i <= 342:
            a, s = 1.0, 0
        else:
            a, s = fit_map(i)
        if a > 0.01:
            delta = blur(new_map * mm, s) - blur(old_map * mm, s)
            out[by0:by1, bx0:bx1] += a * delta * mm_soft
        log.append((i, "map", round(a, 2), s))
    elif CARD_START <= i < CARD_END:
        for el in ELEMENTS:
            name, y0, y1, cy, old, new = el
            a, s = (1.0, 1.0) if i == CARD_REF else fit_card(fr, el)
            # the card is flat blue, so clear the row and draw the new element
            # with the original's scale and opacity
            a = 1.0 if a > 0.85 else a
            z = np.empty((y1 - y0, CARD_X1 - CARD_X0, 3), np.float32)
            z[:] = CARD_BG
            if a > 0.01:
                z += a * (scaled(new, y0, y1, cy, s, CARD_BG) - CARD_BG)
            out[y0:y1, CARD_X0:CARD_X1] = z
            # repaint the static card border/margins next to the row so the
            # old text's overshoot never peeks out at the edges
            for c0, c1 in ((66, CARD_X0), (CARD_X1, 654)):
                out[y0:y1, c0:c1] = card_ref[y0:y1, c0:c1]
            log.append((i, name, round(a, 2), float(s)))
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())

enc.stdin.close()
enc.wait()
with open(OUT + ".fitlog.txt", "w") as fh:
    for row in log:
        fh.write(" ".join(map(str, row)) + "\n")
print("frames", len(frames))
