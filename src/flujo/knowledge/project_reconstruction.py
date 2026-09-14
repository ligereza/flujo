"""Reconstruct latent creative project units from the read-only SSD index.

The bounded folder scan that produced the index answers a different question
than the one Curatoria and Postulacion need. It asks "which folders contain an
editable anchor" and calls each answer a project. Measured on the real index
(``archivo_index.sqlite``, 917 project rows, 45536 assets): 758 of those rows
(82.7%) are a single library item, because a downloaded material or model ships
its own folder with one ``.blend`` inside. A funding draft built from that row
describes a purchased texture, not a work.

This module reconstructs project units over those rows. It never rewrites the
source: it reads, derives features, and records a decision with the evidence
that produced it.

Why a lexicographic cascade and not a score
-------------------------------------------
A single scalar would let a large byte count outvote the fact that a folder is a
dependency, and the magnitudes are not comparable: "82.7% of rows carry a uuid
leaf under assets/" is a structural signature, while "has video" is a media mix.
Adding them asserts an exchange rate nobody measured. The cascade instead asks
ranked yes/no questions whose predicates are individually falsifiable, and
abstains when two rules of the same rank disagree.

What the evidence can and cannot prove
--------------------------------------
``full_sha256`` exists for 112 of 45536 assets, so exact duplication is provable
for 0.25% of the index. ``sample_sha256`` exists for all of them but a sample is
not an identity: two files can agree on a sample and differ in full content.
Therefore a shared sample hash never decides project identity here; it produces
an explicit tie with both alternatives preserved.

Separation of layers, kept in the persisted record:

- RAW INPUT       a row of the index
- OBSERVATION     a path, an extension, a byte count, an mtime
- DERIVED FEATURE a computed predicate such as "leaf ends in a uuid"
- RELATION        "this folder depends on that library item"
- INTERPRETATION  "DREFGIRA is a fundable work" -- never produced here
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ._contract_helpers import compact_json as stable_json

CONTRACT = "mak-project-reconstruction-v1"
ALGORITHM_VERSION = "lexicographic-role-cascade-1"

# Epistemic labels. VERIFIED_CONTROLLED_CASE is reserved for the synthetic
# ground-truth cases in the test suite; real-index decisions are EMPIRICAL at
# best, because the index is an observation of a disk we cannot re-derive.
VERIFIED_CONTROLLED_CASE = "VERIFIED_CONTROLLED_CASE"
EMPIRICAL = "EMPIRICAL"
COUNTEREXAMPLE = "COUNTEREXAMPLE"
HYPOTHESIS = "HYPOTHESIS"
UNKNOWN = "UNKNOWN"

ROLE_PROJECT_UNIT = "project_unit"
ROLE_SUBPROJECT = "subproject"
ROLE_LIBRARY_DEPENDENCY = "library_dependency"
ROLE_SHARED_RESOURCE = "shared_resource"
ROLE_EXPORTED_PRODUCT = "exported_product"
ROLE_UNDECIDED = "undecided"

# The relation vocabulary, and the inverse of each one.
#
# Direction carries meaning here: "the work depends on this purchased texture"
# and "this purchased texture depends on the work" are opposite claims, and the
# second one would make a library item look like a project. A projector that
# re-anchors an edge at its other endpoint therefore has to say the inverse
# predicate, not the same one.
#
# Measured on the real LYON reconstruction: 24 ``contains`` edges at the source
# became 56 in the persisted graph, half of them pointing backwards, because
# ``reconstruction_adapter`` kept the predicate while swapping the endpoints.
# Nothing caught it for the plainest possible reason -- the vocabulary had one
# producer, zero consumers and zero tests, so no code had ever read an edge.
#
# A symmetric relation is its own inverse and says so explicitly. Anything not
# listed here has no declared direction, and ``inverse_relation`` refuses rather
# than guessing: a silent guess is how the first inversion survived.
REL_CONTAINS = "contains"
REL_CONTAINED_BY = "contained_by"
REL_DEPENDS_ON = "depends_on"
REL_DEPENDED_ON_BY = "depended_on_by"
REL_SHARED_RESOURCE = "shared_resource"
REL_SHARED_RESOURCE_OF = "shared_resource_of"
REL_SHARES_LIBRARY_WITH = "shares_library_with"
REL_UNRELATED = "unrelated"
REL_IDENTITY_UNDECIDED = "identity_undecided"

RELATION_INVERSES: dict[str, str] = {
    REL_CONTAINS: REL_CONTAINED_BY,
    REL_CONTAINED_BY: REL_CONTAINS,
    REL_DEPENDS_ON: REL_DEPENDED_ON_BY,
    REL_DEPENDED_ON_BY: REL_DEPENDS_ON,
    # Directed: one owner uses this resource folder.
    REL_SHARED_RESOURCE: REL_SHARED_RESOURCE_OF,
    REL_SHARED_RESOURCE_OF: REL_SHARED_RESOURCE,
    # Symmetric: a statement about a pair of container roots, not about an owner.
    # This one used to be spelled ``shared_resource`` as well, which made the
    # predicate mean two different things in one vocabulary and left direction
    # unrecoverable from the name.
    REL_SHARES_LIBRARY_WITH: REL_SHARES_LIBRARY_WITH,
    REL_UNRELATED: REL_UNRELATED,
    REL_IDENTITY_UNDECIDED: REL_IDENTITY_UNDECIDED,
}

SYMMETRIC_RELATIONS = frozenset(
    name for name, inverse in RELATION_INVERSES.items() if name == inverse)


class UnknownRelationError(ValueError):
    """A relation was projected without a declared inverse."""


def inverse_relation(predicate: str) -> str:
    """The predicate that states the same fact from the other endpoint."""
    try:
        return RELATION_INVERSES[predicate]
    except KeyError:
        raise UnknownRelationError(f"relation_without_inverse: {predicate}") from None

# A uuid4 tail is how the asset browsers that MAK actually uses name a
# downloaded item's folder. Measured: 758 rows carry one, and every single one
# of them also sits under an ``assets/<kind>/`` segment -- the two predicates
# coincide exactly, which is why neither is used alone.
UUID_TAIL = re.compile(
    r"_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
ASSETS_SEGMENT = re.compile(r"(?:^|/)assets/([^/]+)/")
CACHE_SEGMENT = re.compile(r"(?:^|/)caches?(?:/|$)", re.IGNORECASE)

# Media kinds that a delivered export is made of, as named by the index.
OUTPUT_MEDIA = frozenset({"video", "image"})
EXPORT_MEDIA_SHARE = 0.8


def _fingerprint_file(path: Path, *, chunk: int = 1 << 20) -> str:
    """Hash the index file itself so a run can be tied to its input.

    The index is 168 MiB, which is cheap. The 940 GB it references is not, and
    is never hashed here.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Evidence:
    """One named, checkable reason. ``kind`` keeps the layers separate."""

    name: str
    kind: str  # observation | derived_feature | relation | human_attestation
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "kind": self.kind, "detail": self.detail}


@dataclass
class RowFeatures:
    """Derived features for one baseline row. Every field is computed, not read."""

    project_id: str
    project_path: str
    container_root: str
    asset_count: int
    anchor_count: int
    bytes_total: int
    dimensionality: str
    depth: int
    leaf: str
    uuid_token: str | None
    assets_kind: str | None
    parent_path: str | None
    media_mix: dict[str, int] = field(default_factory=dict)
    cache_asset_count: int = 0
    non_cache_asset_count: int = 0
    uuid_shared_roots: tuple[str, ...] = ()

    @property
    def output_media_share(self) -> float:
        total = sum(self.media_mix.values())
        if not total:
            return 0.0
        return sum(c for k, c in self.media_mix.items() if k in OUTPUT_MEDIA) / total


@dataclass
class Decision:
    """The classification of one row, with what argued for and against it."""

    project_path: str
    role: str
    epistemic_status: str
    rule: str
    evidence_for: list[Evidence] = field(default_factory=list)
    evidence_against: list[Evidence] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    tie_breaker_needed: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_path": self.project_path,
            "role": self.role,
            "epistemic_status": self.epistemic_status,
            "rule": self.rule,
            "evidence_for": [e.as_dict() for e in self.evidence_for],
            "evidence_against": [e.as_dict() for e in self.evidence_against],
            "alternatives": list(self.alternatives),
            **({"tie_breaker_needed": self.tie_breaker_needed}
               if self.tie_breaker_needed else {}),
        }


@dataclass
class UnitRelation:
    left: str
    relation: str
    right: str
    epistemic_status: str
    evidence_for: list[Evidence] = field(default_factory=list)
    evidence_against: list[Evidence] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    tie_breaker_needed: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "relation": self.relation,
            "right": self.right,
            "epistemic_status": self.epistemic_status,
            "evidence_for": [e.as_dict() for e in self.evidence_for],
            "evidence_against": [e.as_dict() for e in self.evidence_against],
            "alternatives": list(self.alternatives),
            **({"tie_breaker_needed": self.tie_breaker_needed}
               if self.tie_breaker_needed else {}),
        }


def _parent_of(path: str, known: Sequence[str]) -> str | None:
    """Nearest strict ancestor among the baseline rows, by path segments."""
    best: str | None = None
    for candidate in known:
        if candidate == path:
            continue
        if path.startswith(candidate + "/"):
            if best is None or len(candidate) > len(best):
                best = candidate
    return best


def derive_features(
    rows: Sequence[Mapping[str, Any]],
    members: Mapping[str, list[Mapping[str, Any]]],
    uuid_roots: Mapping[str, set[str]],
) -> dict[str, RowFeatures]:
    """Compute the derived layer for every baseline row in scope."""
    paths = [str(r["project_path"]) for r in rows]
    features: dict[str, RowFeatures] = {}
    for row in rows:
        path = str(row["project_path"])
        leaf = path.rsplit("/", 1)[-1]
        tail = UUID_TAIL.search(leaf)
        uuid_token = tail.group(0)[1:] if tail else None
        kind_match = ASSETS_SEGMENT.search(path)
        assets_kind = kind_match.group(1) if kind_match else None
        row_members = members.get(str(row["project_id"]), [])
        media: dict[str, int] = {}
        cached = 0
        for member in row_members:
            media[str(member["media_kind"])] = media.get(str(member["media_kind"]), 0) + 1
            relative = str(member["relative_path"])
            tail_path = relative[len(path):] if relative.startswith(path) else relative
            if CACHE_SEGMENT.search(tail_path):
                cached += 1
        features[path] = RowFeatures(
            project_id=str(row["project_id"]),
            project_path=path,
            container_root=str(row["container_root"]),
            asset_count=int(row["asset_count"]),
            anchor_count=int(row["anchor_count"]),
            bytes_total=int(row["bytes"]),
            dimensionality=str(row["dimensionality"]),
            depth=path.count("/") + 1,
            leaf=leaf,
            uuid_token=uuid_token,
            assets_kind=assets_kind,
            parent_path=_parent_of(path, paths),
            media_mix=media,
            cache_asset_count=cached,
            non_cache_asset_count=len(row_members) - cached,
            uuid_shared_roots=tuple(sorted(uuid_roots.get(uuid_token, set())))
            if uuid_token else (),
        )
    return features


def classify_row(feature: RowFeatures) -> Decision:
    """Rank the questions; the first rank that answers decides.

    Rank 1  a library item, and whether it is shared across containers
    Rank 2  a delivered export with no editable source of its own
    Rank 3  a subproject of a row above it
    Rank 4  a project unit in its own right

    A row that carries the library signature but also carries editable material
    outside its cache directories is a genuine tie and is left UNDECIDED.
    """
    library_signature = bool(feature.uuid_token) and feature.assets_kind is not None
    signature_evidence = [
        Evidence("uuid_leaf", "derived_feature",
                 f"leaf {feature.leaf!r} ends in a uuid4 tail"),
        Evidence("assets_segment", "derived_feature",
                 f"path sits under assets/{feature.assets_kind}/"),
        Evidence("single_anchor", "observation",
                 f"anchor_count={feature.anchor_count}"),
    ]

    if library_signature:
        # A library item may drag hundreds of baked cache frames with it; the
        # anchor count is what stays at one. Measured on the real index: four
        # rows carry 61-301 assets and still exactly one anchor, and every extra
        # asset is a .vdb or .uni under caches/.
        if feature.anchor_count == 1 and feature.non_cache_asset_count <= 1:
            if len(feature.uuid_shared_roots) > 1:
                return Decision(
                    feature.project_path, ROLE_SHARED_RESOURCE, EMPIRICAL,
                    rule="R1b_shared_library_item",
                    evidence_for=signature_evidence + [
                        Evidence("uuid_across_containers", "derived_feature",
                                 "same uuid token indexed under container roots "
                                 + ", ".join(feature.uuid_shared_roots))],
                    evidence_against=[
                        Evidence("no_exclusive_owner", "derived_feature",
                                 "presence in several containers argues against "
                                 "exclusive membership in any of them")],
                )
            return Decision(
                feature.project_path, ROLE_LIBRARY_DEPENDENCY, EMPIRICAL,
                rule="R1a_library_item",
                evidence_for=signature_evidence,
            )
        if feature.anchor_count == 1 and feature.non_cache_asset_count > 1:
            return Decision(
                feature.project_path, ROLE_UNDECIDED, UNKNOWN,
                rule="R1c_library_signature_with_extra_sources",
                evidence_for=signature_evidence,
                evidence_against=[
                    Evidence("sources_outside_caches", "observation",
                             f"{feature.non_cache_asset_count} assets are not "
                             "under a caches/ segment")],
                alternatives=[ROLE_LIBRARY_DEPENDENCY, ROLE_SUBPROJECT],
                tie_breaker_needed="open the anchor and list its external file "
                                   "references, or obtain an operator attestation",
            )
        return Decision(
            feature.project_path, ROLE_UNDECIDED, UNKNOWN,
            rule="R1d_library_signature_with_several_anchors",
            evidence_for=signature_evidence,
            evidence_against=[
                Evidence("several_anchors", "observation",
                         f"anchor_count={feature.anchor_count} exceeds one")],
            alternatives=[ROLE_LIBRARY_DEPENDENCY, ROLE_SUBPROJECT],
            tie_breaker_needed="an anchor inventory is required before treating "
                               "this folder as a dependency",
        )

    if feature.anchor_count == 0 and feature.asset_count:
        share = feature.output_media_share
        if share >= EXPORT_MEDIA_SHARE:
            return Decision(
                feature.project_path, ROLE_EXPORTED_PRODUCT, EMPIRICAL,
                rule="R2_export_without_source",
                evidence_for=[
                    Evidence("no_anchor", "observation", "anchor_count=0"),
                    Evidence("output_media_dominant", "derived_feature",
                             f"{share:.0%} of assets are video or image"),
                    Evidence("media_mix", "observation", stable_json(feature.media_mix)),
                ],
                evidence_against=[
                    Evidence("source_not_indexed", "derived_feature",
                             "the editable source of this export is not in this "
                             "container; it may exist elsewhere or not at all")],
            )
        return Decision(
            feature.project_path, ROLE_UNDECIDED, UNKNOWN,
            rule="R2b_no_anchor_mixed_media",
            evidence_for=[Evidence("no_anchor", "observation", "anchor_count=0")],
            evidence_against=[
                Evidence("output_media_not_dominant", "derived_feature",
                         f"only {share:.0%} of assets are video or image")],
            alternatives=[ROLE_EXPORTED_PRODUCT, ROLE_PROJECT_UNIT],
            tie_breaker_needed="identify whether an editable source exists in "
                               "another container before naming this a delivery",
        )

    if feature.parent_path:
        return Decision(
            feature.project_path, ROLE_SUBPROJECT, EMPIRICAL,
            rule="R3_subproject_of_indexed_parent",
            evidence_for=[
                Evidence("indexed_ancestor", "derived_feature",
                         f"nearest indexed ancestor is {feature.parent_path!r}"),
                Evidence("own_anchors", "observation",
                         f"anchor_count={feature.anchor_count}"),
                Evidence("outside_assets_tree", "derived_feature",
                         "path carries no assets/<kind>/ segment"),
            ],
            evidence_against=[
                Evidence("containment_is_not_membership", "derived_feature",
                         "folder containment alone does not prove the parent "
                         "authored this material; the subproject stays "
                         "separately addressable")],
        )

    return Decision(
        feature.project_path, ROLE_PROJECT_UNIT, EMPIRICAL,
        rule="R4_root_unit",
        evidence_for=[
            Evidence("no_indexed_ancestor", "derived_feature",
                     "no baseline row is a strict ancestor of this path"),
            Evidence("own_anchors", "observation",
                     f"anchor_count={feature.anchor_count}"),
        ],
    )


def _unit_owner(path: str, decisions: Mapping[str, Decision],
                features: Mapping[str, RowFeatures]) -> str | None:
    """Nearest ancestor row (or self) that is a unit or subproject."""
    current: str | None = path
    while current is not None:
        role = decisions[current].role
        if role in {ROLE_PROJECT_UNIT, ROLE_SUBPROJECT, ROLE_EXPORTED_PRODUCT}:
            return current
        current = features[current].parent_path
    return None


@dataclass
class Reconstruction:
    contract: str
    algorithm_version: str
    index_path: str
    index_fingerprint: str
    scope: str
    decisions: dict[str, Decision]
    features: dict[str, RowFeatures]
    relations: list[UnitRelation]
    asset_assignment: dict[str, str]
    unassigned_assets: list[str]
    reconciliation: dict[str, Any]

    def units(self) -> list[str]:
        return [p for p, d in self.decisions.items()
                if d.role in {ROLE_PROJECT_UNIT, ROLE_SUBPROJECT, ROLE_EXPORTED_PRODUCT}]

    def unknowns(self) -> list[Decision]:
        return [d for d in self.decisions.values() if d.epistemic_status == UNKNOWN]

    def summary(self) -> dict[str, Any]:
        roles: dict[str, int] = {}
        for decision in self.decisions.values():
            roles[decision.role] = roles.get(decision.role, 0) + 1
        return {
            "contract": self.contract,
            "algorithm_version": self.algorithm_version,
            "scope": self.scope,
            "index_fingerprint": self.index_fingerprint,
            "baseline_rows": len(self.decisions),
            "roles": roles,
            "relations": len(self.relations),
            "unknown_decisions": len(self.unknowns()),
            "unknown_relations": sum(1 for r in self.relations
                                     if r.epistemic_status == UNKNOWN),
            "reconciliation": self.reconciliation,
        }


def _load_scope(con: sqlite3.Connection, scope: str) -> list[dict[str, Any]]:
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(
        "SELECT project_id, project_path, container_root, dimensionality, "
        "storage_role, asset_count, bytes, anchor_count, strategy, confidence "
        "FROM projects WHERE project_path = ? OR project_path LIKE ? "
        "ORDER BY project_path", (scope, scope + "/%"))]


def _uuid_root_map(con: sqlite3.Connection) -> dict[str, set[str]]:
    """Which container roots carry each library uuid token.

    This is the identity signal that survives the missing hashes: a uuid token
    naming a downloaded item is stable across copies, so seeing it under two
    container roots is measured reuse rather than an inferred similarity.
    """
    mapping: dict[str, set[str]] = {}
    for path, root in con.execute("SELECT project_path, container_root FROM projects"):
        tail = UUID_TAIL.search(str(path).rsplit("/", 1)[-1])
        if tail:
            mapping.setdefault(tail.group(0)[1:], set()).add(str(root))
    return mapping


def _members_by_row(con: sqlite3.Connection, rows: Sequence[Mapping[str, Any]]
                    ) -> dict[str, list[dict[str, Any]]]:
    con.row_factory = sqlite3.Row
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        out[str(row["project_id"])] = [dict(r) for r in con.execute(
            "SELECT a.asset_id, a.relative_path, a.extension, a.media_kind, "
            "a.bytes, a.mtime_ns, a.full_sha256, a.sample_sha256, m.family_id, "
            "m.member_role FROM project_members m JOIN assets a "
            "ON a.asset_id = m.asset_id WHERE m.project_id = ?",
            (str(row["project_id"]),))]
    return out


def cross_root_relations(con: sqlite3.Connection, scope: str,
                         attestations: Mapping[str, Any] | None = None
                         ) -> list[UnitRelation]:
    """Decide nothing across container roots on name similarity alone.

    Two roots are compared only through measured identity. A shared library uuid
    yields ``shares_library_with``, which is symmetric and says nothing about
    ownership. A shared ``sample_sha256`` without a full hash
    yields an explicit tie, because a sample is not an identity. Name similarity
    on its own yields ``unrelated``.
    """
    con.row_factory = sqlite3.Row
    roots = [str(r[0]) for r in con.execute(
        "SELECT DISTINCT container_root FROM projects")]
    scope_root = scope.split("/", 1)[0]
    if scope_root not in roots:
        return []
    prefix = scope_root.casefold()[:4]
    lexical_neighbours = sorted(
        r for r in roots
        if r != scope_root and r.casefold()[:4] == prefix)
    relations: list[UnitRelation] = []
    attested = (attestations or {}).get("unrelated_roots") or []
    for other in lexical_neighbours:
        shared_uuid = con.execute(
            "SELECT COUNT(DISTINCT a.project_path) FROM projects a JOIN projects b "
            "ON substr(a.project_path, -36) = substr(b.project_path, -36) "
            "WHERE a.container_root = ? AND b.container_root = ? "
            "AND a.project_path LIKE '%-%-%-%-%'", (scope_root, other)).fetchone()[0]
        sample_shared = con.execute(
            "SELECT COUNT(*) FROM assets a JOIN assets b "
            "ON a.sample_sha256 = b.sample_sha256 "
            "WHERE a.relative_path LIKE ? AND b.relative_path LIKE ?",
            (scope_root + "/%", other + "/%")).fetchone()[0]
        full_shared = con.execute(
            "SELECT COUNT(*) FROM assets a JOIN assets b "
            "ON a.full_sha256 = b.full_sha256 AND a.full_sha256 IS NOT NULL "
            "WHERE a.relative_path LIKE ? AND b.relative_path LIKE ?",
            (scope_root + "/%", other + "/%")).fetchone()[0]
        lexical = Evidence("lexical_prefix", "derived_feature",
                           f"{scope_root!r} and {other!r} share the prefix "
                           f"{prefix!r}, which proves nothing about identity")
        pair_key = f"{scope_root}|{other}"
        if pair_key in attested or f"{other}|{scope_root}" in attested:
            relations.append(UnitRelation(
                scope_root, REL_UNRELATED, other, EMPIRICAL,
                evidence_for=[lexical, Evidence(
                    "operator_attestation", "human_attestation",
                    "the operator declared these to be different commissions")],
                evidence_against=[Evidence(
                    "shared_sample_hashes", "observation",
                    f"{sample_shared} asset pairs share a sample hash")]
                if sample_shared else [],
            ))
            continue
        if shared_uuid:
            relations.append(UnitRelation(
                scope_root, REL_SHARES_LIBRARY_WITH, other, EMPIRICAL,
                evidence_for=[Evidence(
                    "shared_library_uuid", "derived_feature",
                    f"{shared_uuid} library uuid tokens are indexed under both "
                    "roots, which is reuse of a purchased item")],
                evidence_against=[Evidence(
                    "reuse_is_not_identity", "derived_feature",
                    "a shared library item does not make two commissions one "
                    "project")],
            ))
            continue
        if sample_shared and not full_shared:
            relations.append(UnitRelation(
                scope_root, REL_IDENTITY_UNDECIDED, other, UNKNOWN,
                evidence_for=[Evidence(
                    "shared_sample_hash", "observation",
                    f"{sample_shared} asset pairs share a sample_sha256")],
                evidence_against=[
                    lexical,
                    Evidence("no_full_hash", "observation",
                             "no full_sha256 is available for those assets, so "
                             "the shared sample is not proof of identity"),
                ],
                alternatives=["same_work_under_two_names",
                              "two_commissions_sharing_branding_assets"],
                tie_breaker_needed="compute full_sha256 for the overlapping "
                                   "assets, or obtain an operator attestation",
            ))
            continue
        relations.append(UnitRelation(
            scope_root, REL_UNRELATED, other, EMPIRICAL,
            evidence_for=[lexical, Evidence(
                "no_measured_identity", "derived_feature",
                "no shared library uuid and no shared asset hash was measured")],
        ))
    return relations


def reconstruct(index_path: str | Path, scope: str, *,
                attestations: Mapping[str, Any] | None = None) -> Reconstruction:
    """Rebuild the project units under ``scope`` without touching the index."""
    path = Path(index_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"index not found: {path}")
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        rows = _load_scope(con, scope)
        if not rows:
            raise ValueError(f"scope has no indexed rows: {scope!r}")
        members = _members_by_row(con, rows)
        features = derive_features(rows, members, _uuid_root_map(con))
        decisions = {p: classify_row(f) for p, f in features.items()}
        relations: list[UnitRelation] = []
        for path_key, feature in features.items():
            decision = decisions[path_key]
            if decision.role == ROLE_SUBPROJECT and feature.parent_path:
                relations.append(UnitRelation(
                    feature.parent_path, REL_CONTAINS, path_key, EMPIRICAL,
                    evidence_for=decision.evidence_for,
                    evidence_against=decision.evidence_against))
            elif decision.role in {ROLE_LIBRARY_DEPENDENCY, ROLE_SHARED_RESOURCE}:
                owner = _unit_owner(feature.parent_path or "", decisions, features) \
                    if feature.parent_path else None
                if owner:
                    relations.append(UnitRelation(
                        owner,
                        REL_DEPENDS_ON if decision.role == ROLE_LIBRARY_DEPENDENCY
                        else REL_SHARED_RESOURCE,
                        path_key, decision.epistemic_status,
                        evidence_for=decision.evidence_for,
                        evidence_against=decision.evidence_against))
        relations.extend(cross_root_relations(con, scope, attestations))

        # Constraint: no asset disappears. Every asset under the scope lands in
        # exactly one bucket, and the totals must reconcile with the index.
        assignment: dict[str, str] = {}
        for row in rows:
            row_path = str(row["project_path"])
            owner = _unit_owner(row_path, decisions, features)
            bucket = owner or f"__{decisions[row_path].role}__"
            for member in members[str(row["project_id"])]:
                assignment[str(member["asset_id"])] = bucket
        total_in_scope = con.execute(
            "SELECT COUNT(*) FROM assets WHERE relative_path = ? "
            "OR relative_path LIKE ?", (scope, scope + "/%")).fetchone()[0]
        unassigned = [r[0] for r in con.execute(
            "SELECT a.asset_id FROM assets a LEFT JOIN project_members m "
            "ON m.asset_id = a.asset_id WHERE m.asset_id IS NULL "
            "AND (a.relative_path = ? OR a.relative_path LIKE ?)",
            (scope, scope + "/%"))]
        reconciliation = {
            "assets_in_scope": int(total_in_scope),
            "assigned": len(assignment),
            "unassigned": len(unassigned),
            "balanced": len(assignment) + len(unassigned) == int(total_in_scope),
        }
        if not reconciliation["balanced"]:
            raise AssertionError(
                "asset reconciliation failed: "
                f"{len(assignment)} assigned + {len(unassigned)} unassigned "
                f"!= {total_in_scope} in scope")
        return Reconstruction(
            contract=CONTRACT, algorithm_version=ALGORITHM_VERSION,
            index_path=str(path), index_fingerprint=_fingerprint_file(path),
            scope=scope, decisions=decisions, features=features,
            relations=relations, asset_assignment=assignment,
            unassigned_assets=unassigned, reconciliation=reconciliation)
    finally:
        con.close()


def baseline_view(index_path: str | Path, scope: str) -> dict[str, Any]:
    """What the existing folder scan reports for the same scope, unchanged.

    Kept so any claim of improvement is measured against the real baseline
    rather than against a description of it.
    """
    path = Path(index_path).expanduser()
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        rows = _load_scope(con, scope)
        single_anchor_under_assets = [
            r for r in rows
            if UUID_TAIL.search(str(r["project_path"]).rsplit("/", 1)[-1])
            and ASSETS_SEGMENT.search(str(r["project_path"]))]
        return {
            "scope": scope,
            "project_rows": len(rows),
            "candidate_projects": [str(r["project_path"]) for r in rows],
            "rows_with_library_signature": len(single_anchor_under_assets),
            "assets_in_scope": con.execute(
                "SELECT COUNT(*) FROM assets WHERE relative_path = ? "
                "OR relative_path LIKE ?", (scope, scope + "/%")).fetchone()[0],
        }
    finally:
        con.close()


def to_payload(reconstruction: Reconstruction) -> dict[str, Any]:
    """Serialize a reconstruction without losing its decision trace."""
    units = [
        {
            "project_id": reconstruction.features[path].project_id,
            "project_path": path,
            "role": decision.role,
            "epistemic_status": decision.epistemic_status,
        }
        for path, decision in sorted(reconstruction.decisions.items())
        if decision.role in {
            ROLE_PROJECT_UNIT, ROLE_SUBPROJECT, ROLE_EXPORTED_PRODUCT
        }
    ]
    return {
        "schema": reconstruction.contract,
        "algorithm_version": reconstruction.algorithm_version,
        "index_path": reconstruction.index_path,
        "index_fingerprint": reconstruction.index_fingerprint,
        "scope": reconstruction.scope,
        "summary": reconstruction.summary(),
        "units": units,
        "decisions": {
            path: decision.as_dict()
            for path, decision in sorted(reconstruction.decisions.items())
        },
        "features": {
            path: asdict(feature)
            for path, feature in sorted(reconstruction.features.items())
        },
        "relations": [relation.as_dict() for relation in reconstruction.relations],
        "asset_assignment": dict(sorted(reconstruction.asset_assignment.items())),
        "unassigned_assets": sorted(reconstruction.unassigned_assets),
    }


def write_payload(reconstruction: Reconstruction, output_dir: str | Path) -> dict[str, str]:
    """Write durable JSON and a small human-inspectable HTML projection."""
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    payload = to_payload(reconstruction)
    json_path = destination / "reconstruction.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = payload["summary"]
    decision_rows = []
    for path, decision in payload["decisions"].items():
        decision_rows.append(
            "<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(path),
                html.escape(decision["role"]),
                html.escape(decision["epistemic_status"]),
                html.escape(decision["rule"]),
            )
        )
    relation_rows = []
    for relation in payload["relations"]:
        relation_rows.append(
            "<tr><td><code>%s</code></td><td>%s</td><td><code>%s</code></td>"
            "<td>%s</td></tr>"
            % (
                html.escape(relation["left"]),
                html.escape(relation["relation"]),
                html.escape(relation["right"]),
                html.escape(relation["epistemic_status"]),
            )
        )
    html_path = destination / "reconstruction.html"
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>MAK reconstruction</title>"
        "<style>body{font:15px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "td,th{border:1px solid #ccc;padding:.4rem;text-align:left}"
        "code{overflow-wrap:anywhere}</style>"
        f"<h1>Project reconstruction: {html.escape(reconstruction.scope)}</h1>"
        f"<p><b>Contract:</b> {html.escape(reconstruction.contract)} · "
        f"<b>Algorithm:</b> {html.escape(reconstruction.algorithm_version)}</p>"
        f"<p><b>Rows:</b> {summary['baseline_rows']} · "
        f"<b>Relations:</b> {summary['relations']} · "
        f"<b>Unknown decisions:</b> {summary['unknown_decisions']} · "
        f"<b>Balanced:</b> {summary['reconciliation']['balanced']}</p>"
        "<h2>Decisions</h2><table><tr><th>Path</th><th>Role</th>"
        "<th>Epistemic status</th><th>Rule</th></tr>"
        + "".join(decision_rows)
        + "</table><h2>Relations</h2><table><tr><th>Left</th><th>Relation</th>"
        "<th>Right</th><th>Status</th></tr>"
        + "".join(relation_rows)
        + "</table>"
        + f"<p>Source index fingerprint: <code>{html.escape(reconstruction.index_fingerprint)}</code></p>",
        encoding="utf-8",
    )
    return {"json": str(json_path), "html": str(html_path)}
