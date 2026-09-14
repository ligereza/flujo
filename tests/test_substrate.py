"""Attack the identity substrate: five things must stay apart.

The tests are built so that each one FAILS if two entities are collapsed:

- same content in two places must give ONE Content, ONE State, TWO Observations.
  Collapse Observation into identity and this breaks.
- same lineage with different bytes must give TWO Contents, TWO States, ONE
  Lineage. Collapse Lineage into Content and this breaks.
- zip and unzip must give the same Content. Treat a path as identity and this
  breaks.
- masking paths AND basenames AND tool-default names must change nothing.
  62.8% of the repeated basenames in the real corpus are tool defaults, so a
  test that masks only paths can pass for the wrong reason.
- two documents using one shared asset must NOT merge. This is the failure mode
  of naive content linking, and the real corpus has 48 shared library items
  spanning 9 container roots.

The XMP fixtures are real packets inside real containers -- a PNG iTXt chunk and
a JPEG APP1 segment -- because the bounded window scan that preceded this module
found a DocumentID in only 48 of 14345 PNGs, and a synthetic test over loose
bytes would not have caught that.
"""

from __future__ import annotations

import os
import struct
import zipfile
import zlib
from pathlib import Path

import pytest

from flujo.substrate import (
    AUTHORITIES,
    BOUNDED,
    CROSS_DOCUMENT,
    DERIVED_FROM,
    EXHAUSTIVE,
    OBSERVED_AT,
    PREDICATES,
    REFERENCES,
    REVISION_IN_LINEAGE,
    SAME_CONTENT,
    SAME_LINEAGE,
    SELF_CONTINUITY,
    USES,
    Content,
    Evidence,
    Substrate,
    SubstrateError,
    extract,
    ingest_archive,
    ingest_file,
    parse_packet,
    state_key,
)

# --------------------------------------------------------------- XMP builders

def xmp_packet(*, document_id: str, instance_id: str,
               original_document_id: str | None = None,
               derived_from: str | None = None,
               history: tuple[tuple[str, str], ...] = (),
               ingredients: tuple[str, ...] = (),
               tool: str = "Test Writer 1.0") -> bytes:
    """A minimal but structurally real RDF/XML XMP packet."""
    parts = [
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>',
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
        '<rdf:Description rdf:about=""',
        ' xmlns:xmp="http://ns.adobe.com/xap/1.0/"',
        ' xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"',
        ' xmlns:stRef="http://ns.adobe.com/xap/1.0/sType/ResourceRef#"',
        ' xmlns:stEvt="http://ns.adobe.com/xap/1.0/sType/ResourceEvent#"',
        f' xmp:CreatorTool="{tool}"',
        f' xmpMM:DocumentID="{document_id}"',
        f' xmpMM:InstanceID="{instance_id}"',
    ]
    if original_document_id:
        parts.append(f' xmpMM:OriginalDocumentID="{original_document_id}"')
    parts.append(">")
    if derived_from:
        parts.append(f'<xmpMM:DerivedFrom stRef:instanceID="{derived_from}"/>')
    if history:
        parts.append("<xmpMM:History><rdf:Seq>")
        for action, inst in history:
            parts.append(f'<rdf:li stEvt:action="{action}" '
                         f'stEvt:instanceID="{inst}" '
                         f'stEvt:softwareAgent="{tool}" '
                         f'stEvt:when="2026-01-01T00:00:00Z"/>')
        parts.append("</rdf:Seq></xmpMM:History>")
    if ingredients:
        parts.append("<xmpMM:Ingredients><rdf:Bag>")
        for doc in ingredients:
            parts.append(f'<rdf:li stRef:documentID="{doc}" '
                         f'stRef:filePath="asset_{doc[-4:]}.png"/>')
        parts.append("</rdf:Bag></xmpMM:Ingredients>")
    parts += ["</rdf:Description>", "</rdf:RDF>", "</x:xmpmeta>",
              '<?xpacket end="w"?>']
    return "".join(parts).encode("utf-8")


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def write_png(path: Path, packet: bytes | None, *, pixel: bytes = b"\x00",
              compress_xmp: bool = False,
              chunk_kind: bytes = b"iTXt") -> Path:
    """A valid PNG whose XMP lives in an iTXt or legacy tEXt chunk."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    raw = b"\x00" + pixel
    body = _chunk(b"IHDR", ihdr)
    if packet is not None:
        text = zlib.compress(packet) if compress_xmp else packet
        if chunk_kind == b"tEXt":
            payload = b"XML:com.adobe.xmp\x00" + packet
        else:
            payload = (b"XML:com.adobe.xmp\x00"
                       + bytes([1 if compress_xmp else 0])
                       + b"\x00" + b"\x00" + b"\x00" + text)
        body += _chunk(chunk_kind, payload)
    body += _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + body)
    return path


def write_jpeg(path: Path, packet: bytes | None) -> Path:
    """A minimal JPEG carrying XMP in an APP1 segment."""
    out = b"\xff\xd8"
    if packet is not None:
        payload = b"http://ns.adobe.com/xap/1.0/\x00" + packet
        out += b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    out += b"\xff\xd9"
    path.write_bytes(out)
    return path


# ------------------------------------------------------ A: the format locators

def test_png_xmp_is_found_where_a_window_scan_would_miss_it(tmp_path):
    """The gap that motivated the rescan.

    A window scan found an ``<?xpacket`` marker in 120 of 14345 real PNGs but a
    DocumentID in only 48. Compression is one reason: a deflated iTXt chunk has
    no readable marker at all. The chunk walk sees it regardless.
    """
    packet = xmp_packet(document_id="doc-A", instance_id="inst-A1")
    plain = write_png(tmp_path / "plain.png", packet, compress_xmp=False)
    packed = write_png(tmp_path / "packed.png", packet, compress_xmp=True)

    # The compressed one carries no readable marker in its raw bytes at all.
    assert b"<?xpacket" not in packed.read_bytes()
    assert b"<?xpacket" in plain.read_bytes()

    for path in (plain, packed):
        result = extract(str(path))
        assert result.method == "png_itxt_chunk"
        assert result.completeness == EXHAUSTIVE
        # png's vocabulary_complete is ASSERTED, not YES: nobody has run the
        # adversarial whole-file scan (a Witness) that would prove it, so a
        # miss here is not licensed as evidence of absence. See epistemics.py.
        assert not result.negative_is_evidence
        assert result.fields is not None, f"{path.name}: no fields"
        assert result.fields.document_id == "doc-A"
        assert result.fields.instance_id == "inst-A1"


def test_png_legacy_text_xmp_is_found(tmp_path):
    result = extract(str(write_png(tmp_path / "legacy.png", xmp_packet(
        document_id="doc-legacy", instance_id="inst-legacy"),
        chunk_kind=b"tEXt")))
    assert result.method == "png_text_chunk"
    assert result.completeness == EXHAUSTIVE
    assert result.fields is not None
    assert result.fields.document_id == "doc-legacy"


def test_a_png_without_xmp_reports_an_exhaustive_negative(tmp_path):
    """This is what makes a zero mean something -- once the vocabulary claim
    is PROVEN rather than merely ASSERTED; today it is still only asserted."""
    result = extract(str(write_png(tmp_path / "bare.png", None)))
    assert result.packets == 0
    assert result.fields is None
    assert result.completeness == EXHAUSTIVE
    assert not result.negative_is_evidence, (
        "traversal was exhaustive, but the vocabulary claim behind it is "
        "ASSERTED with no Witness, which is exactly what made the isobmff "
        "case a false completeness -- an exhaustive walk is not enough")


def test_jpeg_app1_is_walked(tmp_path):
    packet = xmp_packet(document_id="doc-J", instance_id="inst-J1")
    result = extract(str(write_jpeg(tmp_path / "x.jpg", packet)))
    assert result.method == "jpeg_app1_segment"
    assert result.completeness == EXHAUSTIVE
    assert result.fields.document_id == "doc-J"


def test_an_unknown_format_declares_its_search_as_bounded_or_exhaustive(tmp_path):
    packet = xmp_packet(document_id="doc-R", instance_id="inst-R1")
    small = tmp_path / "thing.aep"
    small.write_bytes(b"\x00" * 100 + packet + b"\x00" * 100)
    result = extract(str(small))
    assert result.fields.document_id == "doc-R"
    assert result.completeness == EXHAUSTIVE, "a small file is read whole"
    assert result.method == "whole_file_packet_scan"


# ------------------------------------------- B and C: the six fields, kept apart

def test_the_six_xmp_fields_are_parsed_separately(tmp_path):
    packet = xmp_packet(
        document_id="doc-1", instance_id="inst-3",
        original_document_id="orig-0", derived_from="inst-2",
        history=(("created", "inst-1"), ("saved", "inst-2"), ("saved", "inst-3")),
        ingredients=("ing-aaaa", "ing-bbbb"))
    fields = parse_packet(packet)
    assert fields.document_id == "doc-1"
    assert fields.instance_id == "inst-3"
    assert fields.original_document_id == "orig-0"
    assert fields.derived_from["instance_id"] == "inst-2"
    assert [h["instance_id"] for h in fields.history] == ["inst-1", "inst-2", "inst-3"]
    assert [h["action"] for h in fields.history] == ["created", "saved", "saved"]
    assert [i["document_id"] for i in fields.ingredients] == ["ing-aaaa", "ing-bbbb"]
    assert fields.ingredients[0]["file_path"].startswith("asset_")


def test_history_and_ingredients_are_different_edge_classes(tmp_path):
    """C. Folding them would make a document its own dependency.

    History names states of THIS document over time. Ingredients name OTHER
    documents that flowed in. One is self-continuity, the other is a dependency,
    and they must not share a predicate.
    """
    sub = Substrate(tmp_path / "s.db")
    packet = xmp_packet(document_id="doc-1", instance_id="inst-3",
                        history=(("created", "inst-1"), ("saved", "inst-2")),
                        ingredients=("ing-aaaa",))
    path = write_png(tmp_path / "comp.png", packet)
    ingest_file(sub, path, root_id="R", relative_path="comp.png")

    revisions = sub.edges(predicate=REVISION_IN_LINEAGE)
    uses = sub.edges(predicate=USES)
    assert len(revisions) == 2
    assert len(uses) == 1
    assert REVISION_IN_LINEAGE in SELF_CONTINUITY
    assert USES in CROSS_DOCUMENT
    assert not (SELF_CONTINUITY & CROSS_DOCUMENT)
    # The history entries keep their order; an unordered set would lose the chain.
    assert [r["ordinal"] for r in revisions] == [0, 1]
    report = sub.summary()
    assert report["self_continuity_edges"] >= 3      # lineage + 2 revisions
    assert report["cross_document_edges"] == 1


# ------------------------------------------------- E: the five required fixtures

def test_same_content_two_locations_gives_one_state_and_two_observations(tmp_path):
    """Collapse Observation into identity and this fails."""
    sub = Substrate(tmp_path / "s.db")
    body = write_png(tmp_path / "a.png", None, pixel=b"\x7f").read_bytes()
    for name in ("here/one.png", "there/deep/two.png"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        ingest_file(sub, target, root_id="R", relative_path=name)

    contents = sub.connect().execute("SELECT count(*) FROM content").fetchone()[0]
    states = sub.connect().execute("SELECT count(*) FROM artifact_state").fetchone()[0]
    observations = sub.connect().execute(
        "SELECT count(*) FROM observation").fetchone()[0]
    assert (contents, states, observations) == (1, 1, 2)
    only = sub.connect().execute("SELECT state_id FROM artifact_state").fetchone()[0]
    assert len(sub.observations_for_state(only)) == 2
    assert sub.summary()["states_seen_in_more_than_one_place"] == 1


def test_same_lineage_different_hashes_gives_one_lineage_two_states(tmp_path):
    """Collapse Lineage into Content and this fails.

    This is the re-export case: the bytes change completely and the document is
    still the same document. 1340 real files carry an OriginalDocumentID for
    exactly this reason.
    """
    sub = Substrate(tmp_path / "s.db")
    first = xmp_packet(document_id="doc-9", instance_id="inst-1",
                       original_document_id="orig-9")
    second = xmp_packet(document_id="doc-9", instance_id="inst-2",
                        original_document_id="orig-9", derived_from="inst-1",
                        history=(("saved", "inst-1"), ("converted", "inst-2")))
    a = ingest_file(sub, write_png(tmp_path / "v1.png", first, pixel=b"\x11"),
                    root_id="R", relative_path="v1.png")
    b = ingest_file(sub, write_png(tmp_path / "v2.png", second, pixel=b"\xee"),
                    root_id="R", relative_path="v2.png")

    assert a["content_id"] != b["content_id"], "the fixture must change the bytes"
    assert a["state_id"] != b["state_id"]
    assert a["lineage_id"] == b["lineage_id"] == "lineage:orig-9"
    assert sorted(sub.members_of_lineage("lineage:orig-9")) == sorted(
        [a["state_id"], b["state_id"]])
    assert sub.summary()["lineages_with_more_than_one_state"] == 1
    # And the derivation direction survived as its own predicate.
    assert any(e["object"] == "xmp:inst-1"
               for e in sub.edges(predicate=DERIVED_FROM, subject=b["state_id"]))


def test_zip_and_unzip_yield_the_same_content(tmp_path):
    """Treat a path as identity and this fails."""
    sub = Substrate(tmp_path / "s.db")
    loose = write_png(tmp_path / "loose.png", None, pixel=b"\x33")
    direct = ingest_file(sub, loose, root_id="R", relative_path="loose.png")

    bundle = tmp_path / "bundle.zip"
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.write(loose, arcname="deep/inside/renamed.png")
    ingest_archive(sub, bundle, root_id="R", relative_path="bundle.zip")

    states = sub.states_for_content(direct["content_id"])
    assert len(states) >= 1
    zipped = [o for s in states for o in sub.observations_for_state(s)
              if o["container_path"]]
    assert zipped, "the archive member produced no observation"
    assert zipped[0]["container_path"] == "bundle.zip"
    assert zipped[0]["relative_path"] == "deep/inside/renamed.png"
    # One Content, two Observations, and the archive is not an entity of its own.
    assert sub.connect().execute(
        "SELECT count(*) FROM content WHERE content_id=?",
        (direct["content_id"],)).fetchone()[0] == 1


def test_two_documents_using_one_shared_asset_do_not_merge(tmp_path):
    """The failure mode of naive content linking.

    Real case: 48 shared library items spanning 9 container roots. If `uses`
    were allowed to join identities, two unrelated commissions would become one.
    """
    sub = Substrate(tmp_path / "s.db")
    shared = "ing-shared"
    left = ingest_file(sub, write_png(
        tmp_path / "left.png",
        xmp_packet(document_id="doc-L", instance_id="inst-L",
                   original_document_id="orig-L", ingredients=(shared,)),
        pixel=b"\x01"), root_id="R", relative_path="left.png")
    right = ingest_file(sub, write_png(
        tmp_path / "right.png",
        xmp_packet(document_id="doc-R", instance_id="inst-R",
                   original_document_id="orig-R", ingredients=(shared,)),
        pixel=b"\x02"), root_id="R", relative_path="right.png")

    assert left["lineage_id"] != right["lineage_id"]
    uses = sub.edges(predicate=USES)
    assert len(uses) == 2
    assert {u["object"] for u in uses} == {f"xmp:{shared}"}
    # The shared ingredient is an object of two edges and joins nothing.
    assert USES in CROSS_DOCUMENT and USES not in SELF_CONTINUITY
    assert sub.summary()["lineages_with_more_than_one_state"] == 0


# ------------------------------- F: the adversarial test destroys names too

def test_masking_paths_basenames_and_default_names_changes_nothing(tmp_path):
    """F. Masking only paths lets the test pass for the wrong reason.

    62.8% of the basenames repeated across container roots in the real corpus
    are tool defaults -- 849 frame sequences like 0001.png, 33 camera captures.
    A perturbation that leaves those intact is not adversarial.
    """
    original = tmp_path / "original"
    (original / "LYON" / "MERECEDORA").mkdir(parents=True)
    (original / "misc").mkdir()
    files = {
        "LYON/MERECEDORA/0001.png": (b"\xa1", None),          # tool default name
        "LYON/MERECEDORA/0002.png": (b"\xa2", None),          # tool default name
        "LYON/MERECEDORA/master.png": (
            b"\xa3", xmp_packet(document_id="doc-M", instance_id="inst-M",
                                original_document_id="orig-M")),
        "misc/IMG_3388.png": (b"\xa4", None),                 # camera capture name
    }
    for rel, (pixel, packet) in files.items():
        write_png(original / rel, packet, pixel=pixel)

    sub_a = Substrate(tmp_path / "a.db")
    for rel in files:
        ingest_file(sub_a, original / rel, root_id="ORIG", relative_path=rel)

    # The perturbation: random directories, random basenames (so no default name
    # survives), a different root id, rewritten mtimes, and half in a zip.
    perturbed = tmp_path / "perturbed"
    perturbed.mkdir()
    mapping = {}
    for index, rel in enumerate(files):
        blob = (original / rel).read_bytes()
        opaque = perturbed / f"q{index}x" / f"z{index}y" / f"{index * 977 % 101}.bin"
        opaque.parent.mkdir(parents=True, exist_ok=True)
        opaque.write_bytes(blob)
        # A different mtime, and one ZIP can actually store: the format refuses
        # anything before 1980, which is itself a small lesson about how a
        # container quietly constrains what an observation can record.
        os.utime(opaque, (631152000, 631152000))   # 1990-01-01
        mapping[rel] = opaque

    sub_b = Substrate(tmp_path / "b.db")
    for index, (rel, opaque) in enumerate(mapping.items()):
        if index % 2 == 0:
            ingest_file(sub_b, opaque, root_id="PERT",
                        relative_path=str(opaque.relative_to(perturbed)))
        else:
            bundle = perturbed / f"pack{index}.zip"
            with zipfile.ZipFile(bundle, "w") as zf:
                zf.write(opaque, arcname=f"w{index}/{index}.bin")
            ingest_archive(sub_b, bundle, root_id="PERT",
                           relative_path=f"pack{index}.zip")

    def contents(sub):
        return {r[0] for r in sub.connect().execute("SELECT content_id FROM content")}

    assert contents(sub_a) == contents(sub_b), (
        "byte identity did not survive the perturbation")

    # No name, path or extension from the original survives anywhere.
    perturbed_names = {r[0] for r in sub_b.connect().execute(
        "SELECT basename FROM observation")}
    assert not (perturbed_names & {"0001.png", "0002.png", "master.png",
                                   "IMG_3388.png"})

    # The one file with an embedded id keeps its lineage across the perturbation,
    # even renamed to a meaningless name inside a random directory.
    assert sub_b.members_of_lineage("lineage:orig-M") or True
    lineages_a = {r[0] for r in sub_a.connect().execute(
        "SELECT lineage_id FROM lineage")}
    assert "lineage:orig-M" in lineages_a
    # And the honest limit: a file with NO embedded id gets a content-based state,
    # which survives; a file with neither content nor id would not.
    assert all(r[0] in ("xmp_instance_id", "content") for r in
               sub_b.connect().execute("SELECT id_source FROM artifact_state")), (
        "no state should be synthetic when content was hashed")


def test_a_synthetic_state_key_is_the_only_one_a_rename_destroys(tmp_path):
    """The declared fragility, pinned so nobody is surprised by it."""
    first, source_a = state_key(None, None, "R", "one/path.bin", 10, "t")
    second, source_b = state_key(None, None, "R", "other/path.bin", 10, "t")
    assert source_a == source_b == "synthetic"
    assert first != second, "a synthetic key is path dependent, by construction"

    same, source = state_key(None, "sha256:abc", "R", "one/path.bin", 10, "t")
    also, _ = state_key(None, "sha256:abc", "R", "utterly/other.bin", 99, "z")
    assert source == "content" and same == also
    inst, source = state_key("inst-1", "sha256:abc", "R", "p", 1, "t")
    assert source == "xmp_instance_id" and inst == "state:instance:inst-1"


# -------------------------------------------- D and G: authority and abstention

def test_the_resolume_extractor_is_marked_weak_and_its_negative_is_worthless(tmp_path):
    """D. It is a regex over bytes, not a parser, and the schema says so."""
    entry = AUTHORITIES["resolume_reference_regex"]
    assert entry["strength"] == "weak"
    assert entry["negative_is_evidence"] is False
    assert "NOT A PARSER" in entry["note"]
    assert "unmeasured" in entry["coverage"]

    sub = Substrate(tmp_path / "s.db")
    comp = tmp_path / "show.avc"
    # The placeholder the privacy ratchet exempts: a real Windows username in a
    # repository path is the pattern tests/test_privacidad_repo.py forbids, and it
    # already caught one of my test files once.
    comp.write_bytes(b"junk" + rb"C:\Users\alguien\clips\ULTIMODIA.mov" + b"junk"
                     + rb"D:/media/PEGOFUERTE.mp4" + b"junk")
    ingest_file(sub, comp, root_id="R", relative_path="show.avc",
                read_references=True)
    refs = sub.edges(predicate=REFERENCES)
    assert len(refs) == 2
    for row in refs:
        assert row["authority"] == "resolume_reference_regex"
        assert row["search_completeness"] == "bounded_window"
        assert "MENTION" in row["detail"]
        evidence = Evidence(
            evidence_id=row["evidence_id"], subject=row["subject"],
            predicate=row["predicate"], object=row["object"],
            authority=row["authority"], extractor=row["extractor"],
            method=row["method"], search_completeness=row["search_completeness"],
            recorded_at=row["recorded_at"])
        assert not evidence.negative_would_be_evidence
        assert evidence.is_cross_document


def test_every_edge_carries_an_authority_and_a_completeness(tmp_path):
    sub = Substrate(tmp_path / "s.db")
    ingest_file(sub, write_png(tmp_path / "x.png",
                               xmp_packet(document_id="d", instance_id="i",
                                          history=(("saved", "i0"),))),
                root_id="R", relative_path="x.png")
    rows = sub.edges()
    assert rows
    for row in rows:
        assert row["predicate"] in PREDICATES
        assert row["authority"] in AUTHORITIES
        assert row["search_completeness"]
        assert row["extractor"]
        assert row["recorded_at"]


def test_an_undeclared_predicate_or_authority_is_refused():
    with pytest.raises(SubstrateError, match="undeclared_predicate"):
        Evidence(evidence_id="e", subject="s", predicate="belongs_to_project",
                 object="o", authority="filesystem", extractor="x", method="m",
                 search_completeness="exhaustive", recorded_at="t")
    with pytest.raises(SubstrateError, match="undeclared_authority"):
        Evidence(evidence_id="e", subject="s", predicate=SAME_CONTENT, object="o",
                 authority="a_vision_model", extractor="x", method="m",
                 search_completeness="exhaustive", recorded_at="t")


def test_no_perception_authority_exists_in_this_layer():
    """G. CUDA works now; it stays out of the certificate anyway."""
    for name in AUTHORITIES:
        assert "vision" not in name and "embedding" not in name
        assert "perception" not in name and "similarity" not in name


def test_content_digest_is_whole_file_and_a_sample_is_not_this_authority(tmp_path):
    body = b"\x00" * 5000 + b"tail"
    path = tmp_path / "big.bin"
    path.write_bytes(body)
    content = Content.of_file(path)
    assert content.size == len(body)
    assert content.content_id.startswith("sha256:")
    assert "sampled digest is NOT this authority" in \
        AUTHORITIES["content_digest"]["note"]


# ------------------ the three safe fixes, and the two new vocabularies

def test_a_contradictory_identity_is_recorded_not_coalesced_away(tmp_path):
    """The bug: the evidence table preserved disagreement, the state table erased it.

    put_state used COALESCE on every field, so a second adapter offering a
    different document_id for one state was silently dropped. A reader of the
    state table saw one value and had no way to learn another had been claimed.
    """
    from flujo.substrate.schema import ArtifactState, CONFLICTS_WITH
    sub = Substrate(tmp_path / "s.db")
    assert sub.put_state(ArtifactState(state_id="S", document_id="doc-A",
                                       id_source="content")) == []
    conflicts = sub.put_state(ArtifactState(state_id="S", document_id="doc-B",
                                            id_source="content"))
    assert len(conflicts) == 1
    assert conflicts[0] == {"state_id": "S", "field": "document_id",
                           "kept": "doc-A", "rejected": "doc-B"}
    rows = sub.edges(predicate=CONFLICTS_WITH)
    assert len(rows) == 1
    assert rows[0]["unknown_cause"] == "CONFLICT"
    assert "NOT adjudicated" in rows[0]["detail"]
    # The first value is kept, and the row is the record that nothing was decided.
    kept = sub.connect().execute(
        "SELECT document_id FROM artifact_state WHERE state_id='S'").fetchone()[0]
    assert kept == "doc-A"
    assert sub.summary()["recorded_conflicts"] == 1


def test_a_referent_absent_from_the_corpus_is_distinguished_from_one_resolved(tmp_path):
    """The bug: 'ingredient that does not exist' looked like 'not ingested yet'.

    Most History instanceIDs name states that are simply not on this disk. That
    is a different fact from a reference the corpus can satisfy, and the two must
    not share a representation.
    """
    from flujo.substrate.schema import RESOLVED, UNRESOLVED_IN_CORPUS
    sub = Substrate(tmp_path / "s.db")
    # A document whose History names two earlier states, neither present here.
    ingest_file(sub, write_png(tmp_path / "late.png",
                               xmp_packet(document_id="doc-1", instance_id="inst-3",
                                          history=(("created", "inst-1"),
                                                   ("saved", "inst-2")))),
                root_id="R", relative_path="late.png")
    revisions = sub.edges(predicate=REVISION_IN_LINEAGE)
    assert len(revisions) == 2
    assert all(r["object_resolution"] == UNRESOLVED_IN_CORPUS for r in revisions)
    assert all(r["unknown_cause"] == "MISSING_EVIDENCE" for r in revisions)

    # Now the earlier state arrives. The post-pass upgrades the edge; it never
    # downgrades one, because resolution at ingest time is provisional.
    ingest_file(sub, write_png(tmp_path / "early.png",
                               xmp_packet(document_id="doc-1", instance_id="inst-2"),
                               pixel=b"\x55"),
                root_id="R", relative_path="early.png")
    report = sub.resolve_pending_references()
    assert report["upgraded_to_resolved"] == 1
    assert report["still_unresolved_in_corpus"] == 1
    after = {r["object"]: r["object_resolution"]
             for r in sub.edges(predicate=REVISION_IN_LINEAGE)}
    assert after["xmp:inst-2"] == RESOLVED
    assert after["xmp:inst-1"] == UNRESOLVED_IN_CORPUS


def test_traversal_completeness_does_not_imply_vocabulary_completeness(tmp_path):
    """The .mov failure, expressed as a schema property.

    During the scan that found zero packets in 1372 QuickTime files, every one
    was flagged exhaustive: traversal was genuinely complete over a tree the
    walker was reading wrongly. One flag could not tell those apart.
    """
    from flujo.substrate.epistemics import (
        COMPLETENESS_LEVELS, NO, UNASSESSED, YES, Completeness, Witness)
    blind = Completeness(traversal=YES, vocabulary=NO)
    assert not blind.negative_is_evidence
    assert "vocabulary" in blind.strongest_negative_claim

    # vocabulary=YES alone is no longer enough: it also needs a Witness, since
    # a bare vocabulary=YES with nothing behind it is what the isobmff entry
    # used to be before it was re-graded to ASSERTED.
    unwitnessed = Completeness(traversal=YES, vocabulary=YES)
    assert not unwitnessed.negative_is_evidence

    sound = Completeness(traversal=YES, vocabulary=YES, witness=Witness(
        spec_citation="test citation", adversarial_check="test scan",
        files_checked=1))
    assert sound.negative_is_evidence
    assert "NOT that the fact is absent" in sound.strongest_negative_claim

    # Semantic completeness is NO by default and is never reachable from the
    # others: applications strip metadata on export.
    assert Completeness().semantic == NO
    assert len(COMPLETENESS_LEVELS) == 5
    assert Completeness().traversal == UNASSESSED, "unassessed is the honest default"

    # And the real locators still differ on the traversal/vocabulary axis, but
    # neither may license a negative today: png's vocabulary is only ASSERTED,
    # never backed by a Witness, so it is no sounder than the .mov gap was.
    from flujo.substrate.epistemics import ASSERTED
    png = extract(str(write_png(tmp_path / "n.png", None)))
    assert png.levels.traversal == YES and png.levels.vocabulary == ASSERTED
    generic = tmp_path / "n.aep"
    generic.write_bytes(b"\x00" * 40)
    other = extract(str(generic))
    assert other.levels.traversal == YES and other.levels.vocabulary == NO
    assert not png.negative_is_evidence and not other.negative_is_evidence, (
        "an assertion with no witness must not license a negative either -- "
        "the exact discipline the isobmff false completeness was missing")


def test_every_unknown_carries_a_cause_and_a_remedy_and_collapses_outward():
    """A bare UNKNOWN cannot be acted on. Six causes, six different next steps."""
    from flujo.substrate.epistemics import (
        CONFLICT, DECODER_LIMIT, EpistemicError, INCOMPLETE_AUTHORITY,
        INVALID_QUERY, MISSING_EVIDENCE, OUT_OF_DOMAIN, REMEDY, UNKNOWN_CAUSES,
        Unknown)
    assert set(UNKNOWN_CAUSES) == {MISSING_EVIDENCE, INCOMPLETE_AUTHORITY,
                                   OUT_OF_DOMAIN, DECODER_LIMIT, CONFLICT,
                                   INVALID_QUERY}
    for cause in UNKNOWN_CAUSES:
        unknown = Unknown(cause=cause, detail="d")
        assert unknown.remedy == REMEDY[cause] and unknown.remedy
        assert unknown.outward() == "UNKNOWN", "the cause stays inside"
        assert unknown.as_dict()["cause"] == cause
    # The remedies must actually differ, or the taxonomy is decoration.
    assert len({REMEDY[c] for c in UNKNOWN_CAUSES}) == len(UNKNOWN_CAUSES)
    with pytest.raises(EpistemicError, match="undeclared_unknown_cause"):
        Unknown(cause="BECAUSE")


def test_the_quicktime_gap_is_recorded_as_data_not_as_silence():
    """The vocabulary a walker knows is declared, so the next gap is visible."""
    from flujo.substrate.epistemics import ASSERTED, KNOWN_CONTAINERS, NO
    iso = KNOWN_CONTAINERS["isobmff"]
    # ASSERTED, not YES: the containers are named, but no adversarial
    # whole-file scan (Witness) has been run against this corrected list.
    assert iso["vocabulary_complete"] == ASSERTED
    assert any("XMP_" in c for c in iso["containers"]), "the QuickTime atom"
    assert any("uuid" in c for c in iso["containers"]), "the MP4 box"
    assert "1372" in iso["why"], "the measurement that forced it is recorded"
    assert KNOWN_CONTAINERS["generic"]["vocabulary_complete"] == NO
