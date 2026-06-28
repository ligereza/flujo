import json
from pathlib import Path
from typing import Any
from .models import Manifest

def load_manifest(path: Path) -> Manifest:
    if not path.exists():
        return Manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Manifest.model_validate(data)
    except Exception:
        # fallback raw
        return Manifest()

def save_manifest(path: Path, manifest: Manifest):
    path.parent.mkdir(parents=True, exist_ok=True)
    # merge with existing to not lose unknown fields
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    new_data = manifest.model_dump(mode="json", exclude_unset=False)
    # keep extra keys from existing
    merged = {**existing, **new_data}
    # ensure nested instagram / extracted_info are fully merged
    if "instagram" in existing and isinstance(existing["instagram"], dict):
        merged["instagram"] = {**existing["instagram"], **new_data.get("instagram", {})}
    if "extracted_info" in existing and isinstance(existing["extracted_info"], dict):
        merged["extracted_info"] = {**existing["extracted_info"], **new_data.get("extracted_info", {})}

    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
