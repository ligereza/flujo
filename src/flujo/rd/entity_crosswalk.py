"""Read-only RD/portfolio entity crosswalk adapter.

The adapter consumes a review-only candidate contract. It never opens SQLite,
does not write source data and does not promote ambiguous names to canonical
entities. A later runtime consumer can use the returned records after an
explicit review gate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
DEFAULT_PATH = _REPO / "data" / "rd_fuentes" / "candidates" / "rd_portfolio_entity_crosswalk.json"


class CrosswalkError(ValueError):
    """Raised when the read-only crosswalk contract is invalid."""


@dataclass(frozen=True)
class EntityLink:
    canonical_id: str
    role: str
    confidence: str
    publication: str
    evidence: tuple[str, ...]
    raw: dict[str, Any]


@dataclass(frozen=True)
class EntityCrosswalk:
    contract: str
    version: int
    status: str
    source_databases: tuple[str, ...]
    entities: tuple[EntityLink, ...]

    def by_id(self, canonical_id: str) -> EntityLink | None:
        return next((item for item in self.entities if item.canonical_id == canonical_id), None)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrosswalkError(f"cannot read crosswalk {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CrosswalkError("crosswalk root must be an object")
    return data


def load_crosswalk(path: Path = DEFAULT_PATH) -> EntityCrosswalk:
    """Load and validate the candidate crosswalk without side effects."""
    data = _load_json(path)
    if data.get("contract") != "rd_portfolio_entity_crosswalk":
        raise CrosswalkError("unexpected crosswalk contract")
    if data.get("version") != 1 or data.get("status") != "review_only":
        raise CrosswalkError("crosswalk must remain version 1 and review_only")
    raw_sources = data.get("source_databases")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise CrosswalkError("crosswalk source_databases must be a non-empty list")
    source_databases: list[str] = []
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, str) or not raw_source.strip():
            raise CrosswalkError(f"source_database[{index}] must be a relative path")
        source = raw_source.strip().replace("\\", "/")
        parts = source.split("/")
        if (
            source.startswith("/")
            or (len(source) > 1 and source[1] == ":")
            or any(part in ("", "..") for part in parts)
        ):
            raise CrosswalkError(
                f"source_database[{index}] must stay a normalized relative path"
            )
        if source in source_databases:
            raise CrosswalkError(f"duplicate source_database: {source}")
        source_databases.append(source)
    raw_entities = data.get("entities")
    if not isinstance(raw_entities, list) or not raw_entities:
        raise CrosswalkError("crosswalk entities must be a non-empty list")

    seen: set[str] = set()
    entities: list[EntityLink] = []
    for index, raw in enumerate(raw_entities):
        if not isinstance(raw, dict):
            raise CrosswalkError(f"entity[{index}] must be an object")
        canonical_id = raw.get("canonical_id")
        required = ("role", "confidence", "publication")
        if not isinstance(canonical_id, str) or not canonical_id:
            raise CrosswalkError(f"entity[{index}] missing canonical_id")
        if canonical_id in seen:
            raise CrosswalkError(f"duplicate canonical_id: {canonical_id}")
        seen.add(canonical_id)
        if any(not isinstance(raw.get(field), str) or not raw[field] for field in required):
            raise CrosswalkError(f"entity[{index}] missing role/confidence/publication")
        evidence = raw.get("evidence")
        if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) for item in evidence):
            raise CrosswalkError(f"entity[{index}] evidence must be a non-empty string list")
        entities.append(EntityLink(
            canonical_id=canonical_id,
            role=raw["role"],
            confidence=raw["confidence"],
            publication=raw["publication"],
            evidence=tuple(evidence),
            raw=dict(raw),
        ))
    return EntityCrosswalk(
        contract=data["contract"],
        version=data["version"],
        status=data["status"],
        source_databases=tuple(source_databases),
        entities=tuple(entities),
    )
