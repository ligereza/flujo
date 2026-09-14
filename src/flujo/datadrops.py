from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def ingest_datadrop_reference(source_path: str | Path, target_dir: str | Path | None = None) -> Path:
    """Crear una carpeta de datadrop a partir de una imagen o PDF real.

    El flujo copia el archivo original, genera un preview (si es posible) y crea
    un manifest.json con metadatos básicos para uso futuro en línea editorial.
    """

    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"No existe el archivo de referencia: {source_path}")

    if target_dir is None:
        target_dir = Path("datadrops") / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{source_path.stem.lower()}"
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c for c in source_path.name if c.isalnum() or c in "._-") or "reference"
    destination = target_dir / safe_name
    destination.write_bytes(source_path.read_bytes())

    analysis_dir = target_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    dimensions = {"width": 0, "height": 0}
    text_excerpt = ""
    preview_path = None

    suffix = source_path.suffix.lower()
    if suffix in {".pdf"}:
        try:
            import fitz  # type: ignore

            with fitz.open(source_path) as doc:
                if doc.page_count:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    preview_path = analysis_dir / "preview.png"
                    pix.save(str(preview_path))
                    dimensions = {"width": int(page.rect.width), "height": int(page.rect.height)}
                    text_excerpt = (page.get_text("text") or "")[:2000]
        except Exception:
            preview_path = None
            dimensions = {"width": 0, "height": 0}
    else:
        try:
            from PIL import Image

            with Image.open(source_path) as im:
                dimensions = {"width": im.width, "height": im.height}
        except Exception:
            pass

    if preview_path and preview_path.exists():
        preview_rel = preview_path.relative_to(target_dir).as_posix()
    else:
        preview_rel = ""

    manifest: dict[str, Any] = {
        "id": target_dir.name,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        "original_filename": source_path.name,
        "source_path": destination.relative_to(target_dir.parent).as_posix() if destination.is_absolute() else destination.as_posix(),
        "type": "pdf" if suffix == ".pdf" else "image",
        "dimensions": dimensions,
        "palette": [],
        "ocr_text_snippet": text_excerpt[:300] if text_excerpt else "",
        "ocr_hints": {},
        "description": f"Referencia real importada desde {source_path.name}",
        "linked_job": "",
        "visual_traits": "Referencia real importada para uso como ground truth visual.",
        "tags": ["datadrop", "real-finished", "reference", "imported"],
        "analysis_source": "local (pdf/image import)",
        "for_future_ai": "Referencia real importada. Usa esta pieza como ejemplo de estilo/estructura/propiedades visuales.",
        "preview_path": preview_rel,
    }

    if preview_rel:
        (analysis_dir / "preview.txt").write_text(text_excerpt[:2000], encoding="utf-8")

    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target_dir
