"""Inspect RD.blend headless: report materials, image nodes, and UV bounds
that touch flyer_final.jpg / color_predominante.png. No guessing -- reads the
real file. Run:
    blender --background RD.blend --python tools_inspect_rd_blend.py
"""
import json
import sys


def main():
    import bpy

    scene = bpy.context.scene
    report = {
        "render_engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "materials": [],
        "objects": [],
    }

    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        img_nodes = []
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                img_nodes.append({
                    "node_name": node.name,
                    "image": node.image.name,
                    "filepath": bpy.path.abspath(node.image.filepath) if node.image.filepath else None,
                    "size": list(node.image.size),
                })
        if img_nodes:
            report["materials"].append({"material": mat.name, "image_nodes": img_nodes})

    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data.uv_layers.active:
            continue
        mat_names = [s.material.name for s in obj.material_slots if s.material]
        relevant = any(
            any(n["filepath"] and ("flyer_final" in n["filepath"] or "color_predominante" in n["filepath"])
                for n in m["image_nodes"])
            for m in report["materials"] if m["material"] in mat_names
        )
        if not relevant:
            continue
        uv = obj.data.uv_layers.active.data
        us = [l.uv.x for l in uv]
        vs = [l.uv.y for l in uv]
        report["objects"].append({
            "object": obj.name,
            "materials": mat_names,
            "uv_bounds": {"u_min": min(us), "u_max": max(us), "v_min": min(vs), "v_max": max(vs)},
        })

    print("=== RD_BLEND_INSPECT_JSON_START ===")
    print(json.dumps(report, indent=2))
    print("=== RD_BLEND_INSPECT_JSON_END ===")


if __name__ == "__main__":
    main()
