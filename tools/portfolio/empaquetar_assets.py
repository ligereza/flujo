"""Empaqueta las imágenes reales de works.json en un directorio de assets plano.

Lee un works.json (salida de generar_works.py), copia cada imagen existente a
<assets>/<obra_id><ext> y reescribe el campo "imagen" a la ruta relativa
"assets/flujo-works/<obra_id><ext>" (la que consume el sitio publicado).

Si "imagen" apunta a un archivo que no existe, se deja en null (nunca se
inventa un archivo ni se rompe la corrida).

Uso:
    py tools/portfolio/empaquetar_assets.py --works out/works.json --assets out/assets/flujo-works
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def empaquetar(works_path: Path, assets_dir: Path, repo_root: Path = _REPO) -> dict:
    """Copia las imágenes existentes de works.json a assets_dir y reescribe rutas.

    Retorna el dict de works.json ya actualizado (también lo escribe en works_path).
    """
    datos = json.loads(works_path.read_text(encoding="utf-8"))
    obras = datos.get("obras", [])

    assets_dir.mkdir(parents=True, exist_ok=True)

    for obra in obras:
        imagen = obra.get("imagen")
        if not imagen:
            obra["imagen"] = None
            continue

        origen = Path(imagen)
        if not origen.is_absolute():
            origen = repo_root / imagen

        if not origen.is_file():
            obra["imagen"] = None
            continue

        ext = origen.suffix
        destino = assets_dir / f"{obra['id']}{ext}"
        shutil.copy2(origen, destino)
        obra["imagen"] = f"assets/flujo-works/{obra['id']}{ext}"

    works_path.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    return datos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--works",
        default=str(_REPO / "out" / "works.json"),
        help="archivo works.json a leer/reescribir (default: out/works.json)",
    )
    ap.add_argument(
        "--assets",
        default=str(_REPO / "out" / "assets" / "flujo-works"),
        help="directorio destino de assets copiados (default: out/assets/flujo-works)",
    )
    args = ap.parse_args(argv)

    works_path = Path(args.works)
    assets_dir = Path(args.assets)

    if not works_path.is_file():
        print(f"ERROR: no existe {works_path}", file=sys.stderr)
        return 1

    datos = empaquetar(works_path, assets_dir)
    copiadas = sum(1 for o in datos.get("obras", []) if o.get("imagen"))

    print(f"OK {works_path} ({copiadas} imagen(es) empaquetada(s) en {assets_dir})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
