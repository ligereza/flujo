#!/usr/bin/env python3
"""Crea manifiesto de entrega de un proyecto renderizado."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) < 1:
        print("Uso: py scripts/project_delivery_manifest.py projects/piezas_vectoriales/NOMBRE")
        return 1

    project = Path(argv[0])
    config = project / "config.json"
    if not config.exists():
        print("No existe config.json en", project)
        return 1

    cfg = json.loads(config.read_text(encoding="utf-8"))
    exports = project / "salida_generada" / "04_exports"
    preview = project / "salida_generada" / "03_preview" / "preview.html"
    zips = sorted(exports.glob("*.zip")) if exports.exists() else []

    if zips:
        entregables = "".join(f"- `{z}`\n" for z in zips)
    else:
        entregables = "- Pendiente generar outputs.\n"

    project_name = cfg.get("project", {}).get("name", project.name)
    manifest = project / "DELIVERY.md"
    manifest.write_text(
        f"""# Delivery — {project_name}

## Proyecto

- Carpeta: `{project}`
- Config: `{config}`
- Preview: `{preview}`

## Entregables ZIP

{entregables}
## Validación sugerida

```bash
py scripts/project_render.py "{config}"
py scripts/piezas_check_outputs.py
```
""",
        encoding="utf-8",
    )
    print(f"Manifiesto creado: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
