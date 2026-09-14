"""Genera el catálogo de obras realizadas (datadrop + flyer_eventos).

Escanea dos familias de manifests:
  - datadrops/<id>/manifest.json: cargas de usuario (imágenes reales)
  - projects/flyer_eventos/<id>/manifest.json: eventos generados

Produce out/works.json con índice de obras (más recientes primero).

Uso:
    py tools/portfolio/generar_works.py [--salida PATH] [datadrops_dir] [flyer_eventos_dir]

Sin argumentos de directorio, busca en los sitios estándar (dos padres up desde este archivo).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def leer_datadrop_manifest(ruta: Path) -> dict | None:
    """Lee un manifest de datadrop, tolerante a campos faltantes.

    Retorna None si el JSON es inválido. Campos faltantes se rellenan con defaults.
    """
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return {
            "id": datos.get("id", ""),
            "uploaded_at": datos.get("uploaded_at", ""),
            "original_filename": datos.get("original_filename", ""),
            "image_path": datos.get("image_path", None),
            "type": datos.get("type", ""),
            "palette": datos.get("palette", []),
        }
    except (json.JSONDecodeError, OSError):
        return None


def leer_flyer_evento_manifest(ruta: Path) -> dict | None:
    """Lee un manifest de flyer_eventos, tolerante a campos faltantes.

    Retorna None si el JSON es inválido. Campos faltantes se rellenan con defaults.
    """
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        input_data = datos.get("input", {})
        return {
            "id": ruta.parent.name,
            "name": datos.get("name", ""),
            "date": datos.get("date", ""),
            "status": datos.get("status", ""),
            "main_image": input_data.get("main_image", None),
            "outputs": datos.get("outputs", []),
        }
    except (json.JSONDecodeError, OSError):
        return None


def extraer_fecha(fecha_str: str) -> str:
    """Extrae la parte de fecha (YYYY-MM-DD) de un timestamp ISO.

    Si es ya una fecha, la retorna. Si es vacía, retorna empty string.
    """
    if not fecha_str:
        return ""
    # Tomar solo los primeros 10 caracteres (YYYY-MM-DD)
    return fecha_str[:10]


def procesar_datadrops(datadrops_dir: Path) -> list[dict]:
    """Escanea todos los manifests de datadrop, retorna obras procesadas."""
    obras = []
    corrupt_count = 0

    if not datadrops_dir.exists():
        return obras

    for item_dir in sorted(datadrops_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        manifest_path = item_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        datos = leer_datadrop_manifest(manifest_path)
        if datos is None:
            corrupt_count += 1
            continue

        fecha = extraer_fecha(datos["uploaded_at"])

        # Extraer paleta: primeros 4 colores hex
        paleta = []
        for color in datos.get("palette", [])[:4]:
            if isinstance(color, dict) and "hex" in color:
                paleta.append(color["hex"])

        obra = {
            "id": datos["id"],
            "fuente": "datadrop",
            "titulo": Path(datos["original_filename"]).stem if datos["original_filename"] else "",
            "fecha": fecha,
            "tipo": datos["type"],
            "estado": "entregado",
            "imagen": datos["image_path"],
            "paleta": paleta,
            "salidas": None,
        }
        obras.append(obra)

    if corrupt_count > 0:
        print(f"datadrop: {corrupt_count} manifest(s) corrompido(s) o inválido(s)", file=sys.stdout)

    return obras


def procesar_flyer_eventos(flyer_dir: Path) -> list[dict]:
    """Escanea todos los manifests de flyer_eventos, retorna obras procesadas."""
    obras = []
    corrupt_count = 0

    if not flyer_dir.exists():
        return obras

    for item_dir in sorted(flyer_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        manifest_path = item_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        datos = leer_flyer_evento_manifest(manifest_path)
        if datos is None:
            corrupt_count += 1
            continue

        fecha = extraer_fecha(datos["date"])
        outputs = datos.get("outputs", [])

        obra = {
            "id": datos["id"],
            "fuente": "flyer_evento",
            "titulo": datos["name"],
            "fecha": fecha,
            "tipo": "flyer_evento",
            "estado": datos["status"],
            "imagen": datos["main_image"],
            "paleta": [],
            "salidas": len(outputs) if outputs else None,
        }
        obras.append(obra)

    if corrupt_count > 0:
        print(f"flyer_eventos: {corrupt_count} manifest(s) corrompido(s) o inválido(s)", file=sys.stdout)

    return obras


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--salida",
        default=str(_REPO / "out" / "works.json"),
        help="archivo de salida (default: out/works.json)"
    )
    ap.add_argument(
        "datadrops_dir",
        nargs="?",
        default=str(_REPO / "datadrops"),
        help="directorio datadrops (default: datadrops/)"
    )
    ap.add_argument(
        "flyer_dir",
        nargs="?",
        default=str(_REPO / "projects" / "flyer_eventos"),
        help="directorio flyer_eventos (default: projects/flyer_eventos/)"
    )
    args = ap.parse_args(argv)

    datadrops_path = Path(args.datadrops_dir)
    flyer_path = Path(args.flyer_dir)
    out_path = Path(args.salida)

    # Procesar ambas familias de manifests
    obras_datadrop = procesar_datadrops(datadrops_path)
    obras_flyer = procesar_flyer_eventos(flyer_path)

    # Combinar y ordenar por fecha descendente
    todas_las_obras = obras_datadrop + obras_flyer
    todas_las_obras.sort(key=lambda x: x["fecha"], reverse=True)

    # Construir JSON de salida
    resultado = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total": len(todas_las_obras),
        "obras": todas_las_obras,
    }

    # Escribir salida
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"OK {out_path} ({resultado['total']} obras)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
