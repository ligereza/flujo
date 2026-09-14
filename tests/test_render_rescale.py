"""Tests del reescalado de proporción / resolución (render.rescale)."""

import copy

import pytest

from flujo.render.rescale import (
    cm_to_px,
    px_to_dpi,
    current_dpi,
    set_dpi,
    set_real_size,
    rescale_file,
)


def base_config():
    return {
        "canvas": {
            "width": 3300,
            "height": 1300,
            "real_size_cm": {"width": 16.5, "height": 6.5},
            "safe_margin_px": 100,
        },
        "global_elements": [
            {"type": "rect", "x": 60, "y": 60, "w": 3180, "h": 1180, "radius": 44},
        ],
        "documents": [
            {
                "id": "doc1",
                "elements": [
                    {"type": "text", "content": "X", "x": 110, "y": 260, "size": 118},
                    {"type": "panel", "x": 120, "y": 570, "w": 1950, "h": 520},
                ],
            }
        ],
    }


# --- conversiones ----------------------------------------------------------

def test_cm_to_px_300dpi():
    # 16.5 cm a 300 dpi = 16.5/2.54*300 ≈ 1949
    assert cm_to_px(16.5, 300) == 1949


def test_px_to_dpi():
    # 3300 px sobre 16.5 cm ≈ 508 dpi
    assert round(px_to_dpi(3300, 16.5)) == 508


def test_current_dpi():
    dpi = current_dpi(base_config())
    assert dpi is not None
    assert round(dpi) == 508


def test_current_dpi_missing_real_size():
    cfg = {"canvas": {"width": 100, "height": 100}}
    assert current_dpi(cfg) is None


# --- set_dpi (resolución) --------------------------------------------------

def test_set_dpi_keeps_real_size_changes_canvas():
    cfg = base_config()
    new, info = set_dpi(cfg, 300, scale_elements=True)
    assert new["canvas"]["real_size_cm"] == {"width": 16.5, "height": 6.5}
    assert new["canvas"]["width"] == cm_to_px(16.5, 300)
    assert new["canvas"]["height"] == cm_to_px(6.5, 300)
    assert info["modo"] == "dpi"
    assert round(info["dpi_despues"]) == 300


def test_set_dpi_scales_elements():
    cfg = base_config()
    new, info = set_dpi(cfg, 300, scale_elements=True)
    factor = info["factor"]
    # un elemento debe haberse escalado por el factor
    orig_x = base_config()["documents"][0]["elements"][0]["x"]
    assert new["documents"][0]["elements"][0]["x"] == round(orig_x * factor)
    assert factor < 1.0  # de 508 a 300 dpi reduce


def test_set_dpi_no_scale_keeps_elements():
    cfg = base_config()
    new, _ = set_dpi(cfg, 300, scale_elements=False)
    assert new["documents"][0]["elements"][0]["x"] == 110  # intacto


def test_set_dpi_does_not_mutate_input():
    cfg = base_config()
    snapshot = copy.deepcopy(cfg)
    set_dpi(cfg, 300)
    assert cfg == snapshot


def test_set_dpi_invalid():
    with pytest.raises(ValueError):
        set_dpi(base_config(), 0)


def test_set_dpi_requires_real_size():
    cfg = {"canvas": {"width": 100, "height": 100}}
    with pytest.raises(ValueError):
        set_dpi(cfg, 300)


# --- set_real_size (proporción) -------------------------------------------

def test_set_real_size_changes_proportion():
    cfg = base_config()
    new, info = set_real_size(cfg, 14, 10)  # mantiene dpi actual (~508)
    assert new["canvas"]["real_size_cm"] == {"width": 14, "height": 10}
    assert info["modo"] == "proporcion"
    # canvas recalculado al dpi actual
    assert new["canvas"]["width"] == cm_to_px(14, info["dpi_usado"])


def test_set_real_size_default_no_scale_warns():
    cfg = base_config()
    new, info = set_real_size(cfg, 14, 10)
    assert info["elementos_reescalados"] is False
    assert info["aviso"]  # debe avisar que hay que reposicionar
    assert new["documents"][0]["elements"][0]["x"] == 110  # intacto


def test_set_real_size_with_explicit_dpi():
    cfg = base_config()
    new, info = set_real_size(cfg, 14, 10, dpi=300)
    assert info["dpi_usado"] == 300
    assert new["canvas"]["width"] == cm_to_px(14, 300)


def test_set_real_size_invalid():
    with pytest.raises(ValueError):
        set_real_size(base_config(), 0, 10)


# --- rescale_file ----------------------------------------------------------

def test_rescale_file_dpi(tmp_path):
    import json
    p = tmp_path / "config.json"
    p.write_text(json.dumps(base_config()), encoding="utf-8")
    info = rescale_file(p, dpi=300)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["canvas"]["width"] == cm_to_px(16.5, 300)
    assert info["modo"] == "dpi"


def test_rescale_file_proportion_to_out(tmp_path):
    import json
    p = tmp_path / "config.json"
    out = tmp_path / "config_14x10.json"
    p.write_text(json.dumps(base_config()), encoding="utf-8")
    info = rescale_file(p, width_cm=14, height_cm=10, out=out)
    assert out.exists()
    # original intacto
    orig = json.loads(p.read_text(encoding="utf-8"))
    assert orig["canvas"]["real_size_cm"]["width"] == 16.5
    new = json.loads(out.read_text(encoding="utf-8"))
    assert new["canvas"]["real_size_cm"]["width"] == 14


def test_rescale_file_requires_args(tmp_path):
    import json
    p = tmp_path / "config.json"
    p.write_text(json.dumps(base_config()), encoding="utf-8")
    with pytest.raises(ValueError):
        rescale_file(p)
