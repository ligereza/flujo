"""
Tests del puente XIO -> RD (src/flujo/rd/xio_ingest.py).

El modulo declara que no acepta campos de identidad: es el limite explicito
del servicio de Reduccion de Danio ("presuntivo: senal de presencia, no
identidad ni pureza ni dosis"). Esta conducta no tenia ninguna cobertura; este
test la fija en las dos rutas de escritura publicas que XIO usa en vivo.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from flujo.rd import xio_ingest


def test_sync_event_rejects_identity_field(tmp_path: Path):
    db_path = tmp_path / "rd.db"
    payload = {
        "clientEventId": "evt-001",
        "eventName": "Evento de prueba",
        "nombre": "Alguien",
    }
    with pytest.raises(ValueError, match="identidad"):
        xio_ingest.sync_event(payload, db_path)


def test_ingest_rejects_nested_identity_field(tmp_path: Path):
    db_path = tmp_path / "rd.db"
    evidence_root = tmp_path / "evidence"
    payload = {
        "date": "2026-09-16",
        "eventRef": "evt-001",
        "sampleCode": "M1",
        "substanceDeclared": "desconocida",
        "mesa": {"label": "Mesa 1", "telefono": "+56900000000"},
    }
    with pytest.raises(ValueError, match="identidad"):
        xio_ingest.ingest(payload, db_path, evidence_root)
