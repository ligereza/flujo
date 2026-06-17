import re
import json
from datetime import datetime, date
from pathlib import Path
from ..paths import flyer_base

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "flyer"

def create_flyer_project(base: Path | None, name: str, source_type: str = "manual") -> Path:
    base = Path(base) if base else flyer_base()
    base.mkdir(parents=True, exist_ok=True)
    slug = slugify(name)
    today = date.today().isoformat()
    project_dir = base / f"{today}_{slug}"
    counter = 1
    while project_dir.exists():
        counter += 1
        project_dir = base / f"{today}_{slug}-{counter}"

    for sub in ["input", "working", "exports", "refs", "analysis", "ai"]:
        d = project_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").write_text("", encoding="utf-8")

    manifest = {
        "tool": "flyer_eventos",
        "name": name,
        "slug": slug,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "created",
        "source": {"type": source_type},
    }
    (project_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (project_dir / "README.md").write_text(f"# {name}\n\nProyecto flyer_eventos.\n", encoding="utf-8")
    return project_dir
