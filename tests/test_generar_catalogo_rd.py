"""Tests para scripts/generar_catalogo_rd.py (catalogo RD regenerable).

El modulo no vive bajo scripts/__init__.py (scripts/ no es un paquete), asi
que se carga por ruta via importlib -- mismo patron que
tests/test_vj_git_performance.py.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from flujo.plano.packs import ALL_PACKS, PACKS

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generar_catalogo_rd.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generar_catalogo_rd_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cat = _load_module()


def test_render_catalogo_es_deterministico():
    """Misma entrada (packs.py real) -> mismo texto, sin timestamps que ensucien el diff."""
    primero = cat.render_catalogo()
    segundo = cat.render_catalogo()
    assert primero == segundo
    assert len(primero) > 0
    # No hay fecha de hoy ni reloj colado en el contenido.
    assert "datetime" not in primero.lower()


def test_main_regenera_bytes_identicos_en_dos_corridas():
    """Correr el generador dos veces produce exactamente el mismo archivo (byte a byte)."""
    assert cat.main() == 0
    primero = cat.OUTPUT.read_bytes()

    assert cat.main() == 0
    segundo = cat.OUTPUT.read_bytes()

    assert primero == segundo


def test_catalogo_generado_coincide_con_render():
    """docs/CATALOGO_RD.md (el entregable real) esta al dia con render_catalogo()."""
    cat.main()
    en_disco = cat.OUTPUT.read_text(encoding="utf-8")
    assert en_disco == cat.render_catalogo()


def test_catalogo_contiene_todos_los_packs_de_packs_py():
    contenido = cat.render_catalogo()
    assert ALL_PACKS, "packs.py no deberia quedar vacio"
    for pack_id in ALL_PACKS:
        pack = PACKS[pack_id]
        assert pack_id in contenido
        assert pack["nombre"] in contenido
        assert pack["label"] in contenido
        for inclusion in pack["inclusiones"]:
            assert inclusion in contenido


def test_desglose_completo_deriva_precio_por_pct():
    """El desglose de COMPLETO en el catalogo es precio*pct/100, no un numero aparte."""
    contenido = cat.render_catalogo()
    pack = PACKS["COMPLETO"]
    for prop in pack["proporciones"]:
        monto_esperado = round(pack["precio"] * prop["pct"] / 100)
        assert f"{prop['label']} | {prop['pct']}% | ${monto_esperado:,.0f}" in contenido


def test_script_no_hardcodea_precios():
    """Los precios de los packs no deben aparecer como literal en el codigo del script:
    tienen que llegar siempre importando flujo.plano.packs, nunca pegados a mano."""
    fuente = MODULE_PATH.read_text(encoding="utf-8")

    for pack_id in ALL_PACKS:
        precio = PACKS[pack_id]["precio"]
        for variante in (str(precio), f"{precio:,}", f"{precio:_}"):
            assert variante not in fuente, (
                f"precio hardcodeado sospechoso en generar_catalogo_rd.py: {variante!r} "
                f"(pack {pack_id})"
            )

    assert "from flujo.plano.packs import" in fuente
    assert "PACKS" in fuente


def test_print_solo_en_feedback_cli():
    """'no print except CLI feedback': los print() quedan confinados a main()."""
    fuente = MODULE_PATH.read_text(encoding="utf-8")
    antes_de_main = fuente.split("\ndef main()")[0]
    assert "print(" not in antes_de_main


def test_fuente_del_script_es_ascii():
    fuente_bytes = MODULE_PATH.read_bytes()
    fuente_bytes.decode("ascii")  # lanza UnicodeDecodeError si hay un byte no-ASCII


def test_footer_marca_el_archivo_como_generado():
    contenido = cat.render_catalogo()
    assert "NO editar a mano" in contenido
    assert "scripts/generar_catalogo_rd.py" in contenido


def test_reporta_estado_real_del_motor_de_cotizaciones():
    """No debe fingir que engine.py anda si no anda: o hay ejemplos reales de
    generar_cotizacion(), o queda constancia explicita del error real."""
    contenido = cat.render_catalogo()
    motor_ok = "engine.py funciono" in contenido
    motor_roto = "Estado del motor de cotizaciones" in contenido
    assert motor_ok or motor_roto
    assert "productora" in contenido
    assert "interno" in contenido
