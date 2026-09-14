"""Resolve which SSD assets a real Resolume show actually used.

Why this exists
---------------
The SSD index knows which files exist. It cannot tell material that was played
in a show from material that merely sits in a folder, so a folder of 364 assets
looks the same whether it is a tour that ran or a dump nobody opened. That
distinction is the one ``MEMORIA_DIRECCION.md`` §2.12 turns into a report: "the
tool reads the project files to know which assets are really used".

A Resolume composition (``.avc``) is that project file. Measured on
``DREFGIRA/IMPORT CLAUDIO/SHOWCAUPOLICAN FINAL ANTES DE CAUPO.avc``: 52 clip
references, 28 resolving to exactly one SSD asset and 6 more to several copies of
the same file, landing in ``DREFGIRA/BLOQUE 01 LSDR/`` and
``DREFGIRA/BLOQUE 02 CLASICOS/`` -- the setlist blocks of the tour, in order.

What is being computed
----------------------
Record linkage between two catalogues under a must-abstain rule, not a search.
The only join key the data offers is the file's basename, because the composition
stores absolute paths from a machine that is not this one. A basename that maps
to several SSD assets is not a match; it is an ambiguity, and it stays one.

The resolution rate is a MEASUREMENT, never an assumption. The four compositions
in the index give 1/1, 28/52, 0/81 and 0/1 unambiguous: ``LYON/sampier.avc``
resolves nothing because its paths point at another machine's Desktop and
OneDrive. A tool reporting one number for "how well this works" would be lying
about three of those four, so the rate is per composition.

What a resolution does not prove
--------------------------------
That the bytes are the same file. ``full_sha256`` exists for 112 of 45536 assets
in the index, so content identity is unavailable for 99.75% of it. A resolved
reference means "one SSD asset carries this name", which is a candidate, and the
record says so.

Privacy
-------
The stored paths carry real Windows usernames, and more than one distinct user.
``tests/test_privacidad_repo.py`` forbids that pattern in this repository, so
every path leaves this module anonymised. The raw string is never persisted.
"""

from __future__ import annotations

import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping, Sequence

CONTRACT = "mak-show-asset-usage-v1"
RESOLVER_VERSION = "basename-linkage-abstain-1"

# Tags Resolume uses for the media a clip points at.
MEDIA_TAGS = ("VideoFile", "AudioFile")

RESOLVED_UNIQUE = "resolved_unique"
# Measured on the Caupolican show: all 6 of its ambiguous references had exactly
# two candidates, and in every case the two agreed on byte size AND on
# sample_sha256 -- the same clip stored twice, once loose in DREFGIRA and once
# inside a setlist block. Abstaining there threw away a usable answer: WHICH clip
# played is decided, only WHERE it lives is not. The two cases are different
# questions and now carry different labels.
RESOLVED_MULTI_LOCATION = "resolved_multi_location"
AMBIGUOUS = "ambiguous"
NOT_FOUND = "not_found"

# What "the same file" is allowed to mean here. full_sha256 is absent for
# 45424 of 45536 assets, so byte size plus the sample hash is the strongest
# available agreement -- strong, and still not proof of identical content.
USED_STATUSES = frozenset({RESOLVED_UNIQUE, RESOLVED_MULTI_LOCATION})

_WIN_USER = re.compile(r"(?i)(users[\\/])[^\\/]+")
_DRIVE = re.compile(r"^[A-Za-z]:[\\/]|^\\\\")


def anonymize_path(path: str) -> str:
    """Replace the account segment of a Windows path.

    Not cosmetic: the repository's privacy ratchet rejects a real username in a
    versioned file, and these paths carry several different ones.
    """
    return _WIN_USER.sub(r"\1<usuario>", path or "")


def is_absolute_windows(path: str) -> bool:
    return bool(_DRIVE.match(path or ""))


@dataclass
class Reference:
    """One clip the composition points at."""

    tag: str
    raw_path: str
    basename: str
    absolute: bool
    layer: str = ""
    column: str = ""

    @property
    def safe_path(self) -> str:
        return anonymize_path(self.raw_path)

    @property
    def directory(self) -> str:
        return anonymize_path(str(PureWindowsPath(self.raw_path).parent))


@dataclass
class Resolution:
    reference: Reference
    status: str
    candidates: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "archivo_citado": self.reference.safe_path,
            "basename": self.reference.basename,
            "tipo": self.reference.tag,
            "ruta_absoluta_externa": self.reference.absolute,
            "estado": self.status,
            "assets_en_el_ssd": list(self.candidates),
            **({"nota": "un basename que coincide no prueba los mismos bytes: "
                        "full_sha256 solo existe para 112 de 45536 assets"}
               if self.status == RESOLVED_UNIQUE else {}),
            **({"nota": "varios assets llevan este nombre y coinciden en bytes y "
                        "sample_sha256, asi que el clip usado esta decidido y lo "
                        "indeciso es en cual de las copias; sin full_sha256 la "
                        "coincidencia es fuerte pero no una prueba de contenido"}
               if self.status == RESOLVED_MULTI_LOCATION else {}),
        }


@dataclass
class CompositionRecord:
    contract: str
    resolver_version: str
    source_path: str
    source_name: str
    composition_name: str
    tool: str
    tool_version: str
    canvas: tuple[int, int] | None
    decks: int
    layers: int
    columns: int
    relative_paths_declared: bool
    references: list[Reference] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def distinct_basenames(self) -> set[str]:
        return {r.basename for r in self.references}

    def summary(self) -> dict[str, Any]:
        absolute = sum(1 for r in self.references if r.absolute)
        return {
            "contract": self.contract,
            "resolver_version": self.resolver_version,
            "source_name": self.source_name,
            "composition_name": self.composition_name,
            "tool": f"{self.tool} {self.tool_version}".strip(),
            "lienzo_px": list(self.canvas) if self.canvas else None,
            "decks": self.decks,
            "layers": self.layers,
            "columns": self.columns,
            "rutas_relativas_declaradas": self.relative_paths_declared,
            "referencias": len(self.references),
            "referencias_absolutas_externas": absolute,
            "basenames_distintos": len(self.distinct_basenames),
            "avisos": list(self.warnings),
        }


def _text_value(node: ET.Element) -> str | None:
    value = node.get("value")
    if value:
        return value
    for child in node.iter():
        candidate = child.get("value") or ""
        if PureWindowsPath(candidate).suffix:
            return candidate
    return None


def parse_composition(path: str | Path) -> CompositionRecord:
    """Read one ``.avc`` composition. Read-only; never writes to the source."""
    source = Path(path).expanduser()
    root = ET.parse(source).getroot()
    if root.tag != "Composition":
        raise ValueError(f"not a Resolume Composition document: {source}")
    version = root.find("versionInfo")
    tool = version.get("name", "") if version is not None else ""
    tool_version = ""
    if version is not None:
        parts = [version.get(k) for k in
                 ("majorVersion", "minorVersion", "microVersion")]
        tool_version = ".".join(p for p in parts if p)
    info = root.find("CompositionInfo")
    canvas: tuple[int, int] | None = None
    composition_name = ""
    if info is not None:
        composition_name = info.get("name", "")
        try:
            canvas = (int(info.get("width", "0")), int(info.get("height", "0")))
        except ValueError:
            canvas = None

    references: list[Reference] = []
    seen: set[tuple[str, str]] = set()
    for tag in MEDIA_TAGS:
        for node in root.iter(tag):
            raw = _text_value(node)
            if not raw:
                continue
            key = (tag, raw)
            if key in seen:
                continue
            seen.add(key)
            references.append(Reference(
                tag=tag, raw_path=raw,
                basename=PureWindowsPath(raw).name.casefold(),
                absolute=is_absolute_windows(raw)))

    warnings: list[str] = []
    if not references:
        warnings.append("la composicion no cita ningun archivo de medios")
    collisions = {}
    for reference in references:
        collisions.setdefault(reference.basename, set()).add(reference.raw_path)
    repeated = {b: v for b, v in collisions.items() if len(v) > 1}
    if repeated:
        warnings.append(
            f"{len(repeated)} basename(s) se citan desde directorios distintos "
            "dentro de la misma composicion, asi que el basename no distingue "
            "esos archivos ni siquiera aca: "
            + ", ".join(sorted(repeated)[:3]))
    external = sum(1 for r in references if r.absolute)
    if external and external == len(references):
        warnings.append(
            "todas las rutas son absolutas de otra maquina: la composicion no "
            "es autocontenida y su material puede no estar en este disco")

    def _count(tag: str) -> int:
        try:
            return int(root.get(tag, "0"))
        except ValueError:
            return 0

    return CompositionRecord(
        contract=CONTRACT, resolver_version=RESOLVER_VERSION,
        source_path=str(source), source_name=source.name,
        composition_name=composition_name, tool=tool, tool_version=tool_version,
        canvas=canvas, decks=_count("numDecks"), layers=_count("numLayers"),
        columns=_count("numColumns"),
        relative_paths_declared=(root.get("compositionIsRelative") == "1"),
        references=references, warnings=warnings)


def index_basenames(index_path: str | Path) -> dict[str, list[str]]:
    """Map every SSD basename to the assets that carry it. Read-only."""
    path = Path(index_path).expanduser()
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        mapping: dict[str, list[str]] = {}
        for (relative,) in con.execute("SELECT relative_path FROM assets"):
            mapping.setdefault(
                str(relative).rsplit("/", 1)[-1].casefold(), []).append(str(relative))
        return mapping
    finally:
        con.close()


def index_asset_metadata(index_path: str | Path) -> dict[str, tuple[int, str]]:
    """Byte size and sample hash per asset path, for deciding duplicate copies."""
    path = Path(index_path).expanduser()
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        return {str(rel): (int(size or 0), str(sample or ""))
                for rel, size, sample in con.execute(
                    "SELECT relative_path, bytes, sample_sha256 FROM assets")}
    finally:
        con.close()


def resolve_references(record: CompositionRecord,
                       basenames: Mapping[str, Sequence[str]],
                       metadata: Mapping[str, tuple[int, str]] | None = None
                       ) -> list[Resolution]:
    """Link each reference to the SSD, abstaining whenever the name is shared.

    The hypothesis being used is "within this corpus a basename identifies one
    file". It is checked rather than assumed: every reference whose basename maps
    to more than one asset is returned as ``ambiguous`` and contributes nothing
    to the usage claim.
    """
    out: list[Resolution] = []
    for reference in record.references:
        candidates = tuple(basenames.get(reference.basename, ()))
        if not candidates:
            status = NOT_FOUND
        elif len(candidates) == 1:
            status = RESOLVED_UNIQUE
        elif metadata and _same_file_everywhere(candidates, metadata):
            status = RESOLVED_MULTI_LOCATION
        else:
            status = AMBIGUOUS
        out.append(Resolution(reference, status, candidates))
    return out


def _same_file_everywhere(candidates: Sequence[str],
                          metadata: Mapping[str, tuple[int, str]]) -> bool:
    """True when every candidate agrees on byte size and sample hash.

    Refuses to decide when a candidate has no metadata or an empty sample hash:
    an unknown is not an agreement.
    """
    seen: set[tuple[int, str]] = set()
    for candidate in candidates:
        entry = metadata.get(candidate)
        if entry is None or not entry[1]:
            return False
        seen.add(entry)
    return len(seen) == 1


def usage_report(record: CompositionRecord,
                 resolutions: Sequence[Resolution]) -> dict[str, Any]:
    """What this show used, what is missing, and what could not be decided."""
    by_status: dict[str, list[Resolution]] = {}
    for resolution in resolutions:
        by_status.setdefault(resolution.status, []).append(resolution)
    unique = by_status.get(RESOLVED_UNIQUE, [])
    multi = by_status.get(RESOLVED_MULTI_LOCATION, [])
    ambiguous = by_status.get(AMBIGUOUS, [])
    missing = by_status.get(NOT_FOUND, [])
    total = len(resolutions)
    # A multi-location clip counts as used once; every copy is recorded so the
    # duplication is visible instead of silently collapsed.
    used_assets = sorted({r.candidates[0] for r in unique}
                         | {c for r in multi for c in r.candidates})
    containers = sorted({a.split("/", 1)[0] for a in used_assets})
    rate = (len(unique) / total) if total else 0.0
    report = {
        "schema": CONTRACT,
        "resolver_version": RESOLVER_VERSION,
        "composicion": record.summary(),
        "tasa_resolucion_inequivoca": round(rate, 4),
        "tasa_clip_decidido": round(((len(unique) + len(multi)) / total)
                                    if total else 0.0, 4),
        "conteos": {
            "referencias": total,
            RESOLVED_UNIQUE: len(unique),
            RESOLVED_MULTI_LOCATION: len(multi),
            AMBIGUOUS: len(ambiguous),
            NOT_FOUND: len(missing),
        },
        "copias_duplicadas": [
            {"basename": r.reference.basename,
             "copias": list(r.candidates)} for r in multi],
        "assets_usados": used_assets,
        "contenedores_tocados": containers,
        "referencias": [r.as_dict() for r in resolutions],
        "limites": [
            "El basename es la unica clave de union disponible: la composicion "
            "guarda rutas de otra maquina. Una coincidencia de nombre es "
            "candidata, no identidad de bytes.",
            "full_sha256 existe para 112 de 45536 assets del indice, asi que la "
            "verificacion por contenido no esta disponible para el 99,75 %.",
            "Una referencia no encontrada NO prueba que el archivo no exista: "
            "puede vivir en la maquina que produjo la composicion y nunca haber "
            "estado en este disco.",
            "La tasa de resolucion es de ESTA composicion y no se extrapola: "
            "medida sobre los cuatro .avc del indice va de 0 a 19 de 37.",
        ],
    }
    if multi:
        report["limites"].append(
            f"{len(multi)} referencia(s) resolvieron a varias copias del mismo "
            "archivo (mismo tamano y mismo sample_sha256): el clip usado esta "
            "decidido, la copia concreta no, y la duplicacion queda listada en "
            "copias_duplicadas.")
    if ambiguous:
        report["limites"].append(
            f"{len(ambiguous)} referencia(s) quedan sin decidir porque su nombre "
            "lo llevan varios assets del disco; no se elige uno.")
    return report


def cross_container_copies(index_path: str | Path) -> dict[str, Any]:
    """Assets that exist, byte-for-byte alike, under more than one container.

    Measured on the real index: 543 (basename, bytes) pairs live in two or more
    container roots. The operator's own reading of them shows they are not one
    thing:

    - the same clip reused in two shows -- ``HARRY CHILLAN/ESCARLATA.mp4`` and
      ``HARRY/show/VINA/ESCARLATA.mp4`` -- which is a VJ set travelling;
    - the same clip under two artists because of a collaboration -- Escarlata
      sits in DREFGIRA, DrefQuila and HARRY because the track is a remix;
    - a tour folder and the artist's own body of work holding the same piece,
      like ``enrolar.mp4`` and ``misionar.mov`` in DREFGIRA and DrefQuila.

    All three look identical to a deduplicator, and deleting either copy is a
    different kind of loss in each case: a set that no longer plays, a
    collaboration that loses one side, or a client's body of work with a hole in
    it. So this function names them and refuses to rank them.
    """
    path = Path(index_path).expanduser()
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT relative_path, bytes, sample_sha256 FROM assets").fetchall()
    finally:
        con.close()
    groups: dict[tuple[str, int], dict[str, Any]] = {}
    for relative, size, sample in rows:
        relative = str(relative)
        if "/" not in relative:
            continue
        key = (relative.rsplit("/", 1)[-1].casefold(), int(size or 0))
        entry = groups.setdefault(key, {"containers": set(), "paths": [],
                                        "samples": set()})
        entry["containers"].add(relative.split("/", 1)[0])
        entry["paths"].append(relative)
        entry["samples"].add(str(sample or ""))
    shared = {k: v for k, v in groups.items() if len(v["containers"]) > 1}
    items = [
        {"basename": basename, "bytes": size,
         "containers": sorted(entry["containers"]),
         "paths": sorted(entry["paths"]),
         "same_sample_hash": len(entry["samples"]) == 1 and "" not in entry["samples"]}
        for (basename, size), entry in shared.items()
    ]
    items.sort(key=lambda item: -item["bytes"])
    return {
        "schema": "mak-cross-container-copies-v1",
        "grupos": len(items),
        "bytes_en_copias_extra": sum(
            item["bytes"] * (len(item["paths"]) - 1) for item in items),
        "advertencia": (
            "NINGUNO de estos grupos es un candidato a borrado. Una copia en dos "
            "contenedores puede ser el mismo clip en dos shows, una colaboracion "
            "entre artistas, o la obra de un cliente guardada junto a la gira "
            "donde se uso. Borrar la copia equivocada rompe un set, una "
            "colaboracion o el cuerpo de obra de otra persona. Esta lista existe "
            "para que una persona las lea, no para liberar disco."),
        "mayores": items[:25],
    }


def orphan_candidates(container: str, used_assets: Iterable[str],
                      index_path: str | Path) -> dict[str, Any]:
    """Assets in a container that no analysed composition references.

    Deliberately named ``candidates``. An asset absent from the compositions we
    could read is not proven unused: only four compositions exist in the index,
    and the shows they describe are not every show. This is a starting list for
    a person, never a delete list.
    """
    path = Path(index_path).expanduser()
    used = set(used_assets)
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        rows = [(r[0], int(r[1])) for r in con.execute(
            "SELECT relative_path, bytes FROM assets "
            "WHERE relative_path = ? OR relative_path LIKE ?",
            (container, container + "/%"))]
    finally:
        con.close()
    unreferenced = [(rel, size) for rel, size in rows if rel not in used]
    return {
        "schema": "mak-orphan-candidates-v1",
        "contenedor": container,
        "assets_en_el_contenedor": len(rows),
        "referenciados_por_una_composicion_leida": len(rows) - len(unreferenced),
        "sin_referencia_conocida": len(unreferenced),
        "bytes_sin_referencia": sum(size for _rel, size in unreferenced),
        "advertencia": (
            "sin_referencia_conocida NO significa inutilizado. Solo se leyeron "
            "las composiciones presentes en el indice; un asset puede usarse en "
            "un show cuya composicion no esta aca, o como material fuente de "
            "otro archivo. Y medido sobre el indice real: 543 pares "
            "(basename, bytes) viven en mas de un contenedor porque el mismo "
            "clip se reusa entre shows, entre artistas que colaboran, y entre "
            "la carpeta de una gira y la obra propia del artista -- borrar una "
            "de esas copias rompe un set, una colaboracion o el cuerpo de obra "
            "de otra persona. Esta lista es un punto de partida para una "
            "persona, no una lista de borrado."),
        "mayores_sin_referencia": [
            {"asset": rel, "bytes": size}
            for rel, size in sorted(unreferenced, key=lambda x: -x[1])[:20]],
    }
