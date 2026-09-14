# -*- coding: utf-8 -*-
"""The RD tariff has ONE source: data/rd_packs.json.

The web projection imports that JSON at build time and the hub serves the same
source at runtime. Keep this test aligned with that architecture: a stale
hardcoded TypeScript price would recreate the old split-brain tariff.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARIFA = REPO_ROOT / "data" / "rd_packs.json"
RD_BRAND = REPO_ROOT / "web" / "src" / "rdBrand.ts"


def _precios_del_json() -> dict[str, int]:
    datos = json.loads(TARIFA.read_text(encoding="utf-8"))
    return {pid: int(p["precio"]) for pid, p in datos["packs"].items()}


def test_python_lee_la_tarifa_del_archivo():
    from flujo.plano import packs

    esperado = _precios_del_json()
    real = {pid: int(p["precio"]) for pid, p in packs.PACKS.items()}
    assert real == esperado, (
        "packs.py no esta leyendo data/rd_packs.json (probablemente cayo al "
        "respaldo interno; revisa el aviso en stderr)"
    )


def test_el_proyecto_typescript_importa_la_tarifa_canonica():
    texto = RD_BRAND.read_text(encoding="utf-8")
    assert "import tariffData from '../../data/rd_packs.json';" in texto
    assert re.search(r"export const PACKS(?::[^=]+)? = TARIFF\.packs;", texto)
    assert not re.search(r"id:\s*'[A-Z]+'.*?precio:\s*[\d_]+'?", texto, re.S), (
        "rdBrand.ts no debe volver a contener una copia hardcoded de precios"
    )


def test_editar_el_archivo_se_ve_sin_reiniciar():
    """La tarifa se lee al importar el modulo, y el hub vive horas. Sin esta
    recarga, editar data/rd_packs.json no cambiaba nada hasta reiniciar -- que
    es lo mismo que no ser configurable. Medido en vivo el 2026-07-26: el hub
    seguia sirviendo el precio del arranque."""
    from flujo.plano import packs

    original = TARIFA.read_text(encoding="utf-8")
    datos = json.loads(original)
    pid = next(iter(datos["packs"]))
    previo = packs.PACKS[pid]["precio"]
    try:
        datos["packs"][pid]["precio"] = previo + 12345
        TARIFA.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        packs.recargar_tarifa()
        assert packs.PACKS[pid]["precio"] == previo + 12345
    finally:
        TARIFA.write_text(original, encoding="utf-8")
        packs.recargar_tarifa()
    assert packs.PACKS[pid]["precio"] == previo


def test_el_hub_recarga_antes_de_responder():
    fuente = (REPO_ROOT / "src" / "flujo" / "web" / "hub.py").read_text(encoding="utf-8")
    assert fuente.count("recargar_tarifa()") >= 2, (
        "el endpoint de tarifa y el render del plano deben releer el archivo; "
        "si no, el hub responde con la copia del arranque"
    )
    assert "recargar_catalogo()" in fuente, (
        "el render del plano debe releer el catalogo de simbolos: un icono "
        "recien agregado no puede exigir reiniciar el hub"
    )


SERVICIOS = REPO_ROOT / "data" / "cotizacion_servicios.json"
SERVICIOS_TS = REPO_ROOT / "web" / "src" / "data" / "cotizacionServicios.ts"


def test_los_servicios_de_cotizacion_son_configurables():
    """Palabra del usuario, 2026-07-26: "esos valores son configurables cierto?
    cada archivo de illustrator es distinto y los valores igual". Estaban
    cableados en QuotePanel.tsx."""
    datos = json.loads(SERVICIOS.read_text(encoding="utf-8"))
    assert datos["items_por_defecto"], "sin items por defecto"
    assert datos["presets"], "sin presets"
    for preset in datos["presets"]:
        assert preset["label"] and preset["items"]
        for item in preset["items"]:
            assert isinstance(item["precio"], int) and item["precio"] >= 0

    panel = (REPO_ROOT / "web" / "src" / "components" / "QuotePanel.tsx").read_text(encoding="utf-8")
    assert "const PRESETS" not in panel and "const DEFAULT_ITEMS" not in panel, (
        "QuotePanel.tsx volvio a cablear los valores; se leen de "
        "data/cotizacion_servicios.json"
    )


def test_el_respaldo_de_servicios_coincide_con_el_archivo():
    """Mismo criterio que la tarifa: un respaldo que contradice al archivo es
    peor que no tener respaldo."""
    datos = json.loads(SERVICIOS.read_text(encoding="utf-8"))
    ts = SERVICIOS_TS.read_text(encoding="utf-8")
    del_json = sorted(
        (i["label"], int(i["precio"]))
        for grupo in [datos["items_por_defecto"]] + [p["items"] for p in datos["presets"]]
        for i in grupo
    )
    del_ts = sorted(
        (label, int(precio))
        for label, precio in re.findall(
            r"label:\s*'([^']+)',\s*qty:\s*\d+,\s*price:\s*(\d+)", ts)
    )
    assert del_ts == del_json, (
        "el respaldo de web/src/data/cotizacionServicios.ts quedo desfasado de "
        "data/cotizacion_servicios.json; se actualizan en el mismo commit.\n"
        f"  solo en json: {sorted(set(del_json) - set(del_ts))}\n"
        f"  solo en ts:   {sorted(set(del_ts) - set(del_json))}"
    )


def test_el_hub_sirve_la_misma_tarifa():
    """/api/rd-packs sale del modulo packs, no de una copia aparte."""
    from flujo.plano import packs

    fuente = (REPO_ROOT / "src" / "flujo" / "web" / "hub.py").read_text(encoding="utf-8")
    assert '"/api/rd-packs"' in fuente, "el endpoint desaparecio"
    assert "_packs.PACKS" in fuente, (
        "el endpoint dejo de servir flujo.plano.packs; una tercera copia de la "
        "tarifa es exactamente el defecto que esto evita"
    )
    assert packs.ALL_PACKS and packs.DEFAULT_PACK in packs.PACKS
