"""Quick look-dev render of the bottle: python3 test_bottle.py <out.png> [percent] [samples]"""
import sys, os, time, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import lib

out = sys.argv[1]; pct = int(sys.argv[2]) if len(sys.argv) > 2 else 50; spp = int(sys.argv[3]) if len(sys.argv) > 3 else 64
s = lib.reset(); s.render.resolution_x, s.render.resolution_y = 720, 1280; s.render.resolution_percentage = pct; s.cycles.samples = spp
b = lib.build_bottle()
b["root"].rotation_euler.z = 0.4
floor = lib.leaf  # noqa
import bmesh
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
fl = lib.mesh_obj("floor", bm, lib.mat_glossy_floor())
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
bd = lib.mesh_obj("backdrop", bm, lib.mat_backdrop((0.02, 0.018, 0.016)))
bd.rotation_euler.x = math.pi / 2; bd.location = (0, 0.35, 0.5)
lib.area_light("key", (-0.22, -0.12, 0.2), (0, 0, 0.05), 0.06, 0.5, 3)
lib.area_light("rimL", (-0.12, 0.15, 0.08), (0, 0, 0.05), 0.02, 0.3, 2)
lib.area_light("rimR", (0.14, 0.12, 0.1), (0, 0, 0.05), 0.02, 0.3, 2)
lib.area_light("back", (0.0, 0.3, 0.06), (0, 0, 0.05), 0.15, 0.15, 1.5, (1, 0.75, 0.45))
lib.camera("cam", (0.0, -0.42, 0.075), (0, 0, 0.058), 85, 5.6)
s.render.filepath = out
t = time.time(); bpy.ops.render.render(write_still=True); print("render s", round(time.time() - t, 1))
