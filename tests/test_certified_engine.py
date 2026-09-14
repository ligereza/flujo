"""Tests for the certified query engine.

The engine's only real bug would be a certificate that is false. Two tests below
attack that directly: one builds a deliberately NON-conservative summary and
requires the soundness audit to catch it, and one runs the audit over the real
corpora and requires zero violations. Everything else pins the guards that the
two audits produced.

Several tests are regressions of specific claims the adversarial pass killed.
They are named for the claim rather than the code, because the thing that must
not come back is the claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flujo.certified import (
    CERTIFIED_NO,
    CERTIFIED_YES,
    UNKNOWN,
    ContractError,
    certify,
    load_contracts,
    refine,
)
from flujo.certified.contracts import (
    DECLARED_3D_FORMATS,
    EXCLUDED_FROM_3D,
    PIPELINE_3D_FORMATS,
    SCENE_FORMATS,
    RULES,
    NOT_WORK_SURFACES,
    WORK_SURFACES,
    rule_for,
)
from flujo.certified.metrics import audit_soundness, provenance_completeness
from flujo.certified.oracle import (
    MONITOR_HETEROGENEITY,
    MONITOR_NEW_AUTHORITY,
    Monitor,
    OracleError,
    OracleRequest,
    ProvisionalFold,
    assert_may_act,
    heterogeneity_signal,
    oracle_queue,
    record_answer,
    validate_fold,
)
from flujo.certified.summary import (
    CERTIFIED_DISTINCT,
    CERTIFIED_EQUIVALENT,
    POLICY_CLAIM,
    UNRESOLVED,
    WORLD_CLAIM,
    Summary,
    empty,
    from_member,
    join_all,
)
from flujo.certified.tree import TreeNode, _normalise_title

REPO = Path(__file__).resolve().parents[1]


def _leaf(scope, *, exts=(), authorities=("ssd_index_extensions", "ssd_index_paths"),
          props=(), root="ROOT", bytes_=0):
    props = list(props)
    if set(exts) & DECLARED_3D_FORMATS:
        props.append("has_3d_format")
    return TreeNode(
        scope=scope,
        summary=from_member(scope, authorities_covering=authorities,
                            sets={"extension": set(exts), "container_root": {root}},
                            properties=props, provenance={"test"}),
        payload={"bytes": bytes_},
    )


def _group(scope, children):
    return TreeNode(scope=scope,
                    summary=join_all((c.summary for c in children), scope=scope),
                    children=list(children))


# ----------------------------------------------------------- the summary algebra

def test_the_join_is_a_semilattice():
    a = _leaf("a", exts=(".blend",)).summary
    b = _leaf("b", exts=(".png",)).summary
    c = _leaf("c", exts=(".aep",)).summary
    left = a.join(b, scope="x").join(c, scope="x")
    right = a.join(b.join(c, scope="x"), scope="x")
    assert left.sets["extension"] == right.sets["extension"]
    assert left.n_members == right.n_members == 3
    assert (a.join(b, scope="x").sets["extension"]
            == b.join(a, scope="x").sets["extension"])
    once = a.join(a, scope="x")
    assert once.sets["extension"] == a.sets["extension"], "union is idempotent"


def test_an_empty_group_never_claims_a_vacuous_universal():
    """`all` over nothing must be undecided, not True."""
    assert empty("nowhere").all("has_3d_format") is None
    assert not empty("nowhere").complete_for("ssd_index_extensions")


def test_partial_coverage_is_visible_and_counted():
    covered = _leaf("a", exts=(".blend",))
    uncovered = _leaf("b", exts=(".png",), authorities=("ssd_index_paths",))
    group = _group("g", [covered, uncovered])
    assert group.summary.complete_for("ssd_index_paths")
    assert not group.summary.complete_for("ssd_index_extensions")
    assert group.summary.uncovered("ssd_index_extensions") == 1


# --------------------------------------------------------- the completeness veto

def test_a_negative_over_partial_coverage_becomes_unknown():
    """The single guard: absence of evidence is not evidence of absence.

    Two members with no 3D format, but the extension authority only reached one
    of them. The uncovered member could carry anything, so the negative is void.
    """
    contracts = load_contracts()
    seen = _leaf("a", exts=(".png",))
    unseen = _leaf("b", exts=(), authorities=("ssd_index_paths",))
    group = _group("g", [seen, unseen])

    cert = certify(contracts["q2_dimension"], group.summary)
    assert cert.verdict == UNKNOWN
    assert cert.vetoed, "the veto must be recorded, not silently applied"
    assert "1 uncovered member" in cert.reason

    # With full coverage the same shape certifies.
    full = _group("g2", [seen, _leaf("c", exts=(".jpg",))])
    assert certify(contracts["q2_dimension"], full.summary).verdict == CERTIFIED_NO


def test_a_certificate_says_whether_it_answered_the_question_or_the_predicate():
    """Never silently answer Q with P."""
    contracts = load_contracts()
    group = _group("g", [_leaf("a", exts=(".png",)), _leaf("b", exts=(".jpg",))])
    cert = certify(contracts["q2_dimension"], group.summary)
    assert cert.verdict == CERTIFIED_NO
    assert cert.answers == "P", "a CORPUS_CLAIM is a narrowing of the question"
    assert not cert.is_about_the_world
    assert cert.predicate != cert.question
    assert "declared 3D set" in cert.reason


# ------------------------------------------------------------------- SOUNDNESS

def test_a_non_conservative_summary_is_caught():
    """The test the whole engine rests on.

    A parent whose summary UNDERSTATES its children is exactly the failure the
    conservative discipline exists to prevent. Here the parent is built by hand
    to forget a child's 3D format, so it certifies NO while a member certifies
    YES. The audit must find it; if it cannot, no other result here means
    anything.
    """
    contracts = load_contracts()
    honest = _leaf("bad/child", exts=(".blend",))
    liar = TreeNode(
        scope="bad",
        # Same member count, same coverage -- but the extension set has been
        # emptied, so the summary is no longer an over-approximation.
        summary=Summary(scope="bad", n_members=1,
                        covered={"ssd_index_extensions": 1, "ssd_index_paths": 1},
                        sets={"extension": frozenset(), "container_root": frozenset({"ROOT"})},
                        counts={}, provenance=frozenset({"test"})),
        children=[honest],
    )
    assert certify(contracts["q2_dimension"], liar.summary).verdict == CERTIFIED_NO
    assert certify(contracts["q2_dimension"], honest.summary).verdict == CERTIFIED_YES

    report = audit_soundness(liar, contracts["q2_dimension"])
    assert not report.sound
    assert len(report.violations) == 1
    violation = report.violations[0]
    assert violation.node_verdict == CERTIFIED_NO
    assert violation.member_verdict == CERTIFIED_YES
    assert violation.member_scope == "bad/child"


def test_an_honest_tree_audits_clean():
    contracts = load_contracts()
    tree = _group("g", [_leaf("g/a", exts=(".png",)), _leaf("g/b", exts=(".jpg",)),
                        _group("g/sub", [_leaf("g/sub/c", exts=(".svg",))])])
    report = audit_soundness(tree, contracts["q2_dimension"])
    assert report.sound
    assert report.certificates_checked >= 1
    assert report.members_verified >= 3


def test_refinement_accounts_for_every_member_exactly_once():
    contracts = load_contracts()
    tree = _group("g", [_leaf("g/a", exts=(".blend",)), _leaf("g/b", exts=(".png",))])
    run = refine(tree, contracts["q2_dimension"])
    assert run.members_pruned + run.members_opened == tree.summary.n_members
    assert run.prune_fraction + run.unknown_rate <= 1.0 + 1e-9


# ------------------------------------------- regressions of the killed claims

def test_the_declared_3d_format_set_still_covers_the_corpus():
    """q2's first version used {.blend} and was UNSOUND, not imprecise.

    Measured then: .blend was 70.1% of 3D files and 5 projects held a 3D format
    with no .blend at all, so the negative certificate was false for those 5. If
    a 3D format appears in the index outside the declared set, this fails.
    """
    index = Path("/home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite")
    if not index.is_file():
        pytest.skip("the portable SSD index is not mounted")
    import sqlite3
    con = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    try:
        present = {str(row[0] or "").lower()
                   for row in con.execute("SELECT DISTINCT extension FROM assets")}
    finally:
        con.close()
    # Every extension a 3D or CAD application authors. Kept wider than the
    # declared set on purpose: this is the net, and anything it catches that the
    # declaration missed is a hole in a certificate.
    known_3d = {".blend", ".blend1", ".fbx", ".obj", ".gltf", ".glb", ".abc",
                ".usd", ".usda", ".usdc", ".c4d", ".max", ".ma", ".mb", ".dae",
                ".stl", ".3ds", ".ply", ".lwo", ".x3d", ".sldprt", ".step",
                ".stp", ".iges", ".igs", ".skp", ".3dm", ".vrm", ".vdb", ".mtl",
                ".spp", ".lxo", ".off", ".3mf", ".amf", ".ifc", ".dwg", ".dxf"}
    escaped = (present & known_3d) - DECLARED_3D_FORMATS
    assert not escaped, (
        f"3D formats present in the corpus but absent from the declared set: "
        f"{sorted(escaped)}. A negative certificate on q2 is UNSOUND until they "
        "are declared.")


def test_the_excluded_image_formats_stay_excluded():
    """.exr and .hdr are images, and a 2D pipeline emits them too.

    Measured presence: .exr 6835 assets, .hdr 9. Adding them because they "look
    3D" would break q2's POSITIVE certificate instead of its negative, which is
    the opposite failure and just as wrong.
    """
    assert not (DECLARED_3D_FORMATS & EXCLUDED_FROM_3D)
    assert ".exr" in EXCLUDED_FROM_3D and ".hdr" in EXCLUDED_FROM_3D
    assert SCENE_FORMATS and PIPELINE_3D_FORMATS
    assert not (SCENE_FORMATS & PIPELINE_3D_FORMATS), (
        "a format is either a scene file or pipeline data, not both")
    assert DECLARED_3D_FORMATS == SCENE_FORMATS | PIPELINE_3D_FORMATS


def test_the_authorship_negative_stays_dead():
    """q11 was reported as the strongest certificate. It is A in one direction.

    Absence of a Python environment marker is nowhere near 'this is mine':
    measured on the real disk, blenderkit contributes 138 assets and downloaded
    asset folders 173, none inside a virtual environment.
    """
    contracts = load_contracts()
    outside = _group("g", [_leaf("g/a", authorities=("pep_405_environment_marker",)),
                           _leaf("g/b", authorities=("pep_405_environment_marker",))])
    cert = certify(contracts["q11_authored"], outside.summary)
    assert cert.verdict == UNKNOWN, "the negative direction must never certify"
    assert "NOT evidence of own authorship" in cert.reason

    inside = _group("g2", [
        _leaf("g2/a", authorities=("pep_405_environment_marker",),
              props=("in_virtualenv",)),
        _leaf("g2/b", authorities=("pep_405_environment_marker",),
              props=("in_virtualenv",))])
    positive = certify(contracts["q11_authored"], inside.summary)
    assert positive.verdict == CERTIFIED_YES
    assert positive.claim_type == WORLD_CLAIM


def test_the_application_certificate_is_typed_as_policy_not_fact():
    """q6 was the falsely solid one: '2026 of 2034 out with one boolean'.

    True by construction, because we defined eligibility as requiring the
    statement. The world claim -- that the work cannot be used -- is false.
    """
    contracts = load_contracts()
    contract = contracts["q6_application"]
    assert contract.claim_type == POLICY_CLAIM
    group = _group("g", [_leaf("g/a", authorities=("iskvw_archive_fields",)),
                         _leaf("g/b", authorities=("iskvw_archive_fields",))])
    cert = certify(contract, group.summary)
    assert cert.verdict == CERTIFIED_NO
    assert cert.answers == "P"
    assert not cert.is_about_the_world
    assert "POLICY CLAIM" in cert.reason
    assert "state of the record" in cert.reason


def test_a_date_hull_over_mixed_sources_refuses():
    """Measured: all 330 files in the `other` surface share a 55 second mtime
    window written by one export. A hull over mixed sources certifies nothing."""
    contracts = load_contracts()
    released = from_member("a", authorities_covering=("artist_discography",),
                           values={"date": (100.0, "artist_discography")})
    stamped = from_member("b", authorities_covering=("filesystem_mtime",),
                          values={"date": (101.0, "filesystem_mtime")})
    mixed = released.join(stamped, scope="g")
    cert = certify(contracts["q7_shown_when"], mixed, {"window": (500.0, 600.0)})
    assert cert.verdict == UNKNOWN
    assert "mixes sources" in cert.reason

    pure = released.join(
        from_member("c", authorities_covering=("artist_discography",),
                    values={"date": (110.0, "artist_discography")}), scope="g")
    ok = certify(contracts["q7_shown_when"], pure, {"window": (500.0, 600.0)})
    assert ok.verdict == CERTIFIED_NO


def test_a_single_undated_member_voids_the_date_negative():
    contracts = load_contracts()
    dated = from_member("a", authorities_covering=("artist_discography",),
                        values={"date": (100.0, "artist_discography")})
    undated = from_member("b", authorities_covering=("artist_discography",),
                          properties=("undated",))
    group = dated.join(undated, scope="g")
    cert = certify(contracts["q7_shown_when"], group, {"window": (500.0, 600.0)})
    assert cert.verdict == UNKNOWN
    assert "could fall anywhere" in cert.reason


def test_an_unresolved_name_voids_the_track_negative():
    contracts = load_contracts()
    resolved = from_member("a", authorities_covering=("artist_discography",),
                           sets={"track_id": {"NEBULA"}})
    unresolved = from_member("b", authorities_covering=("artist_discography",),
                             properties=("unmatched_name",))
    group = resolved.join(unresolved, scope="g")
    cert = certify(contracts["q3_track"], group, {"track": "Pasajero"})
    assert cert.verdict == UNKNOWN
    assert "never resolved" in cert.reason


def test_the_undecidable_queries_only_ever_abstain():
    """q8, q9, q10 and q13 have no predicate, and no summary may change that."""
    contracts = load_contracts()
    rich = _group("g", [_leaf("g/a", exts=(".blend", ".aep", ".svg"), bytes_=10**10),
                        _leaf("g/b", exts=(".png",), bytes_=10**9)])
    for cid in ("q8_concept", "q9_rig", "q10_delivered", "q13_record_kind"):
        cert = certify(contracts[cid], rich.summary)
        assert cert.verdict == UNKNOWN, f"{cid} produced a certificate"
        assert not contracts[cid].decidable
        assert cert.answers == "P"


def test_every_contract_has_a_rule_and_every_rule_a_contract():
    contracts = load_contracts()
    assert set(RULES) == set(contracts), (
        f"declared but unimplemented: {sorted(set(contracts) - set(RULES))}; "
        f"implemented but undeclared: {sorted(set(RULES) - set(contracts))}")
    for cid in contracts:
        assert callable(rule_for(cid))
    with pytest.raises(ContractError, match="no_rule_for_contract"):
        rule_for("q99_invented")


def test_the_surface_sets_do_not_overlap():
    assert not (WORK_SURFACES & NOT_WORK_SURFACES)


def test_the_operator_words_survive_as_values_not_identifiers():
    """The domain words stay where a human reads them, in the contract file."""
    text = (REPO / "data" / "certified_queries.json").read_text(encoding="utf-8")
    assert "obra" in text and "registro" in text


def test_track_normalisation_handles_the_real_cases():
    assert _normalise_title("MERECEDORA") == _normalise_title("La Merecedora")
    assert _normalise_title("01 CDR.mov") == "cdr"
    assert _normalise_title("  NEBULA  ") == "nebula"


# ------------------------------------------------- the oracle and the residue

def test_a_fold_may_not_claim_certified_equivalence():
    with pytest.raises(OracleError, match="may_not_claim_certified_equivalence"):
        validate_fold(ProvisionalFold(
            scope="stories", contract_id="q13_record_kind",
            epistemic_state=CERTIFIED_EQUIVALENT, n_members=5899,
            residue=("id", "surface", "month"), missing_authority="text_presence",
            reopen_when=("a detector exists",),
            monitors=(Monitor(MONITOR_HETEROGENEITY, ("bytes",)),)))


def test_a_fold_without_residue_or_a_named_gap_is_refused():
    base = dict(scope="stories", contract_id="q13_record_kind",
                epistemic_state=UNRESOLVED, n_members=5899,
                reopen_when=("a detector exists",),
                monitors=(Monitor(MONITOR_HETEROGENEITY, ("bytes",)),))
    with pytest.raises(OracleError, match="needs_residue"):
        validate_fold(ProvisionalFold(residue=(), missing_authority="text_presence",
                                      **base))
    with pytest.raises(OracleError, match="must_name_the_authority_it_lacks"):
        validate_fold(ProvisionalFold(residue=("id",), missing_authority="", **base))


def test_a_monitor_built_on_the_missing_feature_is_refused():
    """The circularity that fails silently.

    A fold forced by the absence of text detection cannot be watched BY text
    detection: the monitor could never fire, the residue would stay intact and
    useless, and the fold would harden into a fact by attrition.
    """
    with pytest.raises(OracleError, match="circular_monitor"):
        validate_fold(ProvisionalFold(
            scope="stories", contract_id="q13_record_kind",
            epistemic_state=UNRESOLVED, n_members=5899,
            residue=("id", "surface", "month"), missing_authority="text_presence",
            reopen_when=("a detector exists",),
            monitors=(Monitor(MONITOR_HETEROGENEITY, ("text_presence",)),)))


def test_a_well_formed_fold_passes_and_needs_a_monitor():
    good = ProvisionalFold(
        scope="stories", contract_id="q13_record_kind", epistemic_state=UNRESOLVED,
        n_members=5899, residue=("media_id", "surface", "yyyymm"),
        missing_authority="text_presence",
        reopen_when=("a text detector with a measured hit rate exists",),
        monitors=(Monitor(MONITOR_HETEROGENEITY, ("bytes", "duration")),
                  Monitor(MONITOR_NEW_AUTHORITY, ("authority_registry",))))
    validate_fold(good)
    assert good.as_dict()["may_license_irreversible_action"] is False
    with pytest.raises(OracleError, match="needs_at_least_one_monitor"):
        validate_fold(ProvisionalFold(
            scope="s", contract_id="q13_record_kind", epistemic_state=UNRESOLVED,
            n_members=2, residue=("id",), missing_authority="text_presence",
            reopen_when=(), monitors=()))


def test_no_irreversible_action_rests_on_an_uncertified_state():
    """Residue restores knowledge. It does not restore deleted bytes."""
    for action in ("delete", "publish", "deduplicate", "send", "overwrite"):
        with pytest.raises(OracleError, match="irreversible_action"):
            assert_may_act(UNRESOLVED, action)
        with pytest.raises(OracleError, match="irreversible_action"):
            assert_may_act(CERTIFIED_DISTINCT, action)
        assert_may_act(CERTIFIED_EQUIVALENT, action)
    assert_may_act(UNRESOLVED, "read")


def test_an_answer_must_be_signed_scoped_and_reasoned():
    request = OracleRequest(
        contract_id="q13_record_kind", question="obra o registro emocional?",
        scope="stories/202510", n_members=120, why_unresolved="no detector",
        missing_authority="text_presence", settles_members=120)
    with pytest.raises(OracleError, match="needs_an_actor"):
        record_answer(request, "registro emocional", actor=" ", reason="r",
                      recorded_at="2026-08-23")
    with pytest.raises(OracleError, match="needs_a_reason"):
        record_answer(request, "registro emocional", actor="mak", reason="",
                      recorded_at="2026-08-23")
    evidence = record_answer(request, "registro emocional", actor="mak",
                             reason="reviewed the month", recorded_at="2026-08-23")
    assert evidence.authority == "operator_attestation"
    assert evidence.scope == "stories/202510"
    assert evidence.as_dict()["actor"] == "mak"


def test_the_oracle_asks_high_and_never_below_its_floor():
    contracts = load_contracts()
    tree = _group("g", [
        _group("g/x", [_leaf("g/x/a", authorities=("pep_405_environment_marker",)),
                       _leaf("g/x/b", authorities=("pep_405_environment_marker",))]),
        _leaf("g/c", authorities=("pep_405_environment_marker",)),
    ])
    requests = oracle_queue(tree, contracts["q11_authored"], min_members=2)
    assert requests, "an unresolved tree should produce at least one request"
    assert requests[0].scope == "g", "the shallowest unresolved node comes first"
    assert all(r.n_members >= 2 for r in requests)
    assert requests[0].missing_authority


def test_heterogeneity_never_concludes():
    """The channel that would have caught the dimensionality failure.

    774 rows marked 3d averaged 0.11 GB while 25 mixed rows averaged 20 GB: a
    180x spread inside one declared class, unchallenged for months.
    """
    wide = _group("g", [_leaf(f"g/{i}", bytes_=b) for i, b in
                        enumerate([1, 1, 2, 2, 3, 10_000])])
    signal = heterogeneity_signal(wide)
    assert signal["signal"] is True
    assert signal["status"] == "SUSPICION_ONLY"
    assert signal["spread"] >= 20.0

    tight = _group("g2", [_leaf(f"g2/{i}", bytes_=b) for i, b in
                          enumerate([10, 11, 12, 13, 14, 15])])
    assert heterogeneity_signal(tight)["signal"] is False
    assert heterogeneity_signal(_group("g3", [_leaf("g3/a", bytes_=1)]))["signal"] is False


def test_provenance_is_complete_on_a_built_tree():
    tree = _group("g", [_leaf("g/a", exts=(".png",)), _leaf("g/b", exts=(".jpg",))])
    report = provenance_completeness(tree)
    assert report["provenance_complete"]
    assert report["members"] == 2
    assert "ssd_index_extensions" in report["complete_authorities"]


def test_the_contract_file_and_the_registry_agree_on_authorities():
    """Every authority a contract names must be declared where authorities live."""
    registry = json.loads(
        (REPO / "data" / "ordering_features.json").read_text(encoding="utf-8"))
    declared = set(registry["authorities"])
    # Authorities introduced by this engine, each documented in the contract file.
    engine_local = {
        "ssd_index_paths", "ssd_index_extensions", "operator_container_map",
        "declared_3d_formats", "ig_export_surfaces", "operator_surface_rule",
        "iskvw_archive_fields", "ig_export_month_folders", "filesystem_mtime",
        "resolume_screen_setups", "declared_entity_roles",
    }
    contracts = load_contracts()
    used = {name for c in contracts.values() for name in c.authorities}
    unknown = used - declared - engine_local
    assert not unknown, (
        f"contracts name authorities that are neither in ordering_features.json "
        f"nor declared as engine-local: {sorted(unknown)}")
