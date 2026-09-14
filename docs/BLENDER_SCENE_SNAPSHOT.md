# Blender scene snapshot and render transformation

This slice records the native Blender scene as an observation of an artifact
state. It does not make the finished image the source of truth and it does not
execute a render or save the `.blend` file.

## Contract

`mak-blender-scene-snapshot-v1` contains:

- the existing substrate `Content`, `ArtifactState` and `Observation` identity;
- Blender version, dirty state, scenes, render settings, camera, objects,
  collections, view layers, compositor nodes and declared external files;
- provenance identifying the read-only Blender Python extractor.

The snapshot digest is derived from the `.blend` content hash, the native scene
payload and extractor configuration. Capture time, root and path remain on the
observation and are not part of state identity. The same bytes and native
payload therefore produce the same state even when observed twice at different
locations or times.

The native probe is launched with `--background --factory-startup
--disable-autoexec`. Its script only reads `bpy.data`; it must not call
`bpy.ops.render` or `bpy.ops.wm.save`.

## Read-only usage

```text
PYTHONPATH=src .venv/bin/python tools/blender_scene_probe.py \
  --snapshot --input /path/to/scene.blend \
  --output /tmp/mak-scene-snapshot.json
```

The report has one row per input. A decoder, launch or integrity error is not
reported as a successful snapshot.

## Preconditions and transformation event

`assess_render_preconditions()` checks only technical applicability: scene,
camera, render settings, requested resolution and external dependency presence.
It does not certify composition, artistic quality or the resulting pixels.

Missing declared dependencies produce `FAIL`. Dependencies whose presence was
not measured produce `UNKNOWN`; neither case can become render success by
default.

`start_transformation()` records an immutable `STARTED` event for
`renderizar`. `finish_transformation()` closes a copy with the output state,
validation ID and status. It rejects reusing the input state as its own output;
a correction must be a new event with `correction_of` pointing at the earlier
event.

This is deliberately not a planner, router or policy store. The next
experiment is to run the snapshot against one real `.blend` in a scratch
location, inspect the extracted fields and only then decide whether a render
executor is justified.
