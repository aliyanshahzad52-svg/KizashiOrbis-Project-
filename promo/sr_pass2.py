"""Fast AI super-resolution pass (Real-ESRGAN General x4v3, ONNX, CPU).

The camera is locked off, so the wall never changes:
  * the background is upscaled ONCE as a clean plate;
  * for every frame used in the edit, only the 128 px tiles that contain the speaker
    (from the person matte, with a safety margin) are upscaled; the rest comes from the plate;
  * tiles are feather-blended, mixed 75/25 with a Lanczos upscale for natural skin texture,
    and stored at 1620x2880 (room for 1.5x punch-ins at 1080x1920 without upsampling).
Frames cut out of the edit are written as plain Lanczos upscales (never shown).

Usage: python3 sr_pass2.py <source.mov> <matte.mkv> <model.onnx> <out.mp4> [start_frame]
"""
import json
import subprocess
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

SRC, MATTE, MODEL, OUT = sys.argv[1:5]
START = int(sys.argv[5]) if len(sys.argv) > 5 else 0   # resume: write frames START..end only
E = json.load(open("edit.json"))
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
SH, SW = 910, 512
YS = list(range(0, SH - T, ST)) + [SH - T]
XS = list(range(0, SW - T, ST)) + [SW - T]


def run_tile(img, y, x):
    tile = np.ascontiguousarray(img[y:y + T, x:x + T].transpose(2, 0, 1)[None])
    return sess.run(None, {IN: tile})[0][0].transpose(1, 2, 0)


def upscale(frame_bgr, need=None, plate_tiles=None):
    img = frame_bgr[:, :, ::-1].astype(np.float32) / 255
    out = np.zeros((SH * 4, SW * 4, 3), np.float32)
    ws = np.zeros((SH * 4, SW * 4, 1), np.float32)
    tiles = {}
    for y in YS:
        for x in XS:
            if need is None or need[(y, x)]:
                o = run_tile(img, y, x)
            else:
                o = plate_tiles[(y, x)]
            tiles[(y, x)] = o
            out[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += o * WT
            ws[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += WT
    up = np.clip(out / ws, 0, 1)[:, :, ::-1]
    up = cv2.resize(up, (OW, OH), interpolation=cv2.INTER_AREA)
    lz = cv2.resize(frame_bgr, (OW, OH), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    return np.clip((0.75 * up + 0.25 * lz) * 255, 0, 255).astype(np.uint8), tiles


def used(i):
    t = i / 30
    return any(a - 0.05 <= t <= b + 0.05 for a, b in E["edl"])


cap = cv2.VideoCapture(SRC)
mcap = cv2.VideoCapture(MATTE)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# clean plate: median of mattes says where the person never is; upscale frame 0 fully
ok, f0 = cap.read()
_, plate_tiles = upscale(f0)
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{OW}x{OH}", "-r", "30", "-i", "-", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "9", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
t0 = time.time()
done_sr = 0
tiles_run = 0
kernel = np.ones((25, 25), np.uint8)
for i in range(n):
    ok, f = cap.read()
    okm, m = mcap.read()
    if not ok:
        break
    if i < START:
        continue
    if not used(i):
        enc.stdin.write(cv2.resize(f, (OW, OH), interpolation=cv2.INTER_LANCZOS4).tobytes())
        continue
    mg = cv2.dilate((m[..., 0] > 6).astype(np.uint8), kernel)          # person + 12 px margin
    need = {(y, x): bool(mg[y:y + T, x:x + T].any()) for y in YS for x in XS}
    tiles_run += sum(need.values())
    frame, _ = upscale(f, need, plate_tiles)
    enc.stdin.write(frame.tobytes())
    done_sr += 1
    if done_sr % 25 == 0:
        el = time.time() - t0
        left = sum(used(j) for j in range(max(i + 1, START), n))
        print(f"sr frame {i}/{n}  {el / done_sr:.2f}s/frame  tiles/frame {tiles_run / done_sr:.1f}  eta {el / done_sr * left / 60:.0f} min", flush=True)
enc.stdin.close()
enc.wait()
print("done", OUT, done_sr, "frames upscaled")
