"""Faithful OrbisNexa re-brand of the IELTS reference reel.

Every frame of the reference is kept (same footage, text, timing and transitions). Only the brand changes:
  * the red diagonal bands / red transition bars become OrbisNexa blue (#0b4fb3 family),
  * the yellow headline accent and yellow transition bars become OrbisNexa sky blue,
  * from the last cut onward the reference's end card is replaced by the OrbisNexa end card
    (ielts_end.html, rendered frame-matched), with the outgoing transition bars kept on top.
Frames are upscaled 720x1280 -> 1080x1920 (Lanczos + gentle sharpening).

Usage: python3 rebrand_ielts.py <reference.mp4> <end.mkv> <end_first_frame> <music.wav> <out.mp4>
"""
import subprocess
import sys

import cv2
import numpy as np

REF, END, E0, MUS, OUT = sys.argv[1:6]
E0 = int(E0)
W, H = 1080, 1920
BLUE_H, SKY_H = 108, 103                 # OpenCV hue (0-180): 216 deg brand blue, 206 deg sky


def remap(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.int16)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    col = s > 28
    red = col & ((h <= 9) | (h >= 160))
    yel = col & (h >= 14) & (h <= 40)
    org = col & (h > 9) & (h < 14)
    h = np.where(red, BLUE_H, h)
    h = np.where(yel, SKY_H, h)
    h = np.where(org, (BLUE_H + SKY_H) // 2, h)
    s = np.where(yel, (s * 0.52).astype(np.int16), s)                    # light sky accent: high contrast on blue
    v = np.where(yel, np.maximum(v, 252), v)
    v = np.where(red, (v * 0.92).astype(np.int16), v)                    # deeper, closer to OrbisNexa royal blue
    out = cv2.cvtColor(np.stack([h, s, v], -1).astype(np.uint8), cv2.COLOR_HSV2BGR)
    return out, red | yel | org


def up(f):
    g = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    g = g + 0.4 * (g - cv2.GaussianBlur(g, (0, 0), 1.1))
    return np.clip(g + 0.5, 0, 255).astype(np.uint8)


def reader(path):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            return
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-i", MUS, "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", OUT],
                       stdin=subprocess.PIPE)
cap = cv2.VideoCapture(REF)
ends = reader(END)
i = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    m, colored = remap(f)
    if i < E0:
        frame = up(m)
    elif i > E0 + 20:                      # transition bars are gone by then (reference frame 411, 13.71 s)
        frame = next(ends)
    else:
        card = next(ends)
        # keep the outgoing transition bars: full-width rows of brand colour (not the reference end-card art)
        rows = colored.mean(1) > 0.6                       # stripes run the full width; logo art never does
        bars = (colored & rows[:, None]).astype(np.float32)
        a = cv2.resize(bars, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        frame = np.clip(card * (1 - a) + up(m) * a + 0.5, 0, 255).astype(np.uint8)
    enc.stdin.write(frame.tobytes())
    i += 1
enc.stdin.close()
enc.wait()
print("done", i, "frames ->", OUT)
