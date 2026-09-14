"""Read a Resolume ScreenSetup and report the venue's projection topology.

Why this exists
---------------
``data/venues/scd-plaza-egana.json`` states the gap in its own words:
``"proyeccion": {"superficie": "desconocido", "notas": "sin datos: el plano de
referencia es una planta, no dice nada de proyeccion."}``. MAK could describe a
room's floor plan and say nothing about the surfaces a VJ actually projects on --
which is the one thing a travelling VJ needs the week before a show.

A Resolume ScreenSetup holds part of that, already measured, because it is the
file the operator built while standing in the room: one entry per physical
surface, with the name they gave it ("CENTRAL ATRAS"), the pixel region of the
composition that feeds it, the output pixel size of the panel or projector, and
whether they had to warp it.

What it describes is a DEPLOYMENT, not a venue
----------------------------------------------
This was measured after the first version of this module framed the output as
"the venue's projection topology", which over-claimed. ``BERLIN 1.xml`` and
``berlin 2.xml`` name the same place and share ZERO surfaces: 59 against 9,
canvas 3043x272 against 1920x1080, classified ``different_rig``. A ScreenSetup is
therefore not a venue fingerprint.

Three things are mixed in one file and it cannot separate them:

- what belongs to the room (a house LED wall's real panel grid, the shape of a
  projection surface),
- what belongs to the rig brought that night (how many outputs, which processor),
- what belongs to the operator's choice (where the canvas was cut, what the
  surfaces were called).

So a record built from it is "the rig as deployed on the day this file was
saved". For a venue that is useful and dated evidence -- better than the 2014 PDF
the venue would otherwise send -- but it is never the venue's permanent
configuration, and a second night can look nothing like it.

What is being computed
----------------------
Not surface reconstruction. The only geometric question that needs deciding is
whether a warp was applied at all, and that is exact arithmetic: an unwarped
Resolume slice stores a ``controlWidth x controlHeight`` bezier lattice whose
points sit on the bilinear interpolation of the output quad's corners. Comparing
the stored lattice against that interpolation decides ``plano`` vs ``deformado``
without fitting anything. The regime, not a heuristic.

The honest boundary
-------------------
A ScreenSetup is measured in PIXELS. It contains no metric scale whatsoever, so
no physical dimension can be derived from it -- not surface size, not throw
distance, not trim height. Everything physical stays ``no_verificado`` and the
limit is written into ``residuos`` rather than left implied. This is the
``schemas/venue.schema.json`` rule ("el escaneo describe, las cotas a mano se
afirman, las cargas se citan") applied to a new source.

The file name is not the venue's identity either. ``CHILLAN.xml`` makes Chillan a
CANDIDATE; a venue record is only named by a person.

What it also cannot see: a disabled slice may or may not reflect the rig that was
actually hung, and overlapping input regions are reported as measured, not
deduplicated.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

CONTRACT = "mak-venue-projection-v1"
PARSER_VERSION = "resolume-screensetup-1"

# A warp nobody applied still stores float noise: measured values such as
# -1.52587890625e-05 against coordinates of magnitude 1024. Half a pixel is the
# smallest deviation that could be an intentional correction, so anything below
# it is noise rather than a warp. Named, and pinned by a test, because a
# tolerance is a threshold and thresholds are a failure mode.
WARP_TOLERANCE_PX = 0.5

WARP_FLAT = "plano"
WARP_WARPED = "deformado"
WARP_UNKNOWN = "desconocido"


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class Surface:
    """One physical surface the operator mapped, as the file records it."""

    name: str
    enabled: bool
    screen: str
    input_quad: tuple[Point, ...]
    output_quad: tuple[Point, ...]
    warp: str
    warp_max_deviation_px: float | None
    control_grid: tuple[int, int] | None

    @staticmethod
    def _extent(quad: Sequence[Point]) -> tuple[float, float]:
        xs = [p.x for p in quad]
        ys = [p.y for p in quad]
        return max(xs) - min(xs), max(ys) - min(ys)

    @property
    def output_size(self) -> tuple[float, float]:
        return self._extent(self.output_quad)

    @property
    def input_size(self) -> tuple[float, float]:
        return self._extent(self.input_quad)

    @property
    def axis_aligned(self) -> bool:
        """True when the output quad is an upright rectangle.

        A rotated or trapezoid quad still has an extent, but calling that extent
        a width would be wrong, so the caller is told which case it is.
        """
        return _is_axis_aligned(self.output_quad)

    @property
    def output_pixels(self) -> float:
        width, height = self.output_size
        return width * height

    def as_dict(self) -> dict[str, Any]:
        width, height = self.output_size
        in_w, in_h = self.input_size
        return {
            "nombre": self.name,
            "habilitada": self.enabled,
            "pantalla": self.screen,
            "salida_px": {"ancho": round(width, 3), "alto": round(height, 3),
                          "rectangular": self.axis_aligned},
            "entrada_px": {"ancho": round(in_w, 3), "alto": round(in_h, 3),
                           "rectangular": _is_axis_aligned(self.input_quad)},
            "warp": self.warp,
            **({"warp_desvio_px": round(self.warp_max_deviation_px, 4)}
               if self.warp_max_deviation_px is not None else {}),
            **({"warp_grid": list(self.control_grid)} if self.control_grid else {}),
        }


@dataclass
class ScreenSetupRecord:
    """Everything a ScreenSetup proves about a venue, and nothing more."""

    contract: str
    parser_version: str
    source_path: str
    source_name: str
    tool: str
    tool_version: str
    canvas: tuple[int, int] | None
    screens: list[str]
    surfaces: list[Surface]
    dmx_slices: int
    warnings: list[str] = field(default_factory=list)

    @property
    def enabled_surfaces(self) -> list[Surface]:
        return [s for s in self.surfaces if s.enabled]

    def summary(self) -> dict[str, Any]:
        flat = sum(1 for s in self.surfaces if s.warp == WARP_FLAT)
        warped = sum(1 for s in self.surfaces if s.warp == WARP_WARPED)
        return {
            "contract": self.contract,
            "parser_version": self.parser_version,
            "source_name": self.source_name,
            "tool": f"{self.tool} {self.tool_version}".strip(),
            "lienzo_px": list(self.canvas) if self.canvas else None,
            "pantallas": len(self.screens),
            "superficies": len(self.surfaces),
            "superficies_habilitadas": len(self.enabled_surfaces),
            "superficies_planas": flat,
            "superficies_deformadas": warped,
            "pixeles_salida": round(sum(s.output_pixels for s in self.surfaces), 3),
            "dmx_slices": self.dmx_slices,
            "avisos": list(self.warnings),
        }


def _is_axis_aligned(quad: Sequence[Point], tol: float = WARP_TOLERANCE_PX) -> bool:
    if len(quad) != 4:
        return False
    top_left, top_right, bottom_right, bottom_left = quad
    return (abs(top_left.y - top_right.y) <= tol
            and abs(bottom_left.y - bottom_right.y) <= tol
            and abs(top_left.x - bottom_left.x) <= tol
            and abs(top_right.x - bottom_right.x) <= tol)


def _points(node: ET.Element | None) -> tuple[Point, ...]:
    if node is None:
        return ()
    out = []
    for vertex in node.findall("v"):
        try:
            out.append(Point(float(vertex.get("x", "nan")),
                             float(vertex.get("y", "nan"))))
        except ValueError:
            continue
    return tuple(out)


def _bilinear(quad: Sequence[Point], u: float, v: float) -> Point:
    """Interpolate inside a quad given as top-left, top-right, bottom-right, bottom-left."""
    top_left, top_right, bottom_right, bottom_left = quad
    top_x = (1 - u) * top_left.x + u * top_right.x
    top_y = (1 - u) * top_left.y + u * top_right.y
    bottom_x = (1 - u) * bottom_left.x + u * bottom_right.x
    bottom_y = (1 - u) * bottom_left.y + u * bottom_right.y
    return Point((1 - v) * top_x + v * bottom_x, (1 - v) * top_y + v * bottom_y)


def classify_warp(output_quad: Sequence[Point], lattice: Sequence[Point],
                  grid: tuple[int, int] | None,
                  tolerance: float = WARP_TOLERANCE_PX
                  ) -> tuple[str, float | None]:
    """Decide whether the stored bezier lattice is the identity warp.

    An untouched Resolume slice stores its control points on the bilinear
    interpolation of the output quad. Deviation above ``tolerance`` means the
    operator corrected the surface -- a curved LED ribbon, a keystoned
    projector, a wall that is not square. Exact comparison, nothing fitted.

    Returns ``(WARP_UNKNOWN, None)`` when the file does not carry enough to
    decide, because an unreadable warp is not a flat warp.
    """
    if grid is None or len(output_quad) != 4:
        return WARP_UNKNOWN, None
    cols, rows = grid
    if cols < 2 or rows < 2 or len(lattice) != cols * rows:
        return WARP_UNKNOWN, None
    worst = 0.0
    for index, point in enumerate(lattice):
        row, col = divmod(index, cols)
        expected = _bilinear(output_quad, col / (cols - 1), row / (rows - 1))
        worst = max(worst, abs(point.x - expected.x), abs(point.y - expected.y))
    return (WARP_FLAT if worst <= tolerance else WARP_WARPED), worst


def _param_value(params: ET.Element | None, name: str) -> str | None:
    if params is None:
        return None
    for param in params.iter():
        if param.get("name") == name and "value" in param.attrib:
            return param.get("value")
    return None


def _slice_record(node: ET.Element, screen_name: str) -> Surface:
    common = next((p for p in node.findall("Params")
                   if p.get("name") == "Common"), None)
    name = _param_value(common, "Name") or ""
    enabled_raw = _param_value(common, "Enabled")
    warper = node.find("Warper")
    bezier = warper.find("BezierWarper") if warper is not None else None
    grid: tuple[int, int] | None = None
    lattice: tuple[Point, ...] = ()
    if bezier is not None:
        try:
            grid = (int(bezier.get("controlWidth", "0")),
                    int(bezier.get("controlHeight", "0")))
        except ValueError:
            grid = None
        lattice = _points(bezier.find("vertices"))
    output_quad = _points(node.find("OutputRect"))
    warp, deviation = classify_warp(output_quad, lattice, grid)
    return Surface(
        name=name,
        enabled=(enabled_raw != "0"),
        screen=screen_name,
        input_quad=_points(node.find("InputRect")),
        output_quad=output_quad,
        warp=warp,
        warp_max_deviation_px=deviation,
        control_grid=grid if grid and grid[0] >= 2 and grid[1] >= 2 else None,
    )


def parse_screen_setup(path: str | Path) -> ScreenSetupRecord:
    """Parse one ScreenSetup file. Read-only; never writes to the source."""
    source = Path(path).expanduser()
    root = ET.parse(source).getroot()
    if root.tag != "XmlState":
        raise ValueError(f"not a Resolume XmlState document: {source}")
    version = root.find("versionInfo")
    tool = version.get("name", "") if version is not None else ""
    tool_version = ""
    if version is not None:
        parts = [version.get(key) for key in
                 ("majorVersion", "minorVersion", "microVersion")]
        tool_version = ".".join(p for p in parts if p)
    setup = root.find("ScreenSetup")
    warnings: list[str] = []
    canvas: tuple[int, int] | None = None
    if setup is not None:
        size = setup.find("CurrentCompositionTextureSize")
        if size is not None:
            try:
                canvas = (int(size.get("width", "0")), int(size.get("height", "0")))
            except ValueError:
                canvas = None
    else:
        warnings.append("el documento no trae ScreenSetup: no describe superficies")

    screens: list[str] = []
    surfaces: list[Surface] = []
    dmx = 0
    scope = setup if setup is not None else root
    for screen in scope.iter("Screen"):
        params = next((p for p in screen.findall("Params")
                       if p.get("name") == "Params"), None)
        screen_name = _param_value(params, "Name") or screen.get("name") or ""
        screens.append(screen_name)
        for slice_node in screen.iter("Slice"):
            surfaces.append(_slice_record(slice_node, screen_name))
        dmx += sum(1 for _ in screen.iter("DmxSlice"))

    undecided = [s.name or "(sin nombre)" for s in surfaces
                 if s.warp == WARP_UNKNOWN]
    if undecided:
        warnings.append(
            "warp indecidible en " + str(len(undecided)) + " superficie(s): "
            + ", ".join(undecided[:5])
            + " -- un warp ilegible no es un warp plano")
    unnamed = sum(1 for s in surfaces if not s.name)
    if unnamed:
        warnings.append(
            f"{unnamed} superficie(s) sin nombre del operador: la topologia se "
            "conoce, el rol de la superficie en la sala no")
    if not surfaces:
        warnings.append("cero superficies: el archivo no aporta proyeccion")

    return ScreenSetupRecord(
        contract=CONTRACT, parser_version=PARSER_VERSION,
        source_path=str(source), source_name=source.name,
        tool=tool, tool_version=tool_version, canvas=canvas,
        screens=screens, surfaces=surfaces, dmx_slices=dmx, warnings=warnings)


def _surface_kind(record: ScreenSetupRecord) -> str:
    """Map onto the ``superficie`` enum the venue schema already declares.

    The enum asks what the light lands on -- pantalla, muro, led, gasa. A
    ScreenSetup cannot see the material, so anything other than ``desconocido``
    would be invention. The topology goes in ``notas`` where it is checkable.
    """
    return "desconocido"


def to_projection_fragment(record: ScreenSetupRecord) -> dict[str, Any]:
    """Build a ``proyeccion`` fragment valid against ``schemas/venue.schema.json``.

    ``resolucion`` is a free-text field in that schema, so the measured pixel
    topology is written there in a form a person can check against the file.
    """
    summary = record.summary()
    canvas = record.canvas
    enabled = record.enabled_surfaces
    resolution = (f"{canvas[0]}x{canvas[1]}" if canvas else "desconocida")
    detail = ", ".join(
        f"{s.name or '(sin nombre)'} {int(s.output_size[0])}x{int(s.output_size[1])}"
        f" {s.warp}" for s in enabled[:12])
    notes = (
        f"DESPLIEGUE, no configuracion permanente de la sala: topologia de "
        f"proyeccion medida en pixeles desde {record.source_name} "
        f"({summary['tool']}), no en metros. "
        f"{len(record.screens)} pantalla(s), {len(record.surfaces)} superficie(s) "
        f"({len(enabled)} habilitada(s)), {summary['superficies_planas']} plana(s) "
        f"y {summary['superficies_deformadas']} deformada(s); "
        f"{summary['dmx_slices']} salida(s) DMX. Superficies: {detail or 'ninguna'}."
    )
    return {
        "superficie": _surface_kind(record),
        "resolucion": resolution,
        "notas": notes,
    }


def projection_residues(record: ScreenSetupRecord) -> list[dict[str, Any]]:
    """State what a ScreenSetup cannot prove, so nobody reads it as a rider.

    ``schemas/venue.schema.json`` keeps ``residuos`` for exactly this: what does
    not fit the ideal model, and by how much. A clean false drawing is worse than
    one carrying a discrepancy note.
    """
    residues = [
        {"descripcion":
            "Este archivo describe un DESPLIEGUE de una fecha, no la "
            "configuracion permanente de la sala. Medido: BERLIN 1.xml y "
            "berlin 2.xml nombran el mismo lugar y no comparten NINGUNA "
            "superficie (59 contra 9, lienzo 3043x272 contra 1920x1080). El "
            "archivo tampoco separa que parte es del recinto, que parte es del "
            "rig que se llevo esa noche y que parte es como el operador corto el "
            "lienzo."},
        {"descripcion":
            "Un ScreenSetup mide PIXELES, no metros: no contiene escala metrica, "
            "asi que ninguna dimension fisica, altura de cuelgue, tiro de "
            "proyeccion ni carga se deriva de este archivo. Todo lo fisico sigue "
            "no_verificado hasta que alguien lo mida en sala."},
        {"descripcion":
            f"El nombre del archivo ({record.source_name}) es un CANDIDATO de "
            "identidad de sala, no una identificacion: un archivo puede ser una "
            "plantilla, una copia o una prueba. Solo una persona nombra un venue."},
        {"descripcion":
            "Las regiones de entrada se reportan tal como estan; si dos "
            "superficies se solapan en el lienzo, el solape no se descuenta."},
    ]
    disabled = [s for s in record.surfaces if not s.enabled]
    if disabled:
        residues.append({"descripcion":
            f"{len(disabled)} superficie(s) estan deshabilitadas en el archivo "
            "y pueden o no corresponder al rig que se colgo esa noche."})
    if record.dmx_slices:
        residues.append({"descripcion":
            f"Hay {record.dmx_slices} salida(s) DMX declarada(s), lo que indica "
            "control de iluminacion desde el mismo equipo; el archivo no dice que "
            "luminarias son ni como estaban colgadas."})
    for warning in record.warnings:
        residues.append({"descripcion": warning})
    return residues


def to_payload(record: ScreenSetupRecord) -> dict[str, Any]:
    """Full machine-readable result: observation, derivation and limits apart."""
    return {
        "schema": record.contract,
        "parser_version": record.parser_version,
        "fuente": {"ruta": record.source_path, "archivo": record.source_name,
                   "herramienta": record.tool,
                   "herramienta_version": record.tool_version},
        "identidad_sala": {"candidato": Path(record.source_name).stem,
                           "estado": "no_verificado",
                           "regla": "solo una persona nombra un venue"},
        "resumen": record.summary(),
        "superficies": [s.as_dict() for s in record.surfaces],
        "proyeccion": to_projection_fragment(record),
        "residuos": projection_residues(record),
    }


# ---------------------------------------------------------------------------
# Rig identity across shows
# ---------------------------------------------------------------------------
# Measured on the real files: harry.xml and CHILLAN.xml share all 11 output
# surfaces -- same operator names, same pixel dimensions -- while their canvases
# differ (1080x1920 against 3400x1920) and so do their input regions. That is
# the same physical rig driven by a different composition, and it is decided by
# topology rather than by the file names happening to sit next to a folder
# called "HARRY CHILLAN".
#
# The alternative is not dismissed: an identical signature is also what a reused
# TEMPLATE looks like. The relation is therefore a candidate carrying both
# readings, never a merge.

# Not every surface name identifies anything. Measured counterexample on the real
# files: ANDACOLLO.xml and "berlin 2.xml" share exactly one triple,
# ('Slice 1', 1920.0, 1080.0) -- Resolume's DEFAULT name at its DEFAULT canvas
# size. Every new composition starts with that slice, so the match is a naming
# artifact and not shared hardware. CHILLAN.xml and la.xml likewise share only
# ('11', 128.0, 256.0), a bare number on a common panel size.
#
# The first version of rig_signature() treated all names as equally identifying
# and produced those two false positives. The repair is in the representation,
# not in an exception list: how much a shared surface is worth depends on whether
# a person typed its name.
NAME_TOOL_DEFAULT = "tool_default"    # "Slice", "Slice 4" -- Resolume wrote it
NAME_LOW_ENTROPY = "low_entropy"      # "1", "11", "A" -- a person typed it, but
                                      # it collides across unrelated venues
NAME_OPERATOR = "operator"            # "CENTRAL ATRAS", "TOTEM L 2", "banner"

_DEFAULT_NAME = re.compile(r"^slice\s*\d*$", re.IGNORECASE)


def name_class(name: str) -> str:
    """How much identity a surface name carries."""
    stripped = (name or "").strip()
    if not stripped or _DEFAULT_NAME.match(stripped):
        return NAME_TOOL_DEFAULT
    if len(stripped) <= 2 or stripped.isdigit():
        return NAME_LOW_ENTROPY
    return NAME_OPERATOR


RIG_SAME_CANDIDATE = "same_rig_candidate"
RIG_SUBSET = "rig_subset_candidate"
RIG_DIFFERENT = "different_rig"


def rig_signature(record: ScreenSetupRecord) -> frozenset[tuple[str, float, float]]:
    """Output topology only: what is physically hung, not how it was fed.

    Input regions and canvas are deliberately excluded -- those change when the
    same rig is driven by a different composition, which is precisely the case
    this signature has to survive.
    """
    return frozenset(
        (s.name, round(s.output_size[0], 1), round(s.output_size[1], 1))
        for s in record.surfaces)


def compare_rigs(left: ScreenSetupRecord, right: ScreenSetupRecord
                 ) -> dict[str, Any]:
    """Relate two ScreenSetups by measured output topology."""
    a, b = rig_signature(left), rig_signature(right)
    shared = a & b
    # Only surfaces a person named can carry rig identity. A shared default
    # slice is Resolume's boilerplate; a shared bare number is a coincidence
    # waiting to happen.
    identifying = {t for t in shared if name_class(t[0]) == NAME_OPERATOR}
    if not identifying:
        relation, status = RIG_DIFFERENT, "EMPIRICAL"
    elif a == b:
        relation, status = RIG_SAME_CANDIDATE, "EMPIRICAL"
    else:
        relation, status = RIG_SUBSET, "UNKNOWN"
    result: dict[str, Any] = {
        "left": left.source_name,
        "right": right.source_name,
        "relation": relation,
        "epistemic_status": status,
        "shared_surfaces": len(shared),
        "left_only": len(a - b),
        "right_only": len(b - a),
        "identifying_surfaces": len(identifying),
        "evidence_for": [
            f"{len(identifying)} superficie(s) nombradas por el operador "
            f"coinciden en nombre y pixeles (de {len(shared)} coincidencias "
            "totales)",
        ],
        "evidence_against": [],
    }
    discounted = shared - identifying
    if discounted:
        result["evidence_against"].append(
            f"{len(discounted)} coincidencia(s) se descartaron por no "
            "identificar nada: "
            + ", ".join(sorted(f"{n!r}" for n, _w, _h in discounted)[:4])
            + " son nombres por defecto de la herramienta o numeros sueltos")
    if left.canvas != right.canvas:
        result["evidence_against"].append(
            f"los lienzos difieren ({left.canvas} vs {right.canvas}): la misma "
            "estructura se alimenta con composiciones distintas")
    if relation == RIG_SAME_CANDIDATE:
        result["alternatives"] = ["mismo rig fisico en dos shows",
                                  "una plantilla reutilizada en otra sala"]
        result["tie_breaker_needed"] = (
            "una foto del rig, una fecha de contrato o la palabra del operador; "
            "la topologia sola no distingue rig de plantilla")
    elif relation == RIG_SUBSET:
        result["alternatives"] = ["el rig crecio o se recorto entre shows",
                                  "dos rigs distintos que comparten paneles"]
        result["tie_breaker_needed"] = (
            "comparar fechas de los shows y la procedencia de los paneles")
    return result


def rig_index(records: Iterable[ScreenSetupRecord]) -> dict[str, Any]:
    """Group files by identical output topology, preserving the ambiguity."""
    items = list(records)
    groups: dict[frozenset[tuple[str, float, float]], list[str]] = {}
    for record in items:
        groups.setdefault(rig_signature(record), []).append(record.source_name)
    relations: list[dict[str, Any]] = []
    for index, left in enumerate(items):
        for right in items[index + 1:]:
            comparison = compare_rigs(left, right)
            if comparison["relation"] != RIG_DIFFERENT:
                relations.append(comparison)
    return {
        "schema": "mak-venue-rig-index-v1",
        "files": len(items),
        "distinct_topologies": len(groups),
        "shared_topologies": [
            {"files": sorted(names), "surfaces": len(signature)}
            for signature, names in groups.items() if len(names) > 1],
        "relations": relations,
    }
