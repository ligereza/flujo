"""Scoring de items: jobs, flyers, piezas."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional

from ..paths import repo_root, is_packaged, workspace_root


class Priority(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


@dataclass
class ItemScore:
    type: str  # job | flyer | pieza
    path: Path
    name: str
    score: int
    priority: Priority
    reason: str
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["path"] = str(self.path)
        d["priority"] = self.priority.value
        return d


PRIORITY_ORDER = {Priority.ALTA: 0, Priority.MEDIA: 1, Priority.BAJA: 2}


def priority_from_score(score: int) -> Priority:
    if score >= 70:
        return Priority.ALTA
    if score >= 40:
        return Priority.MEDIA
    return Priority.BAJA


# ============================================================
# Jobs
# ============================================================

def _try_yaml(text: str) -> Optional[dict]:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return None
    except Exception:
        return None


def _read_brief_simple(text: str) -> dict:
    """Lee un brief.yaml sin dependencias."""
    data: dict = {}
    current_section: Optional[str] = None
    current_list: Optional[str] = None
    for line in text.splitlines():
        raw = line.rstrip()
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        content = raw.strip()
        if content.startswith("- ") and current_list:
            data.setdefault(current_list, []).append(content[2:].strip().strip('"'))
            continue
        if ":" in content:
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            if indent == 0:
                current_section = None
                current_list = None
                if val == "":
                    current_section = key
                    data[key] = {}
                else:
                    data[key] = _coerce(val)
                    if key in ("productos", "pendientes", "posibles_formatos"):
                        current_list = key
            else:
                if current_section:
                    if val == "":
                        data[current_section][key] = {}
                    else:
                        data[current_section][key] = _coerce(val)
    return data


def _coerce(v: str):
    if v == "":
        return ""
    if v.lower() in ("true", "yes", "si", "sí"):
        return True
    if v.lower() in ("false", "no"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v.replace(",", "."))
    except ValueError:
        pass
    return v.strip('"').strip("'")


def score_job(brief_path: Path) -> Optional[ItemScore]:
    if not brief_path.exists():
        return None
    text = brief_path.read_text(encoding="utf-8", errors="ignore")
    data = _try_yaml(text) or _read_brief_simple(text)
    if not isinstance(data, dict):
        return None

    estado = str(data.get("estado", "borrador") or "borrador")
    pendientes = data.get("pendientes", []) or []
    if isinstance(pendientes, str):
        pendientes = [pendientes]
    entrega = data.get("entrega", {}) or {}
    texto_aprobado = bool((data.get("contenido", {}) or {}).get("texto_aprobado", False))

    score = 0
    reasons: List[str] = []

    if estado in ("borrador", "pendiente_datos"):
        score += 80
        reasons.append("faltan datos críticos")
    elif estado == "listo_para_disenar":
        score += 50
        reasons.append("listo para diseñar")
    elif estado == "en_diseno":
        score += 30
        reasons.append("en diseño")

    if estado == "brief_extraido_pendiente_revision":
        score += 60
        reasons.append("brief extraído, pendiente revisión")

    if pendientes:
        score += min(len(pendientes) * 5, 20)
        reasons.append(f"{len(pendientes)} pendientes")

    if not texto_aprobado and estado in ("listo_para_disenar", "en_diseno"):
        score += 10
        reasons.append("texto no aprobado")

    if isinstance(entrega, dict):
        pass

    return ItemScore(
        type="job",
        path=brief_path.parent,
        name=brief_path.parent.name,
        score=score,
        priority=priority_from_score(score),
        reason=", ".join(reasons) or "revisar",
        extra={"estado": estado, "pendientes_count": len(pendientes)},
    )


# ============================================================
# Flyers
# ============================================================

def score_flyer(manifest_path: Path) -> Optional[ItemScore]:
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    status = data.get("status", "created") or "created"
    name = data.get("name", manifest_path.parent.name)
    instagram = data.get("instagram", {}) or {}

    score = 0
    reasons: List[str] = []

    if status == "from_email_pending_download":
        score += 75
        reasons.append("falta descargar de Instagram")
    elif status == "created":
        score += 25
        reasons.append("creado, falta completar datos")
    elif status == "downloaded_pending_review":
        score += 40
        reasons.append("descargado, pendiente revisión")
    elif status == "in_progress":
        score += 30
        reasons.append("en progreso")

    if instagram.get("media_guess") == "video_possible":
        score += 10
        reasons.append("parece video")

    return ItemScore(
        type="flyer",
        path=manifest_path.parent,
        name=name,
        score=score,
        priority=priority_from_score(score),
        reason=", ".join(reasons) or "revisar",
        extra={"status": status},
    )


# ============================================================
# Piezas
# ============================================================

def score_pieza(config_path: Path) -> Optional[ItemScore]:
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    project = config_path.parent
    salida = project / "salida_generada"
    has_outputs = salida.exists() and any(salida.rglob("*.svg"))

    score = 0
    reasons: List[str] = []

    if not has_outputs:
        score += 60
        reasons.append("sin salidas generadas")
    else:
        score += 10
        reasons.append("salidas generadas, revisar")

    return ItemScore(
        type="pieza",
        path=project,
        name=str((data.get("project") or {}).get("name", project.name)),
        score=score,
        priority=priority_from_score(score),
        reason=", ".join(reasons) or "revisar",
        extra={"has_outputs": has_outputs},
    )


# ============================================================
# Colección
# ============================================================

def collect_items(repo: Optional[Path] = None) -> List[ItemScore]:
    """Recolecta y ordena items por prioridad."""
    if repo is None:
        repo = workspace_root() if is_packaged() else repo_root()
    items: List[ItemScore] = []

    jobs = repo / "jobs"
    if jobs.exists():
        for brief in jobs.glob("*/brief.yaml"):
            if brief.parent.name.startswith("_"):
                continue
            item = score_job(brief)
            if item:
                items.append(item)

    flyers = repo / "projects" / "flyer_eventos"
    if flyers.exists():
        for manifest in flyers.glob("*/manifest.json"):
            item = score_flyer(manifest)
            if item:
                items.append(item)

    piezas = repo / "projects" / "piezas_vectoriales"
    if piezas.exists():
        for config in piezas.glob("*/config.json"):
            item = score_pieza(config)
            if item:
                items.append(item)

    items.sort(key=lambda x: (PRIORITY_ORDER[x.priority], -x.score))
    return items
