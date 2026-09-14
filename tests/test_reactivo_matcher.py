"""
Comprehensive tests for reactivo_matcher color matching module.

Tests hex parsing, Lab conversions, color distance, and reagent ranking.
No network calls. Uses fixtures with the real reactivos.json schema.
"""

import json
import math
import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flujo.analyze.reactivo_matcher import (
    hex_a_rgb,
    rgb_a_lab,
    delta_e76,
    cargar_reactivos,
    ranquear,
    clasificar,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tmp_reactivos_file(tmp_path):
    """
    Create a temporary reactivos.json file with the real schema.
    Uses 3 actual entries copied from the real file.
    """
    reactivos_data = {
        "disclaimer": "Test disclaimer",
        "fuente": "Test source",
        "reacciones": [
            {
                "reactivo": "Marquis",
                "familia": "MDMA / MDA",
                "reaccion": "violeta a negro",
                "hex": "#3b1a4a"
            },
            {
                "reactivo": "Marquis",
                "familia": "anfetamina",
                "reaccion": "naranja a marron",
                "hex": "#b5651d"
            },
            {
                "reactivo": "Ehrlich",
                "familia": "LSD / indoles",
                "reaccion": "purpura a magenta",
                "hex": "#7a1f5a"
            },
        ]
    }

    file_path = tmp_path / "reactivos.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(reactivos_data, f)

    return file_path


@pytest.fixture
def corrupt_reactivos_file(tmp_path):
    """
    Create a file with some corrupt/invalid entries (missing hex, bad format).
    Should still load valid entries and skip invalid ones.
    """
    reactivos_data = {
        "reacciones": [
            {
                "reactivo": "Marquis",
                "familia": "MDMA",
                "hex": "#3b1a4a"
            },
            {
                "reactivo": "BadEntry",
                "familia": "Unknown",
                # Missing hex field
            },
            {
                "reactivo": "AlsoBad",
                "familia": "Test",
                "hex": "#zzz"  # Invalid hex
            },
            {
                "reactivo": "Ehrlich",
                "familia": "LSD",
                "hex": "#7a1f5a"
            },
        ]
    }

    file_path = tmp_path / "reactivos_corrupt.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(reactivos_data, f)

    return file_path


# ============================================================================
# Test hex_a_rgb parsing
# ============================================================================

def test_hex_6digit_with_hash():
    """Parse 6-digit hex with # prefix"""
    r, g, b = hex_a_rgb("#3b1a4a")
    assert r == 0x3b
    assert g == 0x1a
    assert b == 0x4a


def test_hex_6digit_without_hash():
    """Parse 6-digit hex without # prefix"""
    r, g, b = hex_a_rgb("3b1a4a")
    assert r == 0x3b
    assert g == 0x1a
    assert b == 0x4a


def test_hex_3digit_with_hash():
    """Parse 3-digit hex (shorthand) with # prefix"""
    r, g, b = hex_a_rgb("#f0a")
    # f -> ff (255), 0 -> 00 (0), a -> aa (170)
    assert r == 0xff
    assert g == 0x00
    assert b == 0xaa


def test_hex_3digit_without_hash():
    """Parse 3-digit hex without #"""
    r, g, b = hex_a_rgb("f0a")
    assert r == 0xff
    assert g == 0x00
    assert b == 0xaa


def test_hex_invalid_length():
    """Reject invalid hex length"""
    with pytest.raises(ValueError, match="Hex must be 3 or 6 digits"):
        hex_a_rgb("#12")

    with pytest.raises(ValueError, match="Hex must be 3 or 6 digits"):
        hex_a_rgb("#1234567")


def test_hex_invalid_chars():
    """Reject non-hex characters"""
    with pytest.raises(ValueError, match="Invalid.*hex"):
        hex_a_rgb("#zzz000")


# ============================================================================
# Test Lab conversion with known values
# ============================================================================

def test_lab_pure_black():
    """Black (0,0,0) should have L ≈ 0"""
    L, a, b = rgb_a_lab((0, 0, 0))
    assert L < 1.0  # Should be very close to 0
    assert abs(a) < 2  # a and b should be near 0 for neutral color
    assert abs(b) < 2


def test_lab_pure_white():
    """White (255,255,255) should have L ≈ 100"""
    L, a, b = rgb_a_lab((255, 255, 255))
    assert 99 < L < 101  # Tolerance 0.5
    assert abs(a) < 2
    assert abs(b) < 2


def test_lab_gray_neutral():
    """Middle gray (128,128,128) should be neutral in a,b"""
    L, a, b = rgb_a_lab((128, 128, 128))
    assert 40 < L < 60  # Roughly middle
    assert abs(a) < 3  # Neutral
    assert abs(b) < 3


def test_lab_pure_red():
    """Pure red should have positive a, negative/small b"""
    L, a, b = rgb_a_lab((255, 0, 0))
    assert L > 50  # Red is somewhat bright
    assert a > 0  # Should be on red side
    # b can vary but shouldn't be too negative


def test_lab_pure_blue():
    """Pure blue should have negative b (blue-ish)"""
    L, a, b = rgb_a_lab((0, 0, 255))
    assert L < 50  # Blue is darker
    assert b < 0  # Should be on blue side


# ============================================================================
# Test delta_e76 distance
# ============================================================================

def test_delta_e76_identical():
    """Same color should have delta_e = 0"""
    lab = (50.0, 20.0, 30.0)
    de = delta_e76(lab, lab)
    assert de == 0.0


def test_delta_e76_symmetric():
    """delta_e(A,B) should equal delta_e(B,A)"""
    lab1 = (50.0, 20.0, 30.0)
    lab2 = (55.0, 25.0, 35.0)
    de1 = delta_e76(lab1, lab2)
    de2 = delta_e76(lab2, lab1)
    assert de1 == de2


def test_delta_e76_euclidean():
    """Verify euclidean distance calculation"""
    lab1 = (0.0, 0.0, 0.0)
    lab2 = (3.0, 4.0, 0.0)
    # sqrt(3^2 + 4^2 + 0^2) = sqrt(25) = 5
    de = delta_e76(lab1, lab2)
    assert abs(de - 5.0) < 0.01


def test_delta_e76_nonnegative():
    """delta_e should always be >= 0"""
    lab1 = (50.0, 20.0, 30.0)
    lab2 = (40.0, 10.0, 20.0)
    de = delta_e76(lab1, lab2)
    assert de >= 0


# ============================================================================
# Test cargar_reactivos with real schema
# ============================================================================

def test_cargar_reactivos_valid_file(tmp_reactivos_file):
    """Load valid reactivos file with real schema"""
    reactivos = cargar_reactivos(tmp_reactivos_file)

    # Should have 3 valid entries
    assert len(reactivos) == 3

    # Check first entry normalized
    first = reactivos[0]
    assert first["reactivo"] == "Marquis"
    assert first["familia"] == "MDMA / MDA"
    assert first["hex"] == "#3b1a4a"  # Normalized


def test_cargar_reactivos_skips_corrupt(corrupt_reactivos_file):
    """Skip corrupt entries (missing hex, invalid format)"""
    reactivos = cargar_reactivos(corrupt_reactivos_file)

    # Should only load 2 valid entries (skip BadEntry and AlsoBad)
    assert len(reactivos) == 2

    # Valid entries should be present
    reactivos_names = {r["reactivo"] for r in reactivos}
    assert "Marquis" in reactivos_names
    assert "Ehrlich" in reactivos_names
    assert "BadEntry" not in reactivos_names
    assert "AlsoBad" not in reactivos_names


def test_cargar_reactivos_normalizes_hex(tmp_reactivos_file):
    """Hex values should be normalized to lowercase #RRGGBB"""
    reactivos = cargar_reactivos(tmp_reactivos_file)

    for r in reactivos:
        hex_val = r["hex"]
        assert hex_val.startswith("#")
        assert len(hex_val) == 7  # # + 6 hex digits
        assert hex_val.islower()  # Normalized to lowercase


# ============================================================================
# Test ranquear ranking
# ============================================================================

def test_ranquear_ordering(tmp_reactivos_file):
    """ranquear should return results sorted by delta_e ascending"""
    reactivos = cargar_reactivos(tmp_reactivos_file)

    # Use an exact color from the file
    results = ranquear("#3b1a4a", reactivos, top=5)

    assert len(results) > 0

    # First result should be exact or very close match
    first_de = results[0]["delta_e"]
    assert first_de < 1.0  # Should be nearly identical

    # Results should be sorted ascending
    delta_es = [r["delta_e"] for r in results]
    assert delta_es == sorted(delta_es)


def test_ranquear_top_limit(tmp_reactivos_file):
    """ranquear should respect top parameter"""
    reactivos = cargar_reactivos(tmp_reactivos_file)

    results_top2 = ranquear("#3b1a4a", reactivos, top=2)
    results_top1 = ranquear("#3b1a4a", reactivos, top=1)
    results_all = ranquear("#3b1a4a", reactivos, top=100)

    assert len(results_top2) <= 2
    assert len(results_top1) <= 1
    assert len(results_all) <= len(reactivos)


def test_ranquear_includes_fields():
    """ranquear results should have all required fields"""
    reactivos = [
        {"reactivo": "Test1", "familia": "Family1", "hex": "#000000"},
        {"reactivo": "Test2", "familia": "Family2", "hex": "#ffffff"},
    ]

    results = ranquear("#7f7f7f", reactivos, top=5)

    for result in results:
        assert "reactivo" in result
        assert "familia" in result
        assert "hex" in result
        assert "delta_e" in result
        assert isinstance(result["delta_e"], float)


# ============================================================================
# Test clasificar with disclaimer
# ============================================================================

def test_clasificar_includes_disclaimer():
    """clasificar should always include disclaimer/nota"""
    result = clasificar("#3b1a4a", path=None, top=5)

    assert "nota" in result
    assert "disclaimer" in result["nota"].lower()
    assert "orientative" in result["nota"].lower()
    assert "safety" in result["nota"].lower()


def test_clasificar_includes_candidatos():
    """clasificar should include candidatos list"""
    result = clasificar("#3b1a4a", path=None, top=5)

    assert "candidatos" in result
    assert isinstance(result["candidatos"], list)


def test_clasificar_includes_observado():
    """clasificar should include normalized observed hex"""
    result = clasificar("#3b1a4a", path=None, top=5)

    assert "observado" in result
    assert result["observado"].startswith("#")


def test_clasificar_with_tmp_file(tmp_reactivos_file):
    """clasificar should work with custom reactivos path"""
    result = clasificar("#3b1a4a", path=tmp_reactivos_file, top=5)

    assert "candidatos" in result
    assert "nota" in result

    # With only 3 entries in tmp file, should have at most 3 candidates
    assert len(result["candidatos"]) <= 3


# ============================================================================
# Test main CLI interface
# ============================================================================

def test_main_with_no_args(capsys):
    """main with no args should show usage"""
    from flujo.analyze.reactivo_matcher import main

    ret = main([])
    assert ret == 1

    captured = capsys.readouterr()
    assert "Usage" in captured.out


def test_main_basic_color(capsys):
    """main should process a basic color argument"""
    from flujo.analyze.reactivo_matcher import main

    ret = main(["#3b1a4a"])
    assert ret == 0

    captured = capsys.readouterr()
    assert "Observed color" in captured.out or "observado" in captured.out


def test_main_with_top_arg(capsys):
    """main should parse --top argument"""
    from flujo.analyze.reactivo_matcher import main

    ret = main(["#3b1a4a", "--top", "3"])
    assert ret == 0


def test_main_json_output(capsys):
    """main should output JSON with --json flag"""
    from flujo.analyze.reactivo_matcher import main

    ret = main(["#3b1a4a", "--json"])
    assert ret == 0

    captured = capsys.readouterr()
    # Should contain JSON-like output
    assert "{" in captured.out


# ============================================================================
# Integration test: end-to-end workflow
# ============================================================================

def test_e2e_workflow(tmp_reactivos_file):
    """End-to-end: load file, classify color, check results"""
    # Load reactivos
    reactivos = cargar_reactivos(tmp_reactivos_file)
    assert len(reactivos) > 0

    # Classify a color not in the file (should find closest)
    result = clasificar("#3b1a4a", path=tmp_reactivos_file, top=5)

    # Verify structure
    assert "observado" in result
    assert "candidatos" in result
    assert "nota" in result

    # Should have found matches
    assert len(result["candidatos"]) > 0

    # First candidate should be exact or close match
    first = result["candidatos"][0]
    assert first["delta_e"] < 2.0  # Within perceptible threshold
