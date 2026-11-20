"""Final compositor for the Italy promo (v2).

Per output frame:
  1. source frame through the edit list, from the AI-upscaled (Real-ESRGAN) intermediate,
     re-framed with smooth zooms (area-filtered downscale - no upsampling, no pixelation);
  2. grade: clean white balance, bright filmic tone curve (never crushed), vibrance with skin
     protection, gentle split-tone, clarity + fine sharpening, light vignette;
  3. subtle depth of field: wall softly defocused behind the speaker (person matte);
  4. kinetic typography composited BEHIND the speaker (matte occlusion);
  5. zoom-blur on emphasis punch-in cuts;
  6. front graphics, captions and end card on top.

Usage: python3 render_final.py <sr.mp4|source.mov> <matte.mkv> <back.mkv> <front.mkv> <audio.wav> <out.mp4>
       python3 render_final.py --still t <sr|source> <matte> <back.png> <front.png> <out.png>
"""
import json
import subprocess
import sys

import cv2
import numpy as np

E = json.load(open("edit.json"))
W, H, FPS = 1080, 1920, 30
SW, SH = 512, 910
FACE_SRC = (225, 400)
EDL = E["edl"]


def out_to_src(t):
    acc = 0.0
    for a, b in EDL:
        if t < acc + (b - a):
            return a + (t - acc)
        acc += b - a
    return EDL[-1][1]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def zoom_at(t):
    shots = E["shots"]
    for k, s in enumerate(shots):
        if s["t0"] <= t < s["t1"] or k == len(shots) - 1:
            prog = min((t - s["t0"]) / max(s["t1"] - s["t0"], 1e-3), 1)
            z = s["zoom"] * (1 + 0.03 * ease(prog))
            if s["trans"] == "ease" and k > 0:
                prev = shots[k - 1]["zoom"] * 1.03
                z = prev + (z - prev) * ease((t - s["t0"]) / 0.8)
            return z
    return 1.0


def crop_rect(z, fw, fh):
    """Crop (x0, y0, cw, ch) in a frame of size fw x fh for zoom z (face kept well placed)."""
    s = fw / SW                              # source px -> frame px
    base = W / fw                            # frame px -> output px at z = 1
    fx, fy = FACE_SRC[0] * s, FACE_SRC[1] * s
    k = ease((z - 1.0) / 0.22)
    sx = (FACE_SRC[0] * W / SW) * (1 - k) + 540 * k     # desired screen x of face
    sy = (FACE_SRC[1] * W / SW) * (1 - k) + 806 * k
    cw, ch = fw / z, fh / z
    x0 = min(max(fx - sx / (base * z), 0), fw - cw)
    y0 = min(max(fy - sy / (base * z), 0), fh - ch)
    return x0, y0, cw, ch


def reframe(img, z, interp_down=cv2.INTER_AREA):
    fh, fw = img.shape[:2]
    x0, y0, cw, ch = crop_rect(z, fw, fh)
    scale = W / cw
    # pre-scale the whole frame with the right filter, then a sub-pixel translate (smooth, alias-free)
    sw, sh = int(round(fw * scale)), int(round(fh * scale))
    pre = cv2.resize(img, (sw, sh), interpolation=interp_down if scale < 1 else cv2.INTER_LANCZOS4)
    M = np.float32([[sw / fw * fw / sw, 0, -x0 * sw / fw], [0, sh / fh * fh / sh, -y0 * sh / fh]])
    return cv2.warpAffine(pre, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ grade
def tone_lut():
    pts = np.array([[0, .018], [.10, .085], [.30, .30], [.50, .54], [.72, .79], [.90, .94], [1.0, .985]])
    x = np.linspace(0, 1, 1024)
    return np.interp(x, pts[:, 0], pts[:, 1]).astype(np.float32)


TONE = tone_lut()
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - 0.07 * np.clip(((xx - W / 2) / (W * .7)) ** 2 + ((yy - H * .45) / (H * .62)) ** 2, 0, 1.5))[..., None]


def grade(bgr):
    f = bgr.astype(np.float32) / 255
    f = f * np.array([1.03, 1.0, 0.975], np.float32) * 1.05                  # WB (B,G,R) + exposure
    f = TONE[np.clip((f * 1023).astype(np.int32), 0, 1023)]                    # filmic curve
    lum = (0.114 * f[..., 0] + 0.587 * f[..., 1] + 0.299 * f[..., 2])[..., None]
    # vibrance (protect skin hues)
    hsv = cv2.cvtColor(np.clip(f, 0, 1), cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0], hsv[..., 1]
    skin = np.clip(1 - np.abs(h - 25) / 22, 0, 1)
    hsv[..., 1] = np.clip(s + 0.16 * (1 - s) * s * 2.2 * (1 - 0.6 * skin), 0, 1)
    f = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    # split tone: cool shadows, warm highlights (subtle)
    f = f + np.concatenate([0.025 * (1 - lum) ** 2, 0.006 * (1 - lum) ** 2, -0.004 * (1 - lum) ** 2], -1)
    f = f + np.concatenate([-0.012 * lum ** 2, 0.0 * lum, 0.014 * lum ** 2], -1)
    # clarity (local contrast) + fine sharpening
    f = f + 0.22 * (f - cv2.GaussianBlur(f, (0, 0), 14))
    f = f + 0.32 * (f - cv2.GaussianBlur(f, (0, 0), 0.9))
    return np.clip(f * VIGN, 0, 1)


def zoom_blur(f, amount):
    """Radial zoom blur centred on the face area."""
    acc = f.copy()
    n = 6
    for k in range(1, n + 1):
        s = 1 + amount * k / n
        M = cv2.getRotationMatrix2D((540, 760), 0, s)
        acc += cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / (n + 1)


# ------------------------------------------------------------------ readers
class SeqReader:
    """Sequential frame reader with forward seeking (the edit list only moves forward).

    A path of the form "first.h264|N|rest.mp4" reads frames 0..N-1 from the first file and
    N.. from the second (a resumed upscale pass)."""

    def __new__(cls, path):
        if "|" in path:
            return _SplitReader(path)
        return super().__new__(cls)

    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.idx = -1
        self.frame = None

    def get(self, i):
        if i < self.idx:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            self.idx = i - 1
        while self.idx < i:
            ok, f = self.cap.read()
            if not ok:
                break
            self.frame = f
            self.idx += 1
        return self.frame


class _SplitReader:
    def __init__(self, path):
        a, n, b = path.split("|")
        self.n = int(n)
        self.a, self.b = SeqReader(a), SeqReader(b)

    def get(self, i):
        return self.a.get(i) if i < self.n else self.b.get(i - self.n)


def rgba_pipe(path):
    return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgra", "-"],
                            stdout=subprocess.PIPE)


def read_rgba(p):
    buf = p.stdout.read(W * H * 4)
    if len(buf) < W * H * 4:
        return None
    return np.frombuffer(buf, np.uint8).reshape(H, W, 4)


def compose(t, src, matte, back, front):
    tv = min(t, E["video_len"] - 1 / FPS)
    z = zoom_at(tv)
    img = reframe(src, z)
    m = reframe(cv2.cvtColor(matte, cv2.COLOR_GRAY2BGR), z, cv2.INTER_AREA)[..., :1].astype(np.float32) / 255
    m = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None]
    f = grade(img)
    # depth: soften the wall behind the speaker a touch
    bg = cv2.GaussianBlur(f, (0, 0), 2.2 * z)
    f = f * m + bg * (1 - m)
    # typography behind the speaker
    if back is not None:
        a = back[..., 3:4].astype(np.float32) / 255 * (1 - m)
        f = f * (1 - a) + back[..., :3].astype(np.float32) / 255 * a
    # zoom-blur punch on emphasis cuts
    for pt in E["punch"]:
        d = t - pt
        if 0 <= d < 0.13:
            f = zoom_blur(f, 0.06 * (1 - d / 0.13))
    # behind the end card the footage keeps moving, softly blurred
    if t >= E["video_len"]:
        k = ease((t - E["video_len"]) / 0.8)
        f = cv2.GaussianBlur(f, (0, 0), 1 + 20 * k)
    if front is not None:
        a = front[..., 3:4].astype(np.float32) / 255
        f = f * (1 - a) + front[..., :3].astype(np.float32) / 255 * a
    return np.clip(f * 255 + 0.5, 0, 255).astype(np.uint8)


def src_index(t):
    return int(round(out_to_src(min(t, E["video_len"] - 1 / FPS)) * FPS))


if sys.argv[1] == "--still":
    t = float(sys.argv[2])
    S, MT, BK, FR, OUT = sys.argv[3:8]
    src = SeqReader(S).get(src_index(t))
    if src.shape[1] == SW:                                    # preview without the SR pass
        src = cv2.resize(src, (1620, 2880), interpolation=cv2.INTER_LANCZOS4)
    mt = cv2.cvtColor(SeqReader(MT).get(src_index(t)), cv2.COLOR_BGR2GRAY)
    back = cv2.imread(BK, cv2.IMREAD_UNCHANGED)
    front = cv2.imread(FR, cv2.IMREAD_UNCHANGED)
    if front.shape[2] == 3:                                   # fully opaque layer (end card)
        front = np.dstack([front, np.full(front.shape[:2], 255, np.uint8)])
    cv2.imwrite(OUT, compose(t, src, mt, back, front))
    sys.exit()

S, MT, BK, FR, AUD, OUT = sys.argv[1:7]
srcR, mtR = SeqReader(S), SeqReader(MT)
pb, pf = rgba_pipe(BK), rgba_pipe(FR)
N = int(round(E["duration"] * FPS))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", AUD, "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", f"{E['duration']:.3f}", OUT],
                       stdin=subprocess.PIPE)
for i in range(N):
    t = i / FPS
    si = src_index(t)
    src = srcR.get(si)
    mt = cv2.cvtColor(mtR.get(si), cv2.COLOR_BGR2GRAY)
    frame = compose(t, src, mt, read_rgba(pb), read_rgba(pf))
    enc.stdin.write(frame.tobytes())
    if i % 150 == 0:
        print("final frame", i, "/", N, flush=True)
enc.stdin.close()
enc.wait()
print("done", OUT)
