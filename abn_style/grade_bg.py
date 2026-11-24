"""Upscale the generated backgrounds (Real-ESRGAN x4) and grade them in OrbisNexa duotones.

Usage: python3 grade_bg.py <realesrgan.onnx> <out_dir> booth=<png> library=<png> college=<png> gate=<png>
Writes booth_grey / booth_duo / library_duo / college_duo / gate_duo .jpg at 1296x2304 (room for slow push-ins).
"""
import sys

import cv2
import numpy as np
import onnxruntime as ort

SRM, OUT = sys.argv[1:3]
SRC = dict(a.split("=", 1) for a in sys.argv[3:])
OW, OH = 1296, 2304
so = ort.SessionOptions()
so.intra_op_num_threads = 4
sr = ort.InferenceSession(SRM, so, providers=["CPUExecutionProvider"])
IN = sr.get_inputs()[0].name
T, O = 128, 10
ST = T - 2 * O
ramp = np.ones(T * 4, np.float32)
r = np.linspace(0.02, 1, O * 8)
ramp[:len(r)] = r
ramp[-len(r):] = r[::-1]
WT = (ramp[:, None] * ramp[None, :])[..., None]


def upscale(f):
    h, w = f.shape[:2]
    ys = list(range(0, h - T, ST)) + [h - T]
    xs = list(range(0, w - T, ST)) + [w - T]
    img = f[:, :, ::-1].astype(np.float32) / 255
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    ws = np.zeros((h * 4, w * 4, 1), np.float32)
    for y in ys:
        for x in xs:
            o = sr.run(None, {IN: np.ascontiguousarray(img[y:y + T, x:x + T].transpose(2, 0, 1)[None])})[0][0].transpose(1, 2, 0)
            out[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += o * WT
            ws[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += WT
    up = np.clip(out / ws, 0, 1)[:, :, ::-1]
    # cover-crop to 9:16 then size
    hh, ww = up.shape[:2]
    tw = int(hh * 9 / 16)
    if tw <= ww:
        x0 = (ww - tw) // 2
        up = up[:, x0:x0 + tw]
    else:
        th = int(ww * 16 / 9)
        y0 = (hh - th) // 2
        up = up[y0:y0 + th]
    return cv2.resize(up, (OW, OH), interpolation=cv2.INTER_AREA)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32) / 255     # BGR


def gradient_map(f, stops, contrast=1.0, gamma=1.0):
    lum = 0.114 * f[..., 0] + 0.587 * f[..., 1] + 0.299 * f[..., 2]
    lum = np.clip((lum - 0.5) * contrast + 0.5, 0, 1) ** gamma
    xs = np.array([s[0] for s in stops])
    cols = np.stack([hexc(s[1]) for s in stops])
    out = np.stack([np.interp(lum, xs, cols[:, c]) for c in range(3)], -1)
    return out


def clarity(f, a=0.25):
    return np.clip(f + a * (f - cv2.GaussianBlur(f, (0, 0), 18)), 0, 1)


def save(name, f):
    cv2.imwrite(f"{OUT}/{name}.jpg", np.clip(f * 255 + 0.5, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 94])
    print("wrote", name, flush=True)


import os
os.makedirs(OUT, exist_ok=True)
for name, path in SRC.items():
    f = clarity(upscale(cv2.imread(path)))
    if name == "booth":
        # faded, airy street for the white-background title shots
        save("booth_grey", gradient_map(f, [(0, "#9aa3b4"), (0.5, "#d5dae3"), (1, "#f4f6fa")], 0.9))
        save("booth_duo", gradient_map(f, [(0, "#040d26"), (0.35, "#0a2a66"), (0.7, "#1f7ae8"), (1, "#bfe2ff")], 1.1))
    elif name == "library":
        save("library_duo", gradient_map(f, [(0, "#071331"), (0.45, "#3b4f78"), (0.8, "#aab8d2"), (1, "#eef3fb")], 1.05))
    elif name == "college":
        save("college_duo", gradient_map(f, [(0, "#050f2b"), (0.4, "#0b3c8f"), (0.75, "#2f86ee"), (1, "#cfe8ff")], 1.1))
    elif name in ("book", "grad", "tablet", "meeting"):
        # crisp black & white (the IELTS reel), slightly lifted blacks
        save(f"ielts_{name}", gradient_map(f, [(0, "#121417"), (0.5, "#7d8189"), (1, "#f3f4f6")], 1.12))
    elif name == "gate":
        save("gate_duo", gradient_map(f, [(0, "#081433"), (0.5, "#40527a"), (0.85, "#b3c1da"), (1, "#eef2f9")], 1.05))
