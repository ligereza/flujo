"""
Harm-reduction color matching for reagent tests.

DISCLAIMER: Colorimetry is ORIENTATIVE ONLY, never confirmatory. Results depend on
lighting conditions, reagent freshness, and observer perception. Reagent testing NEVER
establishes safety or purity -- results are PRESUMPTIVE only, indicating possible
presence of a substance family, not identification with certainty or purity measurement.
A color match does NOT make a substance safe.

This module ranks observed hex colors against a reference palette of known reagent
reactions using CIE76 perceptual distance (sRGB -> Lab color space).

Functions:
  hex_a_rgb(hex_str) -> (r, g, b)
  rgb_a_lab(rgb) -> (L, a, b)
  delta_e76(lab1, lab2) -> float
  cargar_reactivos(path) -> list[dict]
  ranquear(hex_observado, reactivos, top=5) -> list[dict]
  clasificar(hex_observado, path=None, top=5) -> dict
  main(argv) -> int
"""

from __future__ import annotations
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def hex_a_rgb(hex_str: str) -> Tuple[int, int, int]:
    """
    Parse hex color string to RGB tuple.

    Tolerates:
      - With or without '#' prefix
      - 3-digit form (#RGB -> #RRGGBB)
      - 6-digit form (#RRGGBB)

    Args:
        hex_str: Color in hex format (e.g., "#3b1a4a", "3b1a4a", "#f0f")

    Returns:
        (r, g, b) tuple with values 0-255

    Raises:
        ValueError: If hex format is invalid
    """
    s = hex_str.lstrip("#").upper()

    if len(s) == 3:
        # 3-digit: expand each digit
        try:
            r = int(s[0] * 2, 16)
            g = int(s[1] * 2, 16)
            b = int(s[2] * 2, 16)
            return (r, g, b)
        except ValueError as e:
            raise ValueError(f"Invalid 3-digit hex: {hex_str}") from e
    elif len(s) == 6:
        # 6-digit
        try:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            return (r, g, b)
        except ValueError as e:
            raise ValueError(f"Invalid 6-digit hex: {hex_str}") from e
    else:
        raise ValueError(f"Hex must be 3 or 6 digits (got {len(s)}): {hex_str}")


def rgb_a_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    Convert sRGB to CIELAB color space.

    Standard formulas:
      1. Normalize RGB to 0..1
      2. Apply gamma (sRGB companding)
      3. Convert to XYZ (D65 illuminant)
      4. Convert XYZ to Lab

    Args:
        rgb: (r, g, b) with values 0-255

    Returns:
        (L, a, b) tuple
          L: 0..100 (lightness)
          a: ~-128..127 (red-green axis)
          b: ~-128..127 (yellow-blue axis)
    """
    # Normalize to 0..1
    r = rgb[0] / 255.0
    g = rgb[1] / 255.0
    b = rgb[2] / 255.0

    # sRGB gamma inverse (linearize)
    def srgb_to_linear(c: float) -> float:
        if c <= 0.04045:
            return c / 12.92
        else:
            return math.pow((c + 0.055) / 1.055, 2.4)

    r_linear = srgb_to_linear(r)
    g_linear = srgb_to_linear(g)
    b_linear = srgb_to_linear(b)

    # RGB to XYZ (D65 matrix)
    x = r_linear * 0.4124564 + g_linear * 0.3575761 + b_linear * 0.1804375
    y = r_linear * 0.2126729 + g_linear * 0.7151522 + b_linear * 0.0721750
    z = r_linear * 0.0193339 + g_linear * 0.1191920 + b_linear * 0.9503041

    # D65 reference white point
    x_ref = 0.95047
    y_ref = 1.00000
    z_ref = 1.08883

    # Normalize
    x = x / x_ref
    y = y / y_ref
    z = z / z_ref

    # XYZ to Lab
    delta = 6.0 / 29.0

    def f(t: float) -> float:
        if t > delta ** 3:
            return math.pow(t, 1.0 / 3.0)
        else:
            return t / (3 * delta ** 2) + 4.0 / 29.0

    f_x = f(x)
    f_y = f(y)
    f_z = f(z)

    L = 116 * f_y - 16
    a = 500 * (f_x - f_y)
    b_out = 200 * (f_y - f_z)

    return (L, a, b_out)


def delta_e76(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """
    CIE76 color difference (Euclidean distance in Lab space).

    Simple, fast, perceptually reasonable for near colors.
    Values < 2 are generally imperceptible to human eye.

    Args:
        lab1, lab2: Lab tuples (L, a, b)

    Returns:
        Delta E (distance, >= 0)
    """
    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return math.sqrt(dL ** 2 + da ** 2 + db ** 2)


def cargar_reactivos(path: Path | str) -> List[Dict]:
    """
    Load reagent reference palette from reactivos.json.

    Normalizes entries to {"reactivo", "familia", "hex"} schema.
    Skips entries missing or with invalid hex.

    Args:
        path: Path to reactivos.json

    Returns:
        List of normalized dicts, each with fields:
          - reactivo: str
          - familia: str
          - hex: str (validated 6-digit format)
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = []
    reactions = data.get("reacciones", [])

    for entry in reactions:
        reactivo = entry.get("reactivo", "").strip()
        familia = entry.get("familia", "").strip()
        hex_val = entry.get("hex", "").strip()

        # Validate
        if not reactivo or not familia or not hex_val:
            continue

        try:
            # Try to parse and normalize hex
            rgb = hex_a_rgb(hex_val)
            # Reformat to standard 6-digit lowercase
            normalized_hex = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except ValueError:
            # Skip invalid hex
            continue

        result.append({
            "reactivo": reactivo,
            "familia": familia,
            "hex": normalized_hex,
        })

    return result


def ranquear(
    hex_observado: str,
    reactivos: List[Dict],
    top: int = 5,
) -> List[Dict]:
    """
    Rank reactivos by perceptual distance to observed color.

    Args:
        hex_observado: Hex color observed in test
        reactivos: List of reference reactivos (from cargar_reactivos)
        top: Number of top matches to return

    Returns:
        Sorted list (ascending delta_e) of dicts:
          {reactivo, familia, hex, delta_e (float, rounded to 2 decimals)}
    """
    try:
        obs_rgb = hex_a_rgb(hex_observado)
    except ValueError:
        return []

    obs_lab = rgb_a_lab(obs_rgb)

    matches = []
    for rxn in reactivos:
        try:
            ref_rgb = hex_a_rgb(rxn["hex"])
            ref_lab = rgb_a_lab(ref_rgb)
            de = delta_e76(obs_lab, ref_lab)
            matches.append({
                "reactivo": rxn["reactivo"],
                "familia": rxn["familia"],
                "hex": rxn["hex"],
                "delta_e": round(de, 2),
            })
        except ValueError:
            continue

    # Sort by delta_e ascending
    matches.sort(key=lambda x: x["delta_e"])

    return matches[:top]


def clasificar(
    hex_observado: str,
    path: Optional[Path | str] = None,
    top: int = 5,
) -> Dict:
    """
    Classify observed color against reagent palette with disclaimer.

    DISCLAIMER: Colorimetry is ORIENTATIVE ONLY. Results depend on lighting,
    reagent freshness, and perception. Reagent testing NEVER establishes safety
    or purity -- PRESUMPTIVE only. A color match does NOT verify identity or
    safety of any substance.

    Args:
        hex_observado: Observed hex color
        path: Path to reactivos.json (defaults to C:\\IA\\flujo\\projects\\cultura\\identidad\\reactivos.json)
        top: Number of top candidates to return

    Returns:
        Dict with keys:
          - observado: str (normalized hex)
          - candidatos: list of ranked matches
          - nota: disclaimer string
    """
    if path is None:
        path = Path(r"C:\IA\flujo\projects\cultura\identidad\reactivos.json")

    try:
        obs_rgb = hex_a_rgb(hex_observado)
        normalized_hex = f"#{obs_rgb[0]:02x}{obs_rgb[1]:02x}{obs_rgb[2]:02x}"
    except ValueError:
        normalized_hex = hex_observado

    try:
        reactivos = cargar_reactivos(path)
        candidatos = ranquear(hex_observado, reactivos, top=top)
    except Exception:
        candidatos = []

    disclaimer = (
        "DISCLAIMER: Colorimetry is ORIENTATIVE ONLY, never confirmatory. "
        "Results depend on lighting conditions, reagent freshness, and observer perception. "
        "Reagent testing NEVER establishes safety or purity -- results are PRESUMPTIVE only, "
        "indicating possible presence of a substance family, not identification with certainty "
        "or purity measurement. A color match does NOT make a substance safe."
    )

    return {
        "observado": normalized_hex,
        "candidatos": candidatos,
        "nota": disclaimer,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI interface: py -m flujo.analyze.reactivo_matcher "#HEX" [--top N] [--json]

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        0 on success, 1 on error
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: python -m flujo.analyze.reactivo_matcher <hex_color> [--top N] [--json]")
        print("Example: python -m flujo.analyze.reactivo_matcher '#3b1a4a' --top 5")
        return 1

    hex_obs = argv[0]
    top_n = 5
    as_json = False

    i = 1
    while i < len(argv):
        if argv[i] == "--top" and i + 1 < len(argv):
            try:
                top_n = int(argv[i + 1])
                i += 2
            except ValueError:
                print(f"Error: --top requires an integer")
                return 1
        elif argv[i] == "--json":
            as_json = True
            i += 1
        else:
            i += 1

    result = clasificar(hex_obs, top=top_n)

    if as_json:
        import json as json_module
        print(json_module.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Observed color: {result['observado']}")
        print(f"\nTop {len(result['candidatos'])} matches:")
        print("-" * 70)
        for i, match in enumerate(result["candidatos"], 1):
            print(
                f"{i}. {match['reactivo']:15} | {match['familia']:30} | "
                f"{match['hex']:8} | E={match['delta_e']:6.2f}"
            )
        print("-" * 70)
        print(f"\n{result['nota']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
