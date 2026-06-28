#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

def usage():
    print('Uso:')
    print('  python scripts/flyer_set_input.py "projects/flyer_eventos/PROYECTO" "ruta/imagen.jpg"')
    sys.exit(1)

if len(sys.argv) < 3:
    usage()

project_dir = Path(sys.argv[1])
image_path = Path(sys.argv[2])

if not project_dir.exists():
    print(f"ERROR: no existe proyecto: {project_dir}")
    sys.exit(1)

if not image_path.exists():
    print(f"ERROR: no existe imagen: {image_path}")
    sys.exit(1)

input_dir = project_dir / "input"
input_dir.mkdir(parents=True, exist_ok=True)

target = input_dir / "input_ig.jpg"
shutil.copy2(image_path, target)

manifest_path = project_dir / "manifest.json"
if manifest_path.exists():
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
else:
    data = {}

data.setdefault("input", {})
data["input"]["main_image"] = str(target).replace("\\", "/")
data["input"]["updated_at"] = datetime.now().isoformat(timespec="seconds")
data["status"] = "input_ready"

manifest_path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"OK: imagen copiada a {target}")
print(f"OK: manifest actualizado {manifest_path}")
