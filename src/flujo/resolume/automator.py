"""Pre-flight generator for Resolume Arena automation via Chataigne/OSC.

The module reads EVENTOS jobs that contain SMPTE setlists and writes a compact,
valid XML session descriptor under ``deliverables/show_automation.xml``. The XML
is intentionally explicit so it can be audited before importing or translating it
into a native Chataigne ``.noisette`` session.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SMPTE_RE = re.compile(r"\b(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}):(?P<f>\d{2})\b")
LAYER_RE = re.compile(r"(?:layer|capa)\s*[:#-]?\s*(\d+)", re.IGNORECASE)
CLIP_RE = re.compile(r"(?:clip|columna|column)\s*[:#-]?\s*(\d+)", re.IGNORECASE)
DURATION_RE = re.compile(
    r"(?:duration|duracion|duraci[oó]n|length)\s*[:#-]?\s*([\d:.]+)\s*(s|sec|seg|seconds)?",
    re.IGNORECASE,
)
SETLIST_KEYS = ("setlist", "tracks", "songs", "scenes", "escenas", "temas", "canciones")
START_KEYS = ("start", "smpte", "timecode", "tc", "inicio")
TITLE_KEYS = ("title", "name", "tema", "song", "scene", "escena", "nombre")
DURATION_KEYS = ("duration", "duracion", "length", "duration_seconds")
LAYER_KEYS = ("layer", "capa")
CLIP_KEYS = ("clip", "columna", "column")


@dataclass(frozen=True)
class ShowCue:
    """A normalized cue that can be mapped to one Resolume clip trigger."""

    title: str
    smpte: str
    layer: int
    clip: int
    duration: str = ""
    duration_seconds: float | None = None

    def osc_address(self) -> str:
        return f"/composition/layers/{self.layer}/clips/{self.clip}/connect"


def parse_smpte_time(value: str, fps: int = 30) -> tuple[int, int, int, int]:
    """Validate and split a SMPTE timecode string in ``HH:MM:SS:FF`` format."""
    if fps <= 0:
        raise ValueError("fps debe ser un entero positivo")
    match = SMPTE_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"SMPTE invalido: {value!r}; se espera HH:MM:SS:FF")
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    frames = int(match.group("f"))
    if minutes > 59 or seconds > 59:
        raise ValueError(f"SMPTE invalido: minutos/segundos fuera de rango en {value!r}")
    if frames >= fps:
        raise ValueError(f"SMPTE invalido: frame {frames} fuera de rango para {fps} fps")
    return hours, minutes, seconds, frames


def _duration_to_seconds(value: object, fps: int) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("s") and text[:-1].replace(".", "", 1).isdigit():
        return float(text[:-1])
    if text.replace(".", "", 1).isdigit():
        return float(text)
    if SMPTE_RE.fullmatch(text):
        h, m, s, f = parse_smpte_time(text, fps=fps)
        return float(h * 3600 + m * 60 + s) + (f / fps)
    parts = text.split(":")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        h, m, s = [int(p) for p in parts]
        return float(h * 3600 + m * 60 + s)
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        m, s = [int(p) for p in parts]
        return float(m * 60 + s)
    return None


def _first_value(data: dict[str, object], keys: tuple[str, ...], default: object = "") -> object:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def _cue_from_dict(item: dict[str, object], index: int, fps: int) -> ShowCue | None:
    smpte_raw = _first_value(item, START_KEYS)
    if not smpte_raw:
        return None
    smpte = str(smpte_raw).strip()
    parse_smpte_time(smpte, fps=fps)
    title = str(_first_value(item, TITLE_KEYS, f"Cue {index}")).strip() or f"Cue {index}"
    layer_raw = _first_value(item, LAYER_KEYS, 1)
    clip_raw = _first_value(item, CLIP_KEYS, index)
    duration_raw = _first_value(item, DURATION_KEYS, "")
    try:
        layer = int(layer_raw)
        clip = int(clip_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Layer/clip invalido en cue {title!r}") from exc
    if layer < 1 or clip < 1:
        raise ValueError(f"Layer/clip deben ser positivos en cue {title!r}")
    return ShowCue(
        title=title,
        smpte=smpte,
        layer=layer,
        clip=clip,
        duration=str(duration_raw).strip() if duration_raw else "",
        duration_seconds=_duration_to_seconds(duration_raw, fps=fps),
    )


def _extract_cue_items(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in SETLIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    show = payload.get("show")
    if isinstance(show, dict):
        return _extract_cue_items(show)
    return []


def _fps_from_intake(payload: object, fallback: int) -> int:
    if not isinstance(payload, dict):
        return fallback
    raw = payload.get("fps", payload.get("frame_rate", fallback))
    try:
        fps = int(raw)
    except (TypeError, ValueError):
        return fallback
    return fps if fps > 0 else fallback


def _parse_intake_json(path: Path, fps: int) -> tuple[list[ShowCue], int]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"No se pudo leer JSON valido en {path}") from exc
    effective_fps = _fps_from_intake(payload, fps)
    cues: list[ShowCue] = []
    for index, item in enumerate(_extract_cue_items(payload), start=1):
        cue = _cue_from_dict(item, index=index, fps=effective_fps)
        if cue is not None:
            cues.append(cue)
    return cues, effective_fps


def _clean_brief_title(text: str) -> str:
    title = re.sub(LAYER_RE, "", text)
    title = re.sub(CLIP_RE, "", title)
    title = re.sub(DURATION_RE, "", title)
    return title.strip(" -|:\t")


def _parse_brief_md(path: Path, fps: int) -> list[ShowCue]:
    cues: list[ShowCue] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SMPTE_RE.search(line)
        if not match:
            continue
        smpte = match.group(0)
        parse_smpte_time(smpte, fps=fps)
        remainder = (line[: match.start()] + line[match.end() :]).strip(" -|:\t")
        layer_match = LAYER_RE.search(line)
        clip_match = CLIP_RE.search(line)
        duration_match = DURATION_RE.search(line)
        layer = int(layer_match.group(1)) if layer_match else 1
        clip = int(clip_match.group(1)) if clip_match else len(cues) + 1
        if layer < 1 or clip < 1:
            raise ValueError(f"Layer/clip deben ser positivos en brief.md para cue {smpte}")
        duration = duration_match.group(1) if duration_match else ""
        title = _clean_brief_title(remainder) or f"Cue {len(cues) + 1}"
        cues.append(
            ShowCue(
                title=title,
                smpte=smpte,
                layer=layer,
                clip=clip,
                duration=duration,
                duration_seconds=_duration_to_seconds(duration, fps=fps),
            )
        )
    return cues


def parse_smpte_setlist(job_path: str | Path, fps: int = 30) -> list[ShowCue]:
    """Read ``intake.json`` or ``brief.md`` from a job and return normalized cues."""
    job = Path(job_path)
    if not job.exists() or not job.is_dir():
        raise FileNotFoundError(f"Job no encontrado: {job}")
    if fps <= 0:
        raise ValueError("fps debe ser un entero positivo")

    intake = job / "intake.json"
    brief = job / "brief.md"

    intake_error: ValueError | None = None
    if intake.exists():
        cues, effective_fps = _parse_intake_json(intake, fps=fps)
        if cues:
            return cues
        intake_error = ValueError(
            f"No se encontraron cues SMPTE validos en intake.json (fps efectivo: {effective_fps})"
        )

    if brief.exists():
        cues = _parse_brief_md(brief, fps=fps)
        if cues:
            return cues

    if not intake.exists() and not brief.exists():
        raise FileNotFoundError(f"El job {job} no contiene intake.json ni brief.md")

    if intake.exists() and not brief.exists() and intake_error is not None:
        raise intake_error

    sources = [str(path.name) for path in (intake, brief) if path.exists()]
    raise ValueError(f"No se encontraron cues SMPTE validos en {', '.join(sources)}")


def build_chataigne_xml(
    cues: list[ShowCue],
    fps: int = 30,
    host: str = "127.0.0.1",
    port: int = 7000,
) -> ET.Element:
    """Build the XML element tree for a pre-flight Chataigne session."""
    if not cues:
        raise ValueError("No hay cues para generar la automatizacion")
    if fps <= 0:
        raise ValueError("fps debe ser un entero positivo")
    if port <= 0 or port > 65535:
        raise ValueError("port OSC fuera de rango")

    root = ET.Element(
        "chataigneSession",
        {
            "version": "preflight-1",
            "generator": "flujo.resolume.automator",
        },
    )
    modules = ET.SubElement(root, "modules")
    ET.SubElement(modules, "timecode", {"source": "smpte", "fps": str(fps)})
    ET.SubElement(
        modules,
        "oscOutput",
        {"name": "Resolume Arena", "host": host, "port": str(port)},
    )
    timeline = ET.SubElement(root, "timeline")
    for index, cue in enumerate(cues, start=1):
        parse_smpte_time(cue.smpte, fps=fps)
        cue_el = ET.SubElement(
            timeline,
            "cue",
            {
                "index": str(index),
                "name": cue.title,
                "smpte": cue.smpte,
                "layer": str(cue.layer),
                "clip": str(cue.clip),
            },
        )
        if cue.duration:
            cue_el.set("duration", cue.duration)
        if cue.duration_seconds is not None:
            cue_el.set("durationSeconds", f"{cue.duration_seconds:.3f}".rstrip("0").rstrip("."))
        ET.SubElement(
            cue_el,
            "osc",
            {
                "output": "Resolume Arena",
                "address": cue.osc_address(),
                "value": "1",
                "type": "int",
            },
        )
    return root


def write_xml(root: ET.Element, output_path: Path) -> Path:
    """Write XML with declaration and verify it can be parsed again."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    ET.parse(output_path)
    return output_path


def generate_show_automation(
    job_path: str | Path,
    fps: int = 30,
    host: str = "127.0.0.1",
    port: int = 7000,
    output: str | Path | None = None,
) -> Path:
    """Generate ``show_automation.xml`` for one EVENTOS job."""
    job = Path(job_path)
    cues = parse_smpte_setlist(job, fps=fps)
    root = build_chataigne_xml(cues, fps=fps, host=host, port=port)
    target = Path(output) if output else job / "deliverables" / "show_automation.xml"
    return write_xml(root, target)
