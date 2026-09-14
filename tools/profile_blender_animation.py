#!/usr/bin/env python3
"""Profile evaluated Blender scene changes at selected frames.

Read-only diagnostic: loads a .blend, samples evaluated mesh signatures,
object transforms, material-node signatures, lights and camera. It never saves
the file or changes render settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from array import array
from pathlib import Path

try:
    import bpy
except ImportError as exc:
    bpy = None
    _BPY_IMPORT_ERROR = exc
else:
    _BPY_IMPORT_ERROR = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", nargs="+", type=int, default=[1, 50, 75])
    parser.add_argument("--scene")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def rounded(values, digits=6):
    return [round(float(value), digits) for value in values]


def matrix_signature(matrix):
    return tuple(rounded(value for row in matrix for value in row))


def mesh_signature(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        coords = array("f", [0.0]) * (len(mesh.vertices) * 3)
        if coords:
            mesh.vertices.foreach_get("co", coords)
        digest = hashlib.sha256(coords.tobytes()).hexdigest()[:16]
        return {
            "vertices": len(mesh.vertices),
            "polygons": len(mesh.polygons),
            "co_sha256": digest,
        }
    finally:
        evaluated.to_mesh_clear()


def material_signature(obj):
    rows = []
    for slot in obj.material_slots:
        material = slot.material
        if not material or not material.use_nodes:
            rows.append(None if not material else material.name)
            continue
        nodes = []
        for node in material.node_tree.nodes:
            image = getattr(node, "image", None)
            nodes.append((node.name, node.bl_idname, image.name if image else None))
        rows.append({"name": material.name, "nodes": sorted(nodes)})
    return rows


def main() -> None:
    args = parse_args()
    if bpy is None:
        raise SystemExit(
            "bpy is not available: this script runs INSIDE Blender via "
            "`blender --background <file.blend> --python "
            "tools/profile_blender_animation.py`, never with the system "
            f"interpreter. ({_BPY_IMPORT_ERROR})")
    scene = bpy.data.scenes.get(args.scene) if args.scene else bpy.context.scene
    if scene is None:
        raise SystemExit("SCENE_NOT_FOUND")
    if bpy.context.window:
        bpy.context.window.scene = scene

    objects = [obj for obj in scene.objects if obj.type == "MESH"]
    records = []
    for frame in sorted(set(args.frames)):
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        frame_row = {
            "frame": frame,
            "camera": scene.camera.name if scene.camera else None,
            "camera_matrix": matrix_signature(scene.camera.matrix_world) if scene.camera else None,
            "lights": {
                obj.name: {
                    "type": obj.data.type,
                    "energy": round(float(obj.data.energy), 6),
                    "color": rounded(obj.data.color),
                    "matrix": matrix_signature(obj.matrix_world),
                }
                for obj in scene.objects
                if obj.type == "LIGHT"
            },
            "objects": {},
        }
        for obj in objects:
            frame_row["objects"][obj.name] = {
                "matrix": matrix_signature(obj.matrix_world),
                "mesh": mesh_signature(obj, depsgraph),
                "materials": material_signature(obj),
            }
        records.append(frame_row)

    changes = []
    first = records[0]
    for name in first["objects"]:
        fields = {}
        for field in ("matrix", "mesh", "materials"):
            values = [row["objects"][name][field] for row in records]
            if any(value != values[0] for value in values[1:]):
                fields[field] = values
        if fields:
            changes.append({"object": name, "changes": fields})

    light_changes = []
    for name in first["lights"]:
        values = [row["lights"].get(name) for row in records]
        if any(value != values[0] for value in values[1:]):
            light_changes.append({"light": name, "values": values})

    output = {
        "blend_path": bpy.data.filepath,
        "scene": scene.name,
        "frames": [row["frame"] for row in records],
        "camera_changes": len({row["camera_matrix"] for row in records}) > 1,
        "light_changes": light_changes,
        "object_changes": changes,
    }
    print("ANIMATION_PROFILE_JSON_BEGIN")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("ANIMATION_PROFILE_JSON_END")


if __name__ == "__main__":
    main()
