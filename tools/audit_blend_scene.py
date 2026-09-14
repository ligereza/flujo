"""Read-only Blender scene audit for the RD render template."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

try:
    import bpy
except ImportError as exc:
    bpy = None
    _BPY_IMPORT_ERROR = exc
else:
    _BPY_IMPORT_ERROR = None


def animation_state(block):
    ad = getattr(block, "animation_data", None)
    if not ad or not ad.action:
        return False
    return True


def image_row(image):
    width, height = image.size[:2]
    resolved = bpy.path.abspath(image.filepath) if image.filepath else ""
    return {
        "name": image.name,
        "source": image.source,
        "filepath": image.filepath,
        "width": width,
        "height": height,
        "channels": image.channels,
        "packed": bool(image.packed_file),
        "users": image.users,
        "estimated_rgba_mib": round(width * height * 4 / 1024 / 1024, 2),
        "is_movie": image.source == "MOVIE",
        "resolved_filepath": resolved,
        "path_exists": bool(resolved and Path(resolved).exists()),
    }


def action_row(block):
    animation = getattr(block, "animation_data", None)
    action = animation.action if animation else None
    if not action:
        return None
    return {
        "action": action.name,
        "fcurves": [
            {
                "data_path": curve.data_path,
                "array_index": curve.array_index,
                "keyframes": len(curve.keyframe_points),
                "frame_min": round(curve.range()[0], 3) if curve.keyframe_points else None,
                "frame_max": round(curve.range()[1], 3) if curve.keyframe_points else None,
            }
            for curve in action.fcurves
        ],
    }


def transform_at(obj, frame):
    scene = bpy.context.scene
    previous = scene.frame_current
    scene.frame_set(frame)
    matrix = list(sum((list(row) for row in obj.matrix_world), []))
    result = {
        "frame": frame,
        "location": [round(value, 6) for value in obj.location],
        "rotation_euler": [round(value, 6) for value in obj.rotation_euler],
        "matrix_world": [round(value, 6) for value in matrix],
    }
    scene.frame_set(previous)
    return result


def main():
    if bpy is None:
        raise SystemExit(
            "bpy is not available: this script runs INSIDE Blender via "
            "`blender --background <file.blend> --python "
            "tools/audit_blend_scene.py`, never with the system interpreter. "
            f"({_BPY_IMPORT_ERROR})")
    scenes = []
    for scene in bpy.data.scenes:
        render = scene.render
        cycles = scene.cycles
        scenes.append({
            "name": scene.name,
            "frame_range": [scene.frame_start, scene.frame_end],
            "render_engine": render.engine,
            "resolution": [render.resolution_x, render.resolution_y, render.resolution_percentage],
            "fps": render.fps,
            "samples": cycles.samples,
            "preview_samples": cycles.preview_samples,
            "use_denoising": cycles.use_denoising,
            "use_persistent_data": render.use_persistent_data,
            "use_simplify": render.use_simplify,
            "simplify_subdivision": render.simplify_subdivision,
            "simplify_child_particles": render.simplify_child_particles,
            "texture_limit_render": cycles.texture_limit_render,
            "tile_size": getattr(cycles, "tile_size", None),
            "bounces": {
                "max": cycles.max_bounces,
                "diffuse": cycles.diffuse_bounces,
                "glossy": cycles.glossy_bounces,
                "transmission": cycles.transmission_bounces,
                "transparent": cycles.transparent_max_bounces,
                "volume": cycles.volume_bounces,
            },
            "camera": scene.camera.name if scene.camera else None,
            "world": scene.world.name if scene.world else None,
            "use_nodes_world": bool(scene.world and scene.world.use_nodes),
            "view_layers": [layer.name for layer in scene.view_layers],
            "compositor": bool(scene.use_nodes),
        })

    object_rows = []
    object_types = Counter()
    modifiers = Counter()
    animated_objects = []
    for obj in bpy.data.objects:
        object_types[obj.type] += 1
        modifier_names = [modifier.type for modifier in obj.modifiers]
        modifiers.update(modifier_names)
        row = {
            "name": obj.name,
            "type": obj.type,
            "hide_render": obj.hide_render,
            "visible": obj.visible_get(),
            "modifiers": modifier_names,
            "animated": animation_state(obj),
            "action": action_row(obj),
        }
        if obj.type == "MESH" and obj.data:
            row.update({
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
            })
        object_rows.append(row)
        if row["animated"]:
            animated_objects.append(obj.name)

    material_rows = []
    node_counts = Counter()
    movie_nodes = []
    image_nodes = []
    for material in bpy.data.materials:
        nodes = list(material.node_tree.nodes) if material.use_nodes else []
        node_counts.update(node.bl_idname for node in nodes)
        for node in nodes:
            image = getattr(node, "image", None)
            if image:
                image_nodes.append({
                    "material": material.name,
                    "node": node.name,
                    "node_type": node.bl_idname,
                    "image": image.name,
                    "source": image.source,
                    "filepath": image.filepath,
                    "users": image.users,
                })
            if image and image.source == "MOVIE":
                movie_nodes.append({
                    "material": material.name,
                    "node": node.name,
                    "image": image.name,
                    "filepath": image.filepath,
                    "frame_duration": image.frame_duration,
                    "fps": getattr(image, "fps", None),
                })
        material_rows.append({
            "name": material.name,
            "use_nodes": material.use_nodes,
            "nodes": len(nodes),
            "animated": animation_state(material),
        })

    images = sorted((image_row(image) for image in bpy.data.images),
                    key=lambda row: row["estimated_rgba_mib"], reverse=True)
    lights = []
    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            data = obj.data
            lights.append({
                "name": obj.name,
                "type": data.type,
                "energy": data.energy,
                "color": list(data.color),
                "animated_object": animation_state(obj),
                "animated_data": animation_state(data),
            })

    camera_samples = []
    camera_actions = []
    for scene in bpy.data.scenes:
        camera = scene.camera
        if not camera:
            continue
        frames = sorted({scene.frame_start,
                         (scene.frame_start + scene.frame_end) // 2,
                         scene.frame_end})
        camera_samples.append({
            "scene": scene.name,
            "camera": camera.name,
            "samples": [transform_at(camera, frame) for frame in frames],
        })
        camera_actions.append({
            "scene": scene.name,
            "camera": camera.name,
            "action": action_row(camera),
        })

    mesh_total = sum(row.get("vertices", 0) for row in object_rows)
    polygon_total = sum(row.get("polygons", 0) for row in object_rows)
    report = {
        "blend_path": bpy.data.filepath,
        "blend_size_bytes": Path(bpy.data.filepath).stat().st_size if bpy.data.filepath else None,
        "scenes": scenes,
        "collections": len(bpy.data.collections),
        "objects": len(bpy.data.objects),
        "object_types": dict(object_types),
        "meshes": len(bpy.data.meshes),
        "mesh_vertices": mesh_total,
        "mesh_polygons": polygon_total,
        "modifiers": dict(modifiers),
        "animated_objects": animated_objects,
        "lights": lights,
        "materials": len(bpy.data.materials),
        "material_rows": material_rows,
        "node_counts": dict(node_counts),
        "movie_nodes": movie_nodes,
        "image_nodes": image_nodes,
        "camera_samples": camera_samples,
        "camera_actions": camera_actions,
        "images_count": len(images),
        "images_estimated_rgba_mib": round(sum(row["estimated_rgba_mib"] for row in images), 2),
        "images": images,
        "filepaths": sorted({image["filepath"] for image in images if image["filepath"]}),
    }
    print("AUDIT_JSON_BEGIN")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    print("AUDIT_JSON_END")


if __name__ == "__main__":
    main()
