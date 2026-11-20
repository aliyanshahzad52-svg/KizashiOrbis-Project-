"""Rebrand the reference UK reel with OrbisNexa branding.

Keeps every original shot, animation, text and the audio. Only changes:
  * Top-right partner watermark -> OrbisNexa watermark (white, same style).
  * Purple end section recoloured to OrbisNexa blue.
  * Final logo card -> OrbisNexa logo + office address and phone numbers.

Usage: python3 rebrand_video.py <reference.mp4> <logo.jpg> <out.mp4>
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, LOGO, OUT = sys.argv[1:4]
W, H, FPS = 720, 1280, 30

# Frame ranges measured from the reference video (30 fps).
WM_START, WM_END = 58, 424       # watermark visible on the city footage
PURPLE_START = 424               # "EXPLORE UK!" section begins
REVEAL_START = 547               # end logo starts to appear

# "September 2026" -> "September 2027": the "6" glyph position (Poppins Bold 35px)
YEAR_6_BOX = (650, 570, 676, 606)     # x0, y0, x1, y1 around the original "6"
YEAR_2_BOX = (628, 572, 650, 604)     # the "2" before it, used to read text opacity
YEAR_7_POS = (652, 575)               # top-left of the new "7"
FONT_POPPINS = __file__.rsplit("/", 1)[0] + "/fonts/Poppins-Bold.ttf"

ADDRESS = ["Iqbal, 8 Allama,", "Raza Block Town, Lahore, Pakistan"]
PHONES = ["+92 370 0035896", "+92 312 4222204"]
BLUE = (0, 102, 214)
NAVY = (12, 27, 61)

FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def white_logo(top, bottom):
    """Monochrome white version of the logo rows [top, bottom) with alpha."""
    im = cv2.imread(LOGO)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    alpha = np.clip((235 - gray) / 60, 0, 1)[top:bottom]
    cols = np.where(alpha.max(0) > 0.3)[0]
    alpha = alpha[:, cols.min() - 8: cols.max() + 9]
    rgba = np.zeros(alpha.shape + (4,), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def fit(img, max_w, max_h):
    s = min(max_w / img.width, max_h / img.height)
    return img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)


def with_shadow(img, blur=4, strength=0.35):
    pad = blur * 3
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel("A").point(lambda v: int(v * strength)))
    out.alpha_composite(sh, (pad, pad + 2))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(img, (pad, pad))
    return out


def pin_icon(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
    pr = r * 0.42
    py = cy - r * 0.12
    d.ellipse([cx - pr, py - pr, cx + pr, py + pr], fill="white")
    d.polygon([(cx - pr * 0.88, py + pr * 0.45), (cx + pr * 0.88, py + pr * 0.45),
               (cx, cy + r * 0.55)], fill="white")
    hr = pr * 0.42
    d.ellipse([cx - hr, py - hr, cx + hr, py + hr], fill=BLUE)


def phone_icon(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(r * 1.15))
    d.text((cx, cy + 1), "☎", font=f, fill="white", anchor="mm")


def contact_card():
    cw, ch = 640, 214
    card = Image.new("RGBA", (cw, ch))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=28, fill=(255, 255, 255, 245))
    f_addr = ImageFont.truetype(FONT_SEMI, 25)
    f_ph = ImageFont.truetype(FONT_BOLD, 30)
    pin_icon(d, 62, 56, 34)
    d.text((114, 24), ADDRESS[0], font=f_addr, fill=NAVY)
    d.text((114, 56), ADDRESS[1], font=f_addr, fill=NAVY)
    d.line([(36, 107), (cw - 36, 107)], fill=(200, 210, 228), width=2)
    phone_icon(d, 62, 160, 34)
    d.text((114, 124), PHONES[0], font=f_ph, fill=NAVY)
    d.text((114, 162), PHONES[1], font=f_ph, fill=NAVY)
    return with_shadow(card, blur=10, strength=0.45)


# --- assets -----------------------------------------------------------------
wm_logo = with_shadow(fit(white_logo(150, 945), 150, 150), blur=3, strength=0.3)
wm_pos = (623 - wm_logo.width // 2, 110 - wm_logo.height // 2)

end_logo = fit(white_logo(150, 1075), 440, 470)
end_logo_c = (360, 360 + end_logo.height // 2 - 10)
card = contact_card()
card_pos = (360 - card.width // 2, 905)


def composite(frame_bgr, overlay, pos, alpha=1.0):
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    ov = overlay
    if alpha < 1:
        ov = overlay.copy()
        ov.putalpha(overlay.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(ov, (int(pos[0]), int(pos[1])))
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def recolor_blue(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s = hsv[..., 0], hsv[..., 1]
    w = np.clip(1 - np.abs(h - 138) / 22, 0, 1) * np.clip((s - 40) / 40, 0, 1)
    hsv[..., 0] = h - 34 * w
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def _seven():
    f = ImageFont.truetype(FONT_POPPINS, 35)
    c = Image.new("L", (60, 60))
    ImageDraw.Draw(c).text((10, 0), "7", font=f, fill=255)
    a = np.array(c, np.float32) / 255
    ys, xs = np.where(a > 0)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


SEVEN = _seven()


def patch_year(fr):
    """Replace the final '6' of 2026 with a '7', matching the text's current opacity."""
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    x0, y0, x1, y1 = YEAR_6_BOX
    bg = float(np.median(np.concatenate([g[y0:y1, x0 - 2], g[y0:y1, x1 + 2], g[y0 - 3, x0:x1]])))
    bx0, by0, bx1, by1 = YEAR_2_BOX
    peak = float(np.percentile(g[by0:by1, bx0:bx1], 98))
    a = np.clip((peak - bg) / max(250 - bg, 1), 0, 1)
    if a < 0.03:
        return fr
    # erase the "6": the background there is a smooth gradient, so rebuild it
    # by blending the clean rows just above and below the glyph
    top = fr[y0 - 1, x0:x1].astype(np.float32)
    bot = fr[y1, x0:x1].astype(np.float32)
    k = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
    fr[y0:y1, x0:x1] = (top[None] * (1 - k) + bot[None] * k).astype(np.uint8)
    x, y = YEAR_7_POS
    h, w = SEVEN.shape
    al = (SEVEN * a)[..., None]
    roi = fr[y:y + h, x:x + w].astype(np.float32)
    fr[y:y + h, x:x + w] = (roi * (1 - al) + 255 * al).astype(np.uint8)
    return fr


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


cap = cv2.VideoCapture(SRC)
wm_mask = None
enc = subprocess.Popen([
    "ffmpeg", "-loglevel", "error", "-y",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow",
    "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)

i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    if WM_START <= i < WM_END:
        if wm_mask is None:
            # build the watermark mask from a frame on plain blue sky (t = 8 s)
            cap2 = cv2.VideoCapture(SRC)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, 240)
            _, r = cap2.read()
            hsv = cv2.cvtColor(r, cv2.COLOR_BGR2HSV)
            m = ((hsv[..., 1] < 60) & (hsv[..., 2] > 215)).astype(np.uint8) * 255
            m[:, :540] = 0
            m[200:, :] = 0
            wm_mask = cv2.dilate(m, np.ones((7, 7), np.uint8))
        fr = cv2.inpaint(fr, wm_mask, 6, cv2.INPAINT_TELEA)
        fr = composite(fr, wm_logo, wm_pos)
    if i >= PURPLE_START:
        if i >= REVEAL_START - 3:
            # remove the old end logo (any light, desaturated pixels in its box)
            hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
            m = np.zeros(fr.shape[:2], np.uint8)
            box = (hsv[370:910, 160:560, 1] < 225) & (hsv[370:910, 160:560, 2] > 60)
            m[370:910, 160:560] = box.astype(np.uint8) * 255
            m = cv2.dilate(m, np.ones((11, 11), np.uint8))
            small = cv2.resize(fr, (W // 2, H // 2))
            ms = cv2.resize(m, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
            filled = cv2.resize(cv2.inpaint(small, ms, 9, cv2.INPAINT_TELEA), (W, H))
            fr = np.where(m[..., None] > 0, filled, fr)
        if i < REVEAL_START - 30:
            fr = patch_year(fr)
        fr = recolor_blue(fr)
        if i >= REVEAL_START:
            t = (i - REVEAL_START) / FPS
            # same reveal as the reference: right-to-left wipe, then fade up
            wipe = ease(t / 0.45)
            lg = end_logo.copy()
            a = np.array(lg.getchannel("A"), np.float32)
            xs = np.arange(lg.width, dtype=np.float32) / lg.width
            edge = 1 - wipe * 1.15
            a *= np.clip((xs - edge) / 0.15, 0, 1)[None, :]
            lg.putalpha(Image.fromarray(a.astype(np.uint8)))
            op = 0.35 + 0.65 * ease(t / 1.1)
            fr = composite(fr, lg, (end_logo_c[0] - lg.width / 2, end_logo_c[1] - lg.height / 2), op)
            q = ease((t - 1.1) / 0.5)
            if q > 0:
                fr = composite(fr, card, (card_pos[0], card_pos[1] + 30 * (1 - q)), q)
    enc.stdin.write(fr.tobytes())
    i += 1

enc.stdin.close()
enc.wait()
print("frames", i)
