"""Composicion del flyer POR NODOS dentro de Blender: sin Photoshop.

Reemplaza al Droplet de Photoshop: el material de pantalla de RD.blend
consume directo FRAME2.png (marco con ventana recortada por alpha) +
input_ig.jpg (flyer ya disenado que entrega la productora), recoloreando
el marco al color predominante del input. Modelo validado EN VIVO con el
usuario (2026-07-10, puente tools/blender/bridge_blender.py):

- El contenido AJUSTA AL ANCHO de la ventana SIEMPRE (los flyers llegan
  en cualquier tamano; nunca se estira ni se recorta a lo ancho).
- El alto sobrante o excedente se maneja con FADE a negro en los bordes
  (lo que el Droplet hacia con su fondo difuminado). Sin doble textura.
- El marco se recolorea fijando el HUE al color del evento (los pixeles
  neutros del marco no cambian; los acentos saltan al color del evento).
- El MISMO png de color extraido manda tambien en el vidrio decorativo
  ('Decorative Glass 05' lee el datablock color_predominante.png).
- La emision de cada material NO se toca (ajuste artistico manual).

IDEMPOTENTE: si el .blend ya trae el grafo (nodos etiquetados MARCO /
CONTENIDO / HUE EVENTO / FADE CONTENIDO / MARCO SOBRE CONTENIDO, como el
RD.blend guardado el 2026-07-10), solo ACTUALIZA imagen, mapping y hue;
si no, lo construye desde cero. Nunca guarda el .blend.

Geometria medida del FRAME2.png real (9898x9899, analisis PIL, no
adivinada): ventana = rectangulo transparente interior, bbox pixel
(6488,378)-(9350,4272).

NO se importa desde flujo (import bpy solo existe dentro de Blender):
    blender -b RD.blend --python blender_nodes.py -- \
        --input input_ig.jpg [--frame FRAME2.png] \
        [--color-png color_predominante.png] [--salida render.png]

Solo --input es obligatorio. Defaults derivados de la carpeta del .blend:
--frame = FRAME2.png junto al .blend; --color-png =
RESULTADOS/color_predominante.png junto al .blend. Rutas relativas que no
existan desde el CWD se resuelven contra la carpeta del .blend.

Los helpers de matematica (fit-width, hue, rutas) son python puro y se
testean sin Blender en tests/test_blender_nodes.py.
"""
import colorsys
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ventana del marco en coordenadas UV de Blender (origen abajo-izquierda,
# eje Y invertido respecto a pixeles de imagen). Medida, no estimada.
WINDOW_UV = {
    "x0": 0.655486,
    "x1": 0.944635,
    "y0": 0.568441,  # 1 - 4272/9899
    "y1": 0.961814,  # 1 - 378/9899
}

# Ancho del fade a negro en coordenadas del contenido (0-1). Validado
# visualmente por el usuario en vivo; se puede afinar a mano en el nodo.
FADE = 0.10

# Still images and moving images share one production layout. The lateral
# borders of the measured glass must match; the source keeps its proportions
# and any vertical excess/shortfall is handled by the existing fade graph.
# Do not silently switch to cover/contain by media type.
IMAGE_LAYOUT_POLICY = "fitwidth_fade"
VIDEO_LAYOUT_POLICY = IMAGE_LAYOUT_POLICY
# Historical/diagnostic helper labels. They remain available for geometry
# comparison, but neither is a production media policy anymore.
COVER_LAYOUT_POLICY = "cover_center"
CONTAIN_LAYOUT_POLICY = "contain_bars"
# Kept as a compatibility symbol for callers from the old split-layout pass;
# it is intentionally the same production policy, not a second layout.
VIDEO_LAYOUT_CONTAIN_BARS = IMAGE_LAYOUT_POLICY
VALID_VIDEO_LAYOUTS = {VIDEO_LAYOUT_POLICY}

# Etiquetas de los nodos del grafo (contrato de idempotencia: si estan,
# el grafo ya existe y solo se actualiza).
LBL_CONTENIDO = "CONTENIDO"
LBL_MARCO = "MARCO"
LBL_HUE = "HUE EVENTO"
LBL_FADE = "FADE CONTENIDO"
LBL_MEZCLA = "MARCO SOBRE CONTENIDO"


def fitwidth_mapping(window_uv, frame_size, input_size):
    """Escala+offset (afin) para el nodo Mapping del contenido.

    El input AJUSTA AL ANCHO de la ventana siempre (sin distorsion, sin
    recorte horizontal); el eje vertical queda centrado y el sobrante o
    excedente lo maneja la mascara de fade. Devuelve (scale_xy, loc_xy)
    tal que uv_input = uv * scale + location.
    """
    fw_px, fh_px = frame_size
    iw_px, ih_px = input_size
    if min(fw_px, fh_px, iw_px, ih_px) <= 0:
        raise ValueError("dimensiones de imagen invalidas (<= 0)")
    win_w_uv = window_uv["x1"] - window_uv["x0"]
    win_h_uv = window_uv["y1"] - window_uv["y0"]
    if win_w_uv <= 0 or win_h_uv <= 0:
        raise ValueError("ventana UV degenerada")
    win_w_px = win_w_uv * fw_px
    win_h_px = win_h_uv * fh_px

    k = win_w_px / iw_px            # fit width SIEMPRE
    frac_w = 1.0
    frac_h = win_h_px / (k * ih_px)  # >1: sobra alto (fade); <1: se recorta

    scale_x = frac_w / win_w_uv
    scale_y = frac_h / win_h_uv
    loc_x = (1.0 - frac_w) / 2.0 - window_uv["x0"] * scale_x
    loc_y = (1.0 - frac_h) / 2.0 - window_uv["y0"] * scale_y
    return (scale_x, scale_y), (loc_x, loc_y)


def classify_fitwidth_layout(window_uv, frame_size, input_size):
    """Describe the shared image/video fit-width-plus-fade policy."""
    fw_px, fh_px = frame_size
    iw_px, ih_px = input_size
    if min(fw_px, fh_px, iw_px, ih_px) <= 0:
        raise ValueError("dimensiones de imagen invalidas (<= 0)")
    win_w_uv = window_uv["x1"] - window_uv["x0"]
    win_h_uv = window_uv["y1"] - window_uv["y0"]
    if win_w_uv <= 0 or win_h_uv <= 0:
        raise ValueError("ventana UV degenerada")
    window_aspect = (win_w_uv * fw_px) / (win_h_uv * fh_px)
    source_aspect = iw_px / ih_px
    return {
        "policy": IMAGE_LAYOUT_POLICY,
        "window_aspect_ratio": round(window_aspect, 6),
        "source_aspect_ratio": round(source_aspect, 6),
        "crop_axis": "vertical" if source_aspect < window_aspect else "none",
        "fade_axis": "vertical",
        "centered": True,
        "distorted": False,
        "black_bars": False,
    }


def fitcontain_mapping(window_uv, frame_size, input_size):
    """Map a complete input inside the window without cropping or stretching.

    Coordinates outside the source range are intentionally left to the
    existing CLIP image node and fade graph, which render them as black bands.
    """
    fw_px, fh_px = frame_size
    iw_px, ih_px = input_size
    if min(fw_px, fh_px, iw_px, ih_px) <= 0:
        raise ValueError("dimensiones de imagen invalidas (<= 0)")
    win_w_uv = window_uv["x1"] - window_uv["x0"]
    win_h_uv = window_uv["y1"] - window_uv["y0"]
    if win_w_uv <= 0 or win_h_uv <= 0:
        raise ValueError("ventana UV degenerada")
    win_w_px = win_w_uv * fw_px
    win_h_px = win_h_uv * fh_px

    k = min(win_w_px / iw_px, win_h_px / ih_px)
    frac_w = win_w_px / (k * iw_px)
    frac_h = win_h_px / (k * ih_px)
    scale_x = frac_w / win_w_uv
    scale_y = frac_h / win_h_uv
    loc_x = (1.0 - frac_w) / 2.0 - window_uv["x0"] * scale_x
    loc_y = (1.0 - frac_h) / 2.0 - window_uv["y0"] * scale_y
    return (scale_x, scale_y), (loc_x, loc_y)


def fitcover_mapping(window_uv, frame_size, input_size, offset_y=0.0):
    """Map an input to cover the measured window, centered and cropped.

    This is intentionally separate from ``fitwidth_mapping``: the still-image
    workflow keeps its validated fit-width/fade behavior, while video clips
    must fill the portrait glass even when their source is 16:9.
    """
    fw_px, fh_px = frame_size
    iw_px, ih_px = input_size
    if min(fw_px, fh_px, iw_px, ih_px) <= 0:
        raise ValueError("dimensiones de imagen invalidas (<= 0)")
    win_w_uv = window_uv["x1"] - window_uv["x0"]
    win_h_uv = window_uv["y1"] - window_uv["y0"]
    if win_w_uv <= 0 or win_h_uv <= 0:
        raise ValueError("ventana UV degenerada")
    win_w_px = win_w_uv * fw_px
    win_h_px = win_h_uv * fh_px

    # Cover: choose the larger scale, so neither window dimension exposes
    # empty content. The remaining source area is cropped symmetrically.
    k = max(win_w_px / iw_px, win_h_px / ih_px)
    frac_w = win_w_px / (k * iw_px)
    frac_h = win_h_px / (k * ih_px)
    scale_x = frac_w / win_w_uv
    scale_y = frac_h / win_h_uv
    loc_x = (1.0 - frac_w) / 2.0 - window_uv["x0"] * scale_x
    # ``offset_y`` is a fraction of the destination window. Positive values
    # move the visible source down in the render. It is optional so callers
    # can preserve the strict mathematical center.
    loc_y = ((1.0 - frac_h) / 2.0 - window_uv["y0"] * scale_y
             + offset_y * scale_y)
    return (scale_x, scale_y), (loc_x, loc_y)


def classify_cover_layout(window_uv, frame_size, input_size):
    """Describe the crop implied by the canonical video cover policy.

    The decision uses measured window and real source dimensions. It never
    assumes that a video is 16:9. ``crop_axis`` explains what cover removes:
    equal left/right strips for ``lateral``, equal top/bottom strips for
    ``vertical``, or nothing when aspect ratios match.
    """
    fw_px, fh_px = frame_size
    iw_px, ih_px = input_size
    if min(fw_px, fh_px, iw_px, ih_px) <= 0:
        raise ValueError("dimensiones de imagen invalidas (<= 0)")
    win_w_uv = window_uv["x1"] - window_uv["x0"]
    win_h_uv = window_uv["y1"] - window_uv["y0"]
    if win_w_uv <= 0 or win_h_uv <= 0:
        raise ValueError("ventana UV degenerada")
    window_aspect = (win_w_uv * fw_px) / (win_h_uv * fh_px)
    source_aspect = iw_px / ih_px
    tolerance = 1e-6
    if source_aspect > window_aspect + tolerance:
        crop_axis = "lateral"
    elif source_aspect < window_aspect - tolerance:
        crop_axis = "vertical"
    else:
        crop_axis = "none"
    return {
        "policy": COVER_LAYOUT_POLICY,
        "window_aspect_ratio": round(window_aspect, 6),
        "source_aspect_ratio": round(source_aspect, 6),
        "crop_axis": crop_axis,
        "centered": True,
        "distorted": False,
        "black_bars": False,
    }


def classify_contain_layout(window_uv, frame_size, input_size):
    """Describe the no-crop layout reserved for non-9:16 video."""
    layout = classify_cover_layout(window_uv, frame_size, input_size)
    source_aspect = layout["source_aspect_ratio"]
    window_aspect = layout["window_aspect_ratio"]
    tolerance = 1e-6
    if source_aspect > window_aspect + tolerance:
        bar_axis = "vertical"
    elif source_aspect < window_aspect - tolerance:
        bar_axis = "lateral"
    else:
        bar_axis = "none"
    layout.update({
        "policy": CONTAIN_LAYOUT_POLICY,
        "crop_axis": "none",
        "bar_axis": bar_axis,
        "black_bars": bar_axis != "none",
    })
    return layout


def hue_de_rgb(rgb):
    """Hue [0,1) de un color RGB 0-255 (colorsys, python puro)."""
    r, g, b = (max(0, min(255, int(c))) / 255.0 for c in rgb)
    h, _s, _v = colorsys.rgb_to_hsv(r, g, b)
    return h


def _parse_args(argv):
    """Argumentos despues de '--' (estilo blender_render.py)."""
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    parsed = {"frame": None, "input": None, "color_png": None, "salida": None}
    key_map = {"--frame": "frame", "--input": "input",
               "--color-png": "color_png", "--salida": "salida"}
    i = 0
    while i < len(args):
        key = key_map.get(args[i])
        if key is None or i + 1 >= len(args):
            raise SystemExit(f"Argumento no reconocido o sin valor: {args[i]}")
        parsed[key] = args[i + 1]
        i += 2
    if not parsed["input"]:
        raise SystemExit("Falta --input (unico argumento obligatorio)")
    return parsed


def _resolver_ruta(ruta, base_blend):
    """Ruta usable: como vino, o relativa a la carpeta del .blend."""
    if ruta and not os.path.exists(ruta) and not os.path.isabs(ruta) and base_blend:
        alterna = os.path.join(base_blend, ruta)
        if os.path.exists(alterna):
            return alterna
    return ruta


def _socket(node, nombre, tipo, salida=False):
    """Socket por nombre Y tipo. ShaderNodeMix (Blender 4.x) duplica los
    nombres A/B/Result en variantes Float/Vector/Color: inputs['A'] devuelve
    la Float oculta y el link de color queda sin conectar (render negro,
    1er error de la validacion real 2026-07-10)."""
    coleccion = node.outputs if salida else node.inputs
    for s in coleccion:
        if s.name == nombre and s.type == tipo:
            return s
    raise SystemExit(f"Socket {nombre}({tipo}) no existe en {node.bl_idname}")


def _color_predominante_bpy(color_png_path):
    """Lee el pixel central del PNG de color predominante via bpy (RGB 0-255)."""
    import bpy

    img = bpy.data.images.load(color_png_path)
    try:
        w, h = img.size
        if w <= 0 or h <= 0 or len(img.pixels) < 4:
            raise ValueError(f"imagen de color invalida: {color_png_path}")
        idx = ((h // 2) * w + (w // 2)) * img.channels
        px = img.pixels[idx:idx + 3]
        return tuple(round(c * 255) for c in px)
    finally:
        bpy.data.images.remove(img)


def _repuntar_color_predominante(color_png_path):
    """Apunta el datablock color_predominante.png al MISMO png del evento.

    El vidrio decorativo de RD.blend (material 'Decorative Glass 05')
    lee esa imagen: sin esto, el marco tomaria el color del evento nuevo
    y el vidrio quedaria con el del evento anterior (detectado por el
    usuario en la validacion en vivo). Una sola imagen extraida manda.
    """
    import bpy

    img = bpy.data.images.get("color_predominante.png")
    if img is None:
        print("Aviso: el .blend no tiene datablock color_predominante.png; "
              "el vidrio decorativo no se recolorea.")
        return False
    img.filepath = color_png_path
    img.reload()
    return True


def _buscar_materiales_flyer():
    """TODOS los materiales cuyo nodo de imagen usa flyer_final (aunque
    este muteado por un rebuild previo). RD.blend real tiene DOS
    (Material.002 pantalla con emision y Material.008 cadena colgante);
    reconstruir solo el primero deja la pantalla en negro (2do error de
    la validacion real 2026-07-10). Sin adivinar nombres."""
    import bpy

    encontrados = []
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image and \
                    "flyer_final" in node.image.name.lower():
                encontrados.append((mat, node))
    if not encontrados:
        raise SystemExit(
            "No encontre un material con textura flyer_final en el .blend; "
            "este script espera el RD.blend real (no adivinar)."
        )
    return encontrados


def _nodo_por_label(mat, label):
    for n in mat.node_tree.nodes:
        if n.label == label:
            return n
    return None


def _actualizar_flyer_nodes(mat, frame_path, input_path, hue_objetivo):
    """Modo UPDATE (idempotencia): el grafo ya existe en el .blend
    guardado; solo cambia imagen del contenido, mapping fit-width y hue."""
    import bpy

    tree = mat.node_tree
    ti = _nodo_por_label(mat, LBL_CONTENIDO)
    tf = _nodo_por_label(mat, LBL_MARCO)
    hv = _nodo_por_label(mat, LBL_HUE)
    mapping = next(n for n in tree.nodes if n.type == "MAPPING" and any(
        l.to_node == ti for l in tree.links if l.from_node == n))

    tf.image = bpy.data.images.load(frame_path, check_existing=True)
    ti.image = bpy.data.images.load(input_path, check_existing=True)
    (sx, sy), (lx, ly) = fitwidth_mapping(
        WINDOW_UV, tuple(tf.image.size), tuple(ti.image.size))
    mapping.inputs["Scale"].default_value = (sx, sy, 1.0)
    mapping.inputs["Location"].default_value = (lx, ly, 0.0)
    hv.outputs[0].default_value = hue_objetivo


def build_flyer_nodes(mat, nodo_original, frame_path, input_path, hue_objetivo):
    """Construye (o actualiza) el grafo: marco recoloreado sobre el input
    ajustado al ancho, con fade a negro en el alto sobrante.

    El nodo de imagen original (flyer_final.jpg) queda mudo, no se borra:
    los links que salian de su Color pasan a salir de la mezcla nueva.
    Devuelve 'update' o 'build' segun el camino tomado.
    """
    import bpy

    if _nodo_por_label(mat, LBL_MEZCLA) is not None:
        _actualizar_flyer_nodes(mat, frame_path, input_path, hue_objetivo)
        return "update"

    tree = mat.node_tree
    nodes, links = tree.nodes, tree.links

    # check_existing: al reconstruir varios materiales, una sola copia en RAM
    frame_img = bpy.data.images.load(frame_path, check_existing=True)
    input_img = bpy.data.images.load(input_path, check_existing=True)

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.vector_type = "POINT"
    (sx, sy), (lx, ly) = fitwidth_mapping(
        WINDOW_UV, tuple(frame_img.size), tuple(input_img.size))
    mapping.inputs["Scale"].default_value = (sx, sy, 1.0)
    mapping.inputs["Location"].default_value = (lx, ly, 0.0)

    tex_input = nodes.new("ShaderNodeTexImage")
    tex_input.image = input_img
    tex_input.extension = "CLIP"    # fuera del contenido no hay textura
    tex_input.label = LBL_CONTENIDO
    tex_frame = nodes.new("ShaderNodeTexImage")
    tex_frame.image = frame_img
    tex_frame.label = LBL_MARCO

    # Recolor del marco: fijar el hue al del color predominante. Los pixeles
    # neutros (marco negro, blancos) no cambian porque su saturacion es ~0;
    # los acentos saltan al color del evento conservando S y V.
    sep = nodes.new("ShaderNodeSeparateColor")
    sep.mode = "HSV"
    comb = nodes.new("ShaderNodeCombineColor")
    comb.mode = "HSV"
    hue_val = nodes.new("ShaderNodeValue")
    hue_val.outputs[0].default_value = hue_objetivo
    hue_val.label = LBL_HUE

    links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_input.inputs["Vector"])
    links.new(tex_frame.outputs["Color"], sep.inputs["Color"])
    links.new(hue_val.outputs[0], comb.inputs["Red"])      # H en modo HSV
    links.new(sep.outputs["Green"], comb.inputs["Green"])  # S
    links.new(sep.outputs["Blue"], comb.inputs["Blue"])    # V

    # Mascara de fade: 1 dentro del contenido, cae a 0 en FADE hacia cada
    # borde (en coords del contenido, o sea despues del mapping).
    sep_xyz = nodes.new("ShaderNodeSeparateXYZ")
    links.new(mapping.outputs["Vector"], sep_xyz.inputs["Vector"])

    def _borde(salida_eje, invertir):
        if invertir:
            m1 = nodes.new("ShaderNodeMath")
            m1.operation = "SUBTRACT"
            m1.inputs[0].default_value = 1.0
            links.new(salida_eje, m1.inputs[1])
            fuente = m1.outputs[0]
        else:
            fuente = salida_eje
        m2 = nodes.new("ShaderNodeMath")
        m2.operation = "DIVIDE"
        m2.inputs[1].default_value = FADE
        m2.use_clamp = True
        links.new(fuente, m2.inputs[0])
        return m2.outputs[0]

    def _eje(salida_eje):
        m = nodes.new("ShaderNodeMath")
        m.operation = "MINIMUM"
        links.new(_borde(salida_eje, False), m.inputs[0])
        links.new(_borde(salida_eje, True), m.inputs[1])
        return m.outputs[0]

    mascara = nodes.new("ShaderNodeMath")
    mascara.operation = "MULTIPLY"
    mascara.use_clamp = True
    links.new(_eje(sep_xyz.outputs["X"]), mascara.inputs[0])
    links.new(_eje(sep_xyz.outputs["Y"]), mascara.inputs[1])

    # Contenido con fade a negro (sin doble textura, pedido del usuario)
    mezcla_fade = nodes.new("ShaderNodeMix")
    mezcla_fade.data_type = "RGBA"
    mezcla_fade.label = LBL_FADE
    _socket(mezcla_fade, "A", "RGBA").default_value = (0.0, 0.0, 0.0, 1.0)
    links.new(mascara.outputs[0], _socket(mezcla_fade, "Factor", "VALUE"))
    links.new(tex_input.outputs["Color"], _socket(mezcla_fade, "B", "RGBA"))

    # Marco (recoloreado) SOBRE el contenido, segun el alpha del marco
    mezcla = nodes.new("ShaderNodeMix")
    mezcla.data_type = "RGBA"
    mezcla.label = LBL_MEZCLA
    links.new(tex_frame.outputs["Alpha"], _socket(mezcla, "Factor", "VALUE"))
    links.new(_socket(mezcla_fade, "Result", "RGBA", salida=True),
              _socket(mezcla, "A", "RGBA"))
    links.new(comb.outputs["Color"], _socket(mezcla, "B", "RGBA"))
    resultado = _socket(mezcla, "Result", "RGBA", salida=True)

    # == y no 'is': bpy recrea el wrapper Python en cada acceso, asi que
    # 'is' compara wrappers distintos del mismo nodo y nunca matchea (3er
    # error de la validacion real 2026-07-10: el link viejo sobrevivia,
    # el nodo quedaba muteado y la pantalla renderizaba negra).
    destinos = [(l.to_node, l.to_socket) for l in tree.links
                if l.from_node == nodo_original and l.from_socket.name == "Color"]
    for l in [l for l in tree.links if l.from_node == nodo_original]:
        tree.links.remove(l)
    for _to_node, to_socket in destinos:
        links.new(resultado, to_socket)
    nodo_original.mute = True
    return "build"


def main():
    import bpy
    from blender_gpu import force_gpu  # noqa: E402 -- modulo hermano

    args = _parse_args(sys.argv)
    base_blend = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
    # defaults desde la carpeta del .blend; rutas relativas tambien caen ahi
    if not args["frame"] and base_blend:
        args["frame"] = os.path.join(base_blend, "FRAME2.png")
    if not args["color_png"] and base_blend:
        args["color_png"] = os.path.join(base_blend, "RESULTADOS",
                                         "color_predominante.png")
    for clave in ("frame", "input", "color_png", "salida"):
        args[clave] = _resolver_ruta(args[clave], base_blend)
    for ruta in ("frame", "input"):
        if not args[ruta] or not os.path.exists(args[ruta]):
            raise SystemExit(f"No existe --{ruta}: {args[ruta]}")

    if args["color_png"] and os.path.exists(args["color_png"]):
        color_png = os.path.abspath(args["color_png"])
        rgb = _color_predominante_bpy(color_png)
        # el mismo png del evento manda tambien en el vidrio decorativo
        _repuntar_color_predominante(color_png)
    else:
        rgb = (0, 254, 254)  # cyan de referencia del flyer_final validado
    hue = hue_de_rgb(rgb)
    print(f"Color predominante RGB={rgb} hue={hue:.4f}")

    for mat, nodo in _buscar_materiales_flyer():
        modo = build_flyer_nodes(mat, nodo, os.path.abspath(args["frame"]),
                                 os.path.abspath(args["input"]), hue)
        print(f"Material '{mat.name}' {modo} por nodos (sin Photoshop).")

    print(f"GPU: {force_gpu()}")
    if args["salida"]:
        bpy.context.scene.render.filepath = os.path.abspath(args["salida"])
        bpy.ops.render.render(write_still=True)
        print(f"Render guardado en: {args['salida']}")


if __name__ == "__main__":
    main()
