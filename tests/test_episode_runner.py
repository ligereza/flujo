"""Stdlib tests for bounded consumer probes."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from flujo.knowledge.episode_runner import probe_declared_consumer, record_probe
from flujo.knowledge.project_ir import LearningStore, build_project_ir
from flujo.knowledge.project_router import route_project


class EpisodeRunnerTests(unittest.TestCase):
    def test_abstention_becomes_verified_gate_episode_without_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = build_project_ir(
                project_id="abstain-demo", title="Abstain", source_root=root,
                state="review_required", domains=["rd"],
                artifacts=[{"relative_path": "scene.blend", "format_family": "3d"}],
            )
            decision = route_project(project)
            probe = probe_declared_consumer(project, decision, repo_root=root)
            self.assertEqual(probe["status"], "abstained")
            self.assertEqual(probe["command"], [])
            store = LearningStore(root / "learning.sqlite")
            store.save_project(project)
            episode_id = record_probe(store, project, decision, probe, episode_id="episode-abstain")
            self.assertEqual(episode_id, "episode-abstain")
            with sqlite3.connect(root / "learning.sqlite") as con:
                self.assertEqual(con.execute("SELECT status FROM project_episodes").fetchone()[0], "abstained")

    def test_blend_probe_stops_when_blender_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = build_project_ir(
                project_id="blend-demo", title="Blend", source_root=root,
                state="candidate", domains=["rd"],
                artifacts=[{"relative_path": "scene.blend", "format_family": "3d"}],
            )
            decision = route_project(project)
            probe = probe_declared_consumer(project, decision, repo_root=root)
            self.assertEqual(decision["selected"]["tool_id"], "blend_scene_audit")
            self.assertIn(probe["status"], {"succeeded", "needs_evidence"})
            self.assertEqual(probe["command"], [])


if __name__ == "__main__":
    unittest.main()
