"""Script bpy para render headless: carga una imagen como textura y renderiza.

NO se importa desde flujo; Blender lo ejecuta:
    blender --background --python blender_render.py -- <textura> <salida> [template.blend]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_gpu import force_gpu  # noqa: E402 -- modulo hermano, sin depender del paquete flujo


def main():
    import bpy  # solo existe dentro de Blender; mantener el modulo importable fuera
    try:
        # Obtener argumentos después de '--'
        if '--' in sys.argv:
            idx = sys.argv.index('--')
            args = sys.argv[idx+1:]
        else:
            args = sys.argv[1:]

        if len(args) < 2:
            print("Error: Se requieren al menos dos argumentos: <input_texture_path> <output_render_path>")
            sys.exit(1)

        input_texture_path = args[0]
        output_render_path = args[1]
        optional_blend_template_path = args[2] if len(args) > 2 else None

        # Cargar plantilla o usar la escena actual
        if optional_blend_template_path:
            if not os.path.exists(optional_blend_template_path):
                raise FileNotFoundError(f"Plantilla Blender no encontrada: {optional_blend_template_path}")
            bpy.ops.wm.open_mainfile(filepath=optional_blend_template_path)

        # Encontrar o crear material llamado 'Texture' en el objeto activo/seleccionado
        obj = bpy.context.active_object
        if obj is None:
            if bpy.context.selected_objects:
                obj = bpy.context.selected_objects[0]
            else:
                # Si no hay objeto, crear un cubo simple para alojar el material
                bpy.ops.mesh.primitive_cube_add()
                obj = bpy.context.active_object

        # Asegurar que el objeto tenga ranuras de material
        if not obj.data.materials:
            obj.data.materials.append(None)

        # Encontrar el material 'Texture' existente o crear uno nuevo
        mat = None
        for m in obj.data.materials:
            if m is not None and m.name == 'Texture':
                mat = m
                break
        if mat is None:
            mat = bpy.data.materials.new(name='Texture')
            obj.data.materials[0] = mat

        # Habilitar el uso de nodos
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Limpiar nodos existentes para evitar conflictos
        nodes.clear()

        # Crear nodos
        tex_image = nodes.new(type='ShaderNodeTexImage')
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')

        # Cargar imagen
        if not os.path.exists(input_texture_path):
            raise FileNotFoundError(f"Textura de entrada no encontrada: {input_texture_path}")
        tex_image.image = bpy.data.images.load(input_texture_path)

        # Enlazar nodos: Image Texture -> Principled BSDF -> Material Output
        links.new(tex_image.outputs['Color'], principled.inputs['Base Color'])
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])

        # Establecer la ruta de salida del renderizado
        bpy.context.scene.render.filepath = output_render_path

        gpu_report = force_gpu()
        print(f"GPU: {gpu_report}")

        # Renderizar imagen fija
        bpy.ops.render.render(write_still=True)

        print(f"Renderizado completado y guardado en: {output_render_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
