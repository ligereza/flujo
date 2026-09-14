from __future__ import annotations

from copy import deepcopy

import pytest

from flujo.knowledge.operation_receipt import (
    build_operation_receipt,
    validate_operation_receipt,
)


pytestmark = pytest.mark.flujo


def test_operation_receipt_is_reproducible_and_read_only() -> None:
    first = build_operation_receipt()
    second = build_operation_receipt()

    assert first == second
    assert validate_operation_receipt(first) is True
    assert first["schema"] == "mak-operation-receipt-v1"
    assert first["operation"]["expanded_count"] == 16
    assert first["control"] == {
        "database_write": False,
        "decision_write": False,
        "selection_effect": "none",
        "promotion": "none",
        "publication": False,
        "semantic_equivalence_authorized": False,
    }


def test_operation_receipt_rejects_control_tampering() -> None:
    tampered = deepcopy(build_operation_receipt())
    tampered["control"]["promotion"] = "publish"

    with pytest.raises(ValueError, match="control_invalid"):
        validate_operation_receipt(tampered)
