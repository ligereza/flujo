#!/usr/bin/env python3
"""tests/test_resolume_screen_setup.py -- projection topology from show files.

Controlled worlds first (a warp we built, so we know the answer), then the nine
real ScreenSetup files from the operator's SSD, which were not written to make
any of this work.

The counterexample is pinned, not hidden: the first version of the rig signature
reported ANDACOLLO and "berlin 2" as related because both contain
('Slice 1', 1920, 1080) -- Resolume's default name at its default canvas. That is
a naming artifact. ``test_a_shared_default_slice_is_not_a_shared_rig`` fails if
that trap ever comes back.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from flujo.venues.resolume_screen_setup import (
    NAME_LOW_ENTROPY,
    NAME_OPERATOR,
    NAME_TOOL_DEFAULT,
    RIG_DIFFERENT,
    RIG_SAME_CANDIDATE,
    WARP_FLAT,
    WARP_TOLERANCE_PX,
    WARP_UNKNOWN,
    WARP_WARPED,
    Point,
    classify_warp,
    compare_rigs,
    name_class,
    parse_screen_setup,
    projection_residues,
    rig_index,
    rig_signature,
    to_payload,
    to_projection_fragment,
)

REPO = Path(__file__).resolve().parents[1]
REAL_DIR = Path("/media/mak/PortableSSD")
REAL_FILES = ["ANDACOLLO.xml", "BERLIN 1.xml", "berlin 2.xml",
              "Black Boss Estandar TEMUCO.xml", "CHILLAN.xml", "cobquecura.xml",
              "harry.xml", "KAYAKAZE 2025 2.xml", "la.xml"]

QUAD = (Point(0, 0), Point(120, 0), Point(120, 60), Point(0, 60))


def _lattice(cols: int, rows: int, jitter: dict[int, tuple[float, float]] | None = None):
    """Identity lattice over QUAD, optionally nudging one control point."""
    points = []
    for row in range(rows):
        for col in range(cols):
            x = 120 * col / (cols - 1)
            y = 60 * row / (rows - 1)
            index = row * cols + col
            if jitter and index in jitter:
                dx, dy = jitter[index]
                x, y = x + dx, y + dy
            points.append(Point(x, y))
    return points


# --- controlled worlds: we know the ground truth --------------------------

def test_an_untouched_lattice_is_flat():
    warp, deviation = classify_warp(QUAD, _lattice(4, 4), (4, 4))
    assert warp == WARP_FLAT
    assert deviation == pytest.approx(0.0, abs=1e-9)


def test_a_moved_control_point_is_a_warp():
    warp, deviation = classify_warp(QUAD, _lattice(4, 4, {5: (9.0, 0.0)}), (4, 4))
    assert warp == WARP_WARPED
    assert deviation == pytest.approx(9.0)


def test_float_noise_below_the_tolerance_is_not_a_warp():
    """Resolume stores values like -1.52587890625e-05 on an untouched slice."""
    noise = -1.52587890625e-05
    warp, deviation = classify_warp(QUAD, _lattice(4, 4, {0: (noise, noise)}), (4, 4))
    assert warp == WARP_FLAT
    assert deviation < WARP_TOLERANCE_PX


def test_the_tolerance_is_a_declared_threshold_and_both_sides_are_tested():
    """A threshold is a failure mode, so both sides of it are pinned."""
    just_under = WARP_TOLERANCE_PX * 0.9
    just_over = WARP_TOLERANCE_PX * 1.1
    assert classify_warp(QUAD, _lattice(4, 4, {5: (just_under, 0)}), (4, 4))[0] == WARP_FLAT
    assert classify_warp(QUAD, _lattice(4, 4, {5: (just_over, 0)}), (4, 4))[0] == WARP_WARPED


def test_an_unreadable_warp_is_unknown_and_never_flat():
    """Absence of evidence must not read as evidence of a flat surface."""
    assert classify_warp(QUAD, [], None)[0] == WARP_UNKNOWN
    assert classify_warp(QUAD, _lattice(4, 4)[:5], (4, 4))[0] == WARP_UNKNOWN
    assert classify_warp((), _lattice(4, 4), (4, 4))[0] == WARP_UNKNOWN


def test_a_warped_output_quad_still_decides_its_own_warp():
    """The test is relative to the quad, so a rotated surface is not a warp."""
    skewed = (Point(10, 5), Point(130, 5), Point(120, 65), Point(0, 65))
    lattice = []
    for row in range(4):
        for col in range(4):
            u, v = col / 3, row / 3
            top_x = (1 - u) * skewed[0].x + u * skewed[1].x
            top_y = (1 - u) * skewed[0].y + u * skewed[1].y
            bot_x = (1 - u) * skewed[3].x + u * skewed[2].x
            bot_y = (1 - u) * skewed[3].y + u * skewed[2].y
            lattice.append(Point((1 - v) * top_x + v * bot_x,
                                 (1 - v) * top_y + v * bot_y))
    assert classify_warp(skewed, lattice, (4, 4))[0] == WARP_FLAT


def test_name_classes_separate_the_tool_from_the_operator():
    assert name_class("Slice") == NAME_TOOL_DEFAULT
    assert name_class("Slice 4") == NAME_TOOL_DEFAULT
    assert name_class("slice 12") == NAME_TOOL_DEFAULT
    assert name_class("") == NAME_TOOL_DEFAULT
    assert name_class("11") == NAME_LOW_ENTROPY
    assert name_class("A") == NAME_LOW_ENTROPY
    assert name_class("CENTRAL ATRAS") == NAME_OPERATOR
    assert name_class("TOTEM L 2") == NAME_OPERATOR
    assert name_class("banner superior") == NAME_OPERATOR


# --- the counterexample, kept ---------------------------------------------

def _fake_record(name: str, surfaces: list[tuple[str, int, int]], canvas=(1920, 1080)):
    """Build a minimal ScreenSetup document and parse it, so the test exercises
    the real parser rather than a hand-built object."""
    root = ET.Element("XmlState", {"name": name})
    ET.SubElement(root, "versionInfo", {
        "name": "Resolume Arena", "majorVersion": "7", "minorVersion": "0"})
    setup = ET.SubElement(root, "ScreenSetup")
    ET.SubElement(setup, "CurrentCompositionTextureSize",
                  {"width": str(canvas[0]), "height": str(canvas[1])})
    screens = ET.SubElement(setup, "screens")
    screen = ET.SubElement(screens, "Screen", {"uniqueId": "1"})
    params = ET.SubElement(screen, "Params", {"name": "Params"})
    ET.SubElement(params, "Param", {"name": "Name", "T": "STRING", "value": "Screen 1"})
    output = ET.SubElement(screen, "Params", {"name": "Output"})
    for surface_name, width, height in surfaces:
        node = ET.SubElement(output, "Slice", {"uniqueId": "2"})
        common = ET.SubElement(node, "Params", {"name": "Common"})
        ET.SubElement(common, "Param",
                      {"name": "Name", "T": "STRING", "value": surface_name})
        ET.SubElement(common, "Param",
                      {"name": "Enabled", "T": "BOOL", "value": "1"})
        for tag in ("InputRect", "OutputRect"):
            rect = ET.SubElement(node, tag, {"orientation": "0"})
            for x, y in ((0, 0), (width, 0), (width, height), (0, height)):
                ET.SubElement(rect, "v", {"x": str(x), "y": str(y)})
        warper = ET.SubElement(node, "Warper")
        bezier = ET.SubElement(warper, "BezierWarper",
                               {"controlWidth": "4", "controlHeight": "4"})
        vertices = ET.SubElement(bezier, "vertices")
        for row in range(4):
            for col in range(4):
                ET.SubElement(vertices, "v", {"x": str(width * col / 3),
                                              "y": str(height * row / 3)})
    return root


def _parsed(tmp_path: Path, filename: str, surfaces, canvas=(1920, 1080)):
    path = tmp_path / filename
    ET.ElementTree(_fake_record(Path(filename).stem, surfaces, canvas)).write(
        path, encoding="utf-8", xml_declaration=True)
    return parse_screen_setup(path)


def test_a_shared_default_slice_is_not_a_shared_rig(tmp_path):
    """THE COUNTEREXAMPLE. Measured on the real files before the repair:
    ANDACOLLO.xml and 'berlin 2.xml' shared exactly ('Slice 1', 1920, 1080),
    which every new Resolume composition contains. Two unrelated venues were
    reported as related."""
    left = _parsed(tmp_path, "one.xml", [("Slice 1", 1920, 1080), ("puerta", 300, 200)])
    right = _parsed(tmp_path, "two.xml", [("Slice 1", 1920, 1080), ("techo", 400, 100)])
    result = compare_rigs(left, right)
    assert result["relation"] == RIG_DIFFERENT
    assert result["shared_surfaces"] == 1
    assert result["identifying_surfaces"] == 0
    assert any("por defecto" in e for e in result["evidence_against"])


def test_a_shared_bare_number_is_not_a_shared_rig(tmp_path):
    """Same trap, second form: CHILLAN and la shared only ('11', 128, 256)."""
    left = _parsed(tmp_path, "a.xml", [("11", 128, 256), ("fondo", 900, 500)])
    right = _parsed(tmp_path, "b.xml", [("11", 128, 256), ("lateral", 200, 800)])
    assert compare_rigs(left, right)["relation"] == RIG_DIFFERENT


def test_an_operator_named_surface_does_carry_rig_identity(tmp_path):
    surfaces = [("CENTRAL ATRAS", 1024, 128), ("TOTEM L", 128, 256)]
    left = _parsed(tmp_path, "show1.xml", surfaces, canvas=(1920, 1080))
    right = _parsed(tmp_path, "show2.xml", surfaces, canvas=(3400, 1920))
    result = compare_rigs(left, right)
    assert result["relation"] == RIG_SAME_CANDIDATE
    assert result["identifying_surfaces"] == 2
    # A different canvas is evidence AGAINST calling them one show.
    assert any("lienzo" in e for e in result["evidence_against"])
    # And a template is never ruled out by topology alone.
    assert "plantilla" in " ".join(result["alternatives"])
    assert result["tie_breaker_needed"]


# --- the honest boundary --------------------------------------------------

def test_the_record_never_claims_metres(tmp_path):
    record = _parsed(tmp_path, "sala.xml", [("FONDO", 800, 400)])
    payload = to_payload(record)
    blob = json.dumps(payload, ensure_ascii=False)
    residues = " ".join(r["descripcion"] for r in payload["residuos"])
    assert "PIXELES, no metros" in residues
    assert "no_verificado" in blob
    # No key anywhere offers a metric measurement.
    assert '"m":' not in blob


def test_the_file_name_is_only_a_candidate_identity(tmp_path):
    record = _parsed(tmp_path, "CHILLAN.xml", [("FONDO", 800, 400)])
    identity = to_payload(record)["identidad_sala"]
    assert identity["candidato"] == "CHILLAN"
    assert identity["estado"] == "no_verificado"
    residues = " ".join(r["descripcion"] for r in projection_residues(record))
    assert "CANDIDATO" in residues


def test_the_surface_kind_is_never_invented(tmp_path):
    """A ScreenSetup cannot see whether light lands on LED, gauze or a wall."""
    record = _parsed(tmp_path, "sala.xml", [("FONDO", 800, 400)])
    assert to_projection_fragment(record)["superficie"] == "desconocido"


def test_the_fragment_validates_against_the_existing_venue_schema(tmp_path):
    """The venue contract is reused, not duplicated."""
    from jsonschema import Draft202012Validator

    schema = json.loads((REPO / "schemas" / "venue.schema.json").read_text(
        encoding="utf-8"))
    record = _parsed(tmp_path, "sala.xml", [("FONDO", 800, 400)])
    Draft202012Validator(schema["properties"]["proyeccion"]).validate(
        to_projection_fragment(record))
    Draft202012Validator(schema["properties"]["residuos"]).validate(
        projection_residues(record))


def test_a_document_that_is_not_a_screen_setup_is_refused(tmp_path):
    path = tmp_path / "other.xml"
    path.write_text("<Something><a/></Something>", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_screen_setup(path)


def test_a_setup_without_surfaces_says_so(tmp_path):
    record = _parsed(tmp_path, "empty.xml", [])
    assert record.surfaces == []
    assert any("cero superficies" in w for w in record.warnings)


def test_parsing_is_deterministic(tmp_path):
    record = _parsed(tmp_path, "sala.xml", [("FONDO", 800, 400), ("Slice 1", 1920, 1080)])
    again = parse_screen_setup(tmp_path / "sala.xml")
    assert to_payload(record) == to_payload(again)
    assert rig_signature(record) == rig_signature(again)


# --- real input: files nobody wrote for these tests -----------------------

def _real(name: str):
    path = REAL_DIR / name
    if not path.is_file():
        pytest.skip(f"SSD not mounted or file absent: {path}")
    return parse_screen_setup(path)


@pytest.mark.parametrize("name", REAL_FILES)
def test_every_real_show_file_parses_into_surfaces(name):
    record = _real(name)
    assert record.tool.startswith("Resolume")
    assert record.canvas and record.canvas[0] > 0 and record.canvas[1] > 0
    assert record.surfaces, f"{name} produced no surfaces"
    for surface in record.surfaces:
        assert surface.warp in {WARP_FLAT, WARP_WARPED, WARP_UNKNOWN}
        assert len(surface.output_quad) == 4


def test_the_real_chillan_file_matches_what_was_measured_by_hand():
    """Numbers read off the file on 2026-08-21, so a regression is visible."""
    record = _real("CHILLAN.xml")
    assert record.canvas == (3400, 1920)
    assert len(record.surfaces) == 11
    assert len(record.enabled_surfaces) == 7
    central = next(s for s in record.surfaces if s.name == "CENTRAL ATRAS")
    assert central.output_size == pytest.approx((1024.000244140625, 128.0))
    assert central.warp == WARP_FLAT


def test_the_real_files_reproduce_the_one_supported_rig_relation():
    records = [_real(n) for n in REAL_FILES]
    index = rig_index(records)
    assert index["files"] == len(REAL_FILES)
    supported = [r for r in index["relations"]
                 if r["relation"] == RIG_SAME_CANDIDATE]
    pairs = {frozenset((r["left"], r["right"])) for r in supported}
    assert pairs == {frozenset(("CHILLAN.xml", "harry.xml"))}, (
        "the only rig relation the evidence supports is CHILLAN/harry; "
        f"got {pairs}")
    # And the three default-name coincidences must stay out.
    assert not [r for r in index["relations"] if r["identifying_surfaces"] == 0]


# --- the consumer: the machine proposes, the human signs ------------------

class TestVenueProposal:
    """`venue.py proyeccion` is the integration point with the venue records.

    The measured topology is worth more than the `aportado` tier that
    `venue.py sembrar` produces from memory, but it is still pixels, so the
    identity of the room stays a human act.
    """

    def _tool(self, monkeypatch, tmp_path):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_venue_tool", REPO / "tools" / "venue.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setattr(module, "DIR_VENUES", tmp_path / "venues")
        monkeypatch.setattr(module, "DIR_PROPUESTAS", tmp_path / "propuestas")
        (tmp_path / "venues").mkdir()
        return module

    def _venue(self, module, venue_id="sala-uno"):
        record = {
            "id": venue_id, "nombre": "Sala Uno", "ciudad": "Santiago",
            "tipo": "club", "publico": False, "fecha_captura": "2026-08-21",
            "fuente_datos": "memoria",
            "proyeccion": {"superficie": "desconocido",
                           "notas": "sin datos"},
        }
        path = module.DIR_VENUES / f"{venue_id}.json"
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path

    def _setup_file(self, tmp_path, name="sala-uno.xml"):
        path = tmp_path / name
        ET.ElementTree(_fake_record(
            Path(name).stem, [("FONDO", 800, 400), ("TOTEM L", 128, 256)])).write(
            path, encoding="utf-8", xml_declaration=True)
        return path

    def test_it_refuses_a_venue_it_was_never_given(self, monkeypatch, tmp_path):
        module = self._tool(monkeypatch, tmp_path)
        setup = self._setup_file(tmp_path)
        assert module.propose_projection(setup, "no-existe") == 2

    def test_without_aplicar_the_record_is_untouched(self, monkeypatch, tmp_path):
        module = self._tool(monkeypatch, tmp_path)
        path = self._venue(module)
        before = path.read_text(encoding="utf-8")
        assert module.propose_projection(self._setup_file(tmp_path), "sala-uno") == 0
        assert path.read_text(encoding="utf-8") == before, "proposal wrote the record"
        proposal = module.DIR_PROPUESTAS / "sala-uno.proyeccion-propuesta.json"
        assert proposal.is_file()
        body = json.loads(proposal.read_text(encoding="utf-8"))
        assert body["firma_requerida"]
        assert body["proyeccion_propuesta"]["resolucion"] == "1920x1080"

    def test_a_proposal_never_lands_in_the_venue_directory(self, monkeypatch, tmp_path):
        """REGRESSION. Written into data/venues/ once, and cargar_todos() globs
        that directory, so `venue.py validar` read the proposal as a venue and
        reported 8 schema errors."""
        module = self._tool(monkeypatch, tmp_path)
        self._venue(module)
        module.propose_projection(self._setup_file(tmp_path), "sala-uno")
        assert module.DIR_PROPUESTAS != module.DIR_VENUES
        stray = [p.name for p in module.DIR_VENUES.glob("*.json")
                 if "propuesta" in p.name]
        assert not stray, f"proposal leaked into the venue glob: {stray}"
        loaded = module.cargar_todos()
        assert len(loaded) == 1 and loaded[0]["id"] == "sala-uno"

    def test_aplicar_writes_the_measured_topology_and_its_residues(
            self, monkeypatch, tmp_path):
        module = self._tool(monkeypatch, tmp_path)
        path = self._venue(module)
        assert module.propose_projection(self._setup_file(tmp_path), "sala-uno",
                                 apply_now=True) == 0
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["proyeccion"]["resolucion"] == "1920x1080"
        assert "FONDO 800x400" in record["proyeccion"]["notas"]
        residues = " ".join(r["descripcion"] for r in record["residuos"])
        assert "PIXELES, no metros" in residues
        # The venue keeps its human-given identity; nothing renamed it.
        assert record["nombre"] == "Sala Uno"
        assert record["fuente_datos"] == "memoria"

    def test_aplicar_is_idempotent_on_residues(self, monkeypatch, tmp_path):
        module = self._tool(monkeypatch, tmp_path)
        path = self._venue(module)
        setup = self._setup_file(tmp_path)
        module.propose_projection(setup, "sala-uno", apply_now=True)
        first = len(json.loads(path.read_text(encoding="utf-8"))["residuos"])
        module.propose_projection(setup, "sala-uno", apply_now=True)
        second = len(json.loads(path.read_text(encoding="utf-8"))["residuos"])
        assert first == second, "re-applying duplicated residues"

    def test_the_applied_record_still_validates_against_the_schema(
            self, monkeypatch, tmp_path):
        from jsonschema import Draft202012Validator

        module = self._tool(monkeypatch, tmp_path)
        path = self._venue(module)
        module.propose_projection(self._setup_file(tmp_path), "sala-uno", apply_now=True)
        schema = json.loads((REPO / "schemas" / "venue.schema.json").read_text(
            encoding="utf-8"))
        Draft202012Validator(schema).validate(
            json.loads(path.read_text(encoding="utf-8")))

    def test_a_name_mismatch_is_reported_not_resolved(self, monkeypatch, tmp_path,
                                                     capsys):
        module = self._tool(monkeypatch, tmp_path)
        self._venue(module)
        module.propose_projection(self._setup_file(tmp_path, "CHILLAN.xml"), "sala-uno")
        out = capsys.readouterr().out
        assert "AVISO" in out and "CHILLAN" in out


# --- the framing correction -----------------------------------------------

class TestDeploymentNotVenue:
    """A ScreenSetup is not a venue fingerprint, and the data must say so.

    The first version of this module called its output "the venue's projection
    topology". Measured counterexample on real files: BERLIN 1.xml and
    berlin 2.xml name the same place and share ZERO surfaces -- 59 against 9,
    canvas 3043x272 against 1920x1080. The file describes the rig as deployed on
    one date, and it cannot separate what belongs to the room from what belongs
    to the rig that travelled or from how the operator cut the canvas.
    """

    def test_the_same_place_name_can_carry_a_completely_different_rig(self):
        left = _real("BERLIN 1.xml")
        right = _real("berlin 2.xml")
        from flujo.venues.resolume_screen_setup import compare_rigs

        result = compare_rigs(left, right)
        assert result["relation"] == RIG_DIFFERENT
        assert result["shared_surfaces"] == 0
        assert left.canvas != right.canvas
        assert len(left.surfaces) != len(right.surfaces)

    def test_the_projection_note_says_deployment_not_configuration(self, tmp_path):
        record = _parsed(tmp_path, "sala.xml", [("FONDO", 800, 400)])
        note = to_projection_fragment(record)["notas"]
        assert note.startswith("DESPLIEGUE")
        assert "no configuracion permanente" in note

    def test_the_residues_carry_the_counterexample(self, tmp_path):
        record = _parsed(tmp_path, "sala.xml", [("FONDO", 800, 400)])
        text = " ".join(r["descripcion"] for r in projection_residues(record))
        assert "DESPLIEGUE de una fecha" in text
        assert "BERLIN 1.xml" in text and "berlin 2.xml" in text
        # And it must name the three things the file cannot separate.
        assert "del recinto" in text and "rig" in text and "corto el lienzo" in text
