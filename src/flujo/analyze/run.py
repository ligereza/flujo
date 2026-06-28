from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
from ..manifest import load_json, write_json

def analyze_project(project_dir: Path, force_ocr: bool = False) -> Dict[str, Any]:
    """
    Analiza un proyecto flyer:
    - colores dominantes de input_ig.jpg
    - OCR opcional
    Guarda resultados en analysis/
    Actualiza manifest.json con analysis_status
    """
    project_dir = Path(project_dir)
    manifest_path = project_dir / "manifest.json"
    input_dir = project_dir / "input"
    analysis_dir = project_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # buscar imagen principal
    candidates = [
        input_dir / "input_ig.jpg",
        *sorted(input_dir.glob("input_ig_*.jpg")),
        *sorted(input_dir.glob("*.jpg")),
        *sorted(input_dir.glob("*.png")),
    ]
    image_path = next((p for p in candidates if p.exists()), None)

    result: Dict[str, Any] = {"project": str(project_dir.name), "analyzed_at": ""}

    if not image_path:
        result["error"] = "no_image_found"
        return result

    # 1. Colores
    try:
        from .colors import extract_palette, save_palette_preview
        from .export import save_aco, save_ase
        palette = extract_palette(image_path, n_colors=6)
        result["palette"] = palette

        # guardar json
        with open(analysis_dir / "palette.json", "w", encoding="utf-8") as f:
            json.dump(palette, f, indent=2, ensure_ascii=False)

        # preview png
        save_palette_preview(palette, analysis_dir / "palette.png")
        result["palette_preview"] = "analysis/palette.png"

        # export Photoshop / Illustrator
        if save_aco(palette, analysis_dir / "palette.aco"):
            result["aco"] = "analysis/palette.aco"
        if save_ase(palette, analysis_dir / "palette.ase", name=project_dir.name):
            result["ase"] = "analysis/palette.ase"
    except Exception as e:
        result["palette_error"] = str(e)

    # 2. OCR (opcional)
    ocr_ran = False
    try:
        from .ocr import run_ocr, extract_hints_from_text
        ocr_res = run_ocr(image_path)
        result["ocr"] = {"available": ocr_res.get("available", False)}

        if ocr_res.get("available") and ocr_res.get("text"):
            text = ocr_res["text"]
            ocr_ran = True
            # guardar texto
            (analysis_dir / "ocr.txt").write_text(text, encoding="utf-8")
            result["ocr"].update({
                "chars": ocr_res.get("chars", 0),
                "lines": ocr_res.get("lines", 0),
                "saved_to": "analysis/ocr.txt"
            })
            # hints
            hints = extract_hints_from_text(text)
            if hints:
                result["ocr"]["hints"] = hints
                with open(analysis_dir / "ocr_hints.json", "w", encoding="utf-8") as f:
                    json.dump(hints, f, indent=2, ensure_ascii=False)
        else:
            # guardar estado "no disponible"
            with open(analysis_dir / "ocr_status.json", "w", encoding="utf-8") as f:
                json.dump(ocr_res, f, indent=2, ensure_ascii=False)
            result["ocr"].update(ocr_res)
    except Exception as e:
        result["ocr_error"] = str(e)

    # 3. Actualizar manifest
    try:
        data = load_json(manifest_path) or {}
        analysis_info = {
            "analyzed_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "palette_colors": [c["hex"] for c in result.get("palette", {}).get("colors", [])],
            "ocr_ran": ocr_ran,
        }
        data["analysis"] = analysis_info
        # marcar step
        steps = data.setdefault("steps", {})
        steps["analysis"] = "done"
        write_json(manifest_path, data)
        result["manifest_updated"] = True
    except Exception as e:
        result["manifest_error"] = str(e)

    result["status"] = "ok" if "palette" in result else "partial"
    return result

def find_latest_flyer() -> Path | None:
    from ..paths import flyer_base
    base = flyer_base()
    if not base.exists():
        return None
    projects = sorted([p for p in base.iterdir() if p.is_dir() and (p / "manifest.json").exists()], reverse=True)
    return projects[0] if projects else None
