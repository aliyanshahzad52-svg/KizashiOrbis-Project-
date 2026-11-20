"""Person matte for every source frame (MODNet portrait matting, ONNX, CPU).

Used to place large background typography *behind* the speaker. The matte is lightly
smoothed over time (no edge flicker) and stored as a lossless grey video (FFV1).

Usage: python3 matte_pass.py <source.mov> <modnet.onnx> <out.mkv>
"""
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

SRC, MODEL, OUT = sys.argv[1:4]
so = ort.SessionOptions()
so.intra_op_num_threads = 2
sess = ort.InferenceSession(MODEL, so, providers=["CPUExecutionProvider"])

cap = cv2.VideoCapture(SRC)
W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                        "-r", "30", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", OUT], stdin=subprocess.PIPE)
prev = None
i = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    x = cv2.resize(f, (512, 896), interpolation=cv2.INTER_AREA)[:, :, ::-1].astype(np.float32) / 255
    m = sess.run(None, {"input": ((x - 0.5) / 0.5).transpose(2, 0, 1)[None]})[0][0, 0]
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_CUBIC)
    m = np.clip(m, 0, 1)
    if prev is not None:                       # temporal smoothing, but follow fast motion
        diff = np.abs(m - prev)
        k = np.clip(diff * 4, 0.45, 1.0)
        m = prev + (m - prev) * k
    prev = m
    enc.stdin.write((m * 255).astype(np.uint8).tobytes())
    i += 1
    if i % 200 == 0:
        print("matte", i, flush=True)
enc.stdin.close()
enc.wait()
print("done", OUT, i)
