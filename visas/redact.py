"""Privacy treatment of the visa photos, in the style of the sample reel (no boxes, bars or patches).

* Sensitive printed details - issuing-country name and code lines, visa number, validity / issue dates,
  passport number, place of issue, holder name, remarks, red serial - are made semi-transparent:
  the ink is faded into the card's own background (dark strokes lifted toward the surrounding paper
  colour, feathered edges), so the data stays only faintly visible and the visa keeps its natural look.
* The holder photo gets a soft, feathered blur like the sample (face not recognisable).
* The lower section (machine-readable lines) is left as it is, except its first characters, which spell the
  issuing country - they get the same fade.
The source photos are only read; this writes the treated cards.

Usage: python3 -I redact.py <out_dir>
"""
import sys

import cv2
import numpy as np

UP = "/root/.claude/uploads/58419071-33a5-5774-82e8-3e5c766ce9cc/"
OUT = sys.argv[1]
FADE = 0.9                                    # how far sensitive ink is faded into the background (0..1)

# file, sticker crop (x0,y0,x1,y1), rotate, photo rect, sensitive rects  (all in original pixels)
VISAS = [
    ("73f6b05f-image.jpg", (55, 345, 1000, 1012), None, (95, 465, 305, 780),
     [(215, 404, 705, 446), (505, 362, 875, 406), (392, 462, 875, 628), (322, 462, 362, 748), (85, 855, 240, 898)]),
    ("24767a6d-image.jpg", (15, 55, 1170, 842), None, (65, 205, 325, 545),
     [(212, 72, 368, 128), (212, 128, 785, 175), (570, 72, 1012, 128), (438, 178, 965, 362), (688, 378, 885, 502),
      (352, 192, 398, 528), (50, 655, 218, 702)]),
    ("3f1f4ff1-image.jpg", (30, 5, 622, 845), "ccw", (250, 25, 505, 255),
     [(556, 148, 606, 262), (556, 348, 606, 745), (512, 148, 556, 745), (358, 238, 527, 748), (248, 238, 292, 352), (145, 25, 180, 175), (328, 540, 360, 745)]),
    ("f4929814-image.jpg", (5, 185, 1120, 930), None, (55, 325, 280, 605),
     [(168, 242, 660, 282), (462, 198, 822, 242), (358, 282, 822, 452), (282, 298, 322, 588), (65, 680, 220, 718)]),
    ("1071f708-image.jpg", (30, 0, 1180, 790), None, (95, 115, 385, 495),
     [(252, 66, 832, 112), (598, 22, 1028, 72), (432, 112, 1002, 302), (382, 128, 422, 458), (100, 565, 285, 608)]),
    ("1bf5e4a3-image.jpg", (5, 15, 930, 625), None, (10, 105, 270, 405),
     [(172, 62, 642, 102), (448, 27, 812, 67), (278, 98, 802, 252), (278, 108, 307, 388), (55, 466, 205, 508)]),
]
TW = 1400                                     # output width of every card


def rects_mask(shape, rects, x0, y0):
    m = np.zeros(shape[:2], np.uint8)
    for a, b, c, d in rects:
        m[max(b - y0, 0):max(d - y0, 0), max(a - x0, 0):max(c - x0, 0)] = 255
    return m


for k, (fn, (x0, y0, x1, y1), rot, photo, sens) in enumerate(VISAS, 1):
    im = cv2.imread(UP + fn)
    crop = im[y0:y1, x0:x1].copy()
    sm = rects_mask(crop.shape, sens, x0, y0)
    pm = rects_mask(crop.shape, [photo], x0, y0)
    if rot == "ccw":
        crop, sm, pm = (cv2.rotate(a, cv2.ROTATE_90_COUNTERCLOCKWISE) for a in (crop, sm, pm))
    h, w = crop.shape[:2]
    s = TW / w
    size = (TW, int(round(h * s)))
    crop = cv2.resize(crop, size, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    sm = cv2.resize(sm, size, interpolation=cv2.INTER_NEAREST)
    pm = cv2.resize(pm, size, interpolation=cv2.INTER_NEAREST)
    img = crop.astype(np.float32)

    # 1. semi-transparent sensitive text: lift the dark ink toward the local paper colour
    k_ = max(int(TW / 60), 7) | 1
    paper = cv2.dilate(img, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_, k_)))      # removes thin dark strokes
    paper = cv2.GaussianBlur(paper, (0, 0), TW / 260)
    a = cv2.GaussianBlur(sm.astype(np.float32) / 255, (0, 0), TW / 180)[..., None] * FADE
    img = img * (1 - a) + paper * a

    # 2. soft feathered blur on the holder photo (like the sample)
    soft = cv2.GaussianBlur(img, (0, 0), TW / 70)
    pa = cv2.GaussianBlur(pm.astype(np.float32) / 255, (0, 0), TW / 120)[..., None]
    img = img * (1 - pa) + soft * pa

    out = cv2.convertScaleAbs(np.clip(img, 0, 255), alpha=1.04, beta=3)
    cv2.imwrite(f"{OUT}/visa{k}.jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("visa", k, out.shape[1], "x", out.shape[0])
