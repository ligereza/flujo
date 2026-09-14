"""Helpers compartidos para scripts de flujo."""
import json
import re
from pathlib import Path
from datetime import datetime


def repo_root() -> Path:
    """Devuelve la raíz del repo asumiendo que este archivo está en scripts/."""
    return Path(__file__).resolve().parents[1]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "item"


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def unique_project_dir(base_dir: Path, name: str) -> Path:
    """Devuelve un directorio de proyecto que no exista, agregando -02, -03, etc. si hace falta."""
    date = datetime.now().strftime("%Y-%m-%d")
    safe = slugify(name)
    project = base_dir / f"{date}_{safe}"
    if not project.exists():
        return project
    n = 2
    while True:
        candidate = Path(f"{project}-{n:02d}")
        if not candidate.exists():
            return candidate
        n += 1


def create_flyer_project(base_dir: Path, name: str, source_type: str = "manual") -> Path:
    """Crea la estructura estándar de un proyecto flyer_eventos."""
    project = unique_project_dir(base_dir, name)
    date = project.name[:10]

    for folder in ["input", "working", "exports", "refs", "analysis", "ai"]:
        d = project / folder
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()

    manifest = {
        "tool": "flyer_eventos",
        "name": name,
        "date": date,
        "status": "created",
        "source": {"type": source_type},
        "input": {
            "main_image": "",
            "event_name": name,
            "event_date": "",
            "format": "",
            "notes": ""
        },
        "steps": {
            "photoshop": "pending",
            "blender": "pending",
            "export": "pending"
        },
        "outputs": []
    }

    write_json(project / "manifest.json", manifest)

    (project / "README.md").write_text(
        f"""# Flyer evento — {name}

Fecha: {date}

## Objetivo

Crear flyer para evento.

## Inputs

- Imagen principal:
- Fecha evento:
- Formato:
- Notas:

## Carpetas

- `input/`: imagen/video base.
- `working/`: archivos intermedios.
- `exports/`: salidas finales o previews.
- `refs/`: referencias.
- `analysis/`: OCR, colores, metadata, reportes.
- `ai/`: contexto y prompts para IA.

## Flujo

1. Poner imagen base en `input/`.
2. Analizar o completar datos si hace falta.
3. Procesar en Photoshop.
4. Exportar JPG a `working/`.
5. Usar en Blender.
6. Export final en `exports/`.

## Estado

- [ ] Input listo
- [ ] Análisis
- [ ] Photoshop
- [ ] Blender
- [ ] Export final
""",
        encoding="utf-8"
    )

    return project
