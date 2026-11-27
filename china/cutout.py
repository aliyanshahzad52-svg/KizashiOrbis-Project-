"""Upscale the generated graduate portrait (Real-ESRGAN x4) and cut him out (MODNet matte + white-bg key).
Usage: python3 cutout.py <portrait.png> <modnet.onnx> <realesrgan.onnx> <out.png>"""
import sys
import cv2
import numpy as np
import onnxruntime as ort

SRC, MOD, SR, OUT = sys.argv[1:5]
im = cv2.imread(SRC)
h, w = im.shape[:2]
# matte
mod = ort.InferenceSession(MOD, providers=["CPUExecutionProvider"])
x = cv2.resize(im, (512, 896), interpolation=cv2.INTER_AREA)[:, :, ::-1].astype(np.float32) / 255
m = mod.run(None, {"input": ((x - .5) / .5).transpose(2, 0, 1)[None]})[0][0, 0]
m = np.clip(cv2.resize(m, (w, h), interpolation=cv2.INTER_CUBIC), 0, 1)
# background is near-white: anything clearly not white is foreground too (cap edges, tassel)
f = im.astype(np.float32) / 255
notwhite = np.clip((0.93 - f.min(2)) / 0.12, 0, 1)
m = np.maximum(m, notwhite * (cv2.GaussianBlur(m, (0, 0), 25) > 0.05))
m = cv2.GaussianBlur(m, (0, 0), 0.8)
# upscale x4 with tiles
sr = ort.InferenceSession(SR, providers=["CPUExecutionProvider"]); IN = sr.get_inputs()[0].name
T, O = 128, 10; ST = T - 2 * O
r = np.linspace(0.02, 1, O * 8); ramp = np.ones(T * 4, np.float32); ramp[:len(r)] = r; ramp[-len(r):] = r[::-1]
WT = (ramp[:, None] * ramp[None, :])[..., None]
img = f[:, :, ::-1]
ys = list(range(0, h - T, ST)) + [h - T]; xs = list(range(0, w - T, ST)) + [w - T]
out = np.zeros((h * 4, w * 4, 3), np.float32); ws = np.zeros((h * 4, w * 4, 1), np.float32)
for y in ys:
    for xx in xs:
        o = sr.run(None, {IN: np.ascontiguousarray(img[y:y + T, xx:xx + T].transpose(2, 0, 1)[None])})[0][0].transpose(1, 2, 0)
        out[y * 4:(y + T) * 4, xx * 4:(xx + T) * 4] += o * WT; ws[y * 4:(y + T) * 4, xx * 4:(xx + T) * 4] += WT
up = np.clip(out / ws, 0, 1)[:, :, ::-1]
up = cv2.resize(up, (w * 2, h * 2), interpolation=cv2.INTER_AREA)
mu = cv2.resize(m, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
# soft, slightly warm-neutral grade (lighter, gentle)
up = np.clip(up * 1.03 + 0.015, 0, 1)
rgba = np.dstack([(up * 255 + .5).astype(np.uint8), (np.clip(mu, 0, 1) * 255).astype(np.uint8)])
cv2.imwrite(OUT, rgba)
print("wrote", OUT, rgba.shape)
