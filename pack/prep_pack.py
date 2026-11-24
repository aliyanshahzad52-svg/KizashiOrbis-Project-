"""Cut the reference poster into textures for the 3D packing animation.

  base_empty.png   base interior with every item removed (LaMa inpainting)
  lid_inside.png   lid interior (mesh pockets + OrbisNexa luggage tag), as in the poster
  passport.png     passport front (part hidden under the cap restored)
  boarding.png     boarding pass (rounded corners, alpha)
  letter.png       university offer letter (strip hidden under the cap restored)

Usage: python3 prep_pack.py <reference.png> <lama.onnx> <out_dir>
"""
import sys

import cv2
import numpy as np
import onnxruntime as ort

REF, LAMA, OUT = sys.argv[1:4]
im = cv2.imread(REF)
H, W = im.shape[:2]

PASS = (212, 770, 380, 958)
BOARD = (396, 768, 660, 880)
LETTER = (447, 880, 682, 1100)
CAP = np.array([[150, 995], [355, 925], [478, 1015], [432, 1050], [418, 1112], [368, 1114],
                [300, 1102], [188, 1082], [148, 1040]], np.int32)
BASE_IN = (158, 754, 698, 1113)
LID_IN = (166, 497, 688, 746)

sess = ort.InferenceSession(LAMA, providers=["CPUExecutionProvider"])


def lama(img, mask):
    h, w = img.shape[:2]
    x = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA)
    m = cv2.resize(mask, (512, 512), interpolation=cv2.INTER_NEAREST)
    xi = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2, 0, 1)[None] / 255
    o = sess.run(None, {"image": xi, "mask": (m > 0).astype(np.float32)[None, None]})[0][0].transpose(1, 2, 0)
    o = cv2.cvtColor(np.clip(o, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    o = cv2.resize(o, (w, h), interpolation=cv2.INTER_CUBIC)
    soft = cv2.GaussianBlur((mask > 0).astype(np.float32), (0, 0), 1.5)[..., None]
    return (o * soft + img * (1 - soft)).astype(np.uint8)


def rect_mask(shape, r, pad=0):
    m = np.zeros(shape[:2], np.uint8)
    cv2.rectangle(m, (r[0] - pad, r[1] - pad), (r[2] + pad, r[3] + pad), 255, -1)
    return m


# ---------------- empty base interior (items removed)
mask = np.zeros((H, W), np.uint8)
for r in (PASS, BOARD, LETTER):
    mask |= rect_mask(mask.shape, r, 5)
cv2.fillPoly(mask, [CAP], 255)
mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
x0, y0 = 145, 600
crop = im[y0:y0 + 560, x0:x0 + 560].copy()
mk = mask[y0:y0 + 560, x0:x0 + 560].copy()
mk[:754 - y0 - 3] = 0                                   # keep the lid / hinge untouched
clean = im.copy()
clean[y0:y0 + 560, x0:x0 + 560] = lama(crop, mk)
cv2.imwrite(f"{OUT}/base_empty.png", clean[BASE_IN[1]:BASE_IN[3], BASE_IN[0]:BASE_IN[2]])
cv2.imwrite(f"{OUT}/lid_inside.png", im[LID_IN[1]:LID_IN[3], LID_IN[0]:LID_IN[2]])

# ---------------- items
cap_mask = np.zeros((H, W), np.uint8)
cv2.fillPoly(cap_mask, [CAP], 255)
cap_mask = cv2.dilate(cap_mask, np.ones((5, 5), np.uint8))
cap_mask[944:960, PASS[0]:PASS[2]] = 255                 # passport foot: lining / zipper shows through there


def item(r, fix_cap=True, radius=0):
    x0, y0, x1, y1 = r
    c = im[y0:y1, x0:x1].copy()
    if fix_cap:
        m = cap_mask[y0:y1, x0:x1]
        if m.any():
            c = cv2.inpaint(c, m, 9, cv2.INPAINT_TELEA)
    a = np.full(c.shape[:2], 255, np.uint8)
    if radius:
        a[:] = 0
        s = 4
        big = np.zeros((c.shape[0] * s, c.shape[1] * s), np.uint8)
        rr = radius * s
        cv2.rectangle(big, (rr, 0), (big.shape[1] - rr, big.shape[0]), 255, -1)
        cv2.rectangle(big, (0, rr), (big.shape[1], big.shape[0] - rr), 255, -1)
        for cx, cy in ((rr, rr), (big.shape[1] - rr, rr), (rr, big.shape[0] - rr), (big.shape[1] - rr, big.shape[0] - rr)):
            cv2.circle(big, (cx, cy), rr, 255, -1)
        a = cv2.resize(big, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_AREA)
    up = cv2.resize(np.dstack([c, a]), None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)  # texture headroom
    return up


cv2.imwrite(f"{OUT}/passport.png", item(PASS, radius=4))
cv2.imwrite(f"{OUT}/boarding.png", item(BOARD, fix_cap=False, radius=7))
cv2.imwrite(f"{OUT}/letter.png", item(LETTER, radius=2))
print("textures written to", OUT)
