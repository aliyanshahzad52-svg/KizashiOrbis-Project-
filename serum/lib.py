"""Shared building blocks for the unbranded serum-bottle commercial (Blender / Cycles via the bpy module).

All dimensions are real-world metres (the bottle is ~12 cm tall with its dropper), so depth of field and
light falloff behave like a real macro product shoot. Nothing here carries text, labels or logos.
"""
import math
import random

import bmesh
import bpy
import addon_utils
from mathutils import Vector, Matrix

CM = 0.01


# ------------------------------------------------------------------ scene / render setup
def reset(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("cycles", default_set=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.render.fps = fps
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1080, 1920, 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "8"
    s.render.film_transparent = False
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    s.view_settings.exposure = 0.0
    c = s.cycles
    c.samples = 96
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    c.max_bounces = 12
    c.diffuse_bounces = 3
    c.glossy_bounces = 8
    c.transmission_bounces = 12
    c.transparent_max_bounces = 8
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 0.6
    c.sample_clamp_indirect = 6.0
    c.seed = 7
    c.use_animated_seed = False          # fixed noise pattern + denoiser = no shimmer between frames
    s.render.use_persistent_data = True
    w = bpy.data.worlds.new("World"); s.world = w; w.use_nodes = True
    world_color((0.004, 0.004, 0.004), 1.0)
    return s


def world_color(rgb, strength):
    w = bpy.context.scene.world
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*rgb, 1); bg.inputs[1].default_value = strength


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); link(ob)
    if mat: ob.data.materials.append(mat)
    return ob


def lathe(name, prof, steps=128, mat=None, closed_axis=True):
    """Revolve a (r, z) profile (metres) around Z."""
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=steps, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat)


def subsurf(ob, lv=2):
    """Subdivide once at build time (baked), so the renderer never re-evaluates it per frame."""
    m = ob.modifiers.new("sub", "SUBSURF"); m.levels = lv; m.render_levels = lv
    bake_modifiers(ob)
    return ob


def bake_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data; ob.modifiers.clear(); ob.data = me
    if old.users == 0: bpy.data.meshes.remove(old)


def smooth_by_angle(ob, deg=40):
    me = ob.data
    for p in me.polygons: p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(deg): e.smooth = False
    bm.to_mesh(me); bm.free()


# ------------------------------------------------------------------ materials
def _p(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    return m, nt, p


def mat_amber_glass():
    m, nt, p = _p("AmberGlass")
    p.inputs["Base Color"].default_value = (1, 1, 1, 1)
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.015
    p.inputs["IOR"].default_value = 1.52
    p.inputs["Coat Weight"].default_value = 0.0
    va = nt.nodes.new("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = (0.964, 0.866, 0.69, 1)
    va.inputs["Density"].default_value = 1400.0
    nt.links.new(va.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m


def mat_serum():
    m, nt, p = _p("Serum")
    p.inputs["Base Color"].default_value = (1, 1, 1, 1)
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.0
    p.inputs["IOR"].default_value = 1.42
    va = nt.nodes.new("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = (0.978, 0.894, 0.66, 1)
    va.inputs["Density"].default_value = 160.0
    nt.links.new(va.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m


def mat_air_bubble():
    m, nt, p = _p("Bubble")
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.0
    p.inputs["IOR"].default_value = 1.0 / 1.42
    return m


def mat_clear_glass():
    m, nt, p = _p("ClearGlass")
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.01
    p.inputs["IOR"].default_value = 1.5
    return m


def mat_water(rough=0.0):
    m, nt, p = _p("Water")
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = rough
    p.inputs["IOR"].default_value = 1.333
    return m


def mat_black_plastic():
    """Glossy black cap collar (fine radial brushing via anisotropy)."""
    m, nt, p = _p("CapPlastic")
    p.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
    p.inputs["Roughness"].default_value = 0.22
    p.inputs["Specular IOR Level"].default_value = 0.55
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Coat Roughness"].default_value = 0.05
    return m


def mat_rubber():
    m, nt, p = _p("Rubber")
    p.inputs["Base Color"].default_value = (0.014, 0.014, 0.015, 1)
    p.inputs["Roughness"].default_value = 0.42
    p.inputs["Specular IOR Level"].default_value = 0.45
    p.inputs["Sheen Weight"].default_value = 0.15
    return m


def mat_stone(dark=0.05, wet=0.35, dry=0.9):
    m, nt, p = _p("Stone")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 180; n1.inputs["Detail"].default_value = 12; n1.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (dark * 0.6, dark * 0.62, dark * 0.6, 1)
    ramp.color_ramp.elements[1].color = (dark * 2.2, dark * 2.1, dark * 1.9, 1)
    nt.links.new(n1.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], p.inputs["Base Color"])
    p.inputs["Specular IOR Level"].default_value = 0.12
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = wet; rr.inputs[4].default_value = dry
    nt.links.new(n1.outputs["Fac"], rr.inputs[0]); nt.links.new(rr.outputs[0], p.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.0004
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 900; n2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"]); nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], p.inputs["Normal"])
    return m


def mat_leaf(hue=(0.05, 0.16, 0.035)):
    """Leaf: waxy front, light shining through (translucency), fine vein pattern."""
    m = bpy.data.materials.new("Leaf"); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # veins: thin lines along UV.u from the midrib
    wave = nt.nodes.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 18; wave.inputs["Distortion"].default_value = 2; wave.inputs["Detail"].default_value = 2
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, 0.6)
    nt.links.new(tc.outputs["UV"], mp.inputs[0]); nt.links.new(mp.outputs[0], wave.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 6
    nt.links.new(tc.outputs["UV"], noise.inputs["Vector"])
    col = nt.nodes.new("ShaderNodeMix"); col.data_type = "RGBA"
    col.inputs[6].default_value = (*hue, 1); col.inputs[7].default_value = (hue[0] * 1.9, hue[1] * 1.6, hue[2] * 1.2, 1)
    nt.links.new(noise.outputs["Fac"], col.inputs[0])
    nt.links.new(col.outputs[2], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.38
    p.inputs["Coat Weight"].default_value = 0.25; p.inputs["Coat Roughness"].default_value = 0.2
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], p.inputs["Normal"])
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent"); nt.links.new(col.outputs[2], tr.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs[0].default_value = 0.28
    nt.links.new(p.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def mat_moss():
    m, nt, p = _p("Moss")
    p.inputs["Base Color"].default_value = (0.045, 0.085, 0.018, 1)
    p.inputs["Roughness"].default_value = 0.55
    p.inputs["Subsurface Weight"].default_value = 0.15
    return m


def mat_backdrop(c1=(0.03, 0.028, 0.026), c2=(0.0, 0.0, 0.0), rough=0.6):
    m, nt, p = _p("Backdrop")
    p.inputs["Base Color"].default_value = (*c1, 1)
    p.inputs["Roughness"].default_value = rough
    return m


def mat_glossy_floor(col=(0.006, 0.006, 0.006), rough=0.06):
    m, nt, p = _p("Floor")
    p.inputs["Base Color"].default_value = (*col, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Specular IOR Level"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 30
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value = rough * .7; rr.inputs[4].default_value = rough * 1.6
    nt.links.new(n.outputs["Fac"], rr.inputs[0]); nt.links.new(rr.outputs[0], p.inputs["Roughness"])
    return m


def mat_emit(col, strength):
    m = bpy.data.materials.new("Emit"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL": nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


# ------------------------------------------------------------------ the product
def _round_corner(p0, c, r, a0, a1, n=8):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def bottle_profiles():
    """Boston-round 30 ml bottle, in cm. Returns (glass_closed_profile, liquid_profile, fill_height)."""
    R, H_SH, NECK, TOP = 1.65, 5.9, 0.78, 8.15
    t, tb = 0.16, 0.45                                       # wall / base thickness
    out = [(0.0, 0.0), (R - 0.35, 0.0)]
    out += _round_corner(None, (R - 0.35, 0.35), 0.35, -math.pi / 2, 0, 6)[1:]
    out += [(R, H_SH)]
    # shoulder: smooth quarter-ellipse into the neck
    for i in range(1, 13):
        a = i / 12 * math.pi / 2
        out.append((NECK + (R - NECK) * math.cos(a), H_SH + 1.25 * math.sin(a)))
    out += [(NECK, TOP - 0.25), (NECK + 0.04, TOP - 0.12), (NECK + 0.04, TOP), (NECK - t * 0.9, TOP)]
    Ri, Ni = R - t, NECK - t * 0.9
    inn = [(Ni, H_SH + 1.25 - 0.05)]
    for i in range(12, -1, -1):
        a = i / 12 * math.pi / 2
        inn.append((Ni + (Ri - Ni) * math.cos(a), H_SH - 0.02 + (1.25 - 0.1) * math.sin(a)))
    inn += [(Ri, 0.35 + tb * .4)]
    inn += _round_corner(None, (Ri - 0.25, tb + 0.25), 0.25, 0, -math.pi / 2, 5)[1:]
    inn += [(0.0, tb)]
    glass = out + inn
    glass = [(r * CM, z * CM) for r, z in glass]
    fill = 5.35
    g = 0.012
    liq = [(0.0, tb + g), (Ri - 0.25 - g, tb + g)]
    liq += _round_corner(None, (Ri - 0.25, tb + 0.25), 0.25 - g, -math.pi / 2, 0, 5)[1:]
    liq += [(Ri - g, fill), (0.0, fill)]
    liq = [(r * CM, z * CM) for r, z in liq]
    return glass, liq, fill * CM


def build_bottle(seed=3, bubbles=140):
    """Returns dict of objects. Root empty 'bottle' at base centre; 'dropper' empty is the removable cap+pipette."""
    root = bpy.data.objects.new("bottle", None); link(root)
    glass_p, liq_p, fill = bottle_profiles()
    gl = lathe("glass", glass_p, 160, mat_amber_glass()); gl.parent = root; subsurf(gl, 2)
    lq = lathe("serum", liq_p, 128, mat_serum()); lq.parent = root; subsurf(lq, 1)
    # suspended micro-bubbles in the serum
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(bubbles):
        rr = 0.012 + rnd.random() ** 3 * 0.05
        a = rnd.random() * math.tau; rad = math.sqrt(rnd.random()) * (1.3 - rr)
        z = 0.7 + rnd.random() * (fill / CM - 0.95)
        ret = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rr * CM)
        bmesh.ops.translate(bm, verts=ret["verts"], vec=(math.cos(a) * rad * CM, math.sin(a) * rad * CM, z * CM))
    bb = mesh_obj("bubbles", bm, mat_air_bubble()); bb.parent = root

    drop = bpy.data.objects.new("dropper", None); link(drop); drop.parent = root
    # ribbed collar (screw cap) - fine vertical knurling
    TOP = 8.15
    prof = [(0.0, TOP - 0.02), (0.6, TOP - 0.02), (0.6, TOP - 0.45), (0.97, TOP - 0.45), (1.0, TOP - 0.4), (1.0, TOP + 1.25),
            (0.97, TOP + 1.3), (0.62, TOP + 1.32), (0.62, TOP + 1.5), (0.0, TOP + 1.5)]
    cap = lathe("cap", [(r * CM, z * CM) for r, z in prof], 360, mat_black_plastic())
    me = cap.data
    for v in me.vertices:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.985 * CM and (TOP - 0.38) * CM < v.co.z < (TOP + 1.22) * CM:
            a = math.atan2(v.co.y, v.co.x)
            k = 1 + 0.022 * (abs(math.cos(30 * a)) ** 0.6 - 0.5)
            v.co.x *= k; v.co.y *= k
    cap.parent = drop; smooth_by_angle(cap, 40)
    # rubber bulb: soft dome with a slight waist
    bp = [(0.0, TOP + 1.45), (0.6, TOP + 1.45)]
    for i in range(1, 25):
        u = i / 24
        z = TOP + 1.45 + u * 2.5
        r = 0.6 + 0.08 * math.sin(u * math.pi * 1.1) - 0.05 * math.sin(u * math.pi * 3) * (u < .4)
        if u > 0.62: r *= math.sqrt(max(0.0, 1 - ((u - 0.62) / 0.38) ** 2))
        bp.append((max(r, 0.0), z))
    bp.append((0.0, TOP + 3.95))
    bulb = lathe("bulb", [(r * CM, z * CM) for r, z in bp], 96, mat_rubber()); bulb.parent = drop; subsurf(bulb, 2)
    # glass pipette with serum inside
    pp = [(0.0, 0.95), (0.06, 0.95), (0.12, 1.3), (0.23, 1.9), (0.23, TOP - 0.05), (0.0, TOP - 0.05)]
    pip = lathe("pipette", [(r * CM, z * CM) for r, z in pp], 64, mat_clear_glass()); pip.parent = drop; subsurf(pip, 1)
    pl = [(0.0, 1.0), (0.04, 1.0), (0.09, 1.3), (0.17, 1.9), (0.17, 4.6), (0.0, 4.6)]
    pliq = lathe("pipette_serum", [(r * CM, z * CM) for r, z in pl], 48, mat_serum()); pliq.parent = drop; subsurf(pliq, 1)
    return dict(root=root, glass=gl, serum=lq, dropper=drop, cap=cap, bulb=bulb, pipette=pip, fill=fill)


# ------------------------------------------------------------------ nature
def stone(name, size, seed, squash=0.55, mat=None):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    rnd = random.Random(seed); off = Vector((rnd.random() * 9, rnd.random() * 9, rnd.random() * 9))
    from mathutils import noise
    for v in bm.verts:
        p = v.co
        d = 0.16 * noise.fractal(p * 0.9 + off, 0.5, 2.0, 3) + 0.012 * noise.noise(p * 5 + off)
        v.co = p * (1 + d)
        v.co.z *= squash
    ob = mesh_obj(name, bm, mat or mat_stone())
    ob.scale = (size, size * (0.8 + 0.4 * rnd.random()), size)
    return ob


def leaf(name, length, width, curl=0.6, fold=0.25, mat=None, seg=36, wseg=8, twist=0.0):
    """Lanceolate leaf as a curved, folded surface (UV u along length)."""
    bm = bmesh.new(); uv_layer = bm.loops.layers.uv.new()
    grid = []
    for i in range(seg + 1):
        u = i / seg
        w = width * (math.sin(math.pi * min(1, u * 1.04)) ** 0.75) * (1 - 0.25 * u)
        row = []
        for j in range(wseg + 1):
            v = j / wseg * 2 - 1
            x = v * w * 0.5
            ang = curl * u ** 1.6
            y0 = length * u
            zf = fold * abs(v) * w * 0.5                     # V-shaped midrib fold
            y = math.sin(ang) * 0 + y0 * math.cos(ang * .5)
            z = zf + length * (1 - math.cos(ang)) * 0.45
            tw = twist * u
            xr = x * math.cos(tw) - z * math.sin(tw); zr = x * math.sin(tw) + z * math.cos(tw)
            row.append(bm.verts.new((xr, y, zr)))
        grid.append(row)
    for i in range(seg):
        for j in range(wseg):
            f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            for l, (a, b) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))):
                l[uv_layer].uv = (a / wseg, b / seg)
    ob = mesh_obj(name, bm, mat)
    sm = ob.modifiers.new("solid", "SOLIDIFY"); sm.thickness = 0.0006
    return ob


def area_light(name, loc, look_at, size, size_y, energy, color=(1, 1, 1), spread=180, glossy=True):
    ld = bpy.data.lights.new(name, "AREA"); ld.shape = "RECTANGLE"; ld.size = size; ld.size_y = size_y
    ld.energy = energy; ld.color = color; ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld); link(ob); ob.location = loc
    ob.visible_glossy = glossy; ob.visible_camera = False
    aim(ob, look_at)
    return ob


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(name, loc, target, lens, fstop=2.8, focus=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24 * 1.0
    cd.sensor_width = 24 * 1080 / 1920
    cd.clip_start = 0.002; cd.clip_end = 50
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop; cd.dof.aperture_blades = 9; cd.dof.aperture_rotation = 0.3
    ob = bpy.data.objects.new(name, cd); link(ob); ob.location = loc
    tgt = bpy.data.objects.new(name + "_tgt", None); link(tgt); tgt.location = target
    c = ob.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    foc = bpy.data.objects.new(name + "_focus", None); link(foc); foc.location = focus or target
    cd.dof.focus_object = foc
    bpy.context.scene.camera = ob
    return ob, tgt, foc


def key(ob, path, frame, value, interp="BEZIER", ease="AUTO"):
    setattr(ob, path, value) if not isinstance(path, tuple) else None
    ob.keyframe_insert(data_path=path, frame=frame)
    fc = ob.animation_data.action
    return fc


def smooth_keys(ob_or_data):
    ad = ob_or_data.animation_data
    if not ad or not ad.action: return
    for fc in _fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


def _fcurves(action):
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out


def anim(ob, path, keys, data=None):
    """keys: list of (frame, value). Auto-clamped bezier = smooth ease in/out."""
    tgt = data or ob
    for f, v in keys:
        setattr(tgt, path, v); tgt.keyframe_insert(data_path=path, frame=f)
    smooth_keys(tgt)


def linear(ob, data=None):
    tgt = data or ob
    for fc in _fcurves(tgt.animation_data.action):
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
