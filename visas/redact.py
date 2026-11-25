"""Privacy treatment of the visa photos for the OrbisNexa visa success-story reel.

One uniform, soft frosted blur (same strength everywhere, feathered edges, no lightening, no overlay):
  * issuing-country name lines and country codes (e.g. MALTA / MLT, IRELAND / IRL, ROMANIA / ROU)
  * validity dates (from / until) and the date of issue
The holder photo gets the same kind of soft blur, as in the sample reel.
Everything else - layout, security print, lower data section - is left untouched.
The source photos are only read; this writes the treated cards.

Usage: python3 -I redact.py <out_dir>
"""
import sys

import cv2
import numpy as np

UP = "/root/.claude/uploads/58419071-33a5-5774-82e8-3e5c766ce9cc/"
OUT = sys.argv[1]
TW = 1400                    # every card is normalised to this width, so blur strength is identical on all
SIGMA = 9.0                  # frosted blur strength (px at TW) - text unreadable, texture still natural
FEATHER = 6.0                # soft edge of each blurred area (px at TW)

# file, sticker crop (x0,y0,x1,y1), rotate, photo rect, areas to blur (all in original photo pixels)
VISAS = [
    ("73f6b05f-image.jpg", (55, 345, 1000, 1012), None, (95, 465, 305, 780),
     [(212, 404, 708, 446),            # MALTA/MALTA/MALTE  MLT
      (505, 362, 622, 406),            # MLT code panel
      (395, 462, 525, 494),            # MALTA (valid for)
      (390, 492, 680, 524),            # from / until dates
      (690, 558, 855, 594)]),          # date of issue
    ("24767a6d-image.jpg", (15, 55, 1170, 842), None, (65, 205, 325, 545),
     [(212, 72, 368, 128),             # VIOSA (Irish)
      (212, 128, 788, 176),            # EIREANN/IRLANDE/IRELAND  IRL
      (568, 72, 712, 128),             # IRL code panel
      (445, 178, 605, 214),            # Ireland (valid for)
      (435, 214, 765, 254),            # from / until dates
      (795, 288, 955, 328)]),          # date of issue
    ("3f1f4ff1-image.jpg", (30, 5, 622, 845), "ccw", (250, 25, 505, 255),
     [(556, 148, 606, 262),            # VIZA (Romanian)
      (526, 148, 560, 645),            # ROMANIA/ROUMANIE/ROMANIA  ROU
      (556, 415, 606, 508),            # ROU code panel
      (488, 352, 530, 478),            # ROMANIA (valid for)
      (456, 228, 502, 578),            # from / until dates
      (402, 635, 438, 748)]),          # date of issue
    ("f4929814-image.jpg", (5, 185, 1120, 930), None, (55, 325, 280, 605),
     [(165, 242, 662, 283),            # MALTA/MALTA/MALTE  MLT
      (460, 198, 582, 242),            # MLT code panel
      (375, 285, 475, 312),            # MALTA
      (355, 310, 645, 342),            # from / until dates
      (665, 368, 815, 400)]),          # date of issue
    ("1071f708-image.jpg", (30, 0, 1180, 790), None, (95, 115, 385, 495),
     [(252, 66, 835, 114),             # MALTA/MALTA/MALTE  MLT
      (596, 20, 748, 74),              # MLT code panel
      (495, 115, 605, 147),            # MALTA
      (475, 147, 815, 184),            # from / until dates
      (845, 225, 1005, 265)]),         # date of issue
    ("1bf5e4a3-image.jpg", (5, 15, 930, 625), None, (10, 105, 270, 405),
     [(170, 62, 645, 104),             # MALTA/MALTA/MALTE  MLT
      (446, 25, 562, 69),              # MLT code panel
      (375, 102, 465, 127),            # MALTA
      (315, 124, 605, 152),            # from / until dates
      (625, 183, 785, 217)]),          # date of issue
]


def rects_mask(shape, rects, x0, y0):
    m = np.zeros(shape[:2], np.uint8)
    for a, b, c, d in rects:
        m[max(b - y0, 0):max(d - y0, 0), max(a - x0, 0):max(c - x0, 0)] = 255
    return m


for k, (fn, (x0, y0, x1, y1), rot, photo, areas) in enumerate(VISAS, 1):
    im = cv2.imread(UP + fn)
    crop = im[y0:y1, x0:x1].copy()
    am = rects_mask(crop.shape, areas, x0, y0)
    pm = rects_mask(crop.shape, [photo], x0, y0)
    if rot == "ccw":
        crop, am, pm = (cv2.rotate(a, cv2.ROTATE_90_COUNTERCLOCKWISE) for a in (crop, am, pm))
    h, w = crop.shape[:2]
    s = TW / w
    size = (TW, int(round(h * s)))
    crop = cv2.resize(crop, size, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    am = cv2.resize(am, size, interpolation=cv2.INTER_NEAREST)
    pm = cv2.resize(pm, size, interpolation=cv2.INTER_NEAREST)
    img = crop.astype(np.float32)

    # uniform frosted blur on the specified areas (colour-preserving: just a blur, nothing added)
    frost = cv2.GaussianBlur(img, (0, 0), SIGMA)
    a = cv2.GaussianBlur(am.astype(np.float32) / 255, (0, 0), FEATHER)[..., None]
    a = np.clip(a * 1.15, 0, 1)                                   # full strength inside, soft only at the rim
    out = img * (1 - a) + frost * a

    # soft blur on the holder photo, as in the sample
    soft = cv2.GaussianBlur(out, (0, 0), TW / 70)
    pa = cv2.GaussianBlur(pm.astype(np.float32) / 255, (0, 0), TW / 120)[..., None]
    out = out * (1 - pa) + soft * pa

    cv2.imwrite(f"{OUT}/visa{k}.jpg", np.clip(out + .5, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("visa", k, size[0], "x", size[1])
