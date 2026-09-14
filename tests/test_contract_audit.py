"""Stdlib tests for bounded physical contract auditing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from flujo.knowledge.contract_registry import ContractRegistry, audit_contracts


class ContractAuditTests(unittest.TestCase):
    def test_audit_classifies_verified_optional_and_missing_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tools").mkdir()
            (root / "tools" / "known.py").write_text("# fixture\n", encoding="utf-8")
            rows = [
                {
                    "contract_id": "c-verified", "kind": "consumer", "contract_key": "known",
                    "source_ref": "tools/known.py:fixture", "payload": {
                        "path": "tools/known.py", "dependencies": ["python3"],
                    },
                },
                {
                    "contract_id": "c-optional", "kind": "consumer", "contract_key": "optional",
                    "source_ref": "tools/known.py:fixture", "payload": {
                        "path": "tools/known.py", "dependencies": ["blender_optional"],
                    },
                },
                {
                    "contract_id": "c-missing", "kind": "state", "contract_key": "missing",
                    "source_ref": "missing.py:fixture", "payload": {},
                },
            ]
            audited = audit_contracts(rows, root)
            self.assertEqual([row["status"] for row in audited], ["verified", "needs_evidence", "unavailable"])

    def test_audit_record_is_append_only_per_run_and_readable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "source.py").write_text("# fixture\n", encoding="utf-8")
            rows = [{
                "contract_id": "c-one", "kind": "format", "contract_key": ".py",
                "source_ref": "source.py:fixture", "payload": {},
            }]
            db = root / "learning.sqlite"
            registry = ContractRegistry(db)
            audited = audit_contracts(rows, root)
            first = registry.record_audit(audited, run_id="run-one")
            second = registry.record_audit(audited, run_id="run-one")
            self.assertEqual(first["recorded"], 1)
            self.assertEqual(second["recorded"], 1)
            with registry.connect() as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM project_contract_audits").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
