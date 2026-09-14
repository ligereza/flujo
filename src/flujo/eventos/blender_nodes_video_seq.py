"""Como blender_nodes_video.py pero renderiza PNG por frame (no FFMPEG mux),
con resume: salta frames ya escritos con tamano sano. Reusa el mismo grafo
de nodos probado (blender_nodes.py) via blender_nodes_video.py.

Uso:
    blender -b RD_video.blend --python blender_nodes_video_seq.py -- \
        --input input_ig_video.mp4 --frame FRAME2.png \
        --color-png color_predominante.png --out-dir RESULTADOS/frames_x \
        --frame-start 1 --frame-end 600 --min-size 20000
"""
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_nodes as bn  # noqa: E402
import blender_nodes_video as bnv  # noqa: E402


def _parse_args(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    parsed = {
        "frame": None, "input": None, "color_png": None, "out_dir": None,
        "frame_start": 1, "frame_end": None, "min_size": 20000,
        "manifest": None, "fps": None, "persistent_data": True,
        "layout": bnv.VIDEO_LAYOUT_PORTRAIT, "issue_flow": None,
    }
    key_map = {
        "--frame": "frame", "--input": "input", "--color-png": "color_png",
        "--out-dir": "out_dir", "--frame-start": "frame_start",
        "--frame-end": "frame_end", "--min-size": "min_size",
        "--manifest": "manifest", "--layout": "layout",
        "--issue-flow": "issue_flow",
        "--fps": "fps",
    }
    i = 0
    while i < len(args):
        if args[i] == "--no-persistent-data":
            parsed["persistent_data"] = False
            i += 1
            continue
        key = key_map.get(args[i])
        if key is None or i + 1 >= len(args):
            raise SystemExit(f"Argumento no reconocido o sin valor: {args[i]}")
        val = args[i + 1]
        if key in ("frame_start", "frame_end", "min_size"):
            val = int(val)
        elif key == "fps":
            val = float(val)
        parsed[key] = val
        i += 2
    if not parsed["input"] or not parsed["out_dir"]:
        raise SystemExit("Faltan --input y/o --out-dir (obligatorios)")
    if parsed["layout"] not in bn.VALID_VIDEO_LAYOUTS:
        raise SystemExit(f"VIDEO_LAYOUT_INVALID: {parsed['layout']}")
    return parsed


def main():
    import bpy
    from blender_gpu import force_gpu  # noqa: E402

    args = _parse_args(sys.argv)
    base_blend = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
    if not args["frame"] and base_blend:
        args["frame"] = os.path.join(base_blend, "FRAME2.png")
    if not args["color_png"] and base_blend:
        args["color_png"] = os.path.join(base_blend, "RESULTADOS", "color_predominante.png")
    for clave in ("frame", "input", "color_png"):
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
    frame_probe = bpy.data.images.load(args["frame"], check_existing=True)
    layout = bnv.describe_video_layout(
        args["layout"], tuple(frame_probe.size), tuple(probe.size))
    print(f"VIDEO_LAYOUT: {json.dumps(layout, ensure_ascii=True)}")

    frame_start = args["frame_start"] or 1
    frame_end = args["frame_end"] or frame_duration
    if frame_end > frame_duration:
        print(f"Aviso: --frame-end {frame_end} > duracion real {frame_duration}; recortando.")
        frame_end = frame_duration

    try:
        flyer_materials = bn._buscar_materiales_flyer()
    except SystemExit as exc:
        print(f"Plantilla video detectada; no se usa el grafo flyer: {exc}")
        flyer_materials = []

    if flyer_materials:
        for mat, nodo in flyer_materials:
            modo = bnv.build_flyer_nodes_video(
                mat, nodo, os.path.abspath(args["frame"]), video_path, hue,
                frame_duration, args["layout"])
            print(f"Material '{mat.name}' {modo} layout={args['layout']} por nodos VIDEO (sin Photoshop).")
    else:
        if args["layout"] != bnv.VIDEO_LAYOUT_FITWIDTH:
            raise SystemExit("VIDEO_LAYOUT_TEMPLATE_REQUIRED: fitwidth_fade requiere RD.blend con grafo flyer")
        swapped = bnv.swap_existing_movie_nodes(video_path, frame_duration)
        if swapped < 1:
            raise SystemExit("VIDEO_NODE_REQUIRED: no hay nodos TEX_IMAGE con source MOVIE")
        print(f"Nodos MOVIE existentes re-apuntados: {swapped}")

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    gpu_report = force_gpu(prefer=("CUDA", "OPTIX", "HIP"))
    if gpu_report.get("device") != "GPU":
        raise SystemExit(f"GPU_REQUIRED: {gpu_report}")
    print(f"GPU: {gpu_report}")

    scene.frame_start = frame_start
    scene.frame_end = frame_end
    video_fps = getattr(probe, "fps", 0) or 0
    source_fps = args["fps"] or video_fps or scene.render.fps
    if source_fps:
        scene.render.fps = round(source_fps)
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.render.use_simplify = True
    scene.cycles.texture_limit_render = "2048"
    scene.cycles.use_auto_tile = True
    scene.cycles.tile_size = 512
    # Reuse BVH/shader data between frames.  The movie image still refreshes
    # per frame; this only avoids rebuilding static scene state.
    scene.render.use_persistent_data = args["persistent_data"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    out_dir = args["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    min_size = args["min_size"]

    rendered = 0
    skipped = 0
    for f in range(frame_start, frame_end + 1):
        out_path = os.path.join(out_dir, f"frame_{f:04d}.png")
        if os.path.exists(out_path) and os.path.getsize(out_path) >= min_size:
            skipped += 1
            continue
        scene.frame_set(f)
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        rendered += 1
        print(f"OK frame {f}/{frame_end} -> {out_path} "
              f"({os.path.getsize(out_path)} bytes)")

    report = {
        "input": video_path,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "source_frames": frame_duration,
        "fps": source_fps,
        "layout": layout,
        "issue_flow": args["issue_flow"],
        "samples": scene.cycles.samples,
        "engine": scene.render.engine,
        "gpu": gpu_report,
        "output_dir": os.path.abspath(out_dir),
        "rendered": rendered,
        "skipped": skipped,
        "png_count": rendered + skipped,
    }
    if args.get("manifest"):
        manifest = bn._resolver_ruta(args["manifest"], base_blend)
        os.makedirs(os.path.dirname(os.path.abspath(manifest)), exist_ok=True)
        with open(manifest, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=True)
    print(f"MANIFEST: {json.dumps(report, ensure_ascii=True)}")
    print(f"Listo: {rendered} renderizados, {skipped} saltados (ya existian).")


if __name__ == "__main__":
    main()
