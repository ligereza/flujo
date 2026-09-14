"""Operational propositions and rebuildable membership projections.

The existing :class:`LearningStore` remains the only persistent authority.
This module adds no domain identity for projects or artworks.  It records
propositions such as ``artifact:R member_of unit:A`` as immutable events and
derives a read model from those events.  A proposition is scoped to one
archive and its identity excludes evidence and wall-clock metadata, so new
evidence can update the proposition without changing what was proposed.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from ._contract_helpers import sha256_ref as _hash


SCHEMA = "mak-operational-memberships-v1"
EVENT_SCHEMA = "mak-operational-event-v1"
ALGORITHM_VERSION = "operational-membership-projection-1"
CAPABILITY_SCHEMA = "mak-operational-capabilities-v1"
CAPABILITY_ALGORITHM_VERSION = "operational-capability-projection-1"
CAPABILITIES = tuple(sorted({
    "backup", "execute", "export", "index_code", "ocr", "preview",
    "semantic_search", "transcribe",
}))
CAPABILITY_STATES = frozenset({"possible", "blocked", "unsupported"})

ROLES = frozenset({
    "source", "output", "publication", "resource", "dependency",
    "reference", "documentation", "working_file", "deliverable", "unknown",
})
EVENT_TYPES = frozenset({"PROPOSE", "ACCEPT", "REJECT", "REVOKE", "REOPEN"})
MEMBERSHIP_STATUSES = frozenset({
    "proposed", "accepted", "rejected", "conflicted",
})

_EVENT_FIELDS = {
    "schema", "event_id", "archive_id", "proposition_id", "subject_ref",
    "predicate", "object_ref", "role", "scope_ref", "event_type",
    "evidence_refs", "negative_evidence_refs", "signal_refs", "producer",
    "producer_version", "supersedes_event_id", "caused_by_event_ids",
    "payload", "recorded_at",
}


class OperationalMembershipError(ValueError):
    """Invalid operational event, proposition or projection."""


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationalMembershipError(f"{field}_invalid")
    return value.strip()


def _sorted_refs(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise OperationalMembershipError(f"{field}_invalid")
    result = sorted(set(value))
    if value != result:
        raise OperationalMembershipError(f"{field}_not_sorted_unique")
    return result


def _canonical_proposition(
    *,
    archive_id: str,
    subject_ref: str,
    predicate: str,
    object_ref: str,
    role: str,
    scope_ref: str,
) -> dict[str, str]:
    archive_id = _required_text(archive_id, "archive_id")
    subject_ref = _required_text(subject_ref, "subject_ref")
    predicate = _required_text(predicate, "predicate")
    object_ref = _required_text(object_ref, "object_ref")
    role = _required_text(role, "role")
    if role not in ROLES:
        raise OperationalMembershipError("role_invalid")
    if not isinstance(scope_ref, str):
        raise OperationalMembershipError("scope_ref_invalid")
    return {
        "archive_id": archive_id,
        "subject_ref": subject_ref,
        "predicate": predicate,
        "object_ref": object_ref,
        "role": role,
        "scope_ref": scope_ref.strip(),
    }


def proposition_id_for(
    *,
    archive_id: str,
    subject_ref: str,
    predicate: str,
    object_ref: str,
    role: str,
    scope_ref: str = "",
) -> str:
    """Return identity for one exact operational proposition.

    Evidence, producer versions, timestamps and scores are deliberately not
    included.  ``archive_id`` is retained so propositions from two archives
    cannot collide even when their physical refs happen to match.
    """
    return "proposition:" + _hash(_canonical_proposition(
        archive_id=archive_id,
        subject_ref=subject_ref,
        predicate=predicate,
        object_ref=object_ref,
        role=role,
        scope_ref=scope_ref,
    ))[7:]


def unit_lineage_ref_for(unit: Mapping[str, Any], archive_id: str) -> str:
    """Return a snapshot-independent reference for a provisional unit.

    Stage 2C ``unit_id`` is a snapshot projection.  Operational propositions
    must survive a replay, so their object reference uses the unit's anchor
    semantics and excludes membership, evidence and snapshot metadata.
    """
    if not isinstance(unit, Mapping):
        raise OperationalMembershipError("unit_not_mapping")
    role = _required_text(unit.get("role"), "unit_role")
    root_path = unit.get("root_path")
    anchors = unit.get("anchor_refs")
    if not isinstance(root_path, str):
        raise OperationalMembershipError("unit_root_path_invalid")
    if not isinstance(anchors, list) or any(not isinstance(item, str) for item in anchors):
        raise OperationalMembershipError("unit_anchor_refs_invalid")
    material = {
        "archive_id": _required_text(archive_id, "archive_id"),
        "role": role,
        "root_path": root_path,
        "anchor_refs": sorted(set(anchors)),
    }
    return "unit-lineage:" + _hash(material)[7:]


def _event_semantics(event: Mapping[str, Any]) -> dict[str, Any]:
    comparable = dict(event)
    comparable.pop("event_id", None)
    comparable.pop("recorded_at", None)
    return comparable


def event_id_for(event: Mapping[str, Any]) -> str:
    """Return an event ID excluding event ID and recording time."""
    if not isinstance(event, Mapping):
        raise OperationalMembershipError("event_not_mapping")
    return "event:" + _hash(_event_semantics(event))[7:]


def build_operational_event(
    *,
    archive_id: str,
    subject_ref: str,
    predicate: str,
    object_ref: str,
    role: str,
    event_type: str,
    scope_ref: str = "",
    evidence_refs: Iterable[str] = (),
    negative_evidence_refs: Iterable[str] = (),
    signal_refs: Iterable[str] = (),
    producer: str = "flujo.knowledge.operational_memberships",
    producer_version: str = "1",
    supersedes_event_id: str | None = None,
    caused_by_event_ids: Iterable[str] = (),
    payload: Mapping[str, Any] | None = None,
    recorded_at: str = "",
) -> dict[str, Any]:
    """Build one canonical event without reading files or using wall clock."""
    if event_type not in EVENT_TYPES:
        raise OperationalMembershipError("event_type_invalid")
    proposition = _canonical_proposition(
        archive_id=archive_id,
        subject_ref=subject_ref,
        predicate=predicate,
        object_ref=object_ref,
        role=role,
        scope_ref=scope_ref,
    )
    if not isinstance(payload, Mapping):
        if payload is not None:
            raise OperationalMembershipError("payload_invalid")
        payload = {}
    event: dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "event_id": "",
        "archive_id": proposition["archive_id"],
        "proposition_id": proposition_id_for(**proposition),
        "subject_ref": proposition["subject_ref"],
        "predicate": proposition["predicate"],
        "object_ref": proposition["object_ref"],
        "role": proposition["role"],
        "scope_ref": proposition["scope_ref"],
        "event_type": event_type,
        "evidence_refs": sorted(set(evidence_refs)),
        "negative_evidence_refs": sorted(set(negative_evidence_refs)),
        "signal_refs": sorted(set(signal_refs)),
        "producer": _required_text(producer, "producer"),
        "producer_version": _required_text(producer_version, "producer_version"),
        "supersedes_event_id": supersedes_event_id,
        "caused_by_event_ids": sorted(set(caused_by_event_ids)),
        "payload": dict(payload),
        "recorded_at": recorded_at,
    }
    # Validate the caller's iterables before calculating the semantic ID.
    for field in ("evidence_refs", "negative_evidence_refs", "signal_refs", "caused_by_event_ids"):
        _sorted_refs(event[field], field)
    if supersedes_event_id is not None and (
        not isinstance(supersedes_event_id, str) or not supersedes_event_id
    ):
        raise OperationalMembershipError("supersedes_event_id_invalid")
    if not isinstance(recorded_at, str):
        raise OperationalMembershipError("recorded_at_invalid")
    event["event_id"] = event_id_for(event)
    validate_operational_event(event)
    return event


def reopen_event_for_material_evidence(
    rejection_event: Mapping[str, Any],
    *,
    trigger: str,
    evidence_refs: Iterable[str] = (),
    signal_refs: Iterable[str] = (),
    producer: str = "flujo.knowledge.operational_memberships",
    producer_version: str = "1",
    payload: Mapping[str, Any] | None = None,
    recorded_at: str = "",
) -> dict[str, Any]:
    """Build a REOPEN event only for an allowed material-evidence trigger.

    A rejected proposition is not reconsidered because of a touch, rename,
    scan order or model version.  The rejection event declares the narrow
    trigger classes that can reopen it.  The returned event supersedes only
    that rejection and keeps the proposition identity unchanged.
    """
    validate_operational_event(rejection_event)
    if rejection_event["event_type"] != "REJECT":
        raise OperationalMembershipError("reopen_source_not_rejection")
    trigger = _required_text(trigger, "reopen_trigger")
    allowed = rejection_event.get("payload", {}).get("reopen_triggers", [])
    if not isinstance(allowed, list) or any(not isinstance(item, str) for item in allowed):
        raise OperationalMembershipError("reopen_policy_invalid")
    if trigger not in allowed:
        raise OperationalMembershipError("reopen_trigger_not_allowed")
    reopen_payload = dict(payload or {})
    reopen_payload.update({
        "reopen_trigger": trigger,
        "reopen_basis_event_id": rejection_event["event_id"],
        "reopen_triggers": sorted(set(allowed)),
    })
    return build_operational_event(
        archive_id=rejection_event["archive_id"],
        subject_ref=rejection_event["subject_ref"],
        predicate=rejection_event["predicate"],
        object_ref=rejection_event["object_ref"],
        role=rejection_event["role"],
        scope_ref=rejection_event["scope_ref"],
        event_type="REOPEN",
        evidence_refs=evidence_refs,
        signal_refs=signal_refs,
        producer=producer,
        producer_version=producer_version,
        supersedes_event_id=rejection_event["event_id"],
        caused_by_event_ids=(rejection_event["event_id"],),
        payload=reopen_payload,
        recorded_at=recorded_at,
    )


def validate_operational_event(event: Mapping[str, Any]) -> bool:
    """Strictly validate one event and its recomputed identifiers."""
    if not isinstance(event, Mapping) or set(event) != _EVENT_FIELDS:
        raise OperationalMembershipError("event_field_set_invalid")
    if event["schema"] != EVENT_SCHEMA:
        raise OperationalMembershipError("event_schema_invalid")
    proposition = _canonical_proposition(
        archive_id=event["archive_id"],
        subject_ref=event["subject_ref"],
        predicate=event["predicate"],
        object_ref=event["object_ref"],
        role=event["role"],
        scope_ref=event["scope_ref"],
    )
    if event["event_type"] not in EVENT_TYPES:
        raise OperationalMembershipError("event_type_invalid")
    expected_proposition = proposition_id_for(**proposition)
    if event["proposition_id"] != expected_proposition:
        raise OperationalMembershipError("event_proposition_id_invalid")
    for field in ("event_id", "producer", "producer_version"):
        _required_text(event[field], field)
    for field in ("evidence_refs", "negative_evidence_refs", "signal_refs", "caused_by_event_ids"):
        _sorted_refs(event[field], field)
    if event["supersedes_event_id"] is not None and (
        not isinstance(event["supersedes_event_id"], str)
        or not event["supersedes_event_id"]
    ):
        raise OperationalMembershipError("supersedes_event_id_invalid")
    if not isinstance(event["payload"], Mapping) or not isinstance(event["recorded_at"], str):
        raise OperationalMembershipError("event_payload_or_time_invalid")
    if event["event_id"] != event_id_for(event):
        raise OperationalMembershipError("event_id_invalid")
    return True


def _active_event_ids(events: list[dict[str, Any]]) -> set[str]:
    superseded: set[str] = set()
    for event in events:
        if event["supersedes_event_id"]:
            superseded.add(event["supersedes_event_id"])
        superseded.update(event["caused_by_event_ids"])
    return {event["event_id"] for event in events if event["event_id"] not in superseded}


def _event_reopen_triggers(events: Iterable[Mapping[str, Any]]) -> list[str]:
    triggers: set[str] = set()
    for event in events:
        payload = event.get("payload", {})
        if isinstance(payload, Mapping):
            values = payload.get("reopen_triggers", [])
            if isinstance(values, list) and all(isinstance(item, str) for item in values):
                triggers.update(values)
    return sorted(triggers)


def _membership_for(events: list[dict[str, Any]]) -> dict[str, Any]:
    events = sorted(events, key=lambda item: item["event_id"])
    active_ids = _active_event_ids(events)
    active = [event for event in events if event["event_id"] in active_ids]
    decisions = [event for event in active if event["event_type"] in {"ACCEPT", "REJECT"}]
    decision_types = {event["event_type"] for event in decisions}
    if len(decision_types) > 1:
        status = "conflicted"
    elif "ACCEPT" in decision_types:
        status = "accepted"
    elif "REJECT" in decision_types:
        status = "rejected"
    else:
        status = "proposed"
    first = events[0]
    evidence = sorted({ref for event in active for ref in event["evidence_refs"]})
    negative = sorted({ref for event in active for ref in event["negative_evidence_refs"]})
    signals = sorted({ref for event in active for ref in event["signal_refs"]})
    return {
        "membership_id": first["proposition_id"],
        "proposition_id": first["proposition_id"],
        "archive_id": first["archive_id"],
        "subject_ref": first["subject_ref"],
        "predicate": first["predicate"],
        "object_ref": first["object_ref"],
        "role": first["role"],
        "scope_ref": first["scope_ref"],
        "status": status,
        "evidence_refs": evidence,
        "negative_evidence_refs": negative,
        "signal_refs": signals,
        "decision_event_ids": sorted(event["event_id"] for event in decisions),
        "event_ids": sorted(event["event_id"] for event in events),
        "decision_source": sorted({event["producer"] for event in active}),
        "producer_versions": sorted({event["producer_version"] for event in active}),
        "reopen_triggers": _event_reopen_triggers(events),
    }


def project_operational_memberships(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Rebuild the current membership view from immutable events only."""
    normalized: list[dict[str, Any]] = []
    for event in events:
        validate_operational_event(event)
        normalized.append(dict(event))
    if len(normalized) != len({event["event_id"] for event in normalized}):
        raise OperationalMembershipError("duplicate_event_id")
    by_proposition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in normalized:
        by_proposition[event["proposition_id"]].append(event)
    memberships = [
        _membership_for(by_proposition[key])
        for key in sorted(by_proposition)
    ]
    negative_memory = [
        {
            "proposition_id": membership["proposition_id"],
            "archive_id": membership["archive_id"],
            "subject_ref": membership["subject_ref"],
            "predicate": membership["predicate"],
            "object_ref": membership["object_ref"],
            "role": membership["role"],
            "scope_ref": membership["scope_ref"],
            "status": "rejected",
            "evidence_refs": membership["evidence_refs"],
            "negative_evidence_refs": membership["negative_evidence_refs"],
            "reopen_triggers": membership["reopen_triggers"],
        }
        for membership in memberships
        if membership["status"] == "rejected"
    ]
    archives = sorted({event["archive_id"] for event in normalized})
    return {
        "schema": SCHEMA,
        "algorithm_version": ALGORITHM_VERSION,
        "archive_id": archives[0] if len(archives) == 1 else "",
        "memberships": memberships,
        "negative_memory": negative_memory,
        "reconciliation": {
            "events": len(normalized),
            "propositions": len(memberships),
            "accepted": sum(item["status"] == "accepted" for item in memberships),
            "rejected": sum(item["status"] == "rejected" for item in memberships),
            "conflicted": sum(item["status"] == "conflicted" for item in memberships),
            "proposed": sum(item["status"] == "proposed" for item in memberships),
            "loss": 0,
            "duplicate_event_ids": len(normalized) - len({item["event_id"] for item in normalized}),
            "truth_promotions": 0,
        },
    }


def validate_membership_projection(payload: Mapping[str, Any]) -> bool:
    """Validate the deterministic projection and its negative-memory view."""
    if not isinstance(payload, Mapping):
        raise OperationalMembershipError("projection_not_mapping")
    required = {"schema", "algorithm_version", "archive_id", "memberships", "negative_memory", "reconciliation"}
    if set(payload) != required:
        raise OperationalMembershipError("projection_field_set_invalid")
    if payload["schema"] != SCHEMA or payload["algorithm_version"] != ALGORITHM_VERSION:
        raise OperationalMembershipError("projection_schema_invalid")
    if not isinstance(payload["memberships"], list) or not isinstance(payload["negative_memory"], list):
        raise OperationalMembershipError("projection_lists_invalid")
    ids: list[str] = []
    for item in payload["memberships"]:
        if not isinstance(item, Mapping):
            raise OperationalMembershipError("membership_invalid")
        for field in (
            "membership_id", "proposition_id", "archive_id", "subject_ref", "predicate",
            "object_ref", "role", "scope_ref", "status",
        ):
            _required_text(item.get(field), f"membership_{field}")
        if item["status"] not in MEMBERSHIP_STATUSES:
            raise OperationalMembershipError("membership_status_invalid")
        for field in (
            "evidence_refs", "negative_evidence_refs", "signal_refs",
            "decision_event_ids", "event_ids", "decision_source", "producer_versions",
            "reopen_triggers",
        ):
            _sorted_refs(item.get(field), f"membership_{field}")
        if item["membership_id"] != item["proposition_id"] or item["membership_id"] in ids:
            raise OperationalMembershipError("membership_id_invalid")
        ids.append(item["membership_id"])
    if ids != sorted(ids):
        raise OperationalMembershipError("membership_order_invalid")
    negative_ids = [item.get("proposition_id") for item in payload["negative_memory"]]
    if negative_ids != sorted(negative_ids) or any(item not in ids for item in negative_ids):
        raise OperationalMembershipError("negative_memory_order_invalid")
    reconciliation = payload["reconciliation"]
    if not isinstance(reconciliation, Mapping):
        raise OperationalMembershipError("reconciliation_invalid")
    if reconciliation.get("propositions") != len(ids):
        raise OperationalMembershipError("reconciliation_propositions_invalid")
    if reconciliation.get("loss") != 0 or reconciliation.get("truth_promotions") != 0:
        raise OperationalMembershipError("reconciliation_safety_invalid")
    return True


def persist_operational_event(store: Any, event: Mapping[str, Any]) -> str:
    """Validate and append through the existing LearningStore only."""
    validate_operational_event(event)
    append = getattr(store, "append_operational_event", None)
    if not callable(append):
        raise OperationalMembershipError("store_missing_operational_event_api")
    return str(append(event))


def project_store_memberships(store: Any, archive_id: str) -> dict[str, Any]:
    """Read the existing store and rebuild one archive's view."""
    archive_id = _required_text(archive_id, "archive_id")
    reader = getattr(store, "operational_events", None)
    if not callable(reader):
        raise OperationalMembershipError("store_missing_operational_event_reader")
    payload = project_operational_memberships(reader(archive_id))
    if payload["archive_id"] != archive_id and payload["memberships"]:
        raise OperationalMembershipError("projection_archive_isolation_invalid")
    validate_membership_projection(payload)
    return payload


_RECONSTRUCTION_PROJECTION_FIELDS = {
    "schema", "source_schema", "archive_id", "snapshot_id", "limits",
    "input_hash", "artifacts", "candidate_observations",
    "artifacts_by_parent", "artifacts_by_content", "native_anchor_refs",
    "probable_output_refs", "candidate_observation_ids", "reconciliation",
}
_RECONSTRUCTION_ARTIFACT_FIELDS = {
    "artifact_id", "physical_id", "artifact_ref", "references",
    "relative_path", "parent_path", "basename", "stem", "suffix_chain",
    "kind", "availability", "family", "media_type", "size", "sha256",
    "content_id", "derived_flags",
}
_CAPABILITY_RECORD_FIELDS = {
    "capability", "state", "preconditions", "missing_preconditions",
    "reason_codes", "evidence_refs",
}


def _validate_reconstruction_projection_for_capabilities(
    projection: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Validate the small Stage 2A boundary used by this read projection.

    Stage 2A deliberately has no public validator of its own.  Repeating this
    boundary check here keeps a capability report fail-closed without making
    the capability layer an alternative reconstruction engine.
    """
    if not isinstance(projection, Mapping):
        raise OperationalMembershipError("reconstruction_projection_not_mapping")
    if set(projection) != _RECONSTRUCTION_PROJECTION_FIELDS:
        raise OperationalMembershipError("reconstruction_projection_fields_invalid")
    if projection["schema"] != "mak-archive-reconstruction-input-v1":
        raise OperationalMembershipError("reconstruction_projection_schema_invalid")
    if projection["source_schema"] != "mak-archive-observation-batch-v1":
        raise OperationalMembershipError("reconstruction_source_schema_invalid")
    for field in ("archive_id", "snapshot_id", "input_hash"):
        _required_text(projection.get(field), f"reconstruction_{field}")
    if not isinstance(projection["limits"], Mapping):
        raise OperationalMembershipError("reconstruction_limits_invalid")
    artifacts = projection["artifacts"]
    if not isinstance(artifacts, list):
        raise OperationalMembershipError("reconstruction_artifacts_invalid")
    refs: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise OperationalMembershipError("reconstruction_artifact_invalid")
        if set(artifact) != _RECONSTRUCTION_ARTIFACT_FIELDS:
            raise OperationalMembershipError("reconstruction_artifact_fields_invalid")
        if "mtime_ns" in artifact or "change_set" in artifact:
            raise OperationalMembershipError("volatile_artifact_field_forbidden")
        for field in (
            "artifact_id", "physical_id", "artifact_ref", "relative_path",
            "basename", "stem", "kind", "availability",
            "family", "media_type",
        ):
            _required_text(artifact.get(field), f"artifact_{field}")
        if not isinstance(artifact["parent_path"], str) or artifact["parent_path"] != artifact["parent_path"].strip():
            raise OperationalMembershipError("artifact_parent_path_invalid")
        if not isinstance(artifact["references"], list):
            raise OperationalMembershipError("artifact_references_invalid")
        if any(not isinstance(ref, str) or not ref for ref in artifact["references"]):
            raise OperationalMembershipError("artifact_references_invalid")
        if artifact["references"] != sorted(set(artifact["references"])):
            raise OperationalMembershipError("artifact_references_not_sorted_unique")
        if not isinstance(artifact["suffix_chain"], list) or any(
            not isinstance(item, str) for item in artifact["suffix_chain"]
        ):
            raise OperationalMembershipError("artifact_suffix_chain_invalid")
        if not isinstance(artifact["derived_flags"], Mapping):
            raise OperationalMembershipError("artifact_derived_flags_invalid")
        if artifact["content_id"] is not None and (
            not isinstance(artifact["content_id"], str) or not artifact["content_id"]
        ):
            raise OperationalMembershipError("artifact_content_id_invalid")
        if artifact["sha256"] is not None and (
            not isinstance(artifact["sha256"], str) or not artifact["sha256"]
        ):
            raise OperationalMembershipError("artifact_sha256_invalid")
        refs.append(artifact["artifact_ref"])
    if len(refs) != len(set(refs)):
        raise OperationalMembershipError("artifact_ref_identity_invalid")
    return artifacts


def _capability_decision(
    capability: str,
    state: str,
    *,
    preconditions: tuple[str, ...] = (),
    missing_preconditions: tuple[str, ...] = (),
    reason_codes: tuple[str, ...] = (),
    artifact_ref: str,
) -> dict[str, Any]:
    if capability not in CAPABILITIES:
        raise OperationalMembershipError("capability_invalid")
    if state not in CAPABILITY_STATES:
        raise OperationalMembershipError("capability_state_invalid")
    return {
        "capability": capability,
        "state": state,
        "preconditions": sorted(set(preconditions)),
        "missing_preconditions": sorted(set(missing_preconditions)),
        "reason_codes": sorted(set(reason_codes)),
        "evidence_refs": [artifact_ref],
    }


def project_artifact_capabilities(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Project observable operation preconditions for one Stage 2A artifact.

    This function does not inspect the path and does not resolve providers.  A
    ``possible`` result means only that the artifact's observed kind,
    availability and declared family satisfy the operation's structural
    preconditions.  Execution, backup and export intentionally remain blocked
    until an explicit policy/target is supplied by a later consumer.
    """
    if not isinstance(artifact, Mapping):
        raise OperationalMembershipError("capability_artifact_not_mapping")
    if set(artifact) != _RECONSTRUCTION_ARTIFACT_FIELDS:
        raise OperationalMembershipError("capability_artifact_fields_invalid")
    artifact_ref = _required_text(artifact.get("artifact_ref"), "artifact_ref")
    kind = _required_text(artifact.get("kind"), "artifact_kind")
    availability = _required_text(artifact.get("availability"), "artifact_availability")
    raw_family = _required_text(artifact.get("family"), "artifact_family")
    raw_media_type = _required_text(artifact.get("media_type"), "artifact_media_type")
    family = raw_family.casefold()
    media_type = raw_media_type.casefold()
    regular_readable = kind == "file" and availability in {"available", "present"}
    known_families = frozenset({
        "archive", "audio", "code", "data", "document", "image", "text",
        "3d", "vector", "video", "web",
    })
    previewable = known_families
    transcription_families = frozenset({"audio", "video"})
    ocr_families = frozenset({"document", "image"})
    searchable_families = frozenset({"code", "data", "document", "text"})
    code_family = family == "code"
    media_text_needed = family in {"audio", "image", "video"}
    pdf_or_image = family in ocr_families or media_type.startswith("image/") or media_type == "application/pdf"

    def read_dependent(
        capability: str,
        supported: bool,
        *,
        possible_reason: str,
        unsupported_reason: str = "family_not_supported",
        extra_missing: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if not supported:
            return _capability_decision(
                capability, "unsupported", reason_codes=(unsupported_reason,),
                artifact_ref=artifact_ref,
            )
        if not regular_readable:
            missing = ("regular_file", "artifact_readable") + extra_missing
            return _capability_decision(
                capability, "blocked", missing_preconditions=missing,
                reason_codes=("artifact_not_readable",), artifact_ref=artifact_ref,
            )
        return _capability_decision(
            capability, "possible", preconditions=(
                "regular_file", "artifact_readable", "family_declared",
            ), reason_codes=(possible_reason,), artifact_ref=artifact_ref,
        )

    decisions = {
        "preview": read_dependent(
            "preview", family in previewable,
            possible_reason="declared_previewable_family",
        ),
        "transcribe": read_dependent(
            "transcribe", family in transcription_families,
            possible_reason="declared_audio_or_video",
        ),
        "ocr": read_dependent(
            "ocr", pdf_or_image,
            possible_reason="declared_image_or_document",
        ),
        "index_code": read_dependent(
            "index_code", code_family,
            possible_reason="declared_code_family",
        ),
    }

    if family in searchable_families:
        decisions["semantic_search"] = read_dependent(
            "semantic_search", True,
            possible_reason="declared_searchable_text_family",
        )
    elif media_text_needed:
        if regular_readable:
            decisions["semantic_search"] = _capability_decision(
                "semantic_search", "blocked",
                preconditions=("regular_file", "artifact_readable", "family_declared"),
                missing_preconditions=("text_representation",),
                reason_codes=("transcription_or_ocr_required",), artifact_ref=artifact_ref,
            )
        else:
            decisions["semantic_search"] = _capability_decision(
                "semantic_search", "blocked",
                missing_preconditions=("regular_file", "artifact_readable", "text_representation"),
                reason_codes=("artifact_not_readable",), artifact_ref=artifact_ref,
            )
    elif family == "archive":
        decisions["semantic_search"] = _capability_decision(
            "semantic_search", "blocked",
            missing_preconditions=("extracted_text",),
            reason_codes=("archive_extraction_required",), artifact_ref=artifact_ref,
        )
    else:
        decisions["semantic_search"] = _capability_decision(
            "semantic_search", "unsupported", reason_codes=("family_unknown",),
            artifact_ref=artifact_ref,
        )

    if code_family:
        decisions["execute"] = _capability_decision(
            "execute", "blocked",
            preconditions=("declared_code_family",) if regular_readable else (),
            missing_preconditions=("regular_file", "artifact_readable", "execution_policy")
            if not regular_readable else ("execution_policy",),
            reason_codes=("execution_policy_required",) if regular_readable
            else ("artifact_not_readable", "execution_policy_required"),
            artifact_ref=artifact_ref,
        )
    else:
        decisions["execute"] = _capability_decision(
            "execute", "unsupported", reason_codes=("not_code_family",),
            artifact_ref=artifact_ref,
        )

    for capability, reason in (
        ("backup", "backup_target_not_declared"),
        ("export", "export_target_not_declared"),
    ):
        decisions[capability] = _capability_decision(
            capability, "blocked",
            preconditions=("artifact_observed",),
            missing_preconditions=("target_declared",),
            reason_codes=(reason,), artifact_ref=artifact_ref,
        )

    capability_rows = [decisions[name] for name in CAPABILITIES]
    return {
        "artifact_ref": artifact_ref,
        "artifact_id": _required_text(artifact.get("artifact_id"), "artifact_id"),
        "physical_id": _required_text(artifact.get("physical_id"), "physical_id"),
        "relative_path": _required_text(artifact.get("relative_path"), "relative_path"),
        "kind": kind,
        "availability": availability,
        "family": raw_family,
        "media_type": raw_media_type,
        "content_id": artifact["content_id"],
        "capabilities": capability_rows,
    }


def project_archive_capabilities(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic capability read model from Stage 2A output."""
    artifacts = _validate_reconstruction_projection_for_capabilities(projection)
    records = [project_artifact_capabilities(artifact) for artifact in artifacts]
    records.sort(key=lambda item: item["artifact_ref"])
    rows = [row for record in records for row in record["capabilities"]]
    reconciliation = {
        "artifacts_observed": len(artifacts),
        "artifacts_projected": len(records),
        "artifact_loss": len(artifacts) - len(records),
        "artifact_ref_duplicates": len(records) - len({item["artifact_ref"] for item in records}),
        "capability_rows": len(rows),
        "possible": sum(row["state"] == "possible" for row in rows),
        "blocked": sum(row["state"] == "blocked" for row in rows),
        "unsupported": sum(row["state"] == "unsupported" for row in rows),
        "source_mutations": 0,
        "truth_promotions": 0,
    }
    if reconciliation["artifact_loss"] != 0 or reconciliation["artifact_ref_duplicates"] != 0:
        raise OperationalMembershipError("capability_reconciliation_failed")
    return {
        "schema": CAPABILITY_SCHEMA,
        "source_projection_schema": projection["schema"],
        "algorithm_version": CAPABILITY_ALGORITHM_VERSION,
        "archive_id": projection["archive_id"],
        "snapshot_id": projection["snapshot_id"],
        "input_hash": projection["input_hash"],
        "capabilities": records,
        "reconciliation": reconciliation,
        "control": {
            "database_write": False,
            "source_mutation": False,
            "promotion": "none",
            "dispatch": False,
        },
    }


def validate_capability_payload(
    projection: Mapping[str, Any], payload: Mapping[str, Any]
) -> bool:
    """Fail-closed validator by deterministic replay of the projection."""
    if not isinstance(payload, Mapping):
        raise OperationalMembershipError("capability_payload_not_mapping")
    expected = project_archive_capabilities(projection)
    if dict(payload) != expected:
        raise OperationalMembershipError("capability_payload_not_replayable")
    for record in payload["capabilities"]:
        if not isinstance(record, Mapping) or not isinstance(record.get("capabilities"), list):
            raise OperationalMembershipError("capability_record_invalid")
        if len(record["capabilities"]) != len(CAPABILITIES):
            raise OperationalMembershipError("capability_record_count_invalid")
        seen: list[str] = []
        for row in record["capabilities"]:
            if set(row) != _CAPABILITY_RECORD_FIELDS:
                raise OperationalMembershipError("capability_row_fields_invalid")
            if row["capability"] in seen or row["capability"] not in CAPABILITIES:
                raise OperationalMembershipError("capability_row_identity_invalid")
            if row["state"] not in CAPABILITY_STATES:
                raise OperationalMembershipError("capability_row_state_invalid")
            for field in ("preconditions", "missing_preconditions", "reason_codes", "evidence_refs"):
                _sorted_refs(row[field], f"capability_{field}")
            seen.append(row["capability"])
        if seen != list(CAPABILITIES):
            raise OperationalMembershipError("capability_row_order_invalid")
    return True


def events_from_unit_assignments(
    units: Mapping[str, Any], *, producer_version: str = "stage2c-1"
) -> list[dict[str, Any]]:
    """Turn assigned Stage 2C rows into proposals without promoting them.

    The existing assignment is treated as a signal from Stage 2C.  It is not
    written here and it is never converted into artistic truth.
    """
    if not isinstance(units, Mapping):
        raise OperationalMembershipError("units_not_mapping")
    archive_id = _required_text(units.get("archive_id"), "archive_id")
    snapshot_id = _required_text(units.get("snapshot_id"), "snapshot_id")
    unit_by_id = {item.get("unit_id"): item for item in units.get("units", []) if isinstance(item, Mapping)}
    assignments = units.get("assignments")
    if not isinstance(assignments, list):
        raise OperationalMembershipError("assignments_invalid")
    output: list[dict[str, Any]] = []
    for assignment in assignments:
        if not isinstance(assignment, Mapping):
            raise OperationalMembershipError("assignment_invalid")
        if assignment.get("status") != "assigned":
            continue
        artifact_ref = _required_text(assignment.get("artifact_ref"), "artifact_ref")
        unit_id = _required_text(assignment.get("unit_id"), "assignment_unit_id")
        unit = unit_by_id.get(unit_id)
        if unit is None:
            raise OperationalMembershipError("assignment_unit_missing")
        object_ref = unit_lineage_ref_for(unit, archive_id)
        output.append(build_operational_event(
            archive_id=archive_id,
            subject_ref=artifact_ref,
            predicate="member_of",
            object_ref=object_ref,
            role="unknown",
            scope_ref="stage2c",
            event_type="PROPOSE",
            producer="flujo.knowledge.archive_unit_reconstruction",
            producer_version=producer_version,
            payload={
                "source_unit_id": unit_id,
                "source_snapshot_id": snapshot_id,
                "source_assignment_status": "assigned",
                "source_unit_role": unit.get("role", "unknown"),
                "reopen_triggers": ["native_reference_added", "explicit_manifest_added", "unit_split"],
            },
        ))
    return sorted(output, key=lambda item: item["event_id"])


__all__ = [
    "ALGORITHM_VERSION", "CAPABILITIES", "CAPABILITY_ALGORITHM_VERSION",
    "CAPABILITY_SCHEMA", "CAPABILITY_STATES", "EVENT_SCHEMA", "EVENT_TYPES", "MEMBERSHIP_STATUSES",
    "OperationalMembershipError", "ROLES", "SCHEMA", "build_operational_event",
    "event_id_for", "events_from_unit_assignments", "persist_operational_event",
    "project_archive_capabilities", "project_artifact_capabilities",
    "project_operational_memberships", "project_store_memberships", "proposition_id_for",
    "reopen_event_for_material_evidence", "unit_lineage_ref_for",
    "validate_capability_payload", "validate_membership_projection", "validate_operational_event",
]
