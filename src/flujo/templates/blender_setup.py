"""blender_setup.py — Flujo para Blender 3D

Uso (en Blender Text Editor o como script):
    exec(open("blender_setup.py").read())
    setup_stand("projects/plano/ejemplos/evento_ejemplo.json")

Crea un stand 3D básico usando:
- Dimensiones del evento (plano)
- Colores y estilo de flujo.json
- Materiales simples para carteleras / recursos 3D

Adáptalo a tu flujo: extrude, agrega texturas, etc.
"""

import bpy
import json
from mathutils import Vector
from pathlib import Path

def load_flujo():
    p = Path("projects/flujo/flujo.json")
    if p.exists():
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        c = data.get("colors", {})
        return {
            "ink": c.get("ink", "#1f2a24"),
            "accent": c.get("accent", "#2d5a4a"),
            "paper": c.get("paper", "#f8f1e3"),
        }
    return {"ink": "#1f2a24", "accent": "#2d5a4a", "paper": "#f8f1e3"}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)) + (1,)

def create_material(name, color_hex):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = hex_to_rgb(color_hex)
    return mat

def setup_stand(evento_json: str):
    """Crea base 3D simple desde un json de plano, usando flujo."""
    with open(evento_json, encoding="utf-8") as f:
        ev = json.load(f)

    styles = load_flujo()
    paper_mat = create_material("Flujo_Paper", styles["paper"])
    accent_mat = create_material("Flujo_Accent", styles["accent"])

    # Base stand (aprox 3m toldo)
    bpy.ops.mesh.primitive_cube_add(size=3, location=(0, 0, 1.5))
    stand = bpy.context.active_object
    stand.name = f"Stand_{ev.get('nombre', 'Evento').replace(' ', '_')}"
    if paper_mat:
        stand.data.materials.append(paper_mat)

    # Panel frontal simple (estilo cartelera)
    bpy.ops.mesh.primitive_plane_add(size=2.5, location=(0, -1.6, 2.5))
    panel = bpy.context.active_object
    panel.name = "Panel_Cartelera"
    if accent_mat:
        panel.data.materials.append(accent_mat)

    # Luz
    bpy.ops.object.light_add(type='SUN', location=(4, 4, 8))

    print(f"[flujo] Stand 3D creado: {stand.name}")
    print("[flujo] Materiales de flujo aplicados.")
    print("[flujo] Adapta a tu modelo de frasco o cartelera 3D.")

if __name__ == "__main__":
    # Run from Blender or command line with bpy
    pass
