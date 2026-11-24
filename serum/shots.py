"""Unbranded serum-bottle commercial: the four shots.

python3 shots.py <shot A|B|C|D> <outdir> [--frames 1,40,80] [--pct 50] [--spp 8]
Renders PNG frames <outdir>/<shot>_####.png (existing frames are skipped, so a render can resume).

A  0.0-6.5 s  darkness -> rim light reveal -> the bottle descends onto a wet stone in still water, ripples spread
B  6.5-10 s   macro: the dropper lifts out of the neck, a drop of serum forms and falls back in
C  10-13 s    the bottle floats and turns while water droplets drift around it
D  13-16.5 s  studio hero shot on a stone plinth, leaf-shadow light, glossy reflections
No text, labels or logos anywhere.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib  # noqa: E402
from lib import CM  # noqa: E402

HANDLE = 8          # extra frames at the end of each shot for the cross-dissolve
SHOTS = {"A": 195, "B": 105, "C": 90, "D": 105}


# ------------------------------------------------------------------ set pieces
def grid(name, size, seg, mat, z=0.0):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=seg, y_segments=seg, size=size / 2)
    ob = lib.mesh_obj(name, bm, mat); ob.location.z = z
    return ob


def backdrop(dist=0.7, col=(0.02, 0.017, 0.013), h=1.2, z0=-0.02):
    """Curved cyclorama so the horizon never shows."""
    bm = bmesh.new()
    prof = []
    for i in range(25):
        a = i / 24 * math.pi / 2
        prof.append((-0.25 + 0.25 * math.sin(a), 0.25 - 0.25 * math.cos(a)))      # (y, z) quarter round
    prof.append((0.0, h))
    rows = []
    for x in (-1.2, 1.2):
        rows.append([bm.verts.new((x, dist + y, z + z0)) for y, z in [(-1.2, 0)] + prof])
    for j in range(len(rows[0]) - 1):
        bm.faces.new((rows[0][j], rows[1][j], rows[1][j + 1], rows[0][j + 1]))
    return lib.mesh_obj("cyc", bm, lib.mat_backdrop(col, rough=0.8))


def flat_stone(name, size, seed, top=0.0, mat=None):
    ob = lib.stone(name, 1.0, seed, squash=0.42, mat=mat or lib.mat_stone(0.009, 0.1, 0.4))
    me = ob.data
    zmax = max(v.co.z for v in me.vertices)
    cut = zmax * 0.55
    for v in me.vertices:
        if v.co.z > cut: v.co.z = cut + (v.co.z - cut) * 0.06          # flatten into a slab
    lib.smooth_by_angle(ob, 70)
    ob.scale = (size, size * 0.85, size)
    ob.location.z = top - cut * size
    return ob


def leaves(seed, spots, hue=(0.04, 0.15, 0.03)):
    """spots: list of (x, y, z, yaw, pitch, length, width, curl)"""
    mats = [lib.mat_leaf(hue), lib.mat_leaf((hue[0] * 0.7, hue[1] * 0.75, hue[2] * 0.6)), lib.mat_leaf((hue[0] * 1.3, hue[1] * 1.05, hue[2] * 0.7))]
    out = []
    for i, (x, y, z, yaw, pitch, L, W, curl) in enumerate(spots):
        lf = lib.leaf(f"leaf{seed}_{i}", L * 0.85, W, curl=curl, fold=0.35, mat=mats[i % 3], twist=0.25 * math.sin(i * 1.7))
        lf.location = (x, y, z); lf.rotation_euler = (pitch, 0, yaw)
        out.append(lf)
    return out


def water(size=0.9, seg=700):
    w = grid("water", size, seg, lib.mat_water(0.0))
    return w


def ripple(ob, frame, pos, height=0.00035, width=0.006, speed=0.0022, life=0, damp=60, falloff=0.22):
    m = ob.modifiers.new("wave", "WAVE")
    m.use_normal = False; m.use_x = True; m.use_y = True; m.use_cyclic = False
    m.start_position_x, m.start_position_y = pos
    m.height = height; m.width = width; m.narrowness = 1.6; m.speed = speed
    m.time_offset = frame; m.lifetime = life; m.damping_time = damp; m.falloff_radius = falloff
    return m


def droplets_on_glass(parent, n=260, seed=5, zr=(0.6, 5.7), R=1.65):
    rnd = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        r = (0.03 + rnd.random() ** 2.2 * 0.11) * CM
        a = rnd.random() * math.tau; z = (zr[0] + rnd.random() * (zr[1] - zr[0])) * CM
        ret = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
        n_ = Vector((math.cos(a), math.sin(a), 0))
        for v in ret["verts"]:
            d = v.co.dot(n_); v.co = v.co - n_ * d + n_ * d * 0.45            # flatten against the glass
        bmesh.ops.translate(bm, verts=ret["verts"], vec=n_ * (R * CM + r * 0.05) + Vector((0, 0, z)))
    ob = lib.mesh_obj("glass_drops", bm, lib.mat_water()); ob.parent = parent
    return ob


def lights_nature():
    L = {}
    L["key"] = lib.area_light("key", (-0.30, -0.20, 0.30), (0, 0, 0.06), 0.25, 0.25, 6.0, (1, 0.96, 0.9))
    L["rimL"] = lib.area_light("rimL", (-0.16, 0.18, 0.10), (0, 0, 0.06), 0.015, 0.35, 3.0)
    L["rimR"] = lib.area_light("rimR", (0.17, 0.16, 0.12), (0, 0, 0.06), 0.015, 0.35, 3.0)
    L["back"] = lib.area_light("back", (0.0, 0.26, 0.05), (0, 0, 0.05), 0.06, 0.06, 1.6, (1, 0.72, 0.42), spread=16, glossy=False)
    L["glow"] = lib.area_light("glow", (0.0, 0.3, 0.12), (0, 0.75, 0.32), 0.3, 0.3, 6.0, (1, 0.82, 0.6), glossy=False)   # light on the backdrop
    return L


def nature_set(stone_top=0.012):
    lib.world_color((0.006, 0.006, 0.0055), 1.0)
    backdrop(0.75, (0.014, 0.012, 0.01))
    w = water()
    floor = grid("riverbed", 2.0, 1, lib.mat_stone(0.012, 0.5), z=-0.025)
    st = flat_stone("stone", 0.06, 11, top=stone_top)
    smat = lib.mat_stone(0.008, 0.12, 0.45)
    st2 = lib.stone("stone2", 0.035, 4, squash=0.5, mat=smat); st2.location = (-0.075, 0.05, -0.004)
    st3 = lib.stone("stone3", 0.025, 8, squash=0.55, mat=smat); st3.location = (0.07, 0.075, -0.003)
    st4 = lib.stone("stone4", 0.02, 21, squash=0.5, mat=smat); st4.location = (0.05, -0.06, -0.006)
    # (heading of the leaf tip as a direction, rise) - fronds arch out from behind the stones
    spec = [(-0.03, 0.035, (-0.55, 0.8), 0.95, 0.15, 0.034, 1.5), (-0.045, 0.02, (-0.95, 0.3), 0.75, 0.12, 0.03, 1.3),
            (0.035, 0.04, (0.6, 0.8), 1.0, 0.16, 0.036, 1.6), (0.05, 0.02, (0.95, 0.35), 0.7, 0.12, 0.028, 1.2),
            (-0.01, 0.06, (-0.2, 1.0), 1.15, 0.17, 0.04, 1.7), (0.015, 0.065, (0.25, 1.0), 1.2, 0.15, 0.034, 1.5),
            (-0.085, 0.05, (-0.8, 0.6), 0.85, 0.11, 0.026, 1.3), (0.08, 0.075, (0.75, 0.65), 0.9, 0.11, 0.026, 1.3),
            (-0.07, -0.05, (-0.9, -0.3), 0.45, 0.09, 0.024, 1.0)]
    lv = leaves(1, [(x, y, 0.004, math.atan2(-d[0], d[1]), rise, L, W, c) for x, y, d, rise, L, W, c in spec])
    return dict(water=w, stone=st, leaves=lv)


# ------------------------------------------------------------------ shots
def shot_A():
    s = bpy.context.scene; s.frame_start, s.frame_end = 1, SHOTS["A"] + HANDLE
    top = 0.012
    n = nature_set(top)
    b = lib.build_bottle()
    root = b["root"]; root.rotation_euler.z = 0.5
    # descends onto the stone: lands at frame 120 (4.0 s), soft settle
    lib.anim(root, "location", [(1, (0, 0, top + 0.075)), (60, (0, 0, top + 0.05)), (112, (0, 0, top + 0.002)), (120, (0, 0, top))])
    lib.anim(root, "rotation_euler", [(1, (0.0, 0.0, 1.3)), (120, (0, 0, 0.5)), (210, (0, 0, 0.45))])
    # ripples: landing ring + a few drops falling into the water around it
    ripple(n["water"], 119, (0.0, 0.0), height=0.00045, falloff=0.3)
    for f, pos in [(30, (-0.09, -0.02)), (80, (0.1, 0.06)), (150, (-0.05, 0.12)), (175, (0.11, -0.05))]:
        ripple(n["water"], f, pos, height=0.00025, falloff=0.12)
    L = lights_nature()
    # light reveal from darkness
    lib.anim(L["rimL"].data, "energy", [(1, 0.0), (18, 0.0), (55, 3.0)])
    lib.anim(L["rimR"].data, "energy", [(1, 0.0), (30, 0.0), (68, 3.0)])
    lib.anim(L["back"].data, "energy", [(1, 0.0), (40, 0.0), (85, 1.6)])
    lib.anim(L["key"].data, "energy", [(1, 0.0), (70, 0.0), (130, 6.0)])
    lib.anim(L["glow"].data, "energy", [(1, 0.0), (60, 0.0), (140, 6.0)])
    cam, tgt, foc = lib.camera("cam", (0.10, -0.30, 0.17), (0, 0, 0.07), 50, 3.2)
    lib.anim(cam, "location", [(1, (0.03, -0.30, 0.12)), (100, (0.10, -0.46, 0.13)), (203, (-0.12, -0.50, 0.085))])
    lib.anim(tgt, "location", [(1, (0, 0, 0.105)), (100, (0, 0, 0.085)), (203, (0, 0, 0.07))])
    lib.anim(foc, "location", [(1, (0, -0.012, 0.105)), (100, (0, -0.012, 0.08)), (203, (0, -0.014, 0.07))])
    return s


def shot_B():
    s = bpy.context.scene; s.frame_start, s.frame_end = 1, SHOTS["B"] + HANDLE
    top = 0.012
    nature_set(top)
    b = lib.build_bottle(); root = b["root"]; root.location.z = top; root.rotation_euler.z = 0.45
    d = b["dropper"]
    # lift and slight twist of the dropper, then hold while a drop forms and falls
    lib.anim(d, "location", [(1, (0, 0, 0)), (12, (0, 0, 0)), (58, (0, 0, 0.083)), (113, (0, 0, 0.086))])
    lib.anim(d, "rotation_euler", [(1, (0, 0, 0)), (14, (0, 0, -0.9)), (58, (0, 0, -1.25)), (113, (0, 0, -1.3))])
    # the drop (serum) grows on the tip and falls into the neck
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
    drop = lib.mesh_obj("drop", bm, lib.mat_serum()); drop.parent = root
    tip = 0.0095 + 0.086                                         # tip height above the bottle base when lifted
    R = 0.0013
    lib.anim(drop, "scale", [(1, (0, 0, 0)), (62, (0.0, 0.0, 0.0)), (80, (R * .8, R * .8, R * .9)), (92, (R, R, R * 1.15)),
                             (96, (R * .92, R * .92, R * 1.3)), (104, (R * .95, R * .95, R * 1.2)), (113, (R, R, R))])
    lib.anim(drop, "location", [(62, (0, 0, tip - 0.0004)), (80, (0, 0, tip - R * .8)), (92, (0, 0, tip - R * 1.2)),
                                (96, (0, 0, tip - R * 1.8)), (104, (0, 0, tip - 0.006)), (113, (0, 0, tip - 0.022))])
    for fc in lib._fcurves(drop.animation_data.action):                   # gravity: accelerate after release
        for kp in fc.keyframe_points:
            if kp.co.x >= 96: kp.interpolation = "QUAD"; kp.easing = "EASE_IN"
    lights_nature()
    cam, tgt, foc = lib.camera("cam", (0.0, -0.20, 0.13), (0, 0, 0.12), 100, 3.5)
    lib.anim(cam, "location", [(1, (0.05, -0.16, 0.10)), (55, (0.025, -0.19, 0.125)), (113, (-0.012, -0.20, 0.112))])
    lib.anim(tgt, "location", [(1, (0, 0, 0.096)), (55, (0, 0, 0.118)), (113, (0, 0, 0.103))])
    lib.anim(foc, "location", [(1, (0, -0.01, 0.096)), (55, (0, -0.003, 0.118)), (113, (0, -0.002, 0.104))])
    s.render.use_motion_blur = True; s.render.motion_blur_shutter = 0.5
    return s


def shot_C():
    s = bpy.context.scene; s.frame_start, s.frame_end = 1, SHOTS["C"] + HANDLE
    lib.world_color((0.004, 0.0035, 0.003), 1.0)
    backdrop(0.6, (0.012, 0.009, 0.006), h=1.5, z0=-0.6)
    b = lib.build_bottle(); root = b["root"]
    droplets_on_glass(root)
    piv = bpy.data.objects.new("pivot", None); lib.link(piv); piv.location = (0, 0, 0.0)
    root.parent = piv; root.location = (0, 0, -0.055)
    lib.anim(piv, "rotation_euler", [(1, (0.42, -0.12, -0.6)), (98, (0.5, -0.22, 0.25))])
    lib.anim(root, "rotation_euler", [(1, (0, 0, 0.0)), (98, (0, 0, 1.6))])
    lib.anim(piv, "location", [(1, (0, 0, -0.004)), (50, (0, 0, 0.002)), (98, (0, 0, -0.002))])
    # free droplets drifting in a slow spiral around the bottle
    rnd = random.Random(3); mat = lib.mat_water()
    for i in range(46):
        r = (0.06 + rnd.random() ** 2 * 0.45) * CM * 2.2
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r)
        d = lib.mesh_obj(f"drop{i}", bm, mat)
        a0 = rnd.random() * math.tau; rad = 0.035 + rnd.random() * 0.045; z0 = (rnd.random() - .5) * 0.13
        sp = (0.5 + rnd.random() * 0.7) * (1 if i % 3 else -1); ph = rnd.random() * 6
        ks, kr = [], []
        for f in range(1, 99, 6):
            a = a0 + sp * f / 30 * 0.55
            ks.append((f, (math.cos(a) * rad, math.sin(a) * rad * 0.9, z0 + 0.006 * math.sin(f / 30 * 1.3 + ph))))
            w = 1 + 0.08 * math.sin(f / 30 * 7 + ph)
            kr.append((f, (w, w, 1 / w)))
        lib.anim(d, "location", ks); lib.anim(d, "scale", kr)
    lib.area_light("key", (-0.25, -0.22, 0.2), (0, 0, 0), 0.25, 0.25, 4.0, (1, 0.95, 0.88))
    lib.area_light("rimL", (-0.16, 0.14, 0.04), (0, 0, 0), 0.015, 0.4, 3.2)
    lib.area_light("rimR", (0.17, 0.12, 0.06), (0, 0, 0), 0.015, 0.4, 3.2)
    lib.area_light("back", (0.02, 0.22, -0.02), (0, 0, 0), 0.12, 0.12, 2.0, (1, 0.7, 0.4))
    lib.area_light("glow", (0.0, 0.22, 0.02), (0, 0.5, 0.1), 0.3, 0.3, 4.0, (1, 0.78, 0.5), glossy=False)
    cam, tgt, foc = lib.camera("cam", (0.0, -0.3, 0.02), (0, 0, 0), 75, 2.8)
    lib.anim(cam, "location", [(1, (-0.11, -0.40, 0.07)), (98, (0.09, -0.37, -0.015))])
    lib.anim(tgt, "location", [(1, (0, 0, 0.004)), (98, (0, 0, 0.0))])
    lib.anim(foc, "location", [(1, (0, -0.014, 0.0)), (98, (0, -0.014, 0.0))])
    s.render.use_motion_blur = True; s.render.motion_blur_shutter = 0.5
    return s


def shot_D():
    s = bpy.context.scene; s.frame_start, s.frame_end = 1, SHOTS["D"] + HANDLE
    lib.world_color((0.004, 0.004, 0.0035), 1.0)
    backdrop(0.42, (0.022, 0.016, 0.011), h=1.0)
    lib.area_light("wallglow", (0.0, 0.12, 0.05), (0, 0.42, 0.16), 0.25, 0.25, 2.0, (1, 0.8, 0.55), glossy=False)
    grid("floor", 3.0, 1, lib.mat_glossy_floor((0.012, 0.009, 0.007), 0.08), z=0.0)
    # stone plinth (travertine-like, soft bevel)
    prof = [(0, 0.0), (5.2, 0.0), (5.4, 0.15), (5.4, 2.85), (5.2, 3.0), (0, 3.0)]
    pl = lib.lathe("plinth", [(r * CM, z * CM) for r, z in prof], 160, lib.mat_stone(0.09, 0.3)); lib.smooth_by_angle(pl, 40)
    b = lib.build_bottle(); root = b["root"]; root.location.z = 0.03; root.rotation_euler.z = 0.35
    lib.anim(root, "rotation_euler", [(1, (0, 0, -0.25)), (113, (0, 0, 0.35))])
    # leaf-shadow gobo: leaves between a hard light and the backdrop
    gob = leaves(7, [(0.10 + 0.03 * math.sin(i), 0.2 + 0.02 * i, 0.12 + 0.03 * math.cos(i * 2), math.radians(40 * i), math.radians(70 + 10 * i % 30), 0.10, 0.025, 0.6) for i in range(9)])
    for g in gob: g.visible_camera = False
    sun = lib.area_light("gobo", (0.32, -0.05, 0.42), (-0.05, 0.42, 0.12), 0.01, 0.01, 30.0, (1, 0.88, 0.7))
    lib.area_light("key", (-0.28, -0.24, 0.24), (0, 0, 0.07), 0.3, 0.3, 5.0, (1, 0.96, 0.9))
    lib.area_light("rimL", (-0.17, 0.15, 0.12), (0, 0, 0.08), 0.015, 0.4, 3.0)
    lib.area_light("rimR", (0.17, 0.14, 0.12), (0, 0, 0.08), 0.015, 0.4, 3.0)
    lib.area_light("back", (0.0, 0.25, 0.08), (0, 0, 0.08), 0.12, 0.12, 1.6, (1, 0.72, 0.42))
    cam, tgt, foc = lib.camera("cam", (0.0, -0.42, 0.11), (0, 0, 0.085), 50, 4.0)
    lib.anim(cam, "location", [(1, (0.07, -0.42, 0.14)), (113, (0.0, -0.34, 0.10))])
    lib.anim(tgt, "location", [(1, (0, 0, 0.09)), (113, (0, 0, 0.083))])
    lib.anim(foc, "location", [(1, (0, -0.014, 0.08)), (113, (0, -0.014, 0.08))])
    return s


if __name__ == "__main__":
    shot, out = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    opt = {args[i]: args[i + 1] for i in range(0, len(args) - 1, 2)}
    s = lib.reset()
    s.cycles.samples = int(opt.get("--spp", 8))
    s.render.resolution_percentage = int(opt.get("--pct", 100))
    {"A": shot_A, "B": shot_B, "C": shot_C, "D": shot_D}[shot]()
    os.makedirs(out, exist_ok=True)
    frames = [int(f) for f in opt["--frames"].split(",")] if "--frames" in opt else range(s.frame_start, s.frame_end + 1)
    import time
    for f in frames:
        path = os.path.join(out, f"{shot}_{f:04d}.png")
        if os.path.exists(path): continue
        t = time.time()
        s.frame_set(f); s.render.filepath = path + ".tmp.png"
        bpy.ops.render.render(write_still=True)
        os.replace(path + ".tmp.png", path)
        print(f"SHOT {shot} frame {f} {time.time() - t:.1f}s", flush=True)
