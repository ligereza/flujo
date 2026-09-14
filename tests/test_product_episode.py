from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flujo.knowledge.application_research_package import compile_application_research_package
from flujo.knowledge.portfolio_dossier import (
    _dossier_without_hash,
    _hash,
    compile_portfolio_dossier,
)
from flujo.knowledge.product_episode import (
    OUTCOME_RECEIPT_SCHEMA,
    ProductEpisodeError,
    SCHEMA,
    compile_product_episode,
    stable_json,
    validate_product_episode,
)
from flujo.knowledge.product_plan import compile_product_plan


def _products(*, source_status: str = "current_verified", confirmed: bool = True) -> tuple[dict, dict, dict]:
    from test_product_plan import _chain

    opportunity, practice, fit, programs, possibility, frontier, evidence_return = _chain(
        source_status=source_status, confirmed=confirmed
    )
    plan = compile_product_plan(
        opportunity, practice, fit, programs, possibility, frontier, evidence_return
    )
    dossier = compile_portfolio_dossier(plan, practice)
    package = compile_application_research_package(plan, opportunity)
    return plan, dossier, package


def _receipt(plan: dict, *, product_id: str = "portfolio_dossier", program_id: str | None = None) -> dict:
    return {
        "schema": OUTCOME_RECEIPT_SCHEMA,
        "outcome_id": "outcome:external-1",
        "product_id": product_id,
        "program_id": program_id or plan["selected_programs"][0]["program_id"],
        "opportunity_id": plan["opportunity_id"],
        "observed_at": "2026-08-26T12:00:00+00:00",
        "status": "succeeded",
        "source_refs": [{"ref": "external:receipt", "sha256": "a" * 64}],
        "validation": {
            "status": "passed",
            "validator": "external-receipt-validator",
            "checks": ["binding", "source_digest", "observed_after_decision"],
        },
    }


def test_verified_draft_without_outcome_is_open_and_not_trainable() -> None:
    plan, dossier, package = _products()
    episode = compile_product_episode(plan, dossier, package)
    assert episode["schema"] == SCHEMA
    assert episode["status"] == "open"
    assert episode["outcome"]["status"] == "unresolved"
    assert episode["outcome"]["eligible"] is False
    assert episode["outcome"]["reason_codes"] == ["outcome_not_received"]
    assert episode["control"]["training_permitted"] is False
    assert episode["record_episode_projection"]["status"] == "needs_evidence"
    assert "database_write" not in episode["record_episode_projection"]
    assert episode["provenance"]["record_episode_mappable"] is False


def test_observed_local_preserves_research_and_gate_observation() -> None:
    plan, dossier, package = _products(source_status="observed_local", confirmed=False)
    episode = compile_product_episode(plan, dossier, package)
    assert episode["outcome"]["eligible"] is False
    assert episode["observation"]["product_gates"]["application_draft"] == "blocked_with_reasons"
    assert episode["observation"]["product_gates"]["research_brief"] == "draftable"
    assert episode["observation"]["counts"]["research_jobs"] == 1
    assert episode["observation"]["truth_promotions"] == 0


def test_verified_external_receipt_is_label_candidate_but_not_training() -> None:
    plan, dossier, package = _products()
    plan["decision_at"] = "2026-08-25T10:00:00+00:00"
    receipt = _receipt(plan)
    episode = compile_product_episode(plan, dossier, package, receipt)
    assert episode["outcome"]["eligible"] is True
    assert episode["outcome"]["eligibility"] == "verified_external_receipt"
    assert episode["outcome"]["label_candidate"]["status"] == "candidate"
    assert episode["outcome"]["label_candidate"]["label"] == "success"
    assert episode["outcome"]["label_candidate"]["training_permitted"] is False
    assert episode["control"]["training_permitted"] is False
    assert episode["record_episode_projection"]["status"] == "proposed"
    assert episode["record_episode_projection"]["status"] not in {"succeeded", "verified"}
    assert "database_write" not in episode["record_episode_projection"]


def test_identity_group_excludes_snapshot_but_keeps_snapshot_provenance() -> None:
    plan, dossier, package = _products()
    first = compile_product_episode(plan, dossier, package)
    next_dossier = copy.deepcopy(dossier)
    next_dossier["practice_identity"]["snapshot_id"] = "snapshot-next"
    next_dossier["dossier_hash"] = "dossier:" + _hash(_dossier_without_hash(next_dossier))
    second = compile_product_episode(plan, next_dossier, package)
    first_group = first["observation"]["identity_group"]
    second_group = second["observation"]["identity_group"]
    assert first_group["group_id"] == second_group["group_id"]
    assert first_group["snapshot_id"] == "snapshot-fixture"
    assert second_group["snapshot_id"] == "snapshot-next"
    assert first["provenance"]["identity_group"] == first_group
    assert "artist_identity" not in first_group


def test_signal_scopes_follow_product_and_open_has_no_label() -> None:
    plan, dossier, package = _products()
    plan["decision_at"] = "2026-08-25T10:00:00+00:00"
    portfolio_episode = compile_product_episode(plan, dossier, package, _receipt(plan, product_id="portfolio_dossier"))
    assert portfolio_episode["outcome"]["label_candidate"]["signal_scopes"] == ["attention", "ranking"]

    observed_plan, observed_dossier, observed_package = _products(
        source_status="observed_local", confirmed=False
    )
    observed_plan["decision_at"] = "2026-08-25T10:00:00+00:00"
    research_episode = compile_product_episode(
        observed_plan,
        observed_dossier,
        observed_package,
        _receipt(observed_plan, product_id="research_brief"),
    )
    assert research_episode["outcome"]["label_candidate"]["signal_scopes"] == [
        "query_selection", "voi_calibration"
    ]

    open_episode = compile_product_episode(*_products())
    assert open_episode["outcome"]["label_candidate"] is None
    assert open_episode["learning_scope"] == [
        "attention", "query_selection", "ranking", "voi_calibration"
    ]


def test_foreign_or_forged_outcome_fails_closed() -> None:
    plan, dossier, package = _products()
    plan["decision_at"] = "2026-08-25T10:00:00+00:00"
    foreign_program = _receipt(plan, program_id="program:foreign")
    with pytest.raises(ProductEpisodeError, match="outcome_program_ref_foreign"):
        compile_product_episode(plan, dossier, package, foreign_program)
    forged_hash = _receipt(plan)
    forged_hash["source_refs"][0]["sha256"] = "not-a-sha256"
    with pytest.raises(ProductEpisodeError, match="outcome.source_ref.sha256_not_sha256"):
        compile_product_episode(plan, dossier, package, forged_hash)


def test_foreign_consumer_refs_fail_closed() -> None:
    plan, dossier, package = _products()
    bad_dossier = copy.deepcopy(dossier)
    bad_dossier["asset_manifest"][0]["artifact_ref"] = "artifact:foreign"
    with pytest.raises(ProductEpisodeError, match="portfolio_dossier_contract_invalid"):
        compile_product_episode(plan, bad_dossier, package)

    bad_package = copy.deepcopy(package)
    bad_package["application_draft"]["programs"][0]["evidence_refs"] = ["artifact:foreign"]
    with pytest.raises(ProductEpisodeError, match="application_program_evidence_ref_foreign"):
        compile_product_episode(plan, dossier, bad_package)


def test_outcome_without_posterior_decision_time_abstains() -> None:
    plan, dossier, package = _products()
    episode = compile_product_episode(plan, dossier, package, _receipt(plan))
    assert episode["outcome"]["eligible"] is False
    assert episode["outcome"]["reason_codes"] == ["decision_timestamp_missing"]
    assert episode["outcome"]["label_candidate"] is None


def test_deterministic_replay_and_no_mutation() -> None:
    plan, dossier, package = _products()
    plan["decision_at"] = "2026-08-25T10:00:00+00:00"
    receipt = _receipt(plan)
    originals = copy.deepcopy((plan, dossier, package, receipt))
    first = compile_product_episode(plan, dossier, package, receipt)
    second = compile_product_episode(copy.deepcopy(plan), copy.deepcopy(dossier), copy.deepcopy(package), copy.deepcopy(receipt))
    assert first == second
    assert stable_json(first) == stable_json(second)
    assert validate_product_episode(plan, dossier, package, first, receipt) is True
    assert (plan, dossier, package, receipt) == originals


def test_cli_without_outcome_is_read_only_projection(tmp_path: Path) -> None:
    plan, dossier, package = _products()
    paths = []
    for name, value in (("plan", plan), ("dossier", dossier), ("package", package)):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        paths.append(str(path))
    run = subprocess.run(
        [sys.executable, "tools/compile_product_episode.py", *paths],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stderr
    output = json.loads(run.stdout)
    assert output["schema"] == SCHEMA
    assert output["control"]["database_write"] is False
    assert "database_write" not in output["record_episode_projection"]
