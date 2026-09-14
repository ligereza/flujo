"""Variante VIDEO de blender_nodes.py: mismo grafo de nodos probado
(MARCO/HUE/FADE/MEZCLA), pero el CONTENIDO es un video (source='MOVIE')
en vez de un JPG estatico.

NO reemplaza a blender_nodes.py (el camino de imagen estatica sigue
intacto, sin tocar). Reutiliza sus helpers puros (fitcover_mapping,
hue_de_rgb, labels, _buscar_materiales_flyer, _nodo_por_label,
_color_predominante_bpy, _repuntar_color_predominante, _resolver_ruta)
importandolos como modulo hermano.

Uso (mismo patron que blender_nodes.py):
    blender -b RD_video.blend --python blender_nodes_video.py -- \
        --input input_ig_video.mp4 --frame FRAME2.png \
        --color-png color_predominante.png --salida render_video.mp4 \
        --frame-start 1 --frame-end 600 --fps 30

Solo --input es obligatorio (mismos defaults derivados de la carpeta
del .blend que blender_nodes.py). --frame-end por defecto = duracion
real del clip (leida via bpy.data.images con source MOVIE), asi que un
smoke test se pide explicito con --frame-end 24.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_nodes as bn  # noqa: E402 -- modulo hermano, reusa el grafo probado

# Images and videos share the same measured fit-width/fade contract. These
# names remain as compatibility aliases for old callers; they no longer select
# different scale policies.
VIDEO_LAYOUT_FITWIDTH = bn.IMAGE_LAYOUT_POLICY
VIDEO_LAYOUT_PORTRAIT = VIDEO_LAYOUT_FITWIDTH
VIDEO_LAYOUT_FRAMED = VIDEO_LAYOUT_FITWIDTH


def _parse_args(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    parsed = {
        "frame": None, "input": None, "color_png": None, "salida": None,
        "frame_start": 1, "frame_end": None, "fps": None,
        "layout": VIDEO_LAYOUT_PORTRAIT,
    }
    key_map = {
        "--frame": "frame", "--input": "input", "--color-png": "color_png",
        "--salida": "salida", "--frame-start": "frame_start",
        "--frame-end": "frame_end", "--fps": "fps", "--layout": "layout",
    }
    i = 0
    while i < len(args):
        key = key_map.get(args[i])
        if key is None or i + 1 >= len(args):
            raise SystemExit(f"Argumento no reconocido o sin valor: {args[i]}")
        val = args[i + 1]
        if key in ("frame_start", "frame_end"):
            val = int(val)
        elif key == "fps":
            val = float(val)
        parsed[key] = val
        i += 2
    if not parsed["input"]:
        raise SystemExit("Falta --input (unico argumento obligatorio)")
    if parsed["layout"] not in bn.VALID_VIDEO_LAYOUTS:
        raise SystemExit(f"VIDEO_LAYOUT_INVALID: {parsed['layout']}")
    return parsed


def video_mapping(layout, frame_size, video_size):
    """Return the shared image/video mapping: fit width, fade vertically."""
    if layout == VIDEO_LAYOUT_FITWIDTH:
        return bn.fitwidth_mapping(bn.WINDOW_UV, frame_size, video_size)
    raise SystemExit(f"VIDEO_LAYOUT_INVALID: {layout}")


def describe_video_layout(layout, frame_size, video_size):
    if layout == VIDEO_LAYOUT_FITWIDTH:
        return bn.classify_fitwidth_layout(bn.WINDOW_UV, frame_size, video_size)
    raise SystemExit(f"VIDEO_LAYOUT_INVALID: {layout}")


def build_flyer_nodes_video(mat, nodo_original, frame_path, video_path,
                             hue_objetivo, frame_duration,
                             layout=VIDEO_LAYOUT_PORTRAIT):
    """Como bn.build_flyer_nodes, pero CONTENIDO = video (source MOVIE).

    Reusa el mismo grafo (MARCO/HUE/FADE/MEZCLA); solo el nodo de
    imagen del contenido pasa a ser un ShaderNodeTexImage cuya .image
    tiene source='MOVIE' con image_user configurado para animar.
    """
    import bpy

    ya_existe = bn._nodo_por_label(mat, bn.LBL_MEZCLA) is not None
    tree = mat.node_tree

    video_img = bpy.data.images.load(video_path, check_existing=True)
    if video_img.source != "MOVIE":
        raise SystemExit(
            f"{video_path} no cargo como MOVIE (source={video_img.source}); "
            "revisa el archivo/codec."
        )

    if ya_existe:
        ti = bn._nodo_por_label(mat, bn.LBL_CONTENIDO)
        tf = bn._nodo_por_label(mat, bn.LBL_MARCO)
        hv = bn._nodo_por_label(mat, bn.LBL_HUE)
        mapping = next(n for n in tree.nodes if n.type == "MAPPING" and any(
            l.to_node == ti for l in tree.links if l.from_node == n))
        tf.image = bpy.data.images.load(frame_path, check_existing=True)
        ti.image = video_img
        frame_size = tuple(tf.image.size)
        video_size = tuple(video_img.size)
        (sx, sy), (lx, ly) = video_mapping(layout, frame_size, video_size)
        mapping.inputs["Scale"].default_value = (sx, sy, 1.0)
        mapping.inputs["Location"].default_value = (lx, ly, 0.0)
        hv.outputs[0].default_value = hue_objetivo
    else:
        # Sin grafo previo: construir con el helper probado usando el
        # video como si fuera la imagen del contenido (mismo tipo de
        # nodo, ShaderNodeTexImage acepta .image con source MOVIE).
        bn.build_flyer_nodes(mat, nodo_original, frame_path, video_path, hue_objetivo)
        ti = bn._nodo_por_label(mat, bn.LBL_CONTENIDO)
        ti.image = video_img  # el helper cargo un STILL; lo reemplazamos por el MOVIE

        # build_flyer_nodes starts from the static-image graph. The explicit
        # issue profile chooses cover for 9:16 or contain+bands otherwise.
        tf = bn._nodo_por_label(mat, bn.LBL_MARCO)
        mapping = next(n for n in tree.nodes if n.type == "MAPPING" and any(
            l.to_node == ti for l in tree.links if l.from_node == n))
        frame_size = tuple(tf.image.size)
        video_size = tuple(video_img.size)
        (sx, sy), (lx, ly) = video_mapping(layout, frame_size, video_size)
        mapping.inputs["Scale"].default_value = (sx, sy, 1.0)
        mapping.inputs["Location"].default_value = (lx, ly, 0.0)

    ti.image_user.frame_duration = frame_duration
    ti.image_user.frame_start = 1
    ti.image_user.frame_offset = 0
    ti.image_user.use_auto_refresh = True
    return "update" if ya_existe else "build"


def swap_existing_movie_nodes(video_path, frame_duration):
    """Repoint the MOVIE nodes already present in a video scene.

    RD.paravideo.blend is a video template, not the flyer image template:
    its Material.002 already contains the screen graph and a MOVIE texture.
    Keep that graph intact and change only the media datablock for the run.
    """
    import bpy

    video_img = bpy.data.images.load(video_path, check_existing=True)
    if video_img.source != "MOVIE":
        raise SystemExit(
            f"{video_path} no cargo como MOVIE (source={video_img.source})"
        )
    swapped = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            if node.image.source != "MOVIE":
                continue
            node.image = video_img
            node.image_user.frame_start = 1
            node.image_user.frame_duration = frame_duration
            node.image_user.frame_offset = 0
            node.image_user.use_auto_refresh = True
            swapped += 1
    return swapped


def main():
    import bpy
    from blender_gpu import force_gpu  # noqa: E402 -- modulo hermano

    args = _parse_args(sys.argv)
    base_blend = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
    if not args["frame"] and base_blend:
        args["frame"] = os.path.join(base_blend, "FRAME2.png")
    if not args["color_png"] and base_blend:
        args["color_png"] = os.path.join(base_blend, "RESULTADOS",
                                          "color_predominante.png")
    for clave in ("frame", "input", "color_png", "salida"):
        args[clave] = bn._resolver_ruta(args[clave], base_blend)
    for ruta in ("frame", "input"):
        if not args[ruta] or not os.path.exists(args[ruta]):
            raise SystemExit(f"No existe --{ruta}: {args[ruta]}")

    if args["color_png"] and os.path.exists(args["color_png"]):
        color_png = os.path.abspath(args["color_png"])
        rgb = bn._color_predominante_bpy(color_png)
        bn._repuntar_color_predominante(color_png)
    else:
        rgb = (0, 254, 254)
    hue = bn.hue_de_rgb(rgb)
    print(f"Color predominante RGB={rgb} hue={hue:.4f}")

    video_path = os.path.abspath(args["input"])
    probe = bpy.data.images.load(video_path, check_existing=True)
    frame_duration = probe.frame_duration
    print(f"Video: {video_path} frame_duration={frame_duration}")

    frame_start = args["frame_start"] or 1
    frame_end = args["frame_end"] or frame_duration
    if frame_end > frame_duration:
        print(f"Aviso: --frame-end {frame_end} > duracion real {frame_duration}; "
              f"recortando a {frame_duration}.")
        frame_end = frame_duration

    for mat, nodo in bn._buscar_materiales_flyer():
        modo = build_flyer_nodes_video(
            mat, nodo, os.path.abspath(args["frame"]), video_path, hue,
            frame_duration, args["layout"])
        print(f"Material '{mat.name}' {modo} layout={args['layout']} por nodos VIDEO (sin Photoshop).")

    print(f"GPU: {force_gpu()}")

    scene = bpy.context.scene
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    if args["fps"]:
        scene.render.fps = int(args["fps"])
    # Política de video: 128 samples adaptive, SIN denoise.
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False

    if args["salida"]:
        out = os.path.abspath(args["salida"])
        scene.render.filepath = out
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        scene.render.ffmpeg.ffmpeg_preset = "GOOD"
        scene.render.ffmpeg.audio_codec = "NONE"
        bpy.ops.render.render(animation=True)
        print(f"Render de video guardado en: {out}")


if __name__ == "__main__":
    main()
