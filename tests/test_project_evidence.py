"""Stdlib tests for mechanical Project IR evidence closure."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from flujo.knowledge.project_evidence import close_project_evidence, record_evidence_closure
from flujo.knowledge.project_ir import LearningStore, build_project_ir


class ProjectEvidenceTests(unittest.TestCase):
    def test_closure_preserves_gaps_and_counts_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scene.blend").write_bytes(b"fixture")
            project = build_project_ir(
                project_id="evidence-demo", title="Evidence", source_root=root,
                state="review_required", unknowns=["official_call"],
                artifacts=[
                    {"relative_path": "scene.blend", "format_family": "3d"},
                    {"relative_path": "missing.png", "format_family": "image"},
                ],
                relations=[{"object": str(root / "scene.blend"), "plane": "active_mak"}],
            )
            closure = close_project_evidence(project, repo_root=root)
            self.assertEqual(closure["status"], "needs_evidence")
            self.assertEqual(closure["checks"]["representative_artifacts_available"], 1)
            self.assertEqual(closure["checks"]["active_mak_links_available"], 1)
            self.assertEqual(closure["unknowns_preserved"], ["official_call"])

    def test_closure_episode_is_recorded_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = build_project_ir(
                project_id="episode-evidence", title="Evidence", source_root=root,
                state="review_required", unknowns=["method"],
            )
            closure = close_project_evidence(project, repo_root=root)
            store = LearningStore(root / "learning.sqlite")
            store.save_project(project)
            first = record_evidence_closure(store, project, closure, episode_id="episode-evidence")
            second = record_evidence_closure(store, project, closure, episode_id="episode-evidence")
            self.assertEqual(first, second)
            self.assertEqual(store.summary()["episodes"], {"needs_evidence": 1})


if __name__ == "__main__":
    unittest.main()
