"""Bake safe static material color maps into a copy of the RD template.

This is a material bake, not a final-lighting bake.  It converts procedural
base-color branches to image textures for static objects while retaining
Principled roughness/metallic/normal and all glass/reflection behavior.  The
runtime screen materials are excluded because their content is replaced by a
MOVIE texture for every video frame.

The source .blend is never saved.  The output is a separate rollback target.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import bpy
except ImportError as exc:
    bpy = None
    _BPY_IMPORT_ERROR = exc
else:
    _BPY_IMPORT_ERROR = None


SKIP_MATERIALS = {
    "Material.002",          # runtime flyer/video screen
    "Material.008",          # second runtime flyer/video consumer
    "Decorative Glass 05",   # receives event color at runtime
    "Glass", "Glass.001", "GlassFrosty", "Liquid1", "LiquidBlue.003",
    "Simple Crystal.001",
}
PROCEDURAL_NODES = {
    "ShaderNodeTexNoise", "ShaderNodeTexVoronoi", "ShaderNodeValToRGB",
    "ShaderNodeGroup", "ShaderNodeMix", "ShaderNodeHueSaturation",
    "ShaderNodeBrightContrast", "ShaderNodeRGBCurve",
}


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resolution", type=int, default=2048)
    return parser.parse_args(values)


def material_is_dynamic(material):
    if material.name in SKIP_MATERIALS:
        return True
    if not material.use_nodes:
        return False
    return any(getattr(node, "image", None) and
               node.image.source == "MOVIE"
               for node in material.node_tree.nodes)


def base_color_source(material, principled):
    socket = principled.inputs.get("Base Color")
    if not socket:
        return []
    return [link.from_node for link in material.node_tree.links
            if link.to_socket == socket]


def candidates(scene):
    found = []
    for obj in scene.objects:
        if obj.type != "MESH" or not obj.data.uv_layers:
            continue
        for slot_index, slot in enumerate(obj.material_slots):
            material = slot.material
            if not material or material_is_dynamic(material) or not material.use_nodes:
                continue
            principled = next((node for node in material.node_tree.nodes
                               if node.bl_idname == "ShaderNodeBsdfPrincipled"), None)
            if not principled:
                continue
            sources = base_color_source(material, principled)
            if not any(node.bl_idname in PROCEDURAL_NODES for node in sources):
                continue
            found.append((obj, slot_index, material, principled))
    return found


def bake_one(scene, obj, slot_index, source_material, resolution):
    # A material may be shared by multiple meshes.  Make this bake local to
    # one object so its UV layout cannot overwrite another object's bake.
    material = source_material.copy()
    material.name = f"{source_material.name}__BAKED_{obj.name}"
    obj.material_slots[slot_index].material = material
    tree = material.node_tree
    principled = next(node for node in tree.nodes
                      if node.bl_idname == "ShaderNodeBsdfPrincipled")
    image = bpy.data.images.new(
        name=f"BAKE_BASECOLOR_{obj.name}_{slot_index}",
        width=resolution,
        height=resolution,
        alpha=True,
        float_buffer=False,
    )
    image.colorspace_settings.name = "sRGB"
    target = tree.nodes.new("ShaderNodeTexImage")
    target.name = "BAKED BASE COLOR"
    target.label = "BAKED BASE COLOR"
    target.image = image
    for node in tree.nodes:
        node.select = False
    target.select = True
    tree.nodes.active = target

    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.active_material_index = slot_index

    scene.render.bake.target = "IMAGE_TEXTURES"
    scene.render.bake.use_clear = True
    scene.render.bake.margin = 16
    scene.render.bake.margin_type = "ADJACENT_FACES"
    scene.render.bake.width = resolution
    scene.render.bake.height = resolution
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_diffuse = True
    scene.render.bake.use_pass_glossy = False
    scene.render.bake.use_pass_transmission = False
    scene.render.bake.use_pass_emit = False
    scene.frame_set(1)
    bpy.ops.object.bake(type="DIFFUSE")

    base_socket = principled.inputs.get("Base Color")
    for link in list(tree.links):
        if link.to_socket == base_socket:
            tree.links.remove(link)
    tree.links.new(target.outputs["Color"], base_socket)
    image.pack()
    return {
        "object": obj.name,
        "slot": slot_index,
        "source_material": source_material.name,
        "baked_material": material.name,
        "image": image.name,
        "resolution": [resolution, resolution],
    }


def main():
    args = parse_args()
    if bpy is None:
        raise SystemExit(
            "bpy is not available: this script runs INSIDE Blender via "
            "`blender --background <file.blend> --python "
            "tools/bake_static_materials.py -- --output ...`, never with the "
            f"system interpreter. ({_BPY_IMPORT_ERROR})")
    output = args.output.expanduser().resolve()
    source = Path(bpy.data.filepath).resolve()
    if output == source:
        raise SystemExit("OUTPUT_MUST_DIFFER_FROM_SOURCE")
    if args.resolution < 256 or args.resolution > 4096:
        raise SystemExit("RESOLUTION_OUT_OF_BOUNDS")
    output.parent.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    selected = candidates(scene)
    results = []
    for obj, slot_index, material, principled in selected:
        del principled
        print(f"BAKE_START: {obj.name} / {material.name}", flush=True)
        results.append(bake_one(scene, obj, slot_index, material, args.resolution))
        print(f"BAKE_OK: {obj.name} / {material.name}", flush=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report = {
        "source": str(source),
        "output": str(output),
        "scene": scene.name,
        "candidates": len(selected),
        "baked": results,
        "excluded_dynamic_materials": sorted(SKIP_MATERIALS),
        "lighting_bake": False,
        "reason": "video content and reflections must remain dynamic",
    }
    print("BAKE_JSON_BEGIN")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    print("BAKE_JSON_END")
    print(f"BAKE_COMPLETE: {output}")


if __name__ == "__main__":
    main()
