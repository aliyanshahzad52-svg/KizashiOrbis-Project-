"""Natural beauty retouch on the graded plate (faces found with MediaPipe Face Landmarker, 478 points).

Per visible face, inside a feathered face mask (eyes, brows and lips excluded from skin work):
  * skin brightness: gentle mid-tone lift, a touch more under the eyes (tired shadows)
  * even tone: frequency separation - only the low-frequency blotches/redness are evened out,
    the high-frequency skin texture (pores, beard, stubble) is kept untouched
  * lips: slightly richer, healthy natural red (saturation + a hint of red), feathered edges
  * eyes: a little extra clarity
  * natural skin tone and hue are kept - faces are brightened and freshened, not whitened
Landmarks are smoothed over time inside each shot so masks never jitter.

Usage: python3 retouch.py <face_landmarker.task> <plate.mkv> <out.mkv>
       python3 retouch.py <face_landmarker.task> --still <in.png> <out.png>
"""
import json
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np

MODEL = sys.argv[1]
W, H = 1920, 1080
V = mp.tasks.vision
LM = V.FaceLandmarker.create_from_options(V.FaceLandmarkerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=MODEL), num_faces=3, running_mode=V.RunningMode.IMAGE,
    min_face_detection_confidence=0.25, min_face_presence_confidence=0.25))

OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149,
        150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LIP_O = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LIP_I = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
EYE_L = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_R = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
BROW_L = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
BROW_R = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]


def detect(img):
    """Landmarks (N x 478 x 2, pixels). Falls back to a crop when a face sits at the frame edge."""
    rgb = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    r = LM.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    faces = [np.array([[p.x * W, p.y * H] for p in f]) for f in r.face_landmarks]
    if not faces:
        x0 = 480
        sub = np.ascontiguousarray(rgb[:, x0:])
        r = LM.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=sub))
        faces = [np.array([[p.x * (W - x0) + x0, p.y * H] for p in f]) for f in r.face_landmarks]
    return faces


def poly(mask, pts, val=1.0):
    cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], val)


def retouch_face(img, P):
    x0, y0 = np.floor(P.min(0)).astype(int) - 40
    x1, y1 = np.ceil(P.max(0)).astype(int) + 40
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 - x0 < 40 or y1 - y0 < 40:
        return img
    Q = P - [x0, y0]
    roi = img[y0:y1, x0:x1].astype(np.float32) / 255
    h, w = roi.shape[:2]
    fw = Q[454, 0] - Q[234, 0]                                   # face width in px
    fw = max(fw, 40)
    feather = max(fw / 18, 2)

    face = np.zeros((h, w), np.float32); poly(face, Q[OVAL])
    holes = np.zeros((h, w), np.float32)
    for idx in (EYE_L, EYE_R, LIP_O):
        poly(holes, Q[idx])
    for idx in (BROW_L, BROW_R):
        c = Q[idx].mean(0); poly(holes, c + (Q[idx] - c) * 1.25)
    holes = cv2.dilate(holes, np.ones((3, 3), np.uint8))
    face = cv2.erode(face, np.ones((5, 5), np.uint8))
    skin = np.clip(cv2.GaussianBlur(face, (0, 0), feather) - cv2.GaussianBlur(holes, (0, 0), feather * 0.6), 0, 1)

    # under-eye: eye shapes moved down and widened
    ue = np.zeros((h, w), np.float32)
    for idx in (EYE_L, EYE_R):
        e = Q[idx]; c = e.mean(0); eh = e[:, 1].max() - e[:, 1].min() + 2
        poly(ue, c + (e - c) * [1.15, 1.6] + [0, eh * 1.7])
    ue = cv2.GaussianBlur(ue, (0, 0), feather * 1.2) * skin

    # 1. even tone, keep texture (frequency separation)
    s_lo = max(fw / 45, 1.5)
    low = cv2.GaussianBlur(roi, (0, 0), s_lo)
    high = roi - low
    even = cv2.bilateralFilter(low, d=0, sigmaColor=0.06, sigmaSpace=fw / 14)
    low2 = low + (even - low) * 0.55 * skin[..., None]
    out = low2 + high

    # 2. brightness: gentle mid-tone lift on skin, a bit more under the eyes
    lift = 1 + 0.07 * skin + 0.06 * ue
    out = 1 - (1 - np.clip(out, 0, 1)) ** lift[..., None]        # lifts mids, protects highlights

    # 3. lips: healthy natural red
    lips = np.zeros((h, w), np.float32); poly(lips, Q[LIP_O])
    inner = np.zeros((h, w), np.float32); poly(inner, Q[LIP_I])
    lips = cv2.GaussianBlur(np.clip(lips - inner, 0, 1), (0, 0), max(fw / 90, 1.2))
    hsv = cv2.cvtColor(np.clip(out, 0, 1), cv2.COLOR_BGR2HSV)
    hh = hsv[..., 0]
    shift = np.where(hh > 180, hh - 360, hh)                       # red/orange hues around 0
    hsv[..., 0] = np.mod(shift - 6 * lips, 360)                    # a hint toward red
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + 0.24 * lips), 0, 1)
    hsv[..., 2] = np.clip(hsv[..., 2] * (1 + 0.03 * lips), 0, 1)
    out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    # 4. eyes: a little clarity
    eyes = np.zeros((h, w), np.float32)
    for idx in (EYE_L, EYE_R):
        c = Q[idx].mean(0); poly(eyes, c + (Q[idx] - c) * 1.3)
    eyes = cv2.GaussianBlur(eyes, (0, 0), feather * 0.5)[..., None]
    out = out + 0.35 * eyes * (out - cv2.GaussianBlur(out, (0, 0), 1.2))

    res = img.copy()
    res[y0:y1, x0:x1] = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
    return res


def process(img, faces):
    for P in faces:
        img = retouch_face(img, P)
    return img


if sys.argv[2] == "--still":
    img = cv2.imread(sys.argv[3])
    faces = detect(img)
    print("faces", len(faces))
    cv2.imwrite(sys.argv[4], process(img, faces))
    sys.exit()

PLATE, OUT = sys.argv[2:4]
E = json.load(open("edit.json"))
FPS = E["fps"]
cuts = [s["t0"] for s in E["shots"]][1:]
src = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", PLATE, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "24000/1001", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", OUT], stdin=subprocess.PIPE)
prev, shot, i, nf = [], 0, 0, 0
while True:
    b = src.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    img = np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()
    t = i / FPS
    s = sum(t >= c for c in cuts)
    if s != shot:
        prev, shot = [], s
    faces = detect(img) if t < E["video"] + 0.6 else []
    # temporal smoothing: match each face to the nearest previous one
    sm = []
    for P in faces:
        if prev:
            d = [np.abs(P.mean(0) - Q.mean(0)).sum() for Q in prev]
            j = int(np.argmin(d))
            if d[j] < 120:
                P = prev[j] * 0.55 + P * 0.45
        sm.append(P)
    prev = sm
    nf += len(sm)
    if t < E["video"] + 0.6:
        img = process(img, sm)
    enc.stdin.write(img.tobytes())
    if i % 96 == 0:
        print("retouch", i, "faces/frame", round(nf / (i + 1), 2), flush=True)
    i += 1
enc.stdin.close(); enc.wait()
print("done retouch", i)
