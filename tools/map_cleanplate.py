"""Remove the reference's round badge from the panning map (frames 0..419).

The map behind the badge is a flat surface under a moving camera, so every
pixel hidden by the badge is visible in some nearby frame. We track the map
with frame-to-frame homographies (ECC) and rebuild the hidden area from the
nearest frames where it was uncovered.

Usage (as a module): clean = build_cleaner(frames); clean(i) -> float32 BGR
"""
import cv2
import numpy as np

H, W = 1280, 720
BADGE_C, BADGE_R = (358.9, 158.7), 116      # badge ends at r~108 (+ blur during fades)
TRACK_Y1 = 300                              # rows that only show the flat map
MAP_END = 420
BADGE_FREE = set(range(0, 5)) | set(range(362, MAP_END))


def _track(frames, sc=0.5):
    yy, xx = np.mgrid[0:TRACK_Y1, 0:W].astype(np.float32)
    keep = (np.hypot(xx - BADGE_C[0], yy - BADGE_C[1]) >= BADGE_R).astype(np.uint8)
    m = cv2.resize(keep, (int(W * sc), int(TRACK_Y1 * sc)), interpolation=cv2.INTER_NEAREST)

    def gray(i):
        g = cv2.cvtColor(frames[i][:TRACK_Y1], cv2.COLOR_BGR2GRAY)
        return cv2.resize(g, (int(W * sc), int(TRACK_Y1 * sc)), interpolation=cv2.INTER_AREA).astype(np.float32)

    S = np.diag([sc, sc, 1.0])
    Si = np.linalg.inv(S)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5)
    A = [np.eye(3)]                          # frame0 coords -> frame i coords
    prev = gray(0)
    for i in range(1, MAP_END):
        cur = gray(i)
        w = np.eye(3, dtype=np.float32)
        try:
            _, w = cv2.findTransformECC(prev, cur, w, cv2.MOTION_HOMOGRAPHY, crit, m, 5)
        except cv2.error:
            w = np.eye(3, dtype=np.float32)
        A.append(Si @ w.astype(np.float64) @ S @ A[-1])
        prev = cur
    return A


def build_cleaner(frames):
    A = _track(frames)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(xx - BADGE_C[0], yy - BADGE_C[1])
    FADE_R = 136                             # blurred badge during its fade in/out
    hole_n, hole_f = d < BADGE_R, d < FADE_R
    soft_n = np.clip((BADGE_R + 6 - d) / 14, 0, 1)[..., None]
    soft_f = np.clip((FADE_R + 6 - d) / 14, 0, 1)[..., None]
    valid_free = (yy < TRACK_Y1)
    valid_badge = valid_free & ~(d < FADE_R + 4)
    ones = np.ones((H, W), np.float32)

    sc = 0.5
    Sm = np.diag([sc, sc, 1.0])
    Smi = np.linalg.inv(Sm)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5)
    small = (int(W * sc), int(TRACK_Y1 * sc))

    def gray(img):
        g = cv2.cvtColor(img[:TRACK_Y1], cv2.COLOR_BGR2GRAY)
        return cv2.resize(g, small, interpolation=cv2.INTER_AREA).astype(np.float32)

    tmpl_mask = cv2.resize((~(d[:TRACK_Y1] < FADE_R + 6)).astype(np.uint8), small,
                           interpolation=cv2.INTER_NEAREST)

    def refine(i, j, M):
        """Directly align frame j to frame i (removes drift of the chained track)."""
        w = (Sm @ M @ Smi).astype(np.float32)
        w /= w[2, 2]
        try:
            _, w = cv2.findTransformECC(gray(frames[i]), gray(frames[j]), w,
                                        cv2.MOTION_HOMOGRAPHY, crit, tmpl_mask, 3)
            return Smi @ w.astype(np.float64) @ Sm
        except cv2.error:
            return M

    def clean(i):
        fading = i <= 18 or 340 <= i <= 362
        hole = hole_f if fading else hole_n
        soft = soft_f if fading else soft_n
        f = frames[i].astype(np.float32)
        Ai_inv = np.linalg.inv(A[i])
        acc = np.zeros_like(f)
        wsum = np.zeros((H, W), np.float32)
        order = sorted(range(MAP_END), key=lambda j: (abs(j - i), j))
        used = 0
        for j in order:
            if abs(j - i) < 4:
                continue
            M = A[j] @ Ai_inv                 # frame i coords -> frame j coords
            src_valid = (valid_free if j in BADGE_FREE else valid_badge).astype(np.float32)
            v = cv2.warpPerspective(src_valid * ones, M, (W, H),
                                    flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
            cover = hole & (v > 0.999)
            if cover.sum() < 0.25 * hole.sum() or not (cover & (wsum < 1)).any():
                continue
            M = refine(i, j, M)
            v = cv2.warpPerspective(src_valid * ones, M, (W, H),
                                    flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
            # feathered weight: fade out towards the edge of the usable area
            wv = cv2.GaussianBlur((v > 0.999).astype(np.float32), (0, 0), 6) * (v > 0.999)
            wv *= 1.0 / (1 + abs(j - i) / 40)
            img = cv2.warpPerspective(frames[j], M, (W, H),
                                      flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                      borderMode=cv2.BORDER_REFLECT).astype(np.float32)
            acc += img * wv[..., None]
            wsum += wv
            used += 1
            if (wsum[hole] > 0.6).all() or used >= 6:
                break
        fill = np.where(wsum[..., None] > 1e-4, acc / np.maximum(wsum, 1e-4)[..., None], f)
        miss = hole & (wsum < 1e-3)
        comp = np.where(hole[..., None], fill, f)
        if miss.any():                        # tiny leftovers: smooth fill
            comp = cv2.inpaint(np.clip(comp, 0, 255).astype(np.uint8), miss.astype(np.uint8) * 255,
                               9, cv2.INPAINT_TELEA).astype(np.float32)
        comp = cv2.GaussianBlur(comp, (0, 0), 1.2)
        return f * (1 - soft) + comp * soft

    return clean
