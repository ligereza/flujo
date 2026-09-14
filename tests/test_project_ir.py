"""Stdlib tests for the bounded Project IR and learning ledger."""

from __future__ import annotations

import json
import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from flujo.knowledge.project_ir import (
    InventoryLimitError,
    LearningStore,
    ProjectIRError,
    build_project_ir,
    inventory_source,
    inspect_learning_target,
    migration_dry_run,
    project_ir_from_application_package,
    validate_project_ir,
)


class ProjectIRTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "incoming"
        (self.root / "nested").mkdir(parents=True)
        (self.root / "notes.md").write_text("project seed\n", encoding="utf-8")
        (self.root / "nested" / "scene.blend").write_bytes(b"blend-fixture")
        (self.root / "nested" / "unknown.xyz").write_bytes(b"opaque-fixture")
        self.db = Path(self.temp.name) / "learning.sqlite"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_bounded_inventory_is_reference_only_and_classifies_unknown(self) -> None:
        rows = inventory_source(self.root)
        self.assertEqual([row["relative_path"] for row in rows], ["nested/scene.blend", "nested/unknown.xyz", "notes.md"])
        self.assertEqual(rows[0]["format_family"], "3d")
        self.assertEqual(rows[1]["format_family"], "unknown")
        self.assertEqual(rows[2]["hash_status"], "full")

        record = build_project_ir(
            project_id="ssd-demo", title="SSD demo", source_root=self.root,
            artifacts=rows, state="unknown", unknowns=["purpose not established"],
        )
        self.assertEqual(validate_project_ir(record), [])
        serialized = json.dumps(record, ensure_ascii=False)
        self.assertNotIn("project seed", serialized)
        self.assertTrue(record["source"]["root_exists"])

    def test_active_requires_evidence(self) -> None:
        with self.assertRaises(ProjectIRError):
            build_project_ir(
                project_id="no-proof", title="No proof", source_root=self.root,
                state="active",
            )

    def test_store_records_project_episode_and_transition(self) -> None:
        rows = inventory_source(self.root)
        record = build_project_ir(
            project_id="demo", title="Demo", source_root=self.root,
            artifacts=rows, state="candidate",
        )
        store = LearningStore(self.db)
        first = store.save_project(record)
        changed_timestamp = copy.deepcopy(record)
        changed_timestamp["provenance"]["created_at"] = "2099-01-01T00:00:00+00:00"
        second = store.save_project(changed_timestamp)
        self.assertEqual(first, second)
        episode = store.record_episode(
            project_id="demo", objective="classify source", phase="intake",
            action={"tool": "inventory_source"}, observation={"unknowns": [".xyz"]},
            outcome={"decision": "abstain"}, validation={"status": "needs_evidence"},
            status="abstained", episode_id="episode-test",
        )
        self.assertEqual(episode, "episode-test")
        store.transition_project(
            "demo", "unknown", reason="format has no declared consumer",
            evidence=[{"source": "fixture", "status": "observed"}],
        )
        self.assertEqual(store.summary("demo"), {
            "schema": "mak-learning-ledger-v1",
            "projects": {"unknown": 1},
            "episodes": {"abstained": 1},
            "rules": {},
            "project_id": "demo",
        })
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM project_transitions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM project_artifacts").fetchone()[0], 3)
            self.assertEqual(con.execute("SELECT version FROM project_records WHERE project_id='demo'").fetchone()[0], 2)

        reduced = copy.deepcopy(record)
        reduced["artifacts"] = reduced["artifacts"][:1]
        store.save_project(reduced)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM project_artifacts WHERE availability='stale'").fetchone()[0], 2)

    def test_episode_is_append_only_and_can_carry_versioned_provenance(self) -> None:
        record = build_project_ir(
            project_id="episode-provenance", title="Episode provenance", source_root=self.root,
            artifacts=inventory_source(self.root), state="candidate",
        )
        store = LearningStore(self.db)
        store.save_project(record)
        episode_id = store.record_episode(
            project_id="episode-provenance", objective="versioned probe", phase="probe",
            action={"tool": "read_only_probe"}, observation={}, outcome={"status": "verified"},
            validation={"status": "passed"}, status="verified", episode_id="episode-provenance-1",
            source_snapshot_hash="sha256:source", code_commit="abc1234",
            tool_versions={"python": "3.12"},
        )
        self.assertEqual(episode_id, "episode-provenance-1")
        with sqlite3.connect(self.db) as con:
            row = con.execute(
                "SELECT source_snapshot_hash,code_commit,tool_versions_json FROM project_episodes"
            ).fetchone()
            self.assertEqual(tuple(row), ("sha256:source", "abc1234", '{"python":"3.12"}'))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "project_episodes_append_only"):
                con.execute("UPDATE project_episodes SET status='failed' WHERE episode_id=?", (episode_id,))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "project_episodes_append_only"):
                con.execute("DELETE FROM project_episodes WHERE episode_id=?", (episode_id,))

        with self.assertRaisesRegex(ProjectIRError, "versioned_provenance_incomplete"):
            store.record_episode(
                project_id="episode-provenance", objective="incomplete", phase="probe",
                action={}, observation={}, outcome={}, validation={}, status="verified",
                source_snapshot_hash="sha256:only", episode_id="episode-provenance-2",
            )
        with self.assertRaisesRegex(ProjectIRError, "episode_id_conflict"):
            store.record_episode(
                project_id="episode-provenance", objective="versioned probe", phase="probe",
                action={"tool": "read_only_probe"}, observation={}, outcome={"status": "verified"},
                validation={"status": "passed"}, status="verified", episode_id=episode_id,
                source_snapshot_hash="sha256:source", code_commit="abc1234",
                tool_versions={"python": "3.12"}, finished_at="2099-01-01T00:00:00+00:00",
            )

    def test_rule_requires_verified_outcomes_before_promotion(self) -> None:
        record = build_project_ir(
            project_id="rule-demo", title="Rule demo", source_root=self.root,
            artifacts=inventory_source(self.root), state="candidate",
        )
        store = LearningStore(self.db)
        store.save_project(record)
        rule_id = store.upsert_rule(
            trigger={"format_family": "3d", "consumer": "rd"},
            action={"tool": "audit_blend_scene", "mode": "read_only"},
        )
        store.record_episode(
            project_id="rule-demo", objective="audit", phase="gate",
            action={"tool": "audit_blend_scene"}, observation={}, outcome={},
            validation={"status": "passed"}, status="succeeded", episode_id="episode-a",
        )
        store.observe_rule(rule_id=rule_id, episode_id="episode-a", verdict="support")
        with self.assertRaisesRegex(ProjectIRError, "evaluation_required"):
            store.promote_rule(rule_id)
        store.record_episode(
            project_id="rule-demo", objective="audit again", phase="gate",
            action={"tool": "audit_blend_scene"}, observation={}, outcome={},
            validation={"status": "verified"}, status="verified", episode_id="episode-b",
        )
        store.observe_rule(rule_id=rule_id, episode_id="episode-b", verdict="support")
        store.record_learning_evaluation(
            target_kind="semantic_rule", target_id=rule_id,
            dataset_fingerprint="sha256:rule-holdout", split_kind="holdout",
            status="passed", metrics={"accuracy": 1.0, "holdout_count": 2},
            evaluation_id="evaluation-rule-demo",
        )
        store.promote_rule(rule_id, evaluation_id="evaluation-rule-demo")
        self.assertEqual(store.rules(status="promoted")[0]["rule_id"], rule_id)

    def test_inventory_limit_is_explicit(self) -> None:
        with self.assertRaises(InventoryLimitError):
            inventory_source(self.root, max_files=2)

    def test_application_package_becomes_reviewable_ir_with_gaps(self) -> None:
        package = {
            "schema": "mak-application-package-v1",
            "application_id": "app_demo",
            "status": "draft_with_evidence_gaps",
            "readiness": 42,
            "fund": {"id": "fondart", "name": "Fondart"},
            "project": {"project_id": "demo", "title": "Demo project", "path": "/ssd/demo", "dimensionality": "3d"},
            "gaps": [{"field": "budget", "reason": "missing"}],
            "evidence": {
                "representative_assets": [{"relative_path": "scene.blend", "availability": "available"}],
                "mak_links": [{"mak_path": "projects/plano", "relation": "consumer", "confidence": 0.8}],
            },
        }
        record = project_ir_from_application_package(package, source_ref="fixture/application.json")
        self.assertEqual(record["state"], "review_required")
        self.assertEqual(record["unknowns"], ["budget: missing"])
        self.assertEqual(record["relations"][0]["object"], "projects/plano")
        self.assertEqual(record["relations"][0].get("plane"), "active_mak")
        self.assertEqual(validate_project_ir(record), [])

    def test_application_package_resolves_indexed_physical_root(self) -> None:
        index = self.root / "source_index_reference.json"
        index.write_text(json.dumps({"source_root": str(self.root)}), encoding="utf-8")
        package = {
            "schema": "mak-application-package-v1",
            "application_id": "app_root",
            "status": "draft_with_evidence_gaps",
            "readiness": 10,
            "fund": {"name": "Fondart"},
            "project": {"project_id": "root-demo", "title": "Root demo", "path": "incoming", "dimensionality": "3d"},
            "gaps": [],
            "evidence": {
                "source_index": str(index),
                "representative_assets": [{"relative_path": "incoming/scene.blend", "availability": "available"}],
            },
        }
        record = project_ir_from_application_package(package, source_ref="fixture/application.json")
        self.assertEqual(record["source"]["root_ref"], str(self.root))
        self.assertTrue(record["source"]["root_exists"])
        self.assertEqual(record["application"]["project_path"], "incoming")

    def test_inspect_target_is_read_only_and_does_not_create_db(self) -> None:
        target = Path(self.temp.name) / "not-created.sqlite"
        report = inspect_learning_target(target)
        self.assertTrue(report["read_only"])
        self.assertTrue(report["compatible"])
        self.assertFalse(target.exists())

        LearningStore(self.db).ensure_schema()
        applied = inspect_learning_target(self.db)
        self.assertEqual(applied["materialization"], "already_applied")
        self.assertEqual(applied["missing"], [])

    def test_migration_dry_run_reports_intake_without_writes(self) -> None:
        package_dir = Path(self.temp.name) / "applications"
        package_dir.mkdir()
        package = {
            "schema": "mak-application-package-v1",
            "application_id": "app_demo",
            "status": "draft_with_evidence_gaps",
            "readiness": 10,
            "fund": {"name": "Fondart"},
            "project": {"project_id": "demo", "title": "Demo", "path": "/ssd/demo", "dimensionality": "3d"},
            "gaps": [{"field": "team", "reason": "missing"}],
            "evidence": {},
        }
        (package_dir / "app.json").write_text(json.dumps(package), encoding="utf-8")
        report = migration_dry_run(self.db, application_dir=package_dir)
        self.assertFalse(report["writes_performed"])
        self.assertTrue(report["compatible"])
        self.assertEqual(report["intake"]["projects"], ["demo"])
        self.assertFalse(self.db.exists())


if __name__ == "__main__":
    unittest.main()


class VerdictProtectionTests(unittest.TestCase):
    """A re-derivation refreshes the evidence and never the verdict.

    Every adapter that writes into this store emits ``review_required``, because
    a machine is not allowed to assert. That means a second import over a project
    a person had already moved to ``active`` would drag it back into the queue
    and destroy the one thing here a machine cannot regenerate. It was harmless
    only while nothing had ever been decided, which was true until now: measured
    on the live database, ``project_transitions`` held zero rows.
    """

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "incoming"
        self.root.mkdir(parents=True)
        (self.root / "notes.md").write_text("project seed\n", encoding="utf-8")
        self.db = Path(self.temp.name) / "learning.db"

    def _record(self, state: str = "review_required") -> dict:
        return build_project_ir(
            project_id="verdict", title="Verdict", source_root=self.root,
            artifacts=inventory_source(self.root), state=state,
        )

    def test_a_decided_project_keeps_its_state_through_a_re_import(self) -> None:
        store = LearningStore(self.db)
        store.save_project(self._record())
        store.transition_project(
            "verdict", "active", reason="the operator recognised the work",
            evidence=[{"kind": "human_attestation",
                       "detail": "the operator named it as delivered work"}],
            actor="operator")

        refreshed = self._record()
        refreshed["unknowns"] = list(refreshed.get("unknowns", ())) + ["re_derived"]
        store.save_project(refreshed)

        with sqlite3.connect(self.db) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT state, ir_json, version FROM project_records "
                "WHERE project_id='verdict'").fetchone()
        self.assertEqual(row["state"], "active",
                         "the re-import reset a project a person had decided")
        self.assertIn("re_derived", json.loads(row["ir_json"])["unknowns"],
                      "the refreshed evidence was not stored")
        self.assertGreater(row["version"], 1)

    def test_an_undecided_project_still_follows_its_producer(self) -> None:
        """The protection must not freeze a project nobody has looked at."""
        store = LearningStore(self.db)
        store.save_project(self._record(state="candidate"))
        store.save_project(self._record(state="review_required"))
        with sqlite3.connect(self.db) as con:
            state = con.execute(
                "SELECT state FROM project_records WHERE project_id='verdict'"
            ).fetchone()[0]
        self.assertEqual(state, "review_required")

    def test_the_stored_state_follows_the_most_recent_transition(self) -> None:
        store = LearningStore(self.db)
        store.save_project(self._record())
        store.transition_project("verdict", "active", reason="looked like a work",
                                 evidence=[{"kind": "human_attestation",
                                            "detail": "recognised on first pass"}],
                                 actor="operator")
        store.transition_project("verdict", "review_required",
                                 reason="the operator changed their mind",
                                 actor="operator")
        store.save_project(self._record(state="candidate"))
        with sqlite3.connect(self.db) as con:
            state = con.execute(
                "SELECT state FROM project_records WHERE project_id='verdict'"
            ).fetchone()[0]
        self.assertEqual(state, "review_required")
