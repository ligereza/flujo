# TRILOGY, FUSED - Geometry Nodes build notes

What this folder's Blender piece is, what was fixed in the polish pass
(2026-07-15), and what was learned doing it. Script: `BLENDER.geonodes_450.py`
(Blender 4.5 LTS, headless-friendly, re-run friendly). Outputs land in
`C:\IA\trilogy_out\` (blend + verification frames, 1920x1080).

## The piece in one paragraph

450 frames = 15 blend modes x 30 frames. A Simulation Zone iterates
`b <- b (op) l` once per real frame, so each 30-frame segment is literally 30
iterations toward that operator's fixed point (MEZCLA). The inherited layer is
the address itself, `l = u` (MAPA), so the fixed-point structure of each
operator becomes a terrain profile over the atlas. Two twins share the same
node tree: the STRUCTURE twin really displaces by `b`; the GAZE twin stays
flat and only carries `b` into the shader as bump (RELIEVE). An orbiting spot
tells them apart.

## Polish pass: what changed and why

1. **Default-cube bug.** The scene reset only cleared the `TRILOGY_GN`
   collection, so under `--factory-startup` Blender's startup Cube (plus its
   Light/Camera) survived and rendered as a white box at world center. Fix:
   explicitly remove objects named `Cube` / `Light` / `Camera` via
   `bpy.data.objects.get()` guards, so re-runs on an already-clean scene do
   not raise.
2. **Spot edge.** `ld.spot_blend = 0.35` - the orbiter's pool of light now
   feathers instead of cutting a hard ellipse into the floor.
3. **Floor.** Base color `(.03,.03,.04,1)` + roughness `0.35`. Darker and
   slightly glossy: the floor now reads as a stage with a faint sheen instead
   of flat gray cardboard.
4. **Camera.** Replaced the hand-tuned euler with a computed aim:
   `cam_pitch_to(loc, target)` returns the X pitch (`atan2(dy, -dz)`, camera
   looks down local -Z) toward `CAM_TARGET = (0, 0, 1.7)`. Push-in is now
   `(0,-24,15) -> (0,-21,13.5)` with location AND rotation keyed, so the aim
   holds during the move. Both twins stay fully in frame with ~10% margin even
   at max relief (z = 2.2).

## Learnings (the transferable part)

- **Simulation Zones have no random access.** To see frame N you must
  `scn.frame_set(f)` for every f in 1..N in order; jumping straight to N
  re-evaluates the zone from an empty state and you render garbage. Every
  driver script here steps 1..450 sequentially and renders on the way through.
  Counterintuitive bonus: this is cheap - the whole 450-step walk plus seven
  1080p renders takes ~5 s in EEVEE Next because each step is one zone
  iteration on a 128x128 grid.
- **Don't iterate camera framing by rendering.** Rendering + eyeballing
  converges slowly. `bpy_extras.object_utils.world_to_camera_view()` projects
  the evaluated world-space bbox corners of each object into normalized frame
  coordinates [0..1], so you can grid-search distance/height/target
  numerically (dozens of poses per second, no pixels), then confirm with a
  single test render. Two renders total instead of a blind loop.
- **Aim by construction, not by taste.** For a camera at x=0 looking down the
  Y axis, pitch = `atan2(dy, -dz)` toward the target. Once the aim is a
  function of position, animating position keeps composition consistent - key
  rotation alongside location and the push-in cannot drift off-subject.
- **`--factory-startup` is not an empty scene.** It is the *default* scene.
  Any script that claims to be re-run friendly must reconcile both worlds: the
  collection it built last time AND the Cube/Light/Camera Blender ships. Guard
  removals with `.get()` so both paths are idempotent.
- **The white box was diagnosable from the render.** The stray object sat at
  world origin between the twins - exactly where nothing of ours was placed.
  Reading the test PNG before touching code pointed straight at scene-reset
  logic rather than at the node tree.
- **The verified drivers live outside the repo** (`gn_final.py` in the job tmp
  dir): exec the script, set resolution/samples, save the .blend, walk frames
  sequentially, render the checkpoint frames. The .py in this folder stays
  pure - it builds the scene and nothing else.

## Reproduce

```
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background \
  --factory-startup --python <driver.py>
```

where the driver execs `BLENDER.geonodes_450.py`, sets
`scn.render.resolution_x/y` and `scn.eevee.taa_render_samples`, then
`scn.frame_set()` from 1 upward and `bpy.ops.render.render(write_still=True)`
at the frames it wants. Verified frames: 030 normal, 060 multiply,
150 hardlight, 180 softlight, 270 colordodge, 330 difference, 450 subtract.
