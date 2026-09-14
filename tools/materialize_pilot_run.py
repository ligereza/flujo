#!/usr/bin/env python3
"""Materialize one canonical MAK pilot into an explicit durable directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flujo.knowledge.pilot_run_manifest import (  # noqa: E402
    PilotRunError,
    build_pilot_outputs,
    build_pilot_outputs_from_observation,
    stable_json,
    validate_pilot_run,
)
from flujo.knowledge.product_view import render_product_markdown  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive-root")
    source.add_argument("--observation", type=Path)
    parser.add_argument("--archive-id")
    parser.add_argument("--opportunity-package", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--practice-receipt-evidence", type=Path)
    parser.add_argument("--opportunity-validity-capture", type=Path)
    parser.add_argument("--technical-context", type=Path)
    args = parser.parse_args()
    try:
        package = json.loads(args.opportunity_package.read_text(encoding="utf-8"))
        practice_receipt_evidence = (
            json.loads(args.practice_receipt_evidence.read_text(encoding="utf-8"))
            if args.practice_receipt_evidence else None
        )
        opportunity_validity_capture = (
            json.loads(args.opportunity_validity_capture.read_text(encoding="utf-8"))
            if args.opportunity_validity_capture else None
        )
        technical_context = (
            json.loads(args.technical_context.read_text(encoding="utf-8"))
            if args.technical_context else None
        )
        if args.observation:
            if args.archive_id or args.max_files is not None:
                raise ValueError("observation_replay_rejects_archive_id_and_max_files")
            observation = json.loads(args.observation.read_text(encoding="utf-8"))
            result = build_pilot_outputs_from_observation(
                observation,
                package,
                practice_receipt_evidence=practice_receipt_evidence,
                opportunity_validity_capture=opportunity_validity_capture,
                technical_context=technical_context,
            )
        else:
            if not args.archive_id:
                raise ValueError("archive_id_required_with_archive_root")
            result = build_pilot_outputs(
                args.archive_root,
                args.archive_id,
                package,
                max_files=args.max_files,
                practice_receipt_evidence=practice_receipt_evidence,
                opportunity_validity_capture=opportunity_validity_capture,
                technical_context=technical_context,
            )
        errors = validate_pilot_run(result)
        if errors:
            raise PilotRunError("result_invalid:" + stable_json(errors))
        args.output_root.mkdir(parents=True, exist_ok=True)
        for name, payload in result["outputs"].items():
            (args.output_root / f"{name}.json").write_text(
                stable_json(payload, pretty=True) + "\n", encoding="utf-8"
            )
        if "portfolio-view" in result["outputs"]:
            (args.output_root / "portfolio-view.md").write_text(
                render_product_markdown(result["outputs"]["portfolio-view"]),
                encoding="utf-8",
            )
        (args.output_root / "manifest.json").write_text(
            stable_json(result["manifest"], pretty=True) + "\n", encoding="utf-8"
        )
        sys.stdout.write(stable_json(result["manifest"], pretty=True) + "\n")
        return 0
    except (OSError, json.JSONDecodeError, PilotRunError, ValueError) as exc:
        sys.stderr.write(stable_json({
            "schema": "mak-pilot-run-error-v1",
            "error": type(exc).__name__,
            "reason": str(exc),
        }) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
