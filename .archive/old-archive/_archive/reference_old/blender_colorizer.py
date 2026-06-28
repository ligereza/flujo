# -*- coding: utf-8 -*-
"""
blender_colorizer.py

Aplica colores extraídos a objetos/materiales en Blender
Se ejecuta en background con: blender archivo.blend --background --python este_script.py
"""

import bpy
import json
import os
from pathlib import Path


class BlenderColorizer:
    """Aplica colores a materiales de Blender"""

    def __init__(self, colors_data=None):
        """
        Args:
            colors_data: dict con {"nombre_material": (r, g, b), ...}
                        o ruta a archivo JSON con los colores
        """
        self.colors = colors_data or {}

        if isinstance(self.colors, str) and os.path.exists(self.colors):
            with open(self.colors, 'r') as f:
                config = json.load(f)
                self.colors = config.get('colores', {})

    @staticmethod
    def rgb_to_blender(r, g, b):
        """Convierte RGB (0-255) a valores Blender (0-1)"""
        return (r / 255.0, g / 255.0, b / 255.0, 1.0)

    def apply_to_all_materials(self, color_primary, color_secondary):
        """
        Aplica dos colores a los materiales principales

        Args:
            color_primary: (r, g, b) para materiales principales
            color_secondary: (r, g, b) para materiales secundarios
        """
        primary_rgba = self.rgb_to_blender(*color_primary)
        secondary_rgba = self.rgb_to_blender(*color_secondary)

        applied = []

        for material in bpy.data.materials:
            if material.use_nodes:
                principled = material.node_tree.nodes.get("Principled BSDF")
                if principled:
                    # Alternar entre colores primario y secundario
                    if len(applied) % 2 == 0:
                        principled.inputs["Base Color"].default_value = primary_rgba
                    else:
                        principled.inputs["Base Color"].default_value = secondary_rgba
                    applied.append(material.name)

        return applied

    def apply_to_material(self, material_name, color):
        """Aplica color a un material específico"""
        if material_name not in bpy.data.materials:
            # Crear material si no existe
            mat = bpy.data.materials.new(name=material_name)
        else:
            mat = bpy.data.materials[material_name]

        mat.use_nodes = True
        principled = mat.node_tree.nodes.get("Principled BSDF")

        if not principled:
            # Si no existe Principled BSDF, crearlo
            links = mat.node_tree.links
            nodes = mat.node_tree.nodes

            # Limpiar nodos existentes
            nodes.clear()

            # Crear nodos
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            output = nodes.new(type='ShaderNodeOutputMaterial')

            links.new(principled.outputs[0], output.inputs[0])

        # Aplicar color
        rgba = self.rgb_to_blender(*color)
        principled.inputs["Base Color"].default_value = rgba

        return mat.name

    def apply_to_objects_by_name(self, mapping):
        """
        Aplica colores a objetos específicos

        Args:
            mapping: {"nombre_objeto": (r, g, b), ...}
        """
        applied = []

        for obj_name, color in mapping.items():
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]

                # Si el objeto tiene material, aplicar color
                if obj.data.materials:
                    for mat in obj.data.materials:
                        self.apply_to_material(mat.name, color)
                        applied.append((obj_name, mat.name, color))
                else:
                    # Crear un material nuevo
                    mat_name = f"{obj_name}_Material"
                    self.apply_to_material(mat_name, color)
                    obj.data.materials.append(bpy.data.materials[mat_name])
                    applied.append((obj_name, mat_name, color))

        return applied

    def apply_from_config_file(self, config_file):
        """Lee configuración de archivo JSON y aplica colores"""
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Espera formato: {"materiales": {"nombre": (r,g,b)}, "objetos": {...}}
        if "materiales" in config:
            for mat_name, color in config["materiales"].items():
                self.apply_to_material(mat_name, tuple(color))

        if "objetos" in config:
            self.apply_to_objects_by_name(config["objetos"])

    def save_material_list(self, output_file):
        """Guarda lista de materiales actuales en JSON"""
        materials = {}
        for mat in bpy.data.materials:
            materials[mat.name] = {
                "color": [c for c in mat.diffuse_color],  # RGBA
                "use_nodes": mat.use_nodes
            }

        with open(output_file, 'w') as f:
            json.dump(materials, f, indent=2)


def main():
    """Función principal - llamada cuando se ejecuta el script en Blender"""

    # Obtener argumentos pasados a Blender
    import sys
    argv = sys.argv

    # Blender pasa: blender.exe archivo.blend --background --python script.py -- arg1 arg2...
    # Los argumentos después de -- están en argv después del índice del script

    colors_file = None
    apply_mode = "all_materials"  # all_materials, objects, or file-based
    color_primary = (255, 100, 50)  # Default: naranja
    color_secondary = (100, 200, 255)  # Default: azul

    try:
        # Buscar argumentos
        if "--colors" in argv:
            idx = argv.index("--colors")
            if idx + 1 < len(argv):
                colors_file = argv[idx + 1]

        if "--mode" in argv:
            idx = argv.index("--mode")
            if idx + 1 < len(argv):
                apply_mode = argv[idx + 1]

        colorizer = BlenderColorizer()

        if apply_mode == "all_materials":
            applied = colorizer.apply_to_all_materials(color_primary, color_secondary)
            print(f"✓ Colores aplicados a {len(applied)} materiales")

        elif apply_mode == "from_file" and colors_file:
            colorizer.apply_from_config_file(colors_file)
            print(f"✓ Colores aplicados desde archivo: {colors_file}")

        # Guardar archivo
        bpy.ops.wm.save_mainfile()
        print("✓ Archivo guardado")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


if __name__ == "__main__":
    main()
