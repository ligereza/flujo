"""Tests for the persisted reconstruction -> Project IR bridge."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from flujo.knowledge import project_reconstruction
from flujo.knowledge.project_reconstruction import (
    REL_CONTAINED_BY,
    REL_CONTAINS,
    REL_SHARED_RESOURCE,
    REL_SHARES_LIBRARY_WITH,
    RELATION_INVERSES,
    SYMMETRIC_RELATIONS,
    UnknownRelationError,
    inverse_relation,
)
from flujo.knowledge.project_router import route_project
from flujo.knowledge.reconstruction_adapter import (
    ADAPTER_SCHEMA,
    adapt_reconstruction,
    project_irs_from_reconstruction,
)
from tests.test_project_reconstruction import make_index
from flujo.knowledge.project_reconstruction import reconstruct, to_payload


def test_reconstruction_units_become_reviewable_ir_without_dependencies(tmp_path: Path) -> None:
    index = tmp_path / "index.sqlite"
    make_index(index)
    payload = to_payload(reconstruct(index, "DREFGIRA"))
    records = project_irs_from_reconstruction(payload, source_ref="fixture/reconstruction.json")

    assert [record["title"] for record in records] == ["DREFGIRA", "DREFGIRA/SHOW"]
    assert all(record["schema"] == "mak-project-ir-v1" for record in records)
    assert all(record["state"] == "review_required" for record in records)
    assert all(record["source"]["kind"] == "portable_ssd_index" for record in records)
    assert all("physical_source_mount_unverified" in record["unknowns"] for record in records)
    assert all(record["consumer_policy"]["portfolio"] == "never_auto_publish" for record in records)
    assert all(route_project(record)["reason"] == "project_state_requires_evidence"
               for record in records)
    # The dependency remains visible as an indexed artifact of its owning
    # unit; it is not promoted to a second Project IR record.
    assert len(records) == 2
    assert not any(record["title"].endswith("waves_55443377") for record in records)


def test_adapter_reads_persisted_json_and_preserves_index_hash(tmp_path: Path) -> None:
    index = tmp_path / "index.sqlite"
    make_index(index)
    payload = to_payload(reconstruct(index, "DREFGIRA"))
    reconstruction = tmp_path / "reconstruction.json"
    reconstruction.write_text(json.dumps(payload), encoding="utf-8")

    records = adapt_reconstruction(reconstruction)

    assert len(records) == 2
    assert records[0]["evidence"][0]["index_fingerprint"] == payload["index_fingerprint"]
    assert records[0]["reconstruction"]["schema"] == "mak-project-reconstruction-v1"


def test_adapter_does_not_mutate_source_index(tmp_path: Path) -> None:
    index = tmp_path / "index.sqlite"
    make_index(index)
    before = index.read_bytes()
    payload = to_payload(reconstruct(index, "DREFGIRA"))
    project_irs_from_reconstruction(payload)
    assert index.read_bytes() == before


def test_an_edge_is_never_stated_twice_in_the_same_direction(tmp_path: Path) -> None:
    """The inversion that made a texture contain the work that uses it.

    Every record keeps its own incident edges with itself as the subject, so an
    edge whose other endpoint is the record has to be re-anchored. Re-anchoring
    without inverting the predicate is a silent lie about direction, and it was
    live: measured on the real LYON reconstruction, 24 ``contains`` edges at the
    source became 56 in the persisted graph with half of them backwards.
    """
    index = tmp_path / "index.sqlite"
    make_index(index)
    payload = to_payload(reconstruct(index, "DREFGIRA"))
    records = project_irs_from_reconstruction(payload)

    edges = [relation for record in records for relation in record["relations"]]
    assert edges, "the fixture produced no relations at all"

    forward = sum(1 for e in edges if e["predicate"] == REL_CONTAINS)
    backward = sum(1 for e in edges if e["predicate"] == REL_CONTAINED_BY)
    assert forward == backward, (
        "each containment edge must be stated once from each side")
    assert forward == sum(1 for r in payload["relations"]
                          if r["relation"] == REL_CONTAINS)

    # The concrete claim: no pair of records both say they contain the other.
    titles = {record["project_id"]: record["title"] for record in records}
    claimed = {(titles[e["subject"]], e["object"])
               for e in edges if e["predicate"] == REL_CONTAINS}
    for owner, contained in claimed:
        assert (contained.rsplit("/", 1)[-1], owner) not in claimed, (
            f"{owner} and {contained} both claim to contain the other")


def test_every_relation_the_reconstruction_emits_has_a_declared_inverse() -> None:
    """The class, not the instance.

    A new predicate added to the producer without an inverse would be projected
    silently in the wrong direction again. ``inverse_relation`` refuses instead,
    so this pins that the refusal cannot fire on the real vocabulary.
    """
    source = (Path(__file__).resolve().parents[1] / "src" / "flujo" /
              "knowledge" / "project_reconstruction.py").read_text(encoding="utf-8")
    emitted = set(re.findall(r'UnitRelation\(\s*[\w.\[\]"\' ]+,\s*(REL_[A-Z_]+)', source))
    emitted |= set(re.findall(r'^\s+(REL_[A-Z_]+) if ', source, re.MULTILINE))
    emitted |= set(re.findall(r'^\s+else (REL_[A-Z_]+),', source, re.MULTILINE))
    assert emitted, "no emission site found; the scan stopped matching the code"
    for name in sorted(emitted):
        predicate = getattr(project_reconstruction, name)
        assert predicate in RELATION_INVERSES, f"{name} has no declared inverse"
        assert inverse_relation(inverse_relation(predicate)) == predicate


def test_a_predicate_without_an_inverse_is_refused_not_guessed() -> None:
    with pytest.raises(UnknownRelationError):
        inverse_relation("related_to")


def test_library_reuse_between_roots_is_symmetric_and_ownership_is_not() -> None:
    """One name used to mean both, which is why direction was unrecoverable.

    ``shares_library_with`` is a claim about two container roots and reads the
    same from either end. ``shared_resource`` is a claim that one owner uses a
    resource folder, and reversing it would make the folder the owner.
    """
    assert REL_SHARES_LIBRARY_WITH in SYMMETRIC_RELATIONS
    assert inverse_relation(REL_SHARES_LIBRARY_WITH) == REL_SHARES_LIBRARY_WITH
    assert REL_SHARED_RESOURCE not in SYMMETRIC_RELATIONS
    assert inverse_relation(REL_SHARED_RESOURCE) == "shared_resource_of"
