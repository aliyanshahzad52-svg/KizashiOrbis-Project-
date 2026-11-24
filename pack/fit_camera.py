"""Fit a perspective camera + suitcase proportions to the reference poster (so the 3D scene matches it).
Points (reference px, 853x1280): lid far edge, hinge, base front-top rim, base front-bottom."""
import numpy as np

IMG = np.array([[163, 490], [692, 490],          # lid far edge (open lid)
                [162, 750], [692, 750],          # hinge line
                [132, 1112], [722, 1112],        # base front-top rim
                [140, 1170], [716, 1170]], float)  # base front-bottom edge
W = 60.0


def project(p, P):
    D, Hb, phi, cy, cz, ty, tz, f = P
    hy = Hb
    pts = np.array([[-W / 2, hy + D * np.sin(phi), -D / 2 - D * np.cos(phi)], [W / 2, hy + D * np.sin(phi), -D / 2 - D * np.cos(phi)],
                    [-W / 2, hy, -D / 2], [W / 2, hy, -D / 2],
                    [-W / 2, hy, D / 2], [W / 2, hy, D / 2],
                    [-W / 2, 0, D / 2], [W / 2, 0, D / 2]])
    cam = np.array([0, cy, cz]); tgt = np.array([0, ty, tz])
    fwd = tgt - cam; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = pts - cam
    x, y, z = rel @ right, rel @ up, rel @ fwd
    u = 426.5 + f * x / z
    v = 640 - f * y / z
    return np.stack([u, v], 1)


def loss(P):
    if P[0] < 10 or P[1] < 3 or not (0.3 < P[2] < 3.1) or P[7] < 100:
        return 1e9
    try:
        return float(((project(None, P) - IMG) ** 2).sum())
    except Exception:
        return 1e9


def nelder(f, x0, step, it=6000):
    n = len(x0)
    S = [x0] + [x0 + np.eye(n)[i] * step[i] for i in range(n)]
    F = [f(s) for s in S]
    for _ in range(it):
        o = np.argsort(F); S = [S[i] for i in o]; F = [F[i] for i in o]
        c = np.mean(S[:-1], 0)
        r = c + (c - S[-1]); fr = f(r)
        if fr < F[0]:
            e = c + 2 * (c - S[-1]); fe = f(e)
            S[-1], F[-1] = (e, fe) if fe < fr else (r, fr)
        elif fr < F[-2]:
            S[-1], F[-1] = r, fr
        else:
            k = c + 0.5 * (S[-1] - c); fk = f(k)
            if fk < F[-1]:
                S[-1], F[-1] = k, fk
            else:
                S = [S[0]] + [S[0] + 0.5 * (s - S[0]) for s in S[1:]]; F = [f(s) for s in S]
    return S[0], F[0]


rng = np.random.default_rng(0)
best = None
for trial in range(60):
    x0 = np.array([rng.uniform(30, 50), rng.uniform(6, 16), rng.uniform(1.4, 2.4), rng.uniform(80, 200),
                   rng.uniform(20, 150), rng.uniform(-10, 10), rng.uniform(-20, 10), rng.uniform(500, 1500)])
    x, fx = nelder(loss, x0, np.array([5, 2, .2, 20, 20, 5, 5, 100]))
    if best is None or fx < best[1]:
        best = (x, fx)
x, fx = best
names = ["D", "Hb", "phi", "cam_y", "cam_z", "tgt_y", "tgt_z", "f_px"]
print({n: round(float(v), 3) for n, v in zip(names, x)}, "err px rms", np.sqrt(fx / 8))
print(np.round(project(None, x), 1))
print("vfov deg", 2 * np.degrees(np.arctan(640 / x[7])), "lid open deg", np.degrees(x[2]))
