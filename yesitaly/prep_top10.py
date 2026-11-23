"""Footage prep for the 'Top 10 universities' reel (reference is 360x640).

  1. the reference's top-left logo is removed with LaMa inpainting (the wall behind it is plain);
  2. every frame is upscaled with Real-ESRGAN General x4v3 (75/25 blend with Lanczos for a natural look)
     and stored at 1080x1920.

Usage: python3 prep_top10.py <reference.mp4> <lama.onnx> <realesrgan.onnx> <seconds> <out.mkv>
"""
import subprocess
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

REF, LAMA, SRM, SECS, OUT = sys.argv[1:6]
W, H = 1080, 1920
so = ort.SessionOptions()
so.intra_op_num_threads = 4
lama = ort.InferenceSession(LAMA, so, providers=["CPUExecutionProvider"])
sr = ort.InferenceSession(SRM, so, providers=["CPUExecutionProvider"])
SR_IN = sr.get_inputs()[0].name

# logo box in reference coordinates (x0, y0, x1, y1) plus margin
LB = (10, 7, 100, 53)
C = 200                                     # inpaint crop (top-left C x C), run at 512


def remove_logo(f):
    crop = f[:C, :C]
    m = np.zeros((C, C), np.uint8)
    cv2.rectangle(m, LB[:2], LB[2:], 1, -1)
    x = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_CUBIC)
    mk = cv2.resize(m, (512, 512), interpolation=cv2.INTER_NEAREST)
    xi = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255
    o = lama.run(None, {"image": xi, "mask": mk.astype(np.float32)[None, None]})[0][0].transpose(1, 2, 0)
    o = cv2.cvtColor(np.clip(o, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    o = cv2.resize(o, (C, C), interpolation=cv2.INTER_AREA)
    soft = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)[..., None]
    f = f.copy()
    f[:C, :C] = (o * soft + crop * (1 - soft)).astype(np.uint8)
    return f


T, O = 128, 10
ST = T - 2 * O
ramp = np.ones(T * 4, np.float32)
r = np.linspace(0.02, 1, O * 4 * 2)
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
            tile = np.ascontiguousarray(img[y:y + T, x:x + T].transpose(2, 0, 1)[None])
            o = sr.run(None, {SR_IN: tile})[0][0].transpose(1, 2, 0)
            out[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += o * WT
            ws[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += WT
    up = np.clip(out / ws, 0, 1)[:, :, ::-1]
    up = cv2.resize(up, (W, H), interpolation=cv2.INTER_AREA)
    lz = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    return np.clip((0.75 * up + 0.25 * lz) * 255 + 0.5, 0, 255).astype(np.uint8)


if len(sys.argv) > 6:                      # --test frame: write a single preview png to OUT
    cap = cv2.VideoCapture(REF)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(sys.argv[6]))
    ok, f = cap.read()
    cv2.imwrite(OUT, upscale(remove_logo(f)))
    sys.exit()

cap = cv2.VideoCapture(REF)
n = int(round(float(SECS) * 30))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "30", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", OUT], stdin=subprocess.PIPE)
t0 = time.time()
for i in range(n):
    ok, f = cap.read()
    if not ok:
        break
    enc.stdin.write(upscale(remove_logo(f)).tobytes())
    if i % 20 == 0:
        print(f"frame {i}/{n}  {(time.time() - t0) / (i + 1):.2f}s/frame", flush=True)
enc.stdin.close()
enc.wait()
print("done prep", n)
