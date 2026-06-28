from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Union


SvgInput = Union[str, Path, Iterable[Union[str, Path]]]


def prepare_svg_for_illustrator(
    svg_inputs: SvgInput,
    output_dir: str | Path | None = None,
    project_name: str = "flujo_svg",
) -> Path:
    """Crear un paquete listo para abrir en Illustrator desde uno o varios SVG.

    El paquete incluye una carpeta ``svg/`` con los archivos copiados, un script
    JSX para Illustrator y un README con instrucciones simples.
    """

    if isinstance(svg_inputs, (str, Path)):
        candidates = [Path(svg_inputs)]
    else:
        candidates = [Path(item) for item in svg_inputs]

    resolved_files: list[Path] = []
    for item in candidates:
        if item.is_dir():
            resolved_files.extend(sorted([p for p in item.rglob("*.svg") if p.is_file()]))
        elif item.suffix.lower() == ".svg" and item.exists():
            resolved_files.append(item)
        else:
            raise FileNotFoundError(f"SVG no encontrado o no válido: {item}")

    if not resolved_files:
        raise FileNotFoundError("No se encontraron archivos SVG para preparar")

    unique_files: list[Path] = []
    seen: set[Path] = set()
    for path in resolved_files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_files.append(resolved)

    base_output = Path(output_dir) if output_dir else Path("exports") / f"{project_name}_illustrator"
    package_dir = base_output / project_name
    package_dir.mkdir(parents=True, exist_ok=True)

    svg_dir = package_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    for source in unique_files:
        destination = svg_dir / source.name
        destination.write_bytes(source.read_bytes())
        copied_files.append(destination.relative_to(package_dir).as_posix())

    manifest = {
        "project": project_name,
        "svg_files": copied_files,
        "created_with": "flujo.export.illustrator.prepare_svg_for_illustrator",
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (package_dir / "import_svg.jsx").write_text(_build_illustrator_jsx(copied_files), encoding="utf-8")
    (package_dir / "README.md").write_text(_build_readme(project_name, copied_files), encoding="utf-8")

    return package_dir


def prepare_supplement_contraportadas_for_illustrator(
    supplements: str | Iterable[str],
    output_dir: str | Path | None = None,
    project_name: str = "suplementos_rd",
) -> Path:
    """Preparar un paquete Illustrator con varias contraportadas de suplementos.

    Genera un SVG por suplemento a partir de la plantilla base, lo guarda en una
    carpeta `svg/` del paquete y crea un script JSX con mesas de trabajo listas
    para abrir en Illustrator junto con un README y un manifest.
    """
    if isinstance(supplements, str):
        names = [supplements]
    else:
        names = [str(item) for item in supplements]

    if not names:
        raise ValueError("Se debe indicar al menos un suplemento")

    from ..comercial.suplementos_config import get_suplemento
    from ..comercial.contraportada_svg import generar_contraportada
    from .illustrator_bridge import write_illustrator_artboards

    base_output = Path(output_dir) if output_dir else Path("exports") / f"{project_name}_illustrator"
    package_dir = base_output / project_name
    package_dir.mkdir(parents=True, exist_ok=True)

    svg_dir = package_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)

    generated_files: list[str] = []
    artboards: list[dict[str, Any]] = []
    for name in names:
        suplemento = get_suplemento(name)
        output_path = svg_dir / f"{_slugify(suplemento.nombre)}_final.svg"
        generar_contraportada(suplemento, output_path=output_path)
        generated_files.append(output_path.relative_to(package_dir).as_posix())
        artboards.append(
            {
                "name": suplemento.nombre,
                "title": suplemento.nombre.upper(),
                "body": [suplemento.descripcion, *suplemento.info_nutricional[:2]],
                "cta": suplemento.beneficio_1,
                "contact": f"{suplemento.whatsapp_label} · {suplemento.contacto_label}",
            }
        )

    manifest = {
        "project": project_name,
        "type": "supplement_contraportadas",
        "supplements": [name for name in names],
        "svg_files": generated_files,
        "datadrop_reference": _load_datadrop_reference(),
        "created_with": "flujo.export.illustrator.prepare_supplement_contraportadas_for_illustrator",
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    spec = {
        "document": {
            "name": project_name,
            "width": 2362,
            "height": 1654,
            "colorMode": "RGB",
        },
        "artboards": artboards,
    }
    write_illustrator_artboards(spec, package_dir / "illustrator_artboards.jsx", base_dir=package_dir)
    (package_dir / "README.md").write_text(_build_supplement_readme(project_name, generated_files, manifest["datadrop_reference"]), encoding="utf-8")

    return package_dir


def prepare_supplement_job_assets(
    job_dir: str | Path,
    request_text: str = "",
    document_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Crear artefactos flexibles para flyer/suplemento dentro de un job."""
    job_path = Path(job_dir)
    job_path.mkdir(parents=True, exist_ok=True)

    flows_dir = job_path / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)

    from ..comercial.suplementos_config import get_suplemento
    from ..comercial.contraportada_svg import generar_contraportada
    from .illustrator_bridge import write_illustrator_artboards

    selected_names = []
    if request_text:
        lowered = request_text.lower()
        for name in ["Impulso", "Creatina", "Pre Fiesta", "Recovery", "Colágeno Fit", "Omega+ Immune", "Sleep Relax"]:
            if name.lower() in lowered:
                selected_names.append(name)
    if not selected_names:
        selected_names = ["Impulso"]

    supplement = get_suplemento(selected_names[0])
    svg_output = flows_dir / "contraportada.svg"
    generar_contraportada(supplement, output_path=svg_output)

    package_dir = flows_dir / "illustrator_package" / job_path.name
    package_dir.mkdir(parents=True, exist_ok=True)
    svg_dir = package_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)

    package_svg = svg_dir / svg_output.name
    package_svg.write_bytes(svg_output.read_bytes())

    size = document_size or (2362, 1654)
    spec = {
        "document": {"name": job_path.name, "width": size[0], "height": size[1], "colorMode": "RGB"},
        "artboards": [
            {
                "name": supplement.nombre,
                "title": supplement.nombre.upper(),
                "body": [supplement.descripcion, *supplement.info_nutricional[:2]],
                "cta": supplement.beneficio_1,
                "contact": f"{supplement.whatsapp_label} · {supplement.contacto_label}",
            }
        ],
    }
    write_illustrator_artboards(spec, package_dir / "illustrator_artboards.jsx", base_dir=package_dir)
    (package_dir / "README.md").write_text(
        f"# {job_path.name}\n\nPaquete de revisión flexible para flyer/suplemento generado desde el hub.\n",
        encoding="utf-8",
    )

    return {
        "created": True,
        "svg_path": str(svg_output).replace("\\", "/"),
        "package_dir": str(package_dir).replace("\\", "/"),
        "supplement": supplement.nombre,
        "document_size": [size[0], size[1]],
    }


def _build_illustrator_jsx(svg_files: list[str]) -> str:
    entries = [f'  new File(baseFolder + "/svg/{path.split("/")[-1]}")' for path in svg_files]
    entries_block = ",\n".join(entries)
    return f"""// import_svg.jsx — preparado por flujo
#target illustrator

function main() {{
    var baseFolder = Folder.current;
    var svgFiles = [
{entries_block}
    ];

    if (!svgFiles.length) {{
        alert("No se encontraron SVGs para importar");
        return;
    }}

    var doc = app.documents.add(DocumentColorSpace.RGB, 1400, 900);
    doc.artboards[0].name = "SVG import";

    var x = 80;
    var y = 120;
    for (var i = 0; i < svgFiles.length; i++) {{
        if (!svgFiles[i].exists) continue;

        var placed = doc.placedItems.add();
        placed.file = svgFiles[i];
        placed.name = svgFiles[i].name.replace(/\\.svg$/i, "");
        placed.position = [x, y];

        var scale = 0.8;
        placed.resize(scale * 100, scale * 100);
        x += 280;
        if ((i + 1) % 3 === 0) {{
            x = 80;
            y -= 240;
        }}
    }}

    alert("SVGs importados. Ajusta tamaño/posición en Illustrator si hace falta.");
}}

main();
"""


def _build_readme(project_name: str, svg_files: list[str]) -> str:
    svg_list = "\n".join(f"- {path}" for path in svg_files)
    return f"""# {project_name}

Paquete preparado para abrir en Illustrator desde SVGs.

## Archivos
{svg_list}

## Pasos
1. Abre `import_svg.jsx` con Illustrator.
2. Asegúrate de que la carpeta `svg/` esté junto al script.
3. Revisa el documento resultante y ajusta escala/posición si hace falta.

## Nota
Este paquete conserva el SVG como vector editable y facilita la revisión en Illustrator.
"""


def _build_supplement_readme(project_name: str, svg_files: list[str], datadrop_reference: dict[str, Any]) -> str:
    svg_list = "\n".join(f"- {path}" for path in svg_files)
    reference_id = datadrop_reference.get("id", "")
    reference_note = datadrop_reference.get("for_future_ai", "")
    return f"""# {project_name}

Paquete preparado para revisar contraportadas de suplementos en Illustrator.

## Archivos
{svg_list}

- `illustrator_artboards.jsx`: script con mesas de trabajo por suplemento
- `manifest.json`: metadatos del paquete y referencia de datadrop

## Pasos
1. Abre `illustrator_artboards.jsx` con Illustrator.
2. Revisa cada mesa de trabajo y ajusta tipografía, color y márgenes si hace falta.
3. Exporta a PDF/PNG cuando la revisión esté lista.

## Referencia datadrop
- ID: {reference_id}
- Nota: {reference_note[:280]}
"""


def _slugify(value: str) -> str:
    return value.lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def _load_datadrop_reference() -> dict[str, Any]:
    from ..paths import repo_root

    datadrops_root = repo_root() / "datadrops"
    if not datadrops_root.exists():
        return {"id": "", "for_future_ai": "", "image_path": ""}

    candidates = sorted(datadrops_root.glob("*/manifest.json"))
    for manifest_path in candidates:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("type") == "flyer" and "suplementos" in str(data.get("original_filename", "")).lower():
            return {
                "id": data.get("id", ""),
                "image_path": data.get("image_path", ""),
                "for_future_ai": data.get("for_future_ai", ""),
            }

    for manifest_path in candidates:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("type") == "flyer":
            return {
                "id": data.get("id", ""),
                "image_path": data.get("image_path", ""),
                "for_future_ai": data.get("for_future_ai", ""),
            }

    return {"id": "", "for_future_ai": "", "image_path": ""}
