"""Create a measured, non-destructive optimized copy of the RD blend.

This is deliberately not a global lighting bake.  The event content is a
MOVIE texture at render time, so baking final illumination/reflections would
freeze one video frame.  The safe optimization pass removes dead datablocks,
reduces oversized reference textures, and sets bounded Cycles defaults while
leaving the original .blend untouched.

Run inside Blender:
    blender -b RD.blend --python optimize_blend_scene.py -- \
        --output RD.optimized.blend
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import bpy
except ImportError as exc:
    bpy = None
    _BPY_IMPORT_ERROR = exc
else:
    _BPY_IMPORT_ERROR = None


def parse_args():
    argv = __import__("sys").argv
    values = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--texture-cap", type=int, default=4096)
    return parser.parse_args(values)


def node_users(image):
    result = []
    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if getattr(node, "image", None) == image:
                result.append(f"{material.name}:{node.name}")
    return result


def texture_users(image):
    return [texture.name for texture in bpy.data.textures
            if texture.type == "IMAGE" and texture.image == image]


def remove_unused_images():
    removed = []
    # Iterate because removing orphan datablocks can expose more orphans.
    changed = True
    while changed:
        changed = False
        for image in list(bpy.data.images):
            if node_users(image) or texture_users(image):
                continue
            # A datablock with users but no actual image/texture consumer is
            # still dead for this render template (e.g. stale preview image).
            removed.append({"name": image.name, "users": image.users})
            bpy.data.images.remove(image)
            changed = True
    return removed


def downscale_large_images(cap):
    changed = []
    for image in list(bpy.data.images):
        if image.source != "FILE" or not image.size[0] or not image.size[1]:
            continue
        width, height = image.size[:2]
        largest = max(width, height)
        if largest <= cap:
            continue
        scale = cap / largest
        new_width = max(1, round(width * scale))
        new_height = max(1, round(height * scale))
        before = [width, height]
        image.scale(new_width, new_height)
        # Pack the reduced pixels into the copy.  This never writes over the
        # source external file, and ensures a future load does not reload the
        # original 12k asset.
        image.pack()
        changed.append({
            "name": image.name,
            "before": before,
            "after": [new_width, new_height],
            "estimated_rgba_mib_before": round(width * height * 4 / 1024 / 1024, 2),
            "estimated_rgba_mib_after": round(new_width * new_height * 4 / 1024 / 1024, 2),
        })
    return changed


def remove_nonrender_scenes(active_scene):
    removed = []
    for scene in list(bpy.data.scenes):
        if scene == active_scene:
            continue
        removed.append(scene.name)
        bpy.data.scenes.remove(scene)
    return removed


def configure_cycles(scene):
    scene.render.engine = "CYCLES"
    scene.render.use_simplify = True
    scene.render.use_persistent_data = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    cycles = scene.cycles
    cycles.samples = 128
    cycles.preview_samples = 32
    cycles.use_denoising = False
    cycles.texture_limit_render = "2048"
    cycles.use_auto_tile = True
    cycles.tile_size = 512

    # Preserve the source bounce budget.  Lowering these values changes glass,
    # floor reflections and transmission; it is not a safe optimization for
    # this scene.  Performance work belongs in baking static material branches
    # and profiling geometry, never in an implicit quality downgrade.


def main():
    args = parse_args()
    if bpy is None:
        raise SystemExit(
            "bpy is not available: this script runs INSIDE Blender via "
            "`blender --background <file.blend> --python "
            "tools/optimize_blend_scene.py -- --output ...`, never with the "
            f"system interpreter. ({_BPY_IMPORT_ERROR})")
    output = args.output.expanduser().resolve()
    if output == Path(bpy.data.filepath).resolve():
        raise SystemExit("OUTPUT_MUST_DIFFER_FROM_SOURCE")
    output.parent.mkdir(parents=True, exist_ok=True)

    active_scene = bpy.context.scene
    if not active_scene.camera:
        active_scene = next((scene for scene in bpy.data.scenes if scene.camera),
                            active_scene)
        if bpy.context.window:
            bpy.context.window.scene = active_scene

    before = {
        "scenes": [scene.name for scene in bpy.data.scenes],
        "objects": len(bpy.data.objects),
        "images": len(bpy.data.images),
        "materials": len(bpy.data.materials),
    }

    removed_scenes = remove_nonrender_scenes(active_scene)
    removed_images = remove_unused_images()
    resized_images = downscale_large_images(args.texture_cap)
    configure_cycles(active_scene)

    # Purge only data that became unreferenced after removing the unused scene.
    try:
        bpy.ops.outliner.orphans_purge(do_recursive=True)
    except RuntimeError:
        pass

    bpy.ops.wm.save_as_mainfile(filepath=str(output))

    report = {
        "source": bpy.data.filepath,
        "output": str(output),
        "active_scene": active_scene.name,
        "before": before,
        "removed_scenes": removed_scenes,
        "removed_images": removed_images,
        "resized_images": resized_images,
        "bake_policy": {
            "final_lighting_bake": False,
            "reason": "runtime MOVIE texture changes per frame; baking final lighting/reflections would freeze one frame",
            "safe_pass": "static asset downscale/repack plus bounded Cycles defaults",
        },
    }
    print("OPTIMIZE_JSON_BEGIN")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    print("OPTIMIZE_JSON_END")
    print(f"OPTIMIZE_OK: {output}")


if __name__ == "__main__":
    main()
