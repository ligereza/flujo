from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..paths import repo_root

ENTITY_DIRS = {
    "productora": "productoras",
    "productoras": "productoras",
    "venue": "venues",
    "venues": "venues",
    "logo": "logos",
    "logos": "logos",
    "event": "events",
    "events": "events",
    "dossier": "dossiers",
    "dossiers": "dossiers",
}


def knowledge_root() -> Path:
    return repo_root() / "knowledge"


def slugify(value: str) -> str:
    value = (value or "item").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "item"


def entity_dir(entity: str) -> Path:
    key = ENTITY_DIRS.get(entity, entity)
    return knowledge_root() / key


def list_entities(entity: str) -> list[str]:
    d = entity_dir(entity)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def load_entity(entity: str, item_id: str) -> dict[str, Any]:
    p = entity_dir(entity) / f"{slugify(item_id)}.yaml"
    if not p.exists():
        raise FileNotFoundError(str(p))
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    try:
        data["_path"] = str(p.relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        # Store fuera del repo (tests con root temporal): ruta absoluta
        data["_path"] = str(p).replace("\\", "/")
    return data


def save_entity(entity: str, item_id: str, data: dict[str, Any]) -> Path:
    d = entity_dir(entity)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slugify(item_id)}.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def dossier_source_dir() -> Path:
    """Carpeta curada de dossiers culturales (fuente de verdad, versionada)."""
    return repo_root() / "projects" / "cultura" / "dossiers"


def _dossier_status(lines: list[str]) -> str:
    """Extrae el parrafo 'Status:' de un dossier (puede ocupar varias lineas)."""
    for i, line in enumerate(lines):
        if line.startswith("Status:"):
            parts = [line[len("Status:"):].strip()]
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    break
                parts.append(nxt.strip())
            return " ".join(p for p in parts if p)
    return "unknown"


def build_dossier_index(path: str | Path) -> dict[str, Any]:
    """Construye el registro-indice de un dossier .md.

    Solo metadata + referencia por ruta: el cuerpo del dossier NO se copia al
    store (el .md curado en projects/cultura/dossiers es la fuente de verdad;
    el indice es el mapa, no el territorio).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), p.stem)
    subject = title
    if ":" in title and title.lower().startswith("dossier"):
        subject = title.split(":", 1)[1].strip()
    try:
        source_path = p.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        source_path = str(p)
    return {
        "id": slugify(p.stem),
        "kind": "dossier",
        "project": slugify(p.stem),
        "title": title,
        "subject": subject,
        "status": _dossier_status(lines),
        "sections": [l[3:].strip() for l in lines if l.startswith("## ")],
        "hard_limit": "HARD LIMIT" in text,
        "source_path": source_path,
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def ingest_dossiers(source_dir: str | Path | None = None) -> list[Path]:
    """Indexa los dossiers curados en knowledge/dossiers/. Idempotente.

    Re-ejecutable: si el .md fuente no cambio (hash igual), el YAML existente
    queda intacto (conserva ingested_at y bytes). Si cambio, se reindexa con
    fecha nueva. Nunca copia el contenido del dossier, solo metadata + ruta.
    """
    src = Path(source_dir) if source_dir else dossier_source_dir()
    if not src.is_dir():
        raise FileNotFoundError(str(src))
    written: list[Path] = []
    for md in sorted(src.glob("*.md")):
        data = build_dossier_index(md)
        existing: dict[str, Any] | None
        try:
            existing = load_entity("dossiers", data["id"])
            existing.pop("_path", None)
        except FileNotFoundError:
            existing = None
        prev_ts = None
        if existing and existing.get("content_sha256") == data["content_sha256"]:
            prev_ts = existing.get("ingested_at")
        data["ingested_at"] = prev_ts or datetime.now().isoformat(timespec="seconds")
        if existing == data:
            written.append(entity_dir("dossiers") / f"{data['id']}.yaml")
            continue
        written.append(save_entity("dossiers", data["id"], data))
    return written


def classify_event_text(text: str) -> dict[str, Any]:
    low = (text or "").lower()
    producers = []
    for pid in list_entities("productoras"):
        data = load_entity("productoras", pid)
        names = [data.get("name", ""), *(data.get("aliases") or [])]
        if any(str(name).lower() in low for name in names if name):
            producers.append(data)
    venues = []
    for vid in list_entities("venues"):
        data = load_entity("venues", vid)
        names = [data.get("name", ""), *(data.get("aliases") or [])]
        if any(str(name).lower() in low for name in names if name):
            venues.append(data)
    preset = "base"
    reasons = []
    if any(v.get("scale_default") == "mainstream" for v in venues):
        preset = "mainstream"; reasons.append("venue mainstream")
    if any(p.get("scale_default") == "mainstream" for p in producers):
        preset = "mainstream"; reasons.append("productora mainstream")
    if "rave" in low or "aporte minimo" in low or "aporte mínimo" in low:
        preset = "under"; reasons.append("senales rave/under")
    if "espacio riesco" in low or "festival" in low or "creamfields" in low:
        preset = "mainstream"; reasons.append("senales masivas")
    deliverables = []
    if "rider" in low: deliverables.append("rider_completo")
    if "cartelera" in low: deliverables.append("cartelera_digital")
    if "flyer" in low and "cartelera" not in low: deliverables.append("flyer_impreso_10x14_vertical")
    if "instagram.com" in low: deliverables.append("descarga_instagram")
    return {
        "preset": preset,
        "confidence": 0.75 if reasons else 0.45,
        "reasons": reasons or ["fallback base"],
        "producers": [p.get("id") for p in producers],
        "venues": [v.get("id") for v in venues],
        "deliverables": deliverables,
    }



def template_for(example_type: str) -> dict[str, Any]:
    tdir = knowledge_root() / "templates"
    candidates = [
        tdir / f"{slugify(example_type)}.for_ai.json",
        tdir / "generic.for_ai.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {"type": example_type, "task": "Completa analisis visual.", "expected_output": {}}


def _producer_context(producer: str) -> dict[str, Any] | None:
    if not producer:
        return None
    try:
        return load_entity("productoras", producer)
    except Exception:
        return {"id": slugify(producer), "status": "unknown"}


def _write_example_readme(out_dir: Path, manifest: dict[str, Any]) -> None:
    text = f"""# Example {manifest['id']}

Tipo: `{manifest['type']}`
Productora: `{manifest.get('producer_id') or 'unknown'}`

## Flujo

1. Abre los archivos de este ejemplo.
2. Entrega `for_ai.json` a una IA con vision.
3. Pide que complete `analysis.json` usando SOLO datos observables.
4. Si aparece logo, registra fuente con:

```bash
py -m flujo knowledge logo-source <producer_id> <archivo_logo>
```

## Prompt sugerido

```txt
Actua como Agent Visual Director de flujo.
Lee for_ai.json, mira las imagenes/SVGs adjuntos y devuelve analysis.json completo.
No inventes datos: usa unknown y confidence cuando falte informacion.
Respeta reglas RD: flyer impreso 10x14 vertical Illustrator/SVG; cartelera digital Photoshop/Blender.
```
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")

def ingest_example(path: str | Path, example_type: str = "unknown", producer: str = "") -> Path:
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(str(src))
    slug = slugify(src.stem if src.is_file() else src.name)
    out_dir = knowledge_root() / "examples" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    if src.is_file():
        dest = out_dir / src.name
        shutil.copy2(src, dest)
        files.append(dest.name)
    else:
        for f in sorted(src.iterdir()):
            if f.is_file():
                dest = out_dir / f.name
                shutil.copy2(f, dest)
                files.append(dest.name)
    template = template_for(example_type)
    producer_ctx = _producer_context(producer)
    manifest = {
        "id": slug,
        "type": example_type,
        "producer_id": slugify(producer) if producer else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": files,
        "status": "needs_analysis",
        "template": template.get("type", "generic"),
        "next_files": ["for_ai.json", "analysis.json"],
    }
    for_ai = {
        "example_id": slug,
        "input_files": files,
        "producer_context": producer_ctx,
        "instructions": template.get("task"),
        "expected_output": template.get("expected_output", {}),
        "return_file": "analysis.json",
        "rules": [
            "No inventar datos: usar unknown/null y confidence.",
            "Flyer impreso/promocional RD = vertical 10x14 cm, Illustrator/SVG.",
            "Cartelera digital = Photoshop/Blender y formatos digitales.",
            "Registrar logo_candidates si aparecen logos de productora o venue.",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "for_ai.json").write_text(json.dumps(for_ai, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_example_readme(out_dir, manifest)
    return out_dir / "manifest.json"


def register_logo_source(producer_id: str, source_path: str | Path) -> Path:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(str(src))
    logo_id = f"{slugify(producer_id)}_primary"
    asset_dir = repo_root() / "assets" / "logos" / slugify(producer_id) / "source"
    asset_dir.mkdir(parents=True, exist_ok=True)
    dest = asset_dir / src.name
    shutil.copy2(src, dest)
    data = {
        "id": logo_id,
        "producer_id": slugify(producer_id),
        "status": "source_registered",
        "source_quality": "unknown",
        "sources": [str(dest.relative_to(repo_root())).replace("\\", "/")],
        "workflow": {"suggested_tool": "logo_clean_lab", "next_action": "vectorize_and_clean"},
        "outputs": {},
    }
    return save_entity("logos", producer_id, data)


def prepare_logo_lab(producer_id: str, source_path: str | Path) -> Path:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(str(src))

    pid = slugify(producer_id)
    logo_dir = repo_root() / "assets" / "logos" / pid
    source_dir = logo_dir / "source"
    work_dir = logo_dir / "work"
    final_dir = logo_dir / "final"

    for d in [source_dir, work_dir, final_dir]:
        d.mkdir(parents=True, exist_ok=True)

    dest = source_dir / src.name
    shutil.copy2(src, dest)

    manifest_data = {
        "id": f"logo_{pid}",
        "producer_id": pid,
        "status": "dirty",
        "files": {
            "source": str(dest.relative_to(repo_root())).replace("\\", "/"),
            "work": str((work_dir).relative_to(repo_root())).replace("\\", "/"),
            "final": str((final_dir).relative_to(repo_root())).replace("\\", "/"),
        },
        "properties": {
            "transparent": None,
            "vector": False,
            "primary_color": "unknown"
        },
        "history": [
            {
                "date": datetime.now().isoformat(timespec="seconds"),
                "action": "ingested",
                "note": f"Original source from {src.name}"
            }
        ]
    }

    manifest_path = logo_dir / "manifest.yaml"
    import yaml
    manifest_path.write_text(yaml.safe_dump(manifest_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    try:
        prod_data = load_entity("productora", pid)
        if "logo_id" not in prod_data:
            prod_data["logo_id"] = manifest_data["id"]
            save_entity("productora", pid, prod_data)
    except Exception:
        pass

    return manifest_path.relative_to(repo_root())
