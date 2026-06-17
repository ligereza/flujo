#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Uso: py scripts/flyer_status.py "projects/flyer_eventos/PROYECTO"')
    sys.exit(1)

project = Path(sys.argv[1])
manifest = project / "manifest.json"

if not project.exists() or not manifest.exists():
    print(f"ERROR: no existe {project}")
    sys.exit(1)

data = json.loads(manifest.read_text(encoding="utf-8"))

print("\n=== Flyer status ===")
print(f"Proyecto: {project}")
print(f"Nombre: {data.get('name', '')}")
print(f"Estado: {data.get('status', '')}\n")

ig = data.get("instagram", {})
if ig:
    print("Instagram:")
    print(f"- URL: {ig.get('url','')}")
    print(f"- Shortcode: {ig.get('shortcode','')}")
    print(f"- Owner: {ig.get('owner','')}")
    print(f"- Fecha IG: {ig.get('date_utc','')}")
    print(f"- Tipo: {ig.get('type','')} / media: {ig.get('media_type','')}")
    print(f"- Download: {ig.get('download_status','')}")
    print(f"- Archivos: {ig.get('file_count',0)}\n")

input_dir = project / "input"
if input_dir.exists():
    ig_files = sorted([f.name for f in input_dir.glob("input_ig*")])
    print(f"Archivos IG en input/: {len(ig_files)}")
    for f in ig_files[:6]:
        print(f"  - {f}")
    if len(ig_files) > 6:
        print(f"  ... y {len(ig_files)-6} más")
    cap = input_dir / "ig_caption.txt"
    if cap.exists():
        txt = cap.read_text(encoding="utf-8", errors="ignore")
        print(f"Caption: {txt[:120].replace(chr(10),' ')}...")
    print()

ext = data.get("extracted_info", {})
print("Extraído:")
for k in ["event_name","producer","producer_suggested","venue","event_date","caption_from_ig"]:
    if ext.get(k):
        v = str(ext[k])[:80].replace("\n"," ")
        print(f"- {k}: {v}")
print()
