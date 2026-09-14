"""Tests de normalizacion de eventos RD.

Los casos vienen de los datos REALES de `data/productoras/*.json`, no de
ejemplos inventados: son las formas que la gente escribio de verdad.
"""

from flujo.rd.eventos import (
    ALTA,
    NULA,
    PARCIAL,
    extraer_lineup,
    indice_triangulacion,
    normalizar_evento,
    normalizar_productora,
    parsear_fecha,
)


class TestParsearFecha:
    def test_fecha_completa_en_espanol(self):
        f = parsear_fecha("12 septiembre 2026")
        assert f.iso == "2026-09-12"
        assert f.confianza == ALTA

    def test_iso_se_respeta(self):
        assert parsear_fecha("2026-09-12").iso == "2026-09-12"

    def test_rango_de_dias_toma_el_primero_y_lo_dice(self):
        f = parsear_fecha("11/12-oct-2025")
        assert f.iso == "2025-10-11"
        assert "rango" in f.nota

    def test_sin_anio_no_lo_inventa(self):
        # "MAR 28 (año no confirmado)" es un caso real del repo.
        f = parsear_fecha("MAR 28 (ano no confirmado)")
        assert f.iso is None, "no debe rellenar el año faltante"
        assert f.confianza == PARCIAL
        assert "sin año" in f.nota

    def test_mes_abreviado(self):
        assert parsear_fecha("20-nov-2026").iso == "2026-11-20"

    def test_sin_dia_queda_a_nivel_mes(self):
        f = parsear_fecha("noviembre 2026")
        assert f.iso == "2026-11"
        assert f.confianza == PARCIAL

    def test_texto_ilegible(self):
        f = parsear_fecha("proximamente")
        assert f.iso is None and f.confianza == NULA

    def test_vacia(self):
        assert parsear_fecha("").confianza == NULA


class TestExtraerLineup:
    def test_caso_real_piknic(self):
        line, co = extraer_lineup(
            "Piknic Electronik Santiago -- lineup PARTIBOI69 (co-org GLOVOX)"
        )
        assert "PARTIBOI69" in line
        assert "GLOVOX" in co

    def test_varios_artistas(self):
        line, _ = extraer_lineup("Fiesta con KI/KI, Sama Abdulhadi y Nina Kraviz")
        assert len(line) == 3
        assert "Nina Kraviz" in line

    def test_sin_lineup(self):
        line, co = extraer_lineup("Piknic (edicion sin identificar)")
        assert line == [] and co == []

    def test_no_duplica(self):
        line, _ = extraer_lineup("con ANNA, ANNA")
        assert line == ["ANNA"]


class TestNormalizarProductora:
    def test_agrega_campos_sin_perder_los_originales(self):
        datos = {
            "name": "Piknic",
            "eventos": [{
                "nombre": "Piknic Santiago -- lineup PARTIBOI69 (co-org GLOVOX)",
                "fecha": "12 septiembre 2026",
                "venue": "Parque Padre Hurtado",
                "estado": "activo_venta",
                "fuente": "post IG",
            }],
        }
        salida, avisos = normalizar_productora(datos)
        ev = salida["eventos"][0]
        assert ev["fecha"] == "12 septiembre 2026", "el crudo se conserva"
        assert ev["fecha_iso"] == "2026-09-12"
        assert ev["lineup"] == ["PARTIBOI69"]
        assert ev["co_organiza"] == ["GLOVOX"]
        assert ev["fuente"] == "post IG", "no se pierde la trazabilidad"
        assert salida["name"] == "Piknic"
        assert avisos == []

    def test_avisa_cuando_no_es_triangulable(self):
        datos = {"eventos": [{"nombre": "Piknic sin datos", "fecha": "MAR 28"}]}
        _, avisos = normalizar_productora(datos)
        assert any("no triangulable" in a for a in avisos)
        assert any("fecha" in a for a in avisos)

    def test_respeta_lineup_ya_cargado_a_mano(self):
        datos = {"eventos": [{"nombre": "algo", "fecha": "2026-01-01", "lineup": ["Cargado A Mano"]}]}
        salida, _ = normalizar_productora(datos)
        assert salida["eventos"][0]["lineup"] == ["Cargado A Mano"]

    def test_no_explota_con_datos_corruptos(self):
        salida, avisos = normalizar_productora({"eventos": "no soy una lista"})
        assert salida["eventos"] == "no soy una lista"
        assert avisos


class TestIndiceTriangulacion:
    def test_cruza_artista_entre_productoras(self):
        prods = {
            "piknic": {"eventos": [{"nombre": "a", "lineup": ["PARTIBOI69"], "fecha_iso": "2026-09-12"}]},
            "glovox": {"eventos": [{"nombre": "b", "lineup": ["Partiboi69"], "fecha_iso": "2026-09-12"}]},
        }
        idx = indice_triangulacion(prods)
        assert len(idx["partiboi69"]) == 2, "mayusculas distintas deben caer en la misma clave"
        assert {e["productora"] for e in idx["partiboi69"]} == {"piknic", "glovox"}

    def test_ignora_eventos_sin_lineup(self):
        assert indice_triangulacion({"x": {"eventos": [{"nombre": "sin lineup"}]}}) == {}
