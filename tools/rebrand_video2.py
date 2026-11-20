"""Rebrand the "Study in your Dream Destination" country-carousel reel.

Keeps every frame, animation, text and the audio. Only changes:
  * Partner logo under "Plan your future, choose" -> OrbisNexa logo.
  * Red background / glow recoloured to OrbisNexa blue.

Usage: python3 rebrand_video2.py <reference.mp4> <logo.jpg> <out.mp4>
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

SRC, LOGO, OUT = sys.argv[1:4]
W, H, FPS = 720, 1280, 30

OLD_LOGO_BOX = (286, 1044, 434, 1220)   # x0, y0, x1, y1 (sits on pure black)
LOGO_MAX_W, LOGO_MAX_H = 250, 168
LOGO_CENTER = (360, 1132)
TARGET_HUE = 106                        # OpenCV hue of OrbisNexa blue


def white_logo(top, bottom):
    im = cv2.imread(LOGO)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    alpha = np.clip((235 - gray) / 60, 0, 1)[top:bottom]
    cols = np.where(alpha.max(0) > 0.3)[0]
    alpha = alpha[:, cols.min() - 4: cols.max() + 5]
    rgba = np.zeros(alpha.shape + (4,), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    s = min(LOGO_MAX_W / img.width, LOGO_MAX_H / img.height)
    return img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)


logo = white_logo(150, 945)          # icon + "OrbisNexa" wordmark
logo_np = np.array(logo).astype(np.float32) / 255
lx = LOGO_CENTER[0] - logo.width // 2
ly = LOGO_CENTER[1] - logo.height // 2


def recolor_blue(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h = hsv[..., 0].astype(np.float32)
    s = hsv[..., 1].astype(np.float32)
    dist = np.minimum(h, 180 - h)
    w = np.clip(1 - (dist - 6) / 8, 0, 1) * np.clip((s - 110) / 60, 0, 1)
    shifted = hsv.copy()
    shifted[..., 0] = TARGET_HUE
    blue = cv2.cvtColor(shifted, cv2.COLOR_HSV2BGR).astype(np.float32)
    w = w[..., None]
    return (frame * (1 - w) + blue * w).astype(np.uint8)


cap = cv2.VideoCapture(SRC)
enc = subprocess.Popen([
    "ffmpeg", "-loglevel", "error", "-y",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow",
    "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)

n = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    fr = recolor_blue(fr)
    x0, y0, x1, y1 = OLD_LOGO_BOX
    fr[y0:y1, x0:x1] = 0
    roi = fr[ly:ly + logo.height, lx:lx + logo.width].astype(np.float32)
    a = logo_np[..., 3:4]
    fr[ly:ly + logo.height, lx:lx + logo.width] = (roi * (1 - a) + 255 * a).astype(np.uint8)
    enc.stdin.write(fr.tobytes())
    n += 1

enc.stdin.close()
enc.wait()
print("frames", n)
