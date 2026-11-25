"""Privacy redaction of the visa photos (for the OrbisNexa visa success-story reel).

Each visa sticker is cropped (and turned upright), then EVERYTHING on it is destroyed by heavy pixelation
+ blur - photo, name, dates, passport / visa numbers, issuing country, MRZ lines, QR code, stamp, serials -
except two small areas that carry no personal data: the EU flag and the word "VISA".
The source photos are read only; nothing un-redacted is written to the project.

Usage: python3 -I redact.py <out_dir>
"""
import sys
import cv2
import numpy as np

UP = "/root/.claude/uploads/58419071-33a5-5774-82e8-3e5c766ce9cc/"
OUT = sys.argv[1]
# portrait photo areas (original px) - wiped completely (identity must not be recoverable)
PHOTO = [(95, 465, 305, 780), (65, 205, 325, 545), (250, 25, 505, 255), (55, 325, 280, 605), (95, 115, 385, 495), (10, 105, 270, 405)]
# file, sticker crop (x0,y0,x1,y1), rotate, keep boxes (original px): EU flag, word "VISA"
VISAS = [
    ("73f6b05f-image.jpg", (55, 345, 1000, 1012), None, [(75, 365, 210, 440), (215, 365, 312, 406)]),
    ("24767a6d-image.jpg", (15, 55, 1170, 842), None, [(42, 75, 205, 165), (394, 75, 505, 126)]),
    ("3f1f4ff1-image.jpg", (30, 5, 622, 845), "ccw", [(535, 30, 605, 150), (558, 268, 605, 345)]),
    ("f4929814-image.jpg", (5, 185, 1120, 930), None, [(28, 205, 160, 280), (170, 203, 265, 241)]),
    ("1071f708-image.jpg", (30, 0, 1180, 790), None, [(85, 15, 245, 100), (255, 15, 365, 61)]),
    ("1bf5e4a3-image.jpg", (5, 15, 930, 625), None, [(35, 30, 165, 95), (175, 30, 260, 66)]),
]
TW = 1400                                          # output width of every card


def destroy(img):
    """Irreversible: pixelate to coarse blocks, then blur - text, faces, codes unreadable."""
    h, w = img.shape[:2]
    bs = max(w // 55, 8)
    small = cv2.resize(img, (max(w // bs, 1), max(h // bs, 1)), interpolation=cv2.INTER_AREA)
    blocky = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(blocky, (0, 0), w / 80)


for k, (fn, (x0, y0, x1, y1), rot, keeps) in enumerate(VISAS, 1):
    im = cv2.imread(UP + fn)
    crop = im[y0:y1, x0:x1].copy()
    ph = np.zeros(crop.shape[:2], np.uint8)
    a_, b_, c_, d_ = PHOTO[k - 1]
    ph[max(b_ - y0, 0):d_ - y0, max(a_ - x0, 0):c_ - x0] = 255
    keep = np.zeros(crop.shape[:2], np.uint8)
    for a, b, c, d in keeps:
        keep[b - y0:d - y0, a - x0:c - x0] = 255
    if rot == "ccw":
        crop = cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)
        keep = cv2.rotate(keep, cv2.ROTATE_90_COUNTERCLOCKWISE)
        ph = cv2.rotate(ph, cv2.ROTATE_90_COUNTERCLOCKWISE)
    h, w = crop.shape[:2]
    s = TW / w
    crop = cv2.resize(crop, (TW, int(round(h * s))), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    keep = cv2.resize(keep, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
    ph = cv2.resize(ph, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
    red = destroy(crop)
    # photo: replaced by a flat frosted panel (average colour of the area, no facial structure left)
    pm = ph > 0
    col = crop[pm].reshape(-1, 3).mean(0)
    panel = np.full_like(crop, 0); panel[:] = (col * 0.55 + 235 * 0.45).astype(np.uint8)
    pa = cv2.GaussianBlur(ph.astype(np.float32) / 255, (0, 0), 10)[..., None]
    red = (red * (1 - pa) + panel * pa).astype(np.uint8)
    a = cv2.GaussianBlur(keep.astype(np.float32) / 255, (0, 0), 2)[..., None]
    out = (crop * a + red * (1 - a)).astype(np.uint8)
    # gentle clean-up of the print colours so the card reads crisply at small size
    out = cv2.convertScaleAbs(out, alpha=1.06, beta=4)
    cv2.imwrite(f"{OUT}/visa{k}.jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("visa", k, out.shape[1], "x", out.shape[0])
