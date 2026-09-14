# =============================================================================
#  THE TRILOGY — ⊕ · u · h·n̂
#  Blender 4.5 LTS · single script · 450 frames · 3 acts × 150
#
#  Act I   MEZCLA   (f 1–150)   : 15 blend modes iterated to their fixed points
#                                 as a garden of columns (bₙ₊₁ = bₙ ⊕ l)
#  Act II  MAPA     (f 151–300) : UV mapping — belonging, seams, distortion
#                                 (checker = texel density, RG gradient = address)
#  Act III RELIEVE  (f 301–450) : bump twin vs displacement twin,
#                                 orbiting light kills one and not the other
#
#  HOW TO USE YOUR OWN OBJECTS / TEXTURES → edit CONFIG below, run in the
#  Scripting tab (Alt+P). Everything is created in collection "TRILOGY".
# =============================================================================

import bpy, math
from mathutils import Vector, Matrix

# ----------------------------- CONFIG ----------------------------------------
CONFIG = {
    # Names of objects ALREADY in your scene to use instead of the defaults.
    # Leave as None to auto-generate primitives.
    "act2_object": None,        # e.g. "MyStatue"  (needs/gets UVs)
    "act3_object": None,        # e.g. "MyTerrain" (will be duplicated as twins)

    # Path to an image texture (color for Act II, height for Act III).
    # Leave as None for procedural (checker / noise / clouds).
    "image_path": None,         # e.g. r"C:\textures\pattern.png"

    "fps": 30,
    "iterations": 30,           # cobweb steps in Act I
    "l_value": 0.35,            # the constant blend layer l
    "b0": 0.15,                 # initial base value
    "column_max_h": 4.0,        # height that b = 1.0 maps to
}
# ------------------------------------------------------------------------------

F1, F2, F3, F_END = 1, 151, 301, 450

# --- the 15 operations ⊕ : [0,1]² → [0,1] ------------------------------------
def _soft(b, l):
    if l <= .5: return b - (1-2*l)*b*(1-b)
    d = ((16*b-12)*b+4)*b if b <= .25 else math.sqrt(b)
    return b + (2*l-1)*(d-b)

MODES = {
    "normal":     lambda b,l: l,
    "multiply":   lambda b,l: b*l,
    "screen":     lambda b,l: 1-(1-b)*(1-l),
    "overlay":    lambda b,l: 2*b*l if b<=.5 else 1-2*(1-b)*(1-l),
    "hardlight":  lambda b,l: 2*b*l if l<=.5 else 1-2*(1-b)*(1-l),
    "softlight":  _soft,
    "darken":     lambda b,l: min(b,l),
    "lighten":    lambda b,l: max(b,l),
    "colordodge": lambda b,l: 1.0 if l>=1 else min(1, b/(1-l)),
    "colorburn":  lambda b,l: 0.0 if l<=0 else 1-min(1,(1-b)/l),
    "difference": lambda b,l: abs(b-l),
    "exclusion":  lambda b,l: b+l-2*b*l,
    "linearburn": lambda b,l: max(0, b+l-1),
    "add":        lambda b,l: min(1, b+l),
    "subtract":   lambda b,l: max(0, b-l),
}
clamp = lambda v: max(0.0, min(1.0, v))

# ----------------------------- scene reset -----------------------------------
scn = bpy.context.scene
scn.frame_start, scn.frame_end = F1, F_END
scn.render.fps = CONFIG["fps"]
if "TRILOGY" in bpy.data.collections:                      # re-run friendly
    col = bpy.data.collections["TRILOGY"]
    for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("TRILOGY")
    scn.collection.children.link(col)

def link(obj):
    for c in obj.users_collection: c.objects.unlink(obj)
    col.objects.link(obj)
    return obj

def hide_span(obj, visible_from, visible_to):
    """Object renders only inside [visible_from, visible_to]."""
    for fr, hid in ((visible_from-1, True), (visible_from, False),
                    (visible_to, False), (visible_to+1, True)):
        if fr < F1 or fr > F_END: continue
        obj.hide_render = hid; obj.hide_viewport = hid
        obj.keyframe_insert("hide_render", frame=fr)
        obj.keyframe_insert("hide_viewport", frame=fr)

def new_mat(name, hue=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    if hue is not None:
        import colorsys
        r,g,b = colorsys.hsv_to_rgb(hue, .65, .9)
        bsdf.inputs["Base Color"].default_value = (r,g,b,1)
    bsdf.inputs["Roughness"].default_value = 0.45
    return m, bsdf

def load_image():
    if CONFIG["image_path"]:
        try: return bpy.data.images.load(CONFIG["image_path"])
        except Exception: print("!! image not found, using procedural")
    return None
IMG = load_image()

# =============================================================================
#  ACT I — MEZCLA · fixed-point garden (frames 1–150)
# =============================================================================
names = list(MODES)
COLS, ROWS, GAP = 5, 3, 2.2
l, b0, K = CONFIG["l_value"], CONFIG["b0"], CONFIG["iterations"]

for i, nm in enumerate(names):
    x = (i % COLS - (COLS-1)/2) * GAP
    y = (i // COLS - (ROWS-1)/2) * GAP
    bpy.ops.mesh.primitive_cylinder_add(radius=.55, depth=1, location=(x, y, 0))
    ob = link(bpy.context.active_object)
    ob.name = f"col_{nm}"
    # pivot at base: shift the MESH up so local z ∈ [0,1]; scale.z now grows from floor
    ob.data.transform(Matrix.Translation((0, 0, 0.5)))
    m, bsdf = new_mat(f"m_{nm}", hue=i/len(names))
    ob.data.materials.append(m)

    # iterate bₙ₊₁ = bₙ ⊕ l and keyframe height + emission pulse
    b = b0
    for k in range(K+1):
        fr = F1 + round(k * (F2-2-F1) / K)
        h = 0.05 + b * CONFIG["column_max_h"]
        ob.scale = (1, 1, h)
        ob.keyframe_insert("scale", frame=fr)
        bsdf.inputs["Emission Strength"].default_value = 2.5*b
        bsdf.inputs["Emission Color"].default_value = bsdf.inputs["Base Color"].default_value
        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)
        b = clamp(MODES[nm](b, l))
    hide_span(ob, F1, F2-1)

# floor for act I
bpy.ops.mesh.primitive_plane_add(size=30, location=(0,0,0))
floor = link(bpy.context.active_object); floor.name = "floor_I"
fm,_ = new_mat("m_floor"); fm.node_tree.nodes["Principled BSDF"]\
    .inputs["Base Color"].default_value = (.05,.05,.06,1)
floor.data.materials.append(fm)
hide_span(floor, F1, F2-1)

# =============================================================================
#  ACT II — MAPA · belonging, seams, distortion (frames 151–300)
# =============================================================================
if CONFIG["act2_object"] and CONFIG["act2_object"] in bpy.data.objects:
    a2 = bpy.data.objects[CONFIG["act2_object"]]
    a2 = a2.copy(); a2.data = a2.data.copy(); link(a2)
else:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=2.2, segments=48, ring_count=24,
                                         location=(0,0,2.2))
    a2 = link(bpy.context.active_object)
a2.name = "MAPA"
bpy.ops.object.select_all(action='DESELECT')
a2.select_set(True)
bpy.context.view_layer.objects.active = a2
if not a2.data.uv_layers:
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66))
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()

# material: mix( UV-address gradient (u→R, v→G) , checker/texture = texel density )
m2 = bpy.data.materials.new("m_MAPA"); m2.use_nodes = True
nt = m2.node_tree; n = nt.nodes; lk = nt.links
bsdf2 = n["Principled BSDF"]
uvn   = n.new("ShaderNodeUVMap")
sep   = n.new("ShaderNodeSeparateXYZ")
comb  = n.new("ShaderNodeCombineColor")
if IMG:
    tex = n.new("ShaderNodeTexImage"); tex.image = IMG
else:
    tex = n.new("ShaderNodeTexChecker"); tex.inputs["Scale"].default_value = 24
mix   = n.new("ShaderNodeMix"); mix.data_type = 'RGBA'
lk.new(uvn.outputs["UV"], sep.inputs["Vector"])
lk.new(sep.outputs["X"], comb.inputs["Red"])
lk.new(sep.outputs["Y"], comb.inputs["Green"])
comb.inputs["Blue"].default_value = 0.15
lk.new(uvn.outputs["UV"], tex.inputs["Vector"])
# ShaderNodeMix gotcha: inputs["A"]/["B"] return the FLOAT sockets;
# for data_type='RGBA' the color sockets are inputs[6]/[7], output is outputs[2]
lk.new(comb.outputs["Color"], mix.inputs[6])         # A: pure address
lk.new(tex.outputs["Color"],  mix.inputs[7])         # B: density/distortion
lk.new(mix.outputs[2], bsdf2.inputs["Base Color"])
a2.data.materials.clear(); a2.data.materials.append(m2)

# animate: address → distortion-reveal → address  (0 → 1 → 0)
fmix = mix.inputs["Factor"]
for fr, v in ((F2,0.0),(F2+70,1.0),(F3-10,0.0)):
    fmix.default_value = v
    fmix.keyframe_insert("default_value", frame=fr)
# slow rotation = the observer walks the atlas
a2.rotation_euler = (0,0,0); a2.keyframe_insert("rotation_euler", frame=F2)
a2.rotation_euler = (0,0,math.tau); a2.keyframe_insert("rotation_euler", frame=F3-1)
hide_span(a2, F2, F3-1)

# =============================================================================
#  ACT III — RELIEVE · bump twin vs displacement twin (frames 301–450)
# =============================================================================
def make_relief_base(x):
    if CONFIG["act3_object"] and CONFIG["act3_object"] in bpy.data.objects:
        src = bpy.data.objects[CONFIG["act3_object"]]
        ob = src.copy(); ob.data = src.data.copy(); link(ob)
        ob.location = (x, 0, ob.location.z)
    else:
        bpy.ops.mesh.primitive_grid_add(size=3.4, x_subdivisions=120,
                                        y_subdivisions=120, location=(x, 0, 1.8))
        ob = link(bpy.context.active_object)
        ob.rotation_euler.x = math.radians(90)   # stand it up, facing camera
    return ob

bump_tw = make_relief_base(-2.2); bump_tw.name = "TWIN_bump"
disp_tw = make_relief_base( 2.2); disp_tw.name = "TWIN_displace"

# shared shader (color + height source)
def relief_mat(name, use_bump):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; lk = nt.links
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (.82,.78,.72,1)
    bsdf.inputs["Roughness"].default_value = .6
    if IMG:
        h = n.new("ShaderNodeTexImage"); h.image = IMG
        hout = h.outputs["Color"]
    else:
        h = n.new("ShaderNodeTexNoise"); h.inputs["Scale"].default_value = 5.0
        h.inputs["Detail"].default_value = 8.0
        hout = h.outputs["Fac"]
    if use_bump:
        bmp = n.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = 0.9
        lk.new(hout, bmp.inputs["Height"])
        lk.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    return m

bump_tw.data.materials.clear()
bump_tw.data.materials.append(relief_mat("m_bump", True))
disp_tw.data.materials.clear()
disp_tw.data.materials.append(relief_mat("m_disp", False))

# real displacement on the right twin (legacy texture ≈ shader noise)
if IMG:
    dtex = bpy.data.textures.new("t_disp", 'IMAGE'); dtex.image = IMG
else:
    dtex = bpy.data.textures.new("t_disp", 'CLOUDS')
    dtex.noise_scale = 0.55; dtex.noise_depth = 6
md = disp_tw.modifiers.new("Relief", 'DISPLACE')
md.texture = dtex; md.mid_level = 0.5
md.strength = 0.0;  md.keyframe_insert("strength", frame=F3)
md.strength = 0.45; md.keyframe_insert("strength", frame=F3+40)

for tw in (bump_tw, disp_tw): hide_span(tw, F3, F_END)

# floor for act III (catches the REAL shadow)
bpy.ops.mesh.primitive_plane_add(size=30, location=(0,0,-0.01))
floor3 = link(bpy.context.active_object); floor3.name = "floor_III"
floor3.data.materials.append(fm)
hide_span(floor3, F3, F_END)

# orbiting light — one full lap over Act III
piv = bpy.data.objects.new("light_pivot", None); link(piv)
piv.location = (0,0,2.0)
ld = bpy.data.lights.new("orbiter", 'SPOT'); ld.energy = 3000
ld.spot_size = math.radians(70)
lo = bpy.data.objects.new("orbiter", ld); link(lo)
lo.parent = piv; lo.location = (0,-8,1.5)
lo.rotation_euler = (math.radians(78),0,0)
piv.rotation_euler.z = 0;        piv.keyframe_insert("rotation_euler", frame=F3)
piv.rotation_euler.z = math.tau; piv.keyframe_insert("rotation_euler", frame=F_END)
try:  # legacy fcurves view still works on single-slot actions in 4.4/4.5
    for fc in piv.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
except AttributeError:
    pass  # orbit will just ease instead of being perfectly linear
hide_span(lo, F3, F_END)

# key light for acts I & II
kd = bpy.data.lights.new("key", 'AREA'); kd.energy = 1200; kd.size = 8
ko = bpy.data.objects.new("key", kd); link(ko)
ko.location = (5,-6,7); ko.rotation_euler = (math.radians(55),0,math.radians(38))
hide_span(ko, F1, F3-1)

# =============================================================================
#  CAMERAS — one per act, bound by timeline markers
# =============================================================================
def cam(name, loc, rot):
    cd = bpy.data.cameras.new(name)
    c = bpy.data.objects.new(name, cd); link(c)
    c.location, c.rotation_euler = loc, rot
    return c

c1 = cam("CAM_I",  (0,-13,7),  (math.radians(62),0,0))
c2 = cam("CAM_II", (0,-8.5,3), (math.radians(80),0,0))
c3 = cam("CAM_III",(0,-8,1.9), (math.radians(88),0,0))
# Act III camera slides to grazing angle: the silhouette test
c3.keyframe_insert("location", frame=F3)        # start pose FIRST
c3.keyframe_insert("rotation_euler", frame=F3)
c3.location = (-7.5,-3.5,1.9)
c3.rotation_euler = (math.radians(88),0,math.radians(-62))
c3.keyframe_insert("location", frame=F_END)
c3.keyframe_insert("rotation_euler", frame=F_END)

scn.timeline_markers.clear()
for nm, fr, c in (("MEZCLA",F1,c1),("MAPA",F2,c2),("RELIEVE",F3,c3)):
    mk = scn.timeline_markers.new(nm, frame=fr); mk.camera = c
scn.camera = c1

# world + engine
scn.world = scn.world or bpy.data.worlds.new("W")
scn.world.use_nodes = True
scn.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.012,.013,.018,1)
try: scn.render.engine = 'BLENDER_EEVEE_NEXT'
except TypeError: scn.render.engine = 'BLENDER_EEVEE'

print("TRILOGY ready · 450 frames · markers: MEZCLA / MAPA / RELIEVE")
