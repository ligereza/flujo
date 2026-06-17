#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Uso: py scripts/flyer_status.py "projects/flyer_eventos/PROYECTO"')
    sys.exit(1)

project = Path(sys.argv[1])
manifest = project / "manifest.json"

if not project.exists():
    print(f"ERROR: no existe proyecto: {project}")
    sys.exit(1)

if not manifest.exists():
    print(f"ERROR: no existe manifest: {manifest}")
    sys.exit(1)

data = json.loads(manifest.read_text(encoding="utf-8"))

print("")
print("=== Flyer status ===")
print(f"Proyecto: {project}")
print(f"Nombre: {data.get('name', '')}")
print(f"Estado: {data.get('status', '')}")
print("")

# Instagram info
ig = data.get("instagram", {})
if ig:
    print("Instagram:")
    print(f"- URL: {ig.get('url','')}")
    print(f"- Shortcode: {ig.get('shortcode','')}")
    print(f"- Owner: {ig.get('owner','')}")
    print(f"- Fecha IG: {ig.get('date_utc','')}")
    print(f"- Tipo: {ig.get('type','')} / media: {ig.get('media_type','')}")
    print(f"- Download: {ig.get('download_status','')}")
    print(f"- Archivos: {ig.get('file_count',0)}")
    print("")

print("Inputs:")
inp = data.get("input", {})
print(f"- Imagen principal: {inp.get('main_image', '')}")
print(f"- Fecha evento: {inp.get('event_date', '')}")
print(f"- Formato: {inp.get('format', '')}")
print(f"- Notas: {inp.get('notes', '')}")

# Revisar archivos físicos en input/
input_dir = project / "input"
if input_dir.exists():
    ig_files = sorted([f.name for f in input_dir.glob("input_ig*")])
    caption_file = input_dir / "ig_caption.txt"
    print("")
    print(f"Archivos IG en input/: {len(ig_files)}")
    for f in ig_files[:6]:
        print(f"  - {f}")
    if len(ig_files) > 6:
        print(f"  ... y {len(ig_files)-6} más")
    if caption_file.exists():
        cap = caption_file.read_text(encoding="utf-8", errors="ignore")
        preview = cap[:120].replace("\n", " ")
        print(f"Caption: {preview}{'...' if len(cap)>120 else ''}")

print("")
print("Pasos:")
steps = data.get("steps", {})
for k, v in steps.items():
    print(f"- {k}: {v}")

print("")
print("Extraído:")
ext = data.get("extracted_info", {})
for k in ["event_name", "producer", "producer_suggested", "venue", "event_date", "caption_from_ig"]:
    if ext.get(k):
        val = str(ext[k])
        if k == "caption_from_ig":
            val = val[:80].replace("\n", " ") + ("..." if len(val) > 80 else "")
        print(f"- {k}: {val}")

print("")
print("Outputs:")
outs = data.get("outputs", [])
if not outs:
    print("- ninguno")
else:
    for out in outs:
        print(f"- {out}")

print("")
