#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render de video RD: mete un mp4 (reel) en RD.paravideo.blend y exporta H264.

Opcion B del pipeline eventos (decidida 2026-07-22): el .blend queda intacto
como plantilla; este script arma una llamada headless de Blender que:
  1. carga el mp4 como movieclip y lee frame_duration/fps REALES (nunca
     hardcodear frames),
  2. re-apunta todos los nodos TEX_IMAGE cuyo source ya es MOVIE (la
     plantilla RD.paravideo.blend trae Material.002 con textura MOVIE)
     al video nuevo, con use_auto_refresh,
  3. configura salida FFMPEG/H264 (FFmpeg embebido de Blender, sin deps)
     y renderea la animacion en GPU (CUDA/OPTIX) o CPU.

Corre igual en WIN (blender.exe) y MAK (GTX 1650, CUDA 13.3, verificado
2026-07-22). stdlib puro.

Uso:
  py tools/render_video_rd.py --video reel.mp4 --out salida.mp4
  py tools/render_video_rd.py --video reel.mp4 --blend RD.paravideo.blend \
      --blender /home/mak/blender/blender --device OPTIX --max-frames 24
"""
import argparse
import os
import subprocess
import sys

DEFAULT_BLEND_WIN = r"C:\rd\AUTOMATIZACION\RD.paravideo.blend"
DEFAULT_BLEND_LINUX = os.path.expanduser("~/RD/AUTOMATIZACION/RD.paravideo.blend")


def build_expr(video: str, out: str, device: str, max_frames: int | None) -> str:
    """Arma el --python-expr. Puro y testeable: no toca disco ni subprocess."""
    cap = ""
    if max_frames:
        cap = "sc.frame_end = min(sc.frame_end, %d)\n" % int(max_frames)
    engine = ""
    if device == "EEVEE":
        # EEVEE-Next: fraccion de la VRAM de Cycles; rehabilita GPUs chicas
        # (GTX 1650 de MAK hace OOM con Cycles en RD.paravideo.blend).
        engine = "sc.render.engine = 'BLENDER_EEVEE_NEXT'\n"
    gpu = ""
    if device in ("CUDA", "OPTIX"):
        gpu = (
            "try:\n"
            "    prefs = bpy.context.preferences.addons['cycles'].preferences\n"
            "    prefs.compute_device_type = %r\n"
            "    prefs.refresh_devices()\n"
            "    for d in prefs.devices:\n"
            "        d.use = True\n"
            "    sc.cycles.device = 'GPU'\n"
            "except Exception as e:\n"
            "    print('GPU_CONFIG_FALLO', e)\n" % device
        )
    return (
        "import bpy\n"
        "clip = bpy.data.movieclips.load(%(video)r)\n"
        "sc = bpy.context.scene\n"
        "sc.frame_start = 1\n"
        "sc.frame_end = max(1, clip.frame_duration)\n"
        "%(cap)s"
        "%(engine)s"
        "if clip.fps:\n"
        "    sc.render.fps = round(clip.fps)\n"
        "vid = bpy.data.images.load(%(video)r)\n"
        "vid.source = 'MOVIE'\n"
        "n_sw = 0\n"
        "for m in bpy.data.materials:\n"
        "    if not m.node_tree:\n"
        "        continue\n"
        "    for n in m.node_tree.nodes:\n"
        "        if n.type == 'TEX_IMAGE' and n.image and n.image.source == 'MOVIE':\n"
        "            n.image = vid\n"
        "            n.image_user.frame_start = 1\n"
        "            n.image_user.frame_duration = clip.frame_duration\n"
        "            n.image_user.use_auto_refresh = True\n"
        "            n_sw += 1\n"
        "print('SWAPPED_NODES', n_sw)\n"
        "%(gpu)s"
        "r = sc.render\n"
        "r.image_settings.file_format = 'FFMPEG'\n"
        "r.ffmpeg.format = 'MPEG4'\n"
        "r.ffmpeg.codec = 'H264'\n"
        "r.ffmpeg.constant_rate_factor = 'MEDIUM'\n"
        "r.ffmpeg.audio_codec = 'AAC'\n"
        "r.filepath = %(out)r\n"
        "bpy.ops.render.render(animation=True)\n"
        "print('RENDER_DONE', r.filepath)\n"
        % {"video": video, "out": out, "cap": cap, "gpu": gpu, "engine": engine}
    )


def default_blend() -> str:
    return DEFAULT_BLEND_WIN if os.name == "nt" else DEFAULT_BLEND_LINUX


def main() -> int:
    ap = argparse.ArgumentParser(description="Render video RD (reel -> H264 via Blender)")
    ap.add_argument("--video", required=True, help="mp4 de entrada (reel)")
    ap.add_argument("--out", required=True, help="ruta de salida .mp4")
    ap.add_argument("--blend", default=default_blend(), help="plantilla .blend (video)")
    ap.add_argument("--blender", default="blender", help="ejecutable de Blender")
    ap.add_argument("--device", default="CUDA", choices=["CUDA", "OPTIX", "CPU", "EEVEE"],
                    help="dispositivo de render (default CUDA)")
    ap.add_argument("--max-frames", type=int, default=None,
                    help="cap de frames (smoke tests)")
    ap.add_argument("--dry-run", action="store_true", help="imprime el comando y sale")
    args = ap.parse_args()

    if not os.path.isfile(args.video):
        print("ERROR: video no existe: %s" % args.video)
        return 2
    if not os.path.isfile(args.blend):
        print("ERROR: blend no existe: %s" % args.blend)
        return 2

    expr = build_expr(os.path.abspath(args.video), os.path.abspath(args.out),
                      args.device, args.max_frames)
    cmd = [args.blender, "-b", args.blend, "--python-expr", expr]
    if args.dry_run:
        print("CMD:", " ".join(cmd[:3]), "... [--python-expr %d chars]" % len(expr))
        print(expr)
        return 0
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    tail = (proc.stdout or "")[-2000:]
    print(tail)
    if proc.returncode != 0:
        print("STDERR:", (proc.stderr or "")[-500:])
        return proc.returncode
    ok = "RENDER_DONE" in tail and os.path.isfile(args.out)
    print("RESULTADO:", "OK" if ok else "SIN_ARCHIVO_DE_SALIDA")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
