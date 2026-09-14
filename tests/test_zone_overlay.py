from __future__ import annotations

from flujo.serve.server import api_plano_render
from flujo.vj.zone_overlay import prepare_zone_overlay, validate_zone_graph


def _graph() -> dict:
    return {
        "zones": [
            {"zone_id": "FOH_VJ"},
            {"zone_id": "NETWORK_CORE"},
        ],
        "nodes": [
            {"node_id": "xio-foh-01", "zone_id": "FOH_VJ",
             "role": "foh_monitor", "active_writer": False},
            {"node_id": "vj-host-01", "zone_id": "FOH_VJ",
             "role": "vj_control", "active_writer": True,
             "writer_groups": ["visual_cues"]},
            {"node_id": "xio-active-01", "zone_id": "FOH_VJ",
             "role": "showcontrol_optional", "active_writer": True,
             "enabled_by_default": False, "writer_groups": ["visual_cues"]},
        ],
        "links": [
            {"link_id": "visual-to-foh", "from": "vj-host-01",
             "to": "xio-foh-01", "direction": "observe"},
        ],
        "policies": {
            "single_active_writer_per_output": True,
            "foh_monitor_must_not_send": True,
        },
    }


def test_existing_graph_shape_is_valid_and_separate() -> None:
    graph = _graph()
    checked = validate_zone_graph(graph)
    assert checked["valid"] is True
    assert checked["summary"]["defaultActiveWriterGroups"] == {
        "visual_cues": ["vj-host-01"]
    }
    overlay = prepare_zone_overlay(graph)
    assert overlay["proposal_only"] is True
    assert overlay["read_only"] is True
    assert overlay["zones"][0]["zone_id"] == "FOH_VJ"


def test_duplicate_writer_and_foh_control_are_rejected() -> None:
    graph = _graph()
    graph["nodes"][2]["enabled_by_default"] = True
    graph["links"].append({
        "link_id": "bad-foh-control", "from": "xio-foh-01",
        "to": "vj-host-01", "direction": "active_control",
    })
    checked = validate_zone_graph(graph)
    assert checked["valid"] is False
    assert any("multiple_default_writers:visual_cues" in error
               for error in checked["errors"])
    assert any("foh_monitor_cannot_control" in error
               for error in checked["errors"])


def test_invalid_graph_remains_reviewable_without_mutation() -> None:
    graph = _graph()
    graph["links"].append({
        "link_id": "unknown-target", "from": "vj-host-01",
        "to": "missing-node", "direction": "observe",
    })
    overlay = prepare_zone_overlay(graph)
    assert overlay["valid"] is False
    assert overlay["proposal_only"] is True
    assert overlay["links"][-1]["to"] == "missing-node"



def test_plano_keeps_overlay_separate_from_rd_zones() -> None:
    result = api_plano_render({
        "pack": "INFO",
        "nombre": "Evento VJ",
        "duracion_horas": 6,
        "asistentes_estimados": 250,
        "zone_overlay": _graph(),
    })
    assert len(result["layout"]["zones"]) > 0
    assert result["overlay"]["valid"] is True
    assert result["overlay"]["proposal_only"] is True
    plain = api_plano_render({
        "pack": "INFO",
        "nombre": "Evento VJ",
        "duracion_horas": 6,
        "asistentes_estimados": 250,
    })
    assert "overlay" not in plain
