"""Cut the two crow characters out of the reference picture and re-colour them to KizashiOrbis green.

python3 prep.py  ->  assets/crow1.png (pebble-dropping crow, pebble removed from the beak)
                     assets/crow2.png (relaxing crow on the deck chair, straw removed, red -> brand green)
                     assets/bowl_profile.json (outline of the fish bowl measured on the picture)
Coordinates in the comments are reference-picture pixels (1122 x 1402).
"""
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
im = np.asarray(Image.open(f"{HERE}/src/reference.jpg").convert("RGB")).astype(np.float32)
H, W, _ = im.shape
BG = np.array([243, 241, 242], np.float32)
diff = np.abs(im - BG).max(2)
lum = im @ np.array([0.299, 0.587, 0.114], np.float32)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def unmix(rgb, a):
    """Remove the light background from semi-transparent edge pixels (colour = a*fg + (1-a)*bg)."""
    a3 = np.maximum(a, 1e-3)[..., None]
    fg = (rgb - (1 - a)[..., None] * BG) / a3
    return np.clip(np.where(a[..., None] > 0.02, fg, rgb), 0, 255)


def save(name, rgb, a, box):
    x0, y0, x1, y1 = box
    out = np.dstack([unmix(rgb, a), a * 255])[y0:y1, x0:x1]
    Image.fromarray(out.astype(np.uint8), "RGBA").save(f"{HERE}/assets/{name}.png")
    print(name, box)


def red_to_green(rgb, mask):
    """Hue-rotate saturated reds to the brand green, keeping the shading."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(2); mn = rgb.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    # pure reds by hue, measured on a slightly blurred copy so JPEG chroma noise does not speckle the wood:
    # stripes / hat / straw sit at -15..+5 deg, the red-brown wood at +15..+30 deg
    bl = np.stack([ndimage.gaussian_filter(rgb[..., c], 1.6) for c in range(3)], -1)
    br, bg_, bb = bl[..., 0], bl[..., 1], bl[..., 2]
    hue = np.degrees(np.arctan2(np.sqrt(3) * (bg_ - bb), 2 * br - bg_ - bb))
    bmx = bl.max(2); bsat = (bmx - bl.min(2)) / np.maximum(bmx, 1)
    red = (hue < 9) & (hue > -40) & (bsat > 0.25) & (bmx > 60) & mask
    hatz = (yy < 700) & (xx > 765) & (xx < 900)
    red |= hatz & mask & (hue < 35) & (hue > -60) & (bsat > 0.12)          # whole hard hat incl. highlights
    w = red.astype(np.float32)
    w = ndimage.gaussian_filter(w, 0.7)
    shade = mx / 255.0                     # brightness of the red surface
    green = np.stack([0.10 * 255 * shade, 0.80 * 255 * shade, 0.42 * 255 * shade], -1)   # ~ #19c46a scaled
    hi = np.clip((mn - 60) / 160, 0, 1)[..., None]   # keep specular highlights white-ish
    green = green * (1 - hi) + rgb * hi
    return rgb * (1 - w[..., None]) + green * w[..., None]


yy, xx = np.mgrid[0:H, 0:W]

# ---------------------------------------------------------------- crow 1 (on the bowl rim)
box1 = (150, 462, 505, 702)
a1 = smooth(205, 135, lum)                               # black bird on a light background
reg = (xx >= box1[0]) & (xx < box1[2]) & (yy >= box1[1]) & (yy < box1[3])
a1 *= reg
# glass rim under the feet: keep only the dark claws there
rim = (yy > 662)
a1 = np.where(rim, smooth(150, 90, lum), a1) * reg
# remove the pebble held in the beak (centre ~ (479, 628), r ~ 18) below the beak tip
peb = ((xx - 479) ** 2 + ((yy - 629) * 0.92) ** 2 < 21 ** 2) & (yy > 611)
a1[peb] = 0
lab, n = ndimage.label(a1 > 0.5)
if n > 1:                                                # drop specks that are not the bird
    sizes = ndimage.sum(np.ones_like(a1), lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.where(sizes > 400)[0])
    a1 *= ndimage.binary_dilation(keep, iterations=2)
save("crow1", im, a1, box1)

# ---------------------------------------------------------------- crow 2 + deck chair
box2 = (598, 578, 975, 1068)
reg = (xx >= box2[0]) & (xx < box2[2]) & (yy >= box2[1]) & (yy < box2[3])
hard = (diff > 26) & reg
hard = ndimage.binary_closing(hard, iterations=4)
holes = ndimage.binary_fill_holes(hard) & ~hard          # only small enclosed gaps (white fabric stripes)
lab, n = ndimage.label(holes)
sizes = ndimage.sum(np.ones(holes.shape), lab, range(1, n + 1))
r_, g_, b_ = im[..., 0], im[..., 1], im[..., 2]
redstripe = (r_ > g_ * 1.8) & (b_ >= g_ * 0.7) & (r_ > 110)
near_red = ndimage.binary_dilation(redstripe, iterations=7)
small = np.isin(lab, 1 + np.where(sizes < 1800)[0])
# a gap is white fabric only if it touches a red stripe; other enclosed gaps are background seen through the chair
touch = ndimage.maximum(near_red, lab, range(1, n + 1)) if n else []
fzone = ((yy > 905) & (yy < 1002) & (xx > 640) & (xx < 905)) | ((xx > 870) & (xx < 968) & (yy > 640) & (yy < 930))
fabric = np.isin(lab, 1 + np.where(np.asarray(touch) > 0)[0]) & small & fzone
fabric &= ~((xx > 858) & (xx < 886) & (yy > 892) & (yy < 936))   # gap between arm-rest and seat is background
hard |= fabric
hard = ndimage.binary_opening(hard, iterations=1)
# the fish bowl overlaps the left of this box: keep only the dark claws inside its outline
inbowl = ((xx - 443) / 212.0) ** 2 + ((yy - 850) / 215.0) ** 2 < 1
hard &= ~inbowl | ((lum < 70) & (xx > 630))
soft = smooth(14, 45, diff) * reg * (~inbowl | ((lum < 70) & (xx > 630)))
soft *= ndimage.binary_dilation(hard, iterations=3)
a2 = np.maximum(soft, ndimage.gaussian_filter(ndimage.binary_erosion(hard, iterations=1).astype(np.float32), 0.8))
a2 *= reg
# the white fabric stripes are as light as the background: fill the seat and back-rest fabric regions
sat = (im.max(2) - im.min(2)) / np.maximum(im.max(2), 1)
# remove the red straw (everything red outside the hard hat) - it is rebuilt in 3D
r, g, b = im[..., 0], im[..., 1], im[..., 2]
redpx = (r > g * 1.6) & (r > b * 1.5) & (r > 120)
hat = (yy < 700) & (xx > 765)
seat = (yy > 900) & (xx > 640)                           # red/white stripes of the seat
back = (xx > 900) & (yy > 640) & (yy < 900)              # stripes of the back rest
straw = redpx & ~hat & ~seat & ~back
straw = ndimage.binary_dilation(straw, iterations=2)
a2[straw] = 0
# floor contact shadow under the chair is rebuilt in 3D: fade the bottom rows that are only shadow
shadow_only = ((lum > 165) & (yy > 990) & ~fabric) | ((lum > 95) & (yy > 1030) & (sat < 0.3))
a2[shadow_only] = 0
a2[(diff < 16) & ~fabric] = 0                            # background specks caught inside the mask
a2[(lum > 200) & ~fabric & ~((yy < 700) & (xx > 765) & (xx < 900))] = 0   # light background seen through gaps
lab, n = ndimage.label(a2 > 0.3)                          # drop leftover specks of the bowl outline
sizes = ndimage.sum(np.ones(a2.shape), lab, range(1, n + 1))
a2 *= ndimage.binary_dilation(np.isin(lab, 1 + np.where(sizes > 3000)[0]), iterations=2)
rgb2 = red_to_green(im, reg & ~straw)
save("crow2", rgb2, a2, box2)

# ---------------------------------------------------------------- bowl outline (outermost glass edge per row)
prof = []
for y in range(664, 1058, 6):
    row = diff[y, 200:440]
    xs = np.where(row > 10)[0]
    if len(xs) == 0:
        continue
    left = 200 + xs[0]
    prof.append([int(y), int(left)])
json.dump(prof, open(f"{HERE}/assets/bowl_profile.json", "w"))
print("profile", prof[:3], prof[-3:])
