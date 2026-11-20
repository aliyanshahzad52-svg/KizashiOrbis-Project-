"""AI super-resolution pass (Real-ESRGAN General x4v3, ONNX, CPU) for the 512x910 source.

Every source frame is upscaled x4 in overlapping 128 px tiles (feathered seams), blended
75/25 with a Lanczos upscale to keep natural skin texture, then stored at 1620x2880
(enough for a 1.5x punch-in at 1080x1920 without any upsampling) as a near-lossless
intermediate.

Usage: python3 sr_pass.py <source.mov> <model.onnx> <out.mp4>
"""
import subprocess
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

SRC, MODEL, OUT = sys.argv[1:4]
OW, OH = 1620, 2880
T, O = 128, 10
ST = T - 2 * O

so = ort.SessionOptions()
so.intra_op_num_threads = 4
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
sess = ort.InferenceSession(MODEL, so, providers=["CPUExecutionProvider"])
IN = sess.get_inputs()[0].name

ramp = np.ones(T * 4, np.float32)
r = np.linspace(0.02, 1, O * 4 * 2)
ramp[:len(r)] = r
ramp[-len(r):] = r[::-1]
WT = (ramp[:, None] * ramp[None, :])[..., None]


def sr(frame_bgr):
    img = frame_bgr[:, :, ::-1].astype(np.float32) / 255
    h, w = img.shape[:2]
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    ws = np.zeros((h * 4, w * 4, 1), np.float32)
    ys = list(range(0, h - T, ST)) + [h - T]
    xs = list(range(0, w - T, ST)) + [w - T]
    for y in ys:
        for x in xs:
            tile = np.ascontiguousarray(img[y:y + T, x:x + T].transpose(2, 0, 1)[None])
            o = sess.run(None, {IN: tile})[0][0].transpose(1, 2, 0)
            out[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += o * WT
            ws[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += WT
    up = np.clip(out / ws, 0, 1)[:, :, ::-1]
    up = cv2.resize(up, (OW, OH), interpolation=cv2.INTER_AREA)
    lz = cv2.resize(frame_bgr, (OW, OH), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    return np.clip((0.75 * up + 0.25 * lz) * 255, 0, 255).astype(np.uint8)


cap = cv2.VideoCapture(SRC)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{OW}x{OH}", "-r", "30", "-i", "-", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "9", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
t0 = time.time()
i = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    enc.stdin.write(sr(f).tobytes())
    i += 1
    if i % 25 == 0:
        el = time.time() - t0
        print(f"sr frame {i}/{n}  {el / i:.2f}s/frame  eta {el / i * (n - i) / 60:.0f} min", flush=True)
enc.stdin.close()
enc.wait()
print("done", OUT, i, "frames")
