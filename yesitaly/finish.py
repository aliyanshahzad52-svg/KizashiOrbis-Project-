"""Join the re-branded footage and the OrbisNexa closing screen; extend the original music under it.

Usage: python3 finish.py <reference.mp4> <main.mkv> <end.mkv> <out.mp4>
"""
import subprocess
import sys
import tempfile
import wave

import cv2
import numpy as np

REF, MAIN, END, OUT = sys.argv[1:5]
W, H, FPS = 1080, 1920, 30
XF = 14                                   # frames of blur-dissolve into the closing screen
tmp = tempfile.mkdtemp()

# ------------------------------------------------------------------ audio: continue the music musically
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", REF, "-vn", "-ac", "2", "-ar", "48000", f"{tmp}/a.wav"], check=True)
w = wave.open(f"{tmp}/a.wav")
SR = w.getframerate()
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
n_main = int(cv2.VideoCapture(MAIN).get(cv2.CAP_PROP_FRAME_COUNT))
n_end = int(cv2.VideoCapture(END).get(cv2.CAP_PROP_FRAME_COUNT))
total = (n_main + n_end) / FPS
L = len(a)
# find the earlier point whose last second best matches the last second of the track (same place in the loop)
win = SR
tail = a[L - win:, 0]
best, best_c = None, -1
env = lambda x: np.abs(x)
for s in range(int(4 * SR), L - win - int(4.6 * SR), int(SR * 0.005)):
    seg = a[s:s + win, 0]
    c = float(np.dot(seg, tail) / (np.linalg.norm(seg) * np.linalg.norm(tail) + 1e-9))
    if c > best_c:
        best, best_c = s, c
cont = a[best + win:]
need = int(total * SR) - L
cont = cont[:need]
xf = int(0.04 * SR)
ramp = np.linspace(0, 1, xf)[:, None]
out = np.concatenate([a, cont])
out[L:L + xf] = a[L - xf:] * 0 + cont[:xf]                        # continuation already lines up in phase
out = out[:int(total * SR)]
fade = int(1.6 * SR)
out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
print(f"music continues from {best / SR:.2f}s (match {best_c:.2f})")
wo = wave.open(f"{tmp}/music.wav", "wb"); wo.setnchannels(2); wo.setsampwidth(2); wo.setframerate(SR)
wo.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes()); wo.close()

# ------------------------------------------------------------------ video
def frames(path):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            return
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", f"{tmp}/music.wav", "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
last = None
for f in frames(MAIN):
    enc.stdin.write(f.tobytes())
    last = f
lastf = last.astype(np.float32)
for k, e in enumerate(frames(END)):
    if k < XF:
        x = (k + 1) / XF
        x = x * x * (3 - 2 * x)
        bl = cv2.GaussianBlur(lastf, (0, 0), 1 + 26 * x)
        bl = bl * (1 + 0.25 * x)                                 # brighten as it dissolves to the light card
        f = bl * (1 - x) + e.astype(np.float32) * x
        e = np.clip(f, 0, 255).astype(np.uint8)
    enc.stdin.write(e.tobytes())
enc.stdin.close()
enc.wait()
print("done", OUT, f"{total:.2f}s")
