"""Evidence gate for deep-learning tasks; deliberately does not train models.

The gate turns the recurring MAK requirement into an executable consumer:
before any model or embedding can be called learning, a task must declare its
labels, a group-independent holdout, leakage policy and an executable
validator.  A passing gate is eligibility evidence, not a quality claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "mak-deep-learning-task-gate-v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def evaluate_manifest(manifest: Mapping[str, Any], *, root: str | Path = ".") -> dict[str, Any]:
    errors: list[str] = []
    if manifest.get("schema") != SCHEMA:
        errors.append("bad_schema")
    for key in ("task_id", "project_id", "objective", "input_ref", "label_ref"):
        if not _text(manifest.get(key)):
            errors.append("missing_" + key)
    split = manifest.get("split")
    if not isinstance(split, Mapping):
        errors.append("missing_split")
        split = {}
    if not _text(split.get("train_ref")):
        errors.append("missing_train_ref")
    if not _text(split.get("holdout_ref")):
        errors.append("missing_holdout_ref")
    if split.get("independent") is not True:
        errors.append("holdout_not_independent")
    if not _text(split.get("group_key")):
        errors.append("missing_group_key")
    try:
        holdout_count = int(split.get("holdout_count"))
    except (TypeError, ValueError):
        holdout_count = 0
    if holdout_count < 2:
        errors.append("holdout_too_small")
    validator = manifest.get("validator")
    if not isinstance(validator, Mapping):
        errors.append("missing_validator")
        validator = {}
    validator_path = _text(validator.get("path"))
    if not validator_path:
        errors.append("missing_validator_path")
    elif not (Path(root).expanduser() / validator_path).is_file() and not Path(validator_path).is_file():
        errors.append("validator_not_found")
    if _text(validator.get("status")).casefold() not in {"ready", "verified"}:
        errors.append("validator_not_ready")
    return {
        "schema": SCHEMA,
        "task_id": _text(manifest.get("task_id")),
        "project_id": _text(manifest.get("project_id")),
        "decision": "eligible" if not errors else "abstain",
        "training_permitted": False,
        "errors": errors,
        "next_action": "run_validator_then_review" if not errors else "complete_manifest_and_abstain",
        "evidence": {
            "objective_declared": bool(_text(manifest.get("objective"))),
            "labels_declared": bool(_text(manifest.get("label_ref"))),
            "independent_holdout": split.get("independent") is True,
            "group_key": _text(split.get("group_key")),
            "holdout_count": holdout_count,
            "validator_path": validator_path,
            "validator_ready": _text(validator.get("status")).casefold() in {"ready", "verified"},
        },
    }


def load_and_evaluate(path: str | Path, *, root: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("manifest_not_object")
    return evaluate_manifest(value, root=root or manifest_path.parent)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = load_and_evaluate(args.manifest, root=args.root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "decision": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["decision"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
