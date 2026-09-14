"""Stdlib tests for the explicit Project IR contract registry."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from flujo.knowledge.contract_registry import ContractRegistry, contract_snapshot, validate_snapshot


class ProjectContractTests(unittest.TestCase):
    def test_snapshot_reuses_declared_formats_and_consumers(self) -> None:
        rows = contract_snapshot()
        self.assertEqual(validate_snapshot(rows), [])
        self.assertTrue(any(row["kind"] == "format" and row["contract_key"] == ".blend" for row in rows))
        blend = next(row for row in rows if row["kind"] == "format" and row["contract_key"] == ".blend")
        self.assertEqual(blend["payload"]["format_family"], "3d")
        consumer = next(row for row in rows if row["kind"] == "consumer" and row["contract_key"] == "blend_scene_audit")
        self.assertIn("blender_optional", consumer["payload"]["dependencies"])

    def test_materialization_is_idempotent_and_retains_stale_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "learning.sqlite"
            registry = ContractRegistry(db)
            rows = contract_snapshot()
            first = registry.materialize(rows)
            second = registry.materialize(rows)
            self.assertEqual(first["total"], second["total"])
            self.assertEqual(second["stale"], 0)

            reduced = rows[:-1]
            third = registry.materialize(reduced)
            self.assertEqual(third["total"], first["total"])
            self.assertEqual(third["stale"], 1)
            summary = registry.summary()
            self.assertEqual(summary["statuses"]["stale"], 1)


if __name__ == "__main__":
    unittest.main()
