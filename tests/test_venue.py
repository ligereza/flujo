# -*- coding: utf-8 -*-
"""La base de venues: que sembrar de memoria no se disfrace de medicion.

La regla que estos tests fijan es la del §6.4 de la memoria de direccion --
descriptivo, nunca certificante -- aplicada al dato: un venue sembrado desde
tres anios de gira vale, pero vale como `aportado`. `medido` lo escribe quien
estuvo en la sala con instrumento y firma, y ese salto de tier es lo unico que
no es gratis.

Lo que NO se prueba aca: que las cotas sembradas sean correctas. No se midieron,
asi que no se afirma que lo sean; se afirma que el archivo dice de si mismo que
vienen de memoria.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import venue  # noqa: E402

ESQUEMA = json.loads((REPO / "schemas" / "venue.schema.json").read_text(encoding="utf-8"))


def _valida(v: dict) -> list[str]:
    import jsonschema

    val = jsonschema.Draft202012Validator(ESQUEMA)
    return [e.message for e in val.iter_errors(v)]


# ----------------------------------------------------------------- sembrar
def test_sembrar_de_memoria_marca_aportado_nunca_medido():
    v = venue.parsear_semilla("Santiago | Sala Uno | teatro | 10 | 4.5 | 6.2 | 9 | columna")
    assert v["fuente_datos"] == "memoria"
    assert v["escenario"]["ancho"]["confianza"] == "aportado"
    assert v["sala"]["altura_truss"]["confianza"] == "aportado"
    todas = [
        m["confianza"]
        for g in ("escenario", "sala")
        for m in v[g].values()
    ]
    assert "medido" not in todas, "de memoria no es medido"


def test_lo_sembrado_valida_contra_el_esquema():
    v = venue.parsear_semilla("Valparaiso | La Otra | club | 8 | 4 | 5 | 7 | -")
    assert _valida(v) == []


def test_el_id_es_estable_y_sin_tildes():
    v = venue.parsear_semilla("Concepción | Galpón Ñuñoa | galpon | 12 | 6 | - | - | -")
    assert v["id"] == "concepcion-galpon-nunoa"


def test_campos_vacios_no_inventan_medidas():
    v = venue.parsear_semilla("Arica | Sin Datos | otro | - | - | - | - | -")
    assert "escenario" not in v and "sala" not in v
    assert _valida(v) == []


def test_una_semilla_sin_nombre_o_ciudad_se_rechaza():
    with pytest.raises(ValueError):
        venue.parsear_semilla(" | Sin Ciudad | club | 8 | 4 | 5 | 7 | -")


def test_tipo_invalido_se_rechaza():
    with pytest.raises(ValueError):
        venue.parsear_semilla("Santiago | X | discoteque | 8 | 4 | 5 | 7 | -")


def test_comentarios_y_lineas_vacias_se_saltan():
    assert venue.parsear_semilla("# comentario") is None
    assert venue.parsear_semilla("   ") is None


def test_acepta_coma_decimal_y_faltantes_al_final():
    v = venue.parsear_semilla("Osorno | Coma | club | 9,5 | 4")
    assert v["escenario"]["ancho"]["m"] == 9.5
    assert "altura_truss" not in v.get("sala", {})


# ----------------------------------------------------------------- coherencia
def _base(**extra) -> dict:
    v = {
        "id": "x-y",
        "nombre": "Y",
        "ciudad": "X",
        "tipo": "club",
        "publico": True,
        "fecha_captura": "2026-07-30",
        "fuente_datos": "memoria",
    }
    v.update(extra)
    return v


def test_avisa_si_firma_sin_un_solo_dato_medido():
    v = _base(firmado_por="MAK", escenario={"ancho": {"m": 10, "confianza": "aportado"}})
    assert any("firmado pero sin" in a for a in venue.coherencia(v))


def test_avisa_si_dice_medido_pero_la_fuente_es_memoria():
    v = _base(escenario={"ancho": {"m": 10, "confianza": "medido"}})
    assert any("De memoria no es medido" in a for a in venue.coherencia(v))


def test_avisa_si_una_sala_no_publica_lleva_direccion():
    """La geometria es valiosa y anonima; la identidad es peligrosa y no se necesita."""
    v = _base(publico=False, direccion="Calle Falsa 123")
    assert any("publico=false" in a for a in venue.coherencia(v))


def test_avisa_si_la_altura_libre_supera_al_truss():
    v = _base(sala={"altura_truss": {"m": 5, "confianza": "aportado"},
                    "altura_libre": {"m": 6, "confianza": "aportado"}})
    assert any("Imposible" in a for a in venue.coherencia(v))


def test_avisa_si_una_cita_no_trae_fuente():
    v = _base(citas=[{"afirmacion": "truss soporta 500 kg", "fuente": "  "}])
    assert any("sin fuente" in a for a in venue.coherencia(v))


def test_un_venue_limpio_no_genera_avisos():
    v = _base(escenario={"ancho": {"m": 10, "confianza": "aportado"}})
    assert venue.coherencia(v) == []


# ----------------------------------------------------------------- esquema
def test_el_esquema_rechaza_una_confianza_inventada():
    v = _base(escenario={"ancho": {"m": 10, "confianza": "masomenos"}})
    assert _valida(v) != []


def test_el_esquema_exige_confianza_en_cada_medida():
    v = _base(escenario={"ancho": {"m": 10}})
    assert _valida(v) != []


def test_el_esquema_rechaza_medidas_absurdas():
    for malo in (0, -3, 9999):
        v = _base(escenario={"ancho": {"m": malo, "confianza": "aportado"}})
        assert _valida(v) != [], f"acepto {malo} m"


# ----------------------------------------------------------------- geometria
def _poli(**extra) -> dict:
    pl = {"puntos": [[0, 0, 0], [1, 0, 0]], "confianza": "ajustado"}
    pl.update(extra)
    return pl


def _geo(*polilineas, **extra) -> dict:
    g = {"unidad": "m", "polilineas": list(polilineas) or [_poli()]}
    g.update(extra)
    return g


def test_un_venue_sin_geometria_sigue_siendo_valido():
    """El bloque es opcional: la base entera existe sin una sola polilinea."""
    assert _valida(_base()) == []
    v = venue.parsear_semilla("Santiago | Sin Plano | club | 8 | 4 | 5 | 7 | -")
    assert "geometria" not in v and _valida(v) == []


def test_la_geometria_minima_valida():
    assert _valida(_base(geometria=_geo())) == []


def test_la_geometria_exige_confianza_por_polilinea():
    """La confianza es POR LINEA: el contorno medido y el techo supuesto conviven."""
    assert _valida(_base(geometria=_geo({"puntos": [[0, 0, 0], [1, 0, 0]]}))) != []
    assert _valida(_base(geometria=_geo(_poli(confianza="masomenos")))) != []


def test_la_geometria_rechaza_puntos_que_no_son_3d():
    for malo in ([0, 0], [0, 0, 0, 0], [0, 0, "alto"]):
        v = _base(geometria=_geo(_poli(puntos=[[0, 0, 0], malo])))
        assert _valida(v) != [], f"acepto un punto {malo}"


def test_una_polilinea_de_un_solo_punto_no_es_una_linea():
    assert _valida(_base(geometria=_geo(_poli(puntos=[[0, 0, 0]])))) != []


def test_la_unidad_es_metros_y_no_se_negocia():
    """Una geometria con unidad ambigua es una geometria inservible."""
    assert _valida(_base(geometria=_geo(unidad="cm"))) != []


def test_la_geometria_rechaza_coordenadas_absurdas():
    assert _valida(_base(geometria=_geo(_poli(puntos=[[0, 0, 0], [9999, 0, 0]])))) != []


def test_avisa_si_la_geometria_dice_medido_pero_la_fuente_es_memoria():
    v = _base(geometria=_geo(_poli(confianza="medido")))
    assert any("polilineas dicen 'medido'" in a for a in venue.coherencia(v))


def test_la_geometria_ajustada_no_dispara_el_aviso_de_memoria():
    assert venue.coherencia(_base(geometria=_geo())) == []


# ------------------------------------------------------- geometria, medida
def test_medir_geometria_cuenta_aristas_cierres_y_bbox():
    """A closed unit square plus one open diagonal: every number is checkable
    by hand, so a regression here is a wrong count, not a style change."""
    cuadrado = {"puntos": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]],
                "confianza": "medido", "capa": "escenario"}
    diagonal = {"puntos": [[0, 0, 0], [1, 1, 2]], "confianza": "aportado"}
    m = venue.medir_geometria(_base(geometria=_geo(cuadrado, diagonal)))
    assert m["polilineas"] == 2
    assert m["aristas"] == 5
    assert m["puntos"] == 7
    assert m["cerradas"] == 1 and m["abiertas"] == 1
    assert m["degenerados"] == 0
    assert m["dim"] == [1, 1, 2]
    assert m["por_confianza"] == {"medido": 4, "aportado": 1}
    assert m["dim_por_capa"]["escenario"] == [1, 1, 0]


def test_medir_geometria_devuelve_none_sin_bloque():
    assert venue.medir_geometria(_base()) is None


def test_un_segmento_de_largo_cero_se_cuenta_y_se_avisa():
    """It draws nothing and still spends edge budget: a defect the screen
    cannot show, so the numbers have to."""
    pl = _poli(puntos=[[0, 0, 0], [0, 0, 0], [1, 0, 0]])
    v = _base(geometria=_geo(pl))
    assert venue.medir_geometria(v)["degenerados"] == 1
    assert any("largo cero" in a for a in venue.coherencia(v))


def test_avisa_si_la_cota_declarada_contradice_el_dibujo():
    """escenario.ancho says 10 m, the drawn stage layer spans 8 m: one of the
    two lies, and the file has to say so about itself."""
    escenario = {"puntos": [[-4, 0, 0], [4, 0, 0]], "confianza": "aportado",
                 "capa": "escenario"}
    v = _base(escenario={"ancho": {"m": 10, "confianza": "aportado"}},
              geometria=_geo(escenario))
    assert any("Uno de los dos miente" in a for a in venue.coherencia(v))


def test_no_avisa_si_la_cota_y_el_dibujo_coinciden():
    escenario = {"puntos": [[-5, 0, 0], [5, 0, 0]], "confianza": "aportado",
                 "capa": "escenario"}
    v = _base(escenario={"ancho": {"m": 10, "confianza": "aportado"}},
              geometria=_geo(escenario))
    assert not any("miente" in a for a in venue.coherencia(v))


def test_avisa_si_la_geometria_supera_el_tope_del_visor():
    gorda = {"puntos": [[(i % 100) / 10, i // 100, 0] for i in range(900)],
             "confianza": "ajustado"}
    v = _base(geometria=_geo(gorda))
    assert venue.medir_geometria(v)["aristas"] == 899
    assert any("tope del visor" in a for a in venue.coherencia(v))


def test_el_comando_geometria_reporta_numeros_y_falla_con_degenerados(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(venue, "DIR_VENUES", tmp_path)
    limpio = _base(id="limpio", geometria=_geo())
    roto = _base(id="roto",
                 geometria=_geo(_poli(puntos=[[0, 0, 0], [0, 0, 0], [1, 0, 0]])))
    (tmp_path / "limpio.json").write_text(json.dumps(limpio), encoding="utf-8")
    assert venue.geometria() == 0
    salida = capsys.readouterr().out
    assert "limpio: 1 polilineas · 1 aristas" in salida
    (tmp_path / "roto.json").write_text(json.dumps(roto), encoding="utf-8")
    assert venue.geometria() == 1, "un segmento de largo cero tiene que fallar"
    assert "largo cero 1" in capsys.readouterr().out


# ------------------------------------------------- la sala demo que viaja en el repo
DEMO = REPO / "data" / "venues" / "scd-plaza-egana.json"


def _demo() -> dict:
    return json.loads(DEMO.read_text(encoding="utf-8"))


def test_la_sala_demo_existe_y_valida():
    """Es el material por defecto del visor: si no valida, el visor abre roto."""
    assert DEMO.is_file(), "falta la sala demo (py tools/venue_geometria_scd.py)"
    assert _valida(_demo()) == []
    assert venue.coherencia(_demo()) == []


def test_la_sala_demo_se_declara_demo_en_el_archivo():
    """El disclaimer vive en el DATO, no en un README que nadie abre al lado."""
    v = _demo()
    assert "DEMO" in v["notas"] and "DEMO" in v["geometria"]["nota"]
    assert "firmado_por" not in v, "una demo no la firma nadie"
    assert v["fuente_datos"] != "memoria"


def test_la_sala_demo_mezcla_niveles_de_confianza():
    """El visor tiene que poder dibujar solido, segmentado y tenue con datos reales."""
    niveles = {pl["confianza"] for pl in _demo()["geometria"]["polilineas"]}
    assert {"medido", "ajustado"} <= niveles
    assert len(niveles) >= 3, f"la demo no ejercita los tiers: {niveles}"


def test_la_sala_demo_cabe_en_el_presupuesto_de_aristas():
    """800 es el tope declarado del visor. Si la demo lo pasa, el visor recorta
    su propio material por defecto -- avisando, pero recorta."""
    aristas = sum(len(pl["puntos"]) - 1 for pl in _demo()["geometria"]["polilineas"])
    assert 0 < aristas <= 800, f"{aristas} aristas: no cabe en el presupuesto"


def test_la_sala_demo_se_regenera_igual():
    """Derivada de verdad: el archivo del repo es lo que imprime su generador."""
    sys.path.insert(0, str(REPO / "tools"))
    import venue_geometria_scd

    assert venue_geometria_scd.documento() == _demo(), (
        "el archivo y su generador divergieron: correr py tools/venue_geometria_scd.py"
    )


def test_el_check_de_scd_no_escribe_el_json_canonico():
    """CI can verify the demo without invoking the default writer."""
    sys.path.insert(0, str(REPO / "tools"))
    import venue_geometria_scd

    antes = DEMO.read_bytes()
    assert venue_geometria_scd.main(["venue_geometria_scd.py", "--check"]) == 0
    assert DEMO.read_bytes() == antes


def test_la_sala_demo_mide_limpio():
    """The demo passes its own numeric bar: the counts the PR declared, zero
    zero-length segments, and a drawn stage that matches the declared measure
    (that agreement is also what keeps coherencia() silent on it)."""
    m = venue.medir_geometria(_demo())
    assert m["polilineas"] == 56 and m["aristas"] == 503
    assert m["degenerados"] == 0
    dim_esc = m["dim_por_capa"]["escenario"]
    declarado = _demo()["escenario"]
    assert abs(dim_esc[0] - declarado["ancho"]["m"]) <= venue.TOLERANCIA_COTA_M
    assert abs(dim_esc[1] - declarado["profundidad"]["m"]) <= venue.TOLERANCIA_COTA_M


# ------------------------------------------------- orbitas: la camara como dato
ORBITA_ESQUEMA = json.loads(
    (REPO / "schemas" / "orbita.schema.json").read_text(encoding="utf-8"))
DIR_ORBITAS = REPO / "data" / "orbitas"


def _valida_orbita(doc: dict) -> list[str]:
    import jsonschema

    val = jsonschema.Draft202012Validator(ORBITA_ESQUEMA)
    return [e.message for e in val.iter_errors(doc)]


def test_toda_orbita_del_repo_valida_contra_su_esquema():
    """Every committed camera path is schema-clean, or the sequence tool would
    reject at run time what the repo shipped as good."""
    archivos = sorted(DIR_ORBITAS.glob("*.json"))
    assert archivos, "no hay ninguna orbita en data/orbitas/"
    for p in archivos:
        errores = _valida_orbita(json.loads(p.read_text(encoding="utf-8")))
        assert errores == [], f"{p.name}: {errores}"


def test_la_orbita_de_ejemplo_es_la_vuelta_por_defecto():
    """The shipped example IS the viewer's default turn written as data: a
    closed two-keyframe loop from 0 to exactly 2*pi. The node smoke proves the
    frames match; this pins the numbers the claim rests on."""
    import math

    doc = json.loads(
        (DIR_ORBITAS / "vuelta-completa.json").read_text(encoding="utf-8"))
    assert doc["cerrar"] is True
    giros = [k["giro"] for k in doc["puntos"]]
    assert giros == [0, math.tau]


def test_el_esquema_de_orbita_rechaza_lo_invalido():
    for malo in (
        {"puntos": [{"giro": 0}]},                                # 1 keyframe
        {"puntos": [{"alto": 0.4}, {"giro": 1}]},                 # sin giro
        {"puntos": [{"giro": 0, "alto": 2.0}, {"giro": 1}]},      # alto fuera de tope
        {"puntos": [{"giro": 0, "dist": 0}, {"giro": 1}]},        # dist no positiva
        {"puntos": [{"giro": 0}, {"giro": 1}], "sorpresa": 1},    # clave inventada
    ):
        assert _valida_orbita(malo) != [], f"acepto {malo}"


# ----------------------------------------------------------------- sitio
def test_el_sitio_no_publica_las_salas_no_publicas(tmp_path, monkeypatch):
    monkeypatch.setattr(venue, "DIR_VENUES", tmp_path / "v")
    monkeypatch.setattr(venue, "SALIDA_SITIO", tmp_path / "out" / "index.html")
    venue.DIR_VENUES.mkdir(parents=True)
    (venue.DIR_VENUES / "a.json").write_text(
        json.dumps(_base(id="a", nombre="Publica")), encoding="utf-8"
    )
    (venue.DIR_VENUES / "b.json").write_text(
        json.dumps(_base(id="b", nombre="Reservada", publico=False)), encoding="utf-8"
    )
    assert venue.sitio() == 0
    html = venue.SALIDA_SITIO.read_text(encoding="utf-8")
    assert "Publica" in html
    assert "Reservada" not in html, "una sala con publico=false no puede salir en el sitio"


def test_el_sitio_es_un_solo_archivo_sin_red(tmp_path, monkeypatch):
    monkeypatch.setattr(venue, "DIR_VENUES", tmp_path / "v")
    monkeypatch.setattr(venue, "SALIDA_SITIO", tmp_path / "out" / "index.html")
    venue.DIR_VENUES.mkdir(parents=True)
    (venue.DIR_VENUES / "a.json").write_text(json.dumps(_base()), encoding="utf-8")
    venue.sitio()
    html = venue.SALIDA_SITIO.read_text(encoding="utf-8")
    assert "<script src=" not in html and "cdn" not in html.lower()
    assert "localStorage" not in html
