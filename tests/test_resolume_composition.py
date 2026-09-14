#!/usr/bin/env python3
"""tests/test_resolume_composition.py -- which assets a real show used.

Controlled worlds where the answer is known, then the four real .avc
compositions in the SSD index, which were saved years before this code existed.

The abstention is the point. A composition stores absolute paths from another
machine, so the only join key is the basename, and a basename shared by several
assets is an ambiguity rather than a match. Measured spread across the four real
files: 1/1, 28/52, 0/81 and 0/1 unambiguous. A single "how well this works"
number would misrepresent every one of them, so the rate is per composition.
"""
from __future__ import annotations

import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from flujo.venues.resolume_composition import (
    AMBIGUOUS,
    NOT_FOUND,
    RESOLVED_UNIQUE,
    anonymize_path,
    index_basenames,
    is_absolute_windows,
    orphan_candidates,
    parse_composition,
    resolve_references,
    usage_report,
)

REAL_DIR = Path("/media/mak/PortableSSD")
REAL_INDEX = Path("/home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite")
CAUPOLICAN = REAL_DIR / "DREFGIRA/IMPORT CLAUDIO/SHOWCAUPOLICAN FINAL ANTES DE CAUPO.avc"


def _composition(tmp_path: Path, name: str, refs, relative: bool = False,
                 canvas=(1920, 1080)):
    root = ET.Element("Composition", {
        "name": "Composition", "numDecks": "2", "numLayers": "3",
        "numColumns": "8", "compositionIsRelative": "1" if relative else "0"})
    ET.SubElement(root, "versionInfo", {
        "name": "Resolume Arena", "majorVersion": "7", "minorVersion": "21"})
    ET.SubElement(root, "CompositionInfo", {
        "name": Path(name).stem, "description": "",
        "width": str(canvas[0]), "height": str(canvas[1])})
    for tag, path in refs:
        ET.SubElement(root, tag, {"value": path})
    out = tmp_path / name
    ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)
    return parse_composition(out)


def _index(tmp_path: Path, relative_paths):
    """A minimal index with the columns the real one has.

    sample_sha256 is included because cross_container_copies reads it: a fixture
    that omits a column the code uses tests a different database than the one
    that ships.
    """
    path = tmp_path / "index.sqlite"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE assets (asset_id TEXT, relative_path TEXT, "
                "bytes INTEGER, sample_sha256 TEXT)")
    con.executemany("INSERT INTO assets VALUES (?,?,?,?)",
                    [(f"a{i}", rel, 1000 + i, f"h{i}")
                     for i, rel in enumerate(relative_paths)])
    con.commit()
    con.close()
    return path


# --- privacy: a real username must never leave this module ----------------

def test_a_windows_username_is_anonymised():
    raw = r"C:\Users\alguien\OneDrive\Escritorio\listas\clip.mov"
    safe = anonymize_path(raw)
    assert "alguien" not in safe
    assert "<usuario>" in safe
    assert safe.endswith(r"listas\clip.mov")


def test_anonymisation_survives_forward_slashes_and_case():
    assert "alguien" not in anonymize_path("c:/USERS/alguien/x.mov")
    assert anonymize_path("") == ""
    assert anonymize_path("relative/clip.mov") == "relative/clip.mov"


def test_no_reference_leaves_the_record_with_a_raw_username(tmp_path):
    record = _composition(tmp_path, "show.avc", [
        ("VideoFile", r"C:\Users\alguien\Desktop\a.mov")])
    blob = json.dumps([r.__dict__ for r in []]) + json.dumps(
        usage_report(record, resolve_references(record, {})), ensure_ascii=False)
    assert "alguien" not in blob
    assert "<usuario>" in blob


def test_absolute_windows_paths_are_recognised():
    assert is_absolute_windows(r"C:\Users\ejemplo\a.mov")
    assert is_absolute_windows(r"\\server\share\a.mov")
    assert not is_absolute_windows("Media/a.mov")
    assert not is_absolute_windows("")


# --- the abstention -------------------------------------------------------

def test_one_asset_with_that_name_resolves(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\unico.mov")])
    resolutions = resolve_references(record, {"unico.mov": ["TOUR/unico.mov"]})
    assert [r.status for r in resolutions] == [RESOLVED_UNIQUE]
    assert resolutions[0].candidates == ("TOUR/unico.mov",)


def test_several_assets_with_that_name_abstain(tmp_path):
    """THE TRAP. Two different clips can share a filename, so a name match is
    not identity. Measured on the real index: 2.mov, 3.mov, 4.mov and
    'comp 2.mov' each name three distinct assets."""
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\2.mov")])
    resolutions = resolve_references(
        record, {"2.mov": ["A/2.mov", "B/2.mov", "C/2.mov"]})
    assert resolutions[0].status == AMBIGUOUS
    assert len(resolutions[0].candidates) == 3
    report = usage_report(record, resolutions)
    # An ambiguity contributes nothing to the usage claim.
    assert report["assets_usados"] == []
    assert report["tasa_resolucion_inequivoca"] == 0.0
    assert any("sin decidir" in x for x in report["limites"])


def test_a_missing_reference_is_not_a_claim_that_the_file_never_existed(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\ausente.mov")])
    report = usage_report(record, resolve_references(record, {}))
    assert report["conteos"][NOT_FOUND] == 1
    assert any("NO prueba que el archivo no exista" in x
               for x in report["limites"])


def test_a_resolution_never_claims_identical_bytes(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\unico.mov")])
    report = usage_report(record, resolve_references(
        record, {"unico.mov": ["TOUR/unico.mov"]}))
    assert any("no identidad de bytes" in x or "candidata, no identidad" in x
               for x in report["limites"])
    assert "full_sha256" in " ".join(report["limites"])


def test_the_same_basename_from_two_directories_is_flagged(tmp_path):
    """Measured inside a real composition: 'Fire Transition 1.mov' is cited from
    two different folders, so the basename does not even separate them there."""
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Footage\fire.mov"),
        ("VideoFile", r"C:\Users\ejemplo\Nueva carpeta\fire.mov")])
    assert len(record.references) == 2
    assert any("directorios distintos" in w for w in record.warnings)


def test_an_all_absolute_composition_is_flagged_as_not_self_contained(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\a.mov"), ("VideoFile", r"D:\y\b.mov")])
    assert any("no es autocontenida" in w for w in record.warnings)


def test_a_composition_with_no_media_says_so(tmp_path):
    record = _composition(tmp_path, "empty.avc", [])
    assert record.references == []
    assert any("no cita ningun archivo" in w for w in record.warnings)


def test_a_document_that_is_not_a_composition_is_refused(tmp_path):
    path = tmp_path / "x.avc"
    path.write_text("<XmlState name='a'><ScreenSetup/></XmlState>", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_composition(path)


def test_parsing_and_resolution_are_deterministic(tmp_path):
    refs = [("VideoFile", r"C:\Users\ejemplo\a.mov"), ("AudioFile", r"C:\Users\ejemplo\b.wav")]
    first = _composition(tmp_path, "s.avc", refs)
    second = parse_composition(tmp_path / "s.avc")
    base = {"a.mov": ["T/a.mov"]}
    assert (usage_report(first, resolve_references(first, base))
            == usage_report(second, resolve_references(second, base)))


def test_the_rate_is_per_composition_and_counts_reconcile(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\one.mov"),
        ("VideoFile", r"C:\Users\ejemplo\two.mov"),
        ("VideoFile", r"C:\Users\ejemplo\three.mov"),
        ("VideoFile", r"C:\Users\ejemplo\four.mov")])
    report = usage_report(record, resolve_references(record, {
        "one.mov": ["A/one.mov"],
        "two.mov": ["A/two.mov", "B/two.mov"]}))
    counts = report["conteos"]
    assert counts[RESOLVED_UNIQUE] == 1
    assert counts[AMBIGUOUS] == 1
    assert counts[NOT_FOUND] == 2
    assert (counts[RESOLVED_UNIQUE] + counts[AMBIGUOUS] + counts[NOT_FOUND]
            == counts["referencias"])
    assert report["tasa_resolucion_inequivoca"] == pytest.approx(0.25)


# --- orphan candidates: a starting list, never a delete list --------------

def test_orphan_candidates_never_claim_an_asset_is_unused(tmp_path):
    index = _index(tmp_path, ["TOUR/used.mov", "TOUR/idle.mov", "OTHER/x.mov"])
    result = orphan_candidates("TOUR", {"TOUR/used.mov"}, index)
    assert result["assets_en_el_contenedor"] == 2
    assert result["referenciados_por_una_composicion_leida"] == 1
    assert result["sin_referencia_conocida"] == 1
    assert "no significa inutilizado" in result["advertencia"].casefold()
    assert "no una lista de borrado" in result["advertencia"]
    assert [o["asset"] for o in result["mayores_sin_referencia"]] == ["TOUR/idle.mov"]


def test_orphan_candidates_stay_inside_the_named_container(tmp_path):
    index = _index(tmp_path, ["TOUR/a.mov", "OTHER/b.mov"])
    result = orphan_candidates("TOUR", set(), index)
    assert result["assets_en_el_contenedor"] == 1


# --- real input -----------------------------------------------------------

def _skip_unless_real():
    if not CAUPOLICAN.is_file() or not REAL_INDEX.is_file():
        pytest.skip("SSD not mounted or index absent")


def test_the_real_caupolican_show_resolves_its_setlist():
    """Numbers measured on 2026-08-21, so a regression is visible."""
    _skip_unless_real()
    record = parse_composition(CAUPOLICAN)
    assert record.composition_name == "SHOWCAUPOLICAN FINAL ANTES DE CAUPO"
    assert record.canvas == (1920, 1080)
    assert record.layers == 6 and record.columns == 24
    assert not record.relative_paths_declared
    report = usage_report(record, resolve_references(
        record, index_basenames(REAL_INDEX)))
    counts = report["conteos"]
    assert counts["referencias"] == 52
    assert counts[RESOLVED_UNIQUE] == 28
    assert counts[AMBIGUOUS] == 6
    assert counts[NOT_FOUND] == 18
    # It pulled material from a second container, which folder structure alone
    # would not have shown.
    assert report["contenedores_tocados"] == ["DREFGIRA",
                                              "descargas hasta RDFLYER 2050"]
    setlist = [a for a in report["assets_usados"] if "BLOQUE 01 LSDR" in a]
    assert len(setlist) >= 8, setlist


def test_a_real_composition_pointing_at_another_machine_resolves_nothing():
    """The honest opposite case, kept: sampier.avc cites another machine's
    Desktop, so nothing resolves and the tool must not pretend otherwise."""
    path = REAL_DIR / "LYON/sampier.avc"
    if not path.is_file() or not REAL_INDEX.is_file():
        pytest.skip("SSD not mounted")
    record = parse_composition(path)
    report = usage_report(record, resolve_references(
        record, index_basenames(REAL_INDEX)))
    assert report["conteos"][RESOLVED_UNIQUE] == 0
    assert report["tasa_resolucion_inequivoca"] == 0.0
    assert report["assets_usados"] == []
    assert any("no es autocontenida" in w
               for w in report["composicion"]["avisos"])


# --- duplicate copies: a decided clip in an undecided location -------------

def test_copies_that_agree_on_size_and_sample_are_one_decided_clip(tmp_path):
    """Measured on the Caupolican show: all 6 of its ambiguous references had
    two candidates that agreed on byte size AND sample_sha256 -- the same clip
    stored loose and again inside a setlist block. Abstaining there threw away
    a usable answer, because WHICH clip played was decided all along."""
    from flujo.venues.resolume_composition import RESOLVED_MULTI_LOCATION

    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\clip.mov")])
    basenames = {"clip.mov": ["TOUR/clip.mov", "TOUR/BLOQUE/clip.mov"]}
    metadata = {"TOUR/clip.mov": (500, "abc"),
                "TOUR/BLOQUE/clip.mov": (500, "abc")}
    resolutions = resolve_references(record, basenames, metadata)
    assert resolutions[0].status == RESOLVED_MULTI_LOCATION
    report = usage_report(record, resolutions)
    assert report["conteos"][RESOLVED_MULTI_LOCATION] == 1
    assert report["conteos"][AMBIGUOUS] == 0
    # The clip counts as used and both copies stay visible.
    assert sorted(report["assets_usados"]) == ["TOUR/BLOQUE/clip.mov",
                                               "TOUR/clip.mov"]
    assert report["copias_duplicadas"][0]["basename"] == "clip.mov"
    # It is NOT counted as unambiguous, because the location is not decided.
    assert report["tasa_resolucion_inequivoca"] == 0.0
    assert report["tasa_clip_decidido"] == 1.0
    assert any("copias del mismo" in x for x in report["limites"])


def test_copies_that_differ_stay_ambiguous(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\clip.mov")])
    basenames = {"clip.mov": ["A/clip.mov", "B/clip.mov"]}
    resolutions = resolve_references(
        record, basenames,
        {"A/clip.mov": (500, "abc"), "B/clip.mov": (900, "zzz")})
    assert resolutions[0].status == AMBIGUOUS
    assert usage_report(record, resolutions)["assets_usados"] == []


def test_a_missing_sample_hash_is_not_an_agreement(tmp_path):
    """An unknown must not read as a match."""
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\clip.mov")])
    basenames = {"clip.mov": ["A/clip.mov", "B/clip.mov"]}
    for metadata in (
            {"A/clip.mov": (500, ""), "B/clip.mov": (500, "")},
            {"A/clip.mov": (500, "abc")},
    ):
        assert resolve_references(
            record, basenames, metadata)[0].status == AMBIGUOUS


def test_without_metadata_the_behaviour_is_unchanged(tmp_path):
    record = _composition(tmp_path, "s.avc", [
        ("VideoFile", r"C:\Users\ejemplo\Desktop\clip.mov")])
    basenames = {"clip.mov": ["A/clip.mov", "B/clip.mov"]}
    assert resolve_references(record, basenames)[0].status == AMBIGUOUS


def test_the_real_caupolican_ambiguities_are_all_duplicate_copies():
    """Every one of the six was the same file in two places, measured."""
    from flujo.venues.resolume_composition import (
        RESOLVED_MULTI_LOCATION, index_asset_metadata)

    _skip_unless_real()
    record = parse_composition(CAUPOLICAN)
    report = usage_report(record, resolve_references(
        record, index_basenames(REAL_INDEX), index_asset_metadata(REAL_INDEX)))
    counts = report["conteos"]
    assert counts[RESOLVED_UNIQUE] == 28
    assert counts[RESOLVED_MULTI_LOCATION] == 6
    assert counts[AMBIGUOUS] == 0
    assert counts[NOT_FOUND] == 18
    assert report["tasa_clip_decidido"] == pytest.approx(34 / 52, abs=1e-4)
    assert len(report["copias_duplicadas"]) == 6


# --- copies that span containers are not waste -----------------------------
#
# Measured on the real index: 543 (basename, bytes) pairs live under two or more
# container roots, 31.3 GB counting only the extra copies. A deduplicator sees
# one thing; the operator's reading shows three, and deleting the wrong copy is
# a different loss in each:
#
#   - the same clip in two shows: HARRY CHILLAN/ESCARLATA.mp4 and
#     HARRY/show/VINA/ESCARLATA.mp4 -- a VJ set travelling;
#   - the same clip under two artists because the track is a collaboration:
#     escarlata.mp4 in DREFGIRA, DrefQuila and HARRY, because it is a remix;
#   - a tour folder and the artist's own body of work: enrolar.mp4 and
#     misionar.mov in DREFGIRA and DrefQuila.


def test_a_copy_in_two_containers_is_reported_and_never_ranked_for_deletion(tmp_path):
    from flujo.venues.resolume_composition import cross_container_copies

    index = _index(tmp_path, ["TOUR/clip.mov", "ARTIST/clip.mov", "TOUR/solo.mov"])
    # give the shared pair the same size so it groups
    import sqlite3
    con = sqlite3.connect(index)
    con.execute("UPDATE assets SET bytes=999, sample_sha256='abc' "
                "WHERE relative_path LIKE '%clip.mov'")
    con.commit(); con.close()
    result = cross_container_copies(index)
    assert result["grupos"] == 1
    group = result["mayores"][0]
    assert group["containers"] == ["ARTIST", "TOUR"]
    assert group["same_sample_hash"] is True
    assert result["bytes_en_copias_extra"] == 999
    warning = result["advertencia"]
    assert "NINGUNO" in warning and "no para liberar disco" in warning
    # It must never present a winner.
    assert "borrar" not in str(group).casefold()


def test_a_file_alone_in_one_container_is_not_a_cross_container_copy(tmp_path):
    from flujo.venues.resolume_composition import cross_container_copies

    index = _index(tmp_path, ["TOUR/a.mov", "TOUR/b.mov"])
    assert cross_container_copies(index)["grupos"] == 0


def test_same_name_different_bytes_does_not_group(tmp_path):
    """Two different edits sharing a filename are not copies of one thing."""
    from flujo.venues.resolume_composition import cross_container_copies

    index = _index(tmp_path, ["TOUR/clip.mov", "ARTIST/clip.mov"])
    assert cross_container_copies(index)["grupos"] == 0  # _index gives distinct sizes


def test_the_orphan_warning_names_the_measured_reason(tmp_path):
    index = _index(tmp_path, ["TOUR/a.mov"])
    warning = orphan_candidates("TOUR", set(), index)["advertencia"]
    assert "543" in warning, "the orphan warning lost the measurement"
    assert "colaboracion" in warning and "cuerpo de obra" in warning


def test_the_real_index_reproduces_the_measured_cross_container_shape():
    from flujo.venues.resolume_composition import cross_container_copies

    if not REAL_INDEX.is_file():
        pytest.skip("SSD index absent")
    result = cross_container_copies(REAL_INDEX)
    assert result["grupos"] == 543

    # escarlata.mp4 appears as TWO distinct groups of different sizes, and that
    # is the whole point of grouping on (basename, bytes): they are different
    # relationships, not one duplicate.
    escarlatas = [item for item in result["mayores"]
                  if item["basename"] == "escarlata.mp4"]
    assert len(escarlatas) == 2, [item["bytes"] for item in escarlatas]
    by_size = {item["bytes"]: item["containers"] for item in escarlatas}
    biggest = max(by_size)
    # The collaboration: the remix sits under three artists at once.
    assert by_size[biggest] == ["DREFGIRA", "DrefQuila", "HARRY"]
    # The travelling set: the same smaller clip played at two shows.
    smaller = min(by_size)
    assert by_size[smaller] == ["HARRY", "HARRY CHILLAN"]
