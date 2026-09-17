"""
Tests de la base de datos RD (src/flujo/rd/database.py).

La DB es una proyeccion regenerable de fuentes canonicas: estos tests fijan que
build_rd_db es idempotente/deterministico, que las 6 tablas cargan datos reales,
que las queries cruzan bien (reactivo x familia, evento -> pack por voluntarios),
that the presumptive disclaimer travels with the data and historical evidence
stays isolated, traceable, and pending review.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from flujo.rd import database as db


@pytest.fixture()
def rd_db(tmp_path: Path) -> Path:
    return db.build_rd_db(tmp_path / "rd.db")


def _tables(path: Path) -> dict[str, int]:
    conn = db.connect(path)
    try:
        return {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("meta", "reactivos", "packs", "inclusiones", "suplementos", "productoras", "eventos")
        }
    finally:
        conn.close()


def test_rd_db_override_points_to_one_external_host_projection(tmp_path: Path, monkeypatch):
    from flujo.rd.paths import rd_db_path

    assert rd_db_path(tmp_path) == tmp_path / "data" / "rd.db"
    external = tmp_path / "mak" / "data" / "rd.db"
    monkeypatch.setenv("FLUJO_RD_DB", str(external))
    assert rd_db_path(tmp_path) == external.resolve()


def test_build_crea_las_6_tablas_con_datos(rd_db: Path):
    n = _tables(rd_db)
    assert n["reactivos"] >= 20        # 21 reacciones en la carta canonica
    assert n["packs"] == 3             # INFO / TESTEO / COMPLETO
    assert n["inclusiones"] >= 12
    assert n["suplementos"] >= 8
    assert n["productoras"] >= 1       # The Grid
    # >=1: eventos incluye fuentes en jobs/ que son gitignored (no estan en un
    # checkout limpio/CI); el piso garantizado es el ejemplo TRACKED de plano.
    assert n["eventos"] >= 1
    assert n["meta"] == 1              # disclaimer


def test_testing_evidence_is_isolated_and_traceable(rd_db: Path):
    conn = db.connect(rd_db)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        expected = {
            "testeo_fuentes",
            "testeo_hojas",
            "testeo_eventos_fuente",
            "testeo_filas_fuente",
            "testeo_observaciones_fuente",
            "testeo_mapa_sustancias",
            "testeo_mapa_reactivos",
            "testeo_enlaces_revision",
        }
        assert expected <= tables
        # `registros_testeo` vive aqui desde el 2026-09-05: el operador pidio una
        # sola base. Lo que este test protege no es la separacion de archivos
        # sino que la evidencia importada siga en sus propias tablas `testeo_*`
        # y no se mezcle con los registros de terreno, que son otra cosa: una
        # observacion colorimetrica del cuaderno 2025 no es una atencion.
        assert {"registros_testeo", "atenciones", "encuestas"} <= tables
        assert "registros_testeo" not in expected
    finally:
        conn.close()

    summary = db.testing_evidence_summary(rd_db)
    assert summary["available"] is True
    assert summary["status"] == "candidate_evidence_pending_human_review"
    # Las cifras crecieron el 2026-09-16 al recuperar el corpus 2024: la
    # planilla de Drive se reusa ano a ano y sus jornadas se habian borrado
    # para empezar 2025, asi que nunca entraron. Hoy la base carga tres
    # periodos -- 2024, 2025 y las jornadas 2026 que siguen anotandose en el
    # mismo archivo. `pending_links` son dos por jornada (venue y productora),
    # que es lo que declara el contrato de integracion.
    #
    # `observations` bajo el 2026-09-16 al mapear las columnas por el TEXTO
    # del encabezado y no por posicion fija: las 68 hojas tienen OCHO
    # estructuras distintas, y en `1904 Team 1` y `0308` las columnas corridas
    # metian el color donde va el reactivo. Esas observaciones fantasma ya no
    # se generan.
    #
    # El 2024 se importa desde `COPIA__PRIMERA-2025.xlsx` y no desde
    # `COPIA__1K7STsT1.xlsx`: son la misma planilla fotografiada con dias de
    # diferencia y la primera trae una jornada mas (`Dame 1001`, 4 muestras)
    # que la segunda ya no tenia. Al cotejar las cinco copias y las 32
    # revisiones de Drive contra la base, esa fue la UNICA hoja ausente.
    assert summary["counts"] == {
        "source_sheets": 68,
        "events": 68,
        "test_rows": 2861,
        "observations": 8361,
        "pending_links": 136,
        "exact_duplicate_rows_excluded_from_aggregate": 3,
        "unresolved_substances": 1,
        "unresolved_reagents": 1,
    }
    assert summary["public_claims_allowed"] is False


def test_candidate_research_is_consolidated_but_not_promoted(rd_db: Path):
    summary = db.research_candidate_summary(rd_db)
    assert summary == {
        "sources": 5,
        "entities": 48,
        "reagents": 12,
        "reaction_patterns": 60,
        "relations": 52,
        "references": 230,
        # Auditoria internacional (DanceSafe/NUAA/UNODC), 2026-08-11: 12
        # reactivos con evidence_status + 4 hallazgos globales del metodo.
        "reagent_audits": 12,
        "global_findings": 4,
        # Subio el 2026-09-16 al completar el valor que la planilla omite por
        # repetirse: la hoja escribe sustancia y reactivo cuando CAMBIAN y los
        # deja en blanco abajo. Un reactivo se hereda solo si esa fila trae un
        # resultado -- casilla y color vacios significan que no se aplico -- y
        # cada celda completada queda marcada en `inherited_fields`.
        "joined_observations": 5730,
        "public_claims_allowed": False,
    }

    conn = db.connect(rd_db)
    try:
        row = conn.execute(
            "SELECT reagent_name, interpretation_policy FROM v_testeo_observaciones_reactivo "
            "WHERE reagent_id = 'marquis' LIMIT 1"
        ).fetchone()
        assert dict(row) == {
            "reagent_name": "Marquis",
            "interpretation_policy": "contains_signal_only_no_claim_of_purity_or_dose",
        }
    finally:
        conn.close()


def test_testing_observations_filter_preserves_source(rd_db: Path):
    rows = db.testing_observations(reagent_id="marquis", db_path=rd_db)
    assert rows
    assert all(row["reagent_normalized_candidate"] == "marquis" for row in rows)
    assert all("interpretation_policy" in row for row in rows)


def test_build_es_idempotente(tmp_path: Path):
    p = tmp_path / "rd.db"
    db.build_rd_db(p)
    antes = _tables(p)
    db.build_rd_db(p)  # reconstruye sobre si misma sin duplicar
    assert _tables(p) == antes


def test_reactivos_por_familia_cruza(rd_db: Path):
    filas = db.reactivos_por_familia("MDMA", rd_db)
    assert len(filas) >= 3
    assert any(f["reactivo"] == "Marquis" for f in filas)
    # todos matchean la familia pedida
    assert all("mdma" in f["familia"].lower() for f in filas)


def test_reactivos_por_reactivo(rd_db: Path):
    filas = db.reactivos_por_reactivo("Marquis", rd_db)
    assert filas and all(f["reactivo"] == "Marquis" for f in filas)


def test_pack_precio_e_inclusiones(rd_db: Path):
    ps = {p["id"]: p for p in db.packs(rd_db)}
    assert ps["INFO"]["precio"] == 250_000       # reconciliado con fuente real 2026-07-02
    assert ps["TESTEO"]["precio"] == 300_000
    assert ps["COMPLETO"]["precio"] == 500_000
    assert len(ps["COMPLETO"]["inclusiones"]) >= 1


def test_precios_derivan_de_packs_py_no_hardcode(rd_db: Path):
    """La DB no inventa precios: coinciden con el modulo canonico plano.packs."""
    from flujo.plano.packs import PACKS

    for p in db.packs(rd_db):
        assert p["precio"] == PACKS[p["id"]]["precio"]
        assert p["voluntarios"] == PACKS[p["id"]]["voluntarios"]


def test_pack_por_voluntarios_mapea_o_none():
    """Logica evento->pack, unitaria (sin depender de eventos gitignored).
    Tras reconciliar precios (2026-07-02), INFO y TESTEO comparten 6 vol: el
    conteo no distingue -> None (ambiguo). COMPLETO=15 sigue unico."""
    assert db._pack_por_voluntarios(15) == "COMPLETO"
    assert db._pack_por_voluntarios(6) is None    # ambiguo INFO/TESTEO
    assert db._pack_por_voluntarios(2) is None    # ningun pack tiene 2 ya
    assert db._pack_por_voluntarios(7) is None
    assert db._pack_por_voluntarios(None) is None


def test_evento_tracked_trae_pack_sugerido(rd_db: Path):
    """El ejemplo TRACKED (projects/plano/ejemplos, 7 vol) siempre esta y su
    pack_sugerido queda None (7 no matchea INFO/TESTEO/COMPLETO)."""
    evs = db.eventos(rd_db)
    assert evs, "debe haber al menos el evento ejemplo tracked"
    ej = [e for e in evs if e["voluntarios"] == 7]
    assert ej and ej[0]["pack_sugerido"] is None


def test_productora_trae_aliases_deserializados(rd_db: Path):
    ps = db.productoras(rd_db)
    grid = [p for p in ps if p["slug"] == "thegrid"]
    assert grid
    assert isinstance(grid[0]["aliases"], list)
    assert "GRID" in grid[0]["aliases"]


def test_disclaimer_presuntivo_presente(rd_db: Path):
    d = db.disclaimer(rd_db)
    assert "PRESUNTIVO" in d.upper()


def test_lookup_familia_cruza_reactivos_y_packs(rd_db: Path):
    """El JOIN que justifica la DB: familia -> panel reactivos + packs con
    testeo + disclaimer, en una llamada."""
    res = db.lookup_familia("MDMA", rd_db)
    assert res["familia"] == "MDMA"
    assert len(res["reactivos"]) >= 3
    assert any(r["reactivo"] == "Marquis" for r in res["reactivos"])
    # 'testeo' se detecta en las inclusiones canonicas; TESTEO y COMPLETO al menos
    ids = {p["id"] for p in res["packs_con_testeo"]}
    assert {"TESTEO", "COMPLETO"} <= ids
    assert "PRESUNTIVO" in res["disclaimer"].upper()


def test_lookup_familia_desconocida_no_revienta(rd_db: Path):
    res = db.lookup_familia("sustancia-inexistente", rd_db)
    assert res["reactivos"] == []
    # los packs con testeo no dependen de la familia -> siguen apareciendo
    assert res["packs_con_testeo"]


def test_connect_autoconstruye_si_no_existe(tmp_path: Path):
    p = tmp_path / "nueva.db"
    assert not p.exists()
    conn = db.connect(p)  # debe construirla al vuelo
    try:
        assert conn.execute("SELECT count(*) FROM reactivos").fetchone()[0] >= 20
    finally:
        conn.close()
    assert p.exists()


def test_testing_projection_separates_obvious_column_errors(rd_db: Path):
    conn = db.connect(rd_db)
    try:
        header = conn.execute(
            "SELECT row_status, substance_map_status FROM testeo_filas_fuente "
            "WHERE source_sheet_name = 'Explícito 30082025' ORDER BY source_row LIMIT 1"
        ).fetchone()
        assert dict(header) == {
            "row_status": "repeated_header",
            "substance_map_status": "repeated_header",
        }
        labels = {
            row["raw_label"]: dict(row)
            for row in conn.execute(
                "SELECT raw_label, normalized_id, mapping_status "
                "FROM testeo_mapa_reactivos WHERE raw_label IN "
                "('Cannabis', 'Fentanilo', 'Mireia', 'Sin reaccion')"
            ).fetchall()
        }
        assert labels["Cannabis"]["normalized_id"] == "cbd_thc"
        assert labels["Fentanilo"]["mapping_status"] == "non_colorimetric_test"
        assert labels["Mireia"]["mapping_status"] == "possible_typo_candidate"
        assert labels["Sin reaccion"]["mapping_status"] == "result_in_reagent_column"

        substance = conn.execute(
            "SELECT normalized_id, mapping_status FROM testeo_mapa_sustancias "
            "WHERE raw_label = 'Ketamina+M'"
        ).fetchone()
        assert dict(substance) == {
            "normalized_id": "ketamine_plus_unspecified_m",
            "mapping_status": "mixture_candidate",
        }
    finally:
        conn.close()


def test_testing_projection_resolves_compact_dates_without_moving_years(rd_db: Path):
    conn = db.connect(rd_db)
    try:
        rows = {
            row["source_sheet_name"]: dict(row)
            for row in conn.execute(
                "SELECT source_sheet_name, date_iso_candidate, date_status, "
                "outside_filename_period_candidate FROM testeo_eventos_fuente "
                "WHERE source_sheet_name IN ('Technoyouth 51225', 'Technoyouth 2825', 'Nebula 2612')"
            ).fetchall()
        }
        assert rows["Technoyouth 51225"]["date_iso_candidate"] == "2025-12-05"
        assert rows["Nebula 2612"]["date_iso_candidate"] == "2025-12-26"
        assert rows["Technoyouth 2825"]["date_iso_candidate"] == "2025-02-28"
        assert rows["Technoyouth 2825"]["outside_filename_period_candidate"] == 0
    finally:
        conn.close()


def test_testing_projection_keeps_duplicate_rows_but_marks_aggregate_exclusions(rd_db: Path):
    conn = db.connect(rd_db)
    try:
        rows = {
            row["source_sheet_name"]: dict(row)
            for row in conn.execute(
                "SELECT source_sheet_name, duplicate_canonical_sheet_candidate, "
                "is_source_copy_candidate FROM testeo_eventos_fuente "
                "WHERE duplicate_group_size > 1"
            ).fetchall()
        }
        assert rows["DAME 0911 A"]["duplicate_canonical_sheet_candidate"] == "DAME 0911 A"
        assert rows["Copy of Copy of DAME 0911 A"]["is_source_copy_candidate"] == 1
        assert rows["Sheet51"]["duplicate_canonical_sheet_candidate"] == "Sheet51"
        assert db.testing_evidence_summary(rd_db)["counts"][
            "exact_duplicate_rows_excluded_from_aggregate"
        ] == 3
    finally:
        conn.close()


# --- Perfil de productora: logos + venues + tipos de fecha (vocab controlado) ---

def test_vocab_normaliza_tipos_y_fallback():
    from flujo.rd.vocab import normalize_tipo, normalize_tipos, TIPOS_FECHA

    assert normalize_tipo("rave") == "RAVE"
    assert normalize_tipo("after party") == "AFTER"
    assert normalize_tipo("underground") == "UNDERGROUND"
    assert normalize_tipo("cosa-inexistente") == "OTRO"   # nunca se pierde
    # dedup + orden canonico deterministico
    got = normalize_tipos(["rave", "festival", "rave", "after"])
    assert got == [t for t in TIPOS_FECHA if t in {"FESTIVAL", "RAVE", "AFTER"}]


def test_venues_canonicos_desde_yaml(rd_db: Path):
    vs = {v["nombre"]: v for v in db.venues(rd_db)}
    assert "Espacio Riesco" in vs
    er = vs["Espacio Riesco"]
    assert er["preset_reco"] == "mainstream"
    assert er["voluntarios_min"] == 8
    assert isinstance(er["requisitos"], dict)   # requirements_defaults deserializado


def test_perfil_productora_trae_tipos_logos_venues(rd_db: Path):
    p = db.productora("creamfields", rd_db)
    assert p is not None
    assert set(p["tipos_fecha"]) >= {"FESTIVAL", "HEADLINERS", "RAVE"}
    assert p["logos"] and p["logos"][0]["knowledge"].endswith("creamfields.yaml")
    assert p["venue_preferido"] == "Espacio Riesco"
    # el venue matchea el canonico -> venue_id resuelto
    ven = p["venues"][0]
    assert ven["venue_id"] == "espacio_riesco"


def test_productora_inexistente_es_none(rd_db: Path):
    assert db.productora("no-existe", rd_db) is None


def test_productoras_por_tipo(rd_db: Path):
    assert "creamfields" in db.productoras_por_tipo("FESTIVAL", rd_db)
    assert set(db.productoras_por_tipo("rave", rd_db)) >= {"creamfields", "thegrid"}
    assert db.productoras_por_tipo("PRIVADO", rd_db) == []   # nadie, sin crash


def test_venue_preferido_via_fixture_sintetica(tmp_path: Path):
    """La maquinaria venue-preferido + enlace canonico, con una productora
    sintetica (no contamina el store real): 2 venues, el segundo preferido y
    enlazado al venue canonico Espacio Riesco."""
    pdir = tmp_path / "prods"
    pdir.mkdir()
    (pdir / "acme.json").write_text(json.dumps({
        "name": "Acme Fiestas",
        "tipos_fecha": ["club", "after"],
        "venues": [
            {"nombre": "Galpon X", "preferido": False, "estado": "confirmado"},
            {"nombre": "Espacio Riesco", "venue_id": "espacio_riesco", "preferido": True, "estado": "confirmado"},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    p = tmp_path / "syn.db"
    db.build_rd_db(p, productoras_dir=pdir)   # venues_dir default -> canonicos reales
    prof = db.productora("acme", p)
    assert prof["venue_preferido"] == "Espacio Riesco"
    assert set(prof["tipos_fecha"]) == {"CLUB", "AFTER"}
    pref = [v for v in prof["venues"] if v["preferido"]][0]
    assert pref["venue_id"] == "espacio_riesco"   # enlazado al canonico


def test_productora_eventos_persisten_veredicto_de_fuente_primaria(tmp_path: Path):
    """Event evidence uses MAK's source gate, but the RD projection persists
    the verdict so panels/reports can surface it without re-running research."""
    import json as _json

    pdir = tmp_path / "prods"
    pdir.mkdir()
    (pdir / "acme.json").write_text(_json.dumps({
        "name": "Acme Fiestas",
        "eventos": [
            {
                "nombre": "Acme confirmado",
                "fecha": "2026-11-20",
                "venue": "Basel Venue",
                "estado": "activo_anunciado",
                "fuente": "post oficial https://www.instagram.com/p/DaRCFPhCfdM/",
            },
            {
                "nombre": "Acme sin fuente",
                "fecha": "needs_confirmation",
                "venue": "TBA",
                "estado": "candidato",
                "fuente": "comentario interno sin URL",
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    path = tmp_path / "rd.db"
    db.build_rd_db(path, productoras_dir=pdir)
    conn = db.connect(path)
    try:
        rows = [
            dict(r) for r in conn.execute(
                "SELECT nombre, fuentes_primarias, sin_fuente_primaria "
                "FROM productora_eventos ORDER BY nombre"
            ).fetchall()
        ]
    finally:
        conn.close()

    assert rows[0]["nombre"] == "Acme confirmado"
    assert json.loads(rows[0]["fuentes_primarias"]) == [
        "https://www.instagram.com/p/DaRCFPhCfdM/"
    ]
    assert rows[0]["sin_fuente_primaria"] == 0
    assert rows[1]["nombre"] == "Acme sin fuente"
    assert json.loads(rows[1]["fuentes_primarias"]) == []
    assert rows[1]["sin_fuente_primaria"] == 1


def test_un_rebuild_no_destruye_los_datos_de_terreno(tmp_path):
    """Lo derivado se rehace; lo acumulado se conserva. Esa es la fusion.

    `build_rd_db()` borra el archivo y lo reescribe entero, y esta bien: todo lo
    que produce se puede volver a derivar de fuentes canonicas. `registros_testeo`,
    `atenciones` y `encuestas` no: son registros de terreno que no existen en
    ninguna otra parte.

    Hasta el 2026-09-05 el choque se evitaba teniendolas en otro archivo. El
    operador pidio una sola base, asi que el rebuild las rescata antes de borrar
    y las repone despues. Este es el test que hace que esa promesa se pueda
    romper: si alguien quita el rescate, la fila desaparece aqui.
    """
    ruta = tmp_path / "rd.db"
    db.build_rd_db(ruta)

    conn = db.connect(ruta)
    try:
        conn.execute(
            "INSERT INTO registros_testeo"
            "(fecha, evento, sustancia_declarada, reactivo, familia_detectada, coincide)"
            " VALUES (?,?,?,?,?,?)",
            ("2026-09-05", "Evento Real", "MDMA", "Marquis", "MDMA / MDA", 1),
        )
        conn.execute(
            "INSERT INTO atenciones(fecha, evento, tipo, rango_etario) VALUES (?,?,?,?)",
            ("2026-09-05", "Evento Real", "hidratacion", "18-25"),
        )
        conn.execute(
            "INSERT INTO encuestas(fecha, evento, pregunta_id, respuesta) VALUES (?,?,?,?)",
            ("2026-09-05", "Evento Real", "p1", "si"),
        )
        conn.commit()
    finally:
        conn.close()

    db.build_rd_db(ruta)

    conn = db.connect(ruta)
    try:
        for tabla in ("registros_testeo", "atenciones", "encuestas"):
            n = conn.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
            assert n == 1, f"el rebuild borro {tabla}: los datos de terreno no se rederivan"
        fila = tuple(conn.execute(
            "SELECT sustancia_declarada, reactivo, coincide FROM registros_testeo"
        ).fetchone())
        assert fila == ("MDMA", "Marquis", 1), "la fila sobrevivio pero llego alterada"
        # Y lo derivado si se rehizo: la fusion no congelo la reconstruccion.
        assert conn.execute(
            "SELECT count(*) FROM rd_entidades_candidatas"
        ).fetchone()[0] > 0
    finally:
        conn.close()


def test_el_rescate_no_duplica_al_reconstruir_dos_veces(tmp_path):
    """Dos rebuilds seguidos dejan una fila, no dos.

    Un rescate que reinserta sin cuidado convierte cada reconstruccion en una
    copia mas, y el conteo de atenciones de terreno se infla solo.
    """
    ruta = tmp_path / "rd.db"
    db.build_rd_db(ruta)
    conn = db.connect(ruta)
    try:
        conn.execute(
            "INSERT INTO atenciones(fecha, evento, tipo) VALUES (?,?,?)",
            ("2026-09-05", "Evento Real", "escucha"),
        )
        conn.commit()
    finally:
        conn.close()

    db.build_rd_db(ruta)
    db.build_rd_db(ruta)

    conn = db.connect(ruta)
    try:
        assert conn.execute("SELECT count(*) FROM atenciones").fetchone()[0] == 1
    finally:
        conn.close()

def test_perfil_enriquecido_de_knowledge_se_fusiona_con_data_productoras(rd_db: Path):
    # Antes de esto, extraccion_db.py leia data/productoras Y
    # knowledge/productoras por separado para armar su propio catalogo de
    # matching -- dos lecturas de la misma fuente, y la DB (la unica que
    # debe consultar el matching de ahora en mas) se quedaba sin el perfil
    # enriquecido de knowledge/ (affinity, service_preferences,
    # relationship, venues_recurrentes...). Ahora build_rd_db() fusiona
    # ambas fuentes en la misma fila.
    prods = {p["slug"]: p for p in db.productoras(rd_db)}
    creamfields = prods["creamfields"]
    # alias de data/productoras/creamfields.json Y de knowledge/productoras/
    # creamfields.yaml conviven en la misma union, sin duplicar
    assert "CREAMFIELDS" in creamfields["aliases"]
    assert "creamfieldscl" in creamfields["aliases"]
    assert len(creamfields["aliases"]) == len(set(creamfields["aliases"]))
    assert creamfields["perfil"] is not None
    assert creamfields["perfil"]["affinity"]["testeo"] is False

    # productoras sin perfil enriquecido no rompen (perfil = None, no KeyError)
    sin_perfil = [p for p in prods.values() if p["perfil"] is None]
    assert sin_perfil, "debe haber al menos una productora sin knowledge/productoras/*.yaml"


def test_knowledge_productoras_template_file_is_never_ingested(rd_db: Path):
    # rave_under_template.yaml es un arquetipo de categoria (id/name
    # terminan en "template"), no una productora real -- nunca debe
    # aparecer en el catalogo de matching.
    slugs = {p["slug"] for p in db.productoras(rd_db)}
    assert "rave_under_template" not in slugs
    nombres = {p["nombre"].lower() for p in db.productoras(rd_db)}
    assert not any(n.endswith("template") for n in nombres)


def test_auditoria_reactivos_queda_sourced_y_no_reemplaza_la_carta(rd_db: Path):
    """La auditoria (DanceSafe/NUAA/UNODC, 2026-08-11) se adjunta, no borra.

    `reactivo`/`familia`/`reaccion`/`hex` siguen siendo la carta propia de RD;
    `auditoria_estado`/`auditoria_nota` son una segunda opinion sentada al
    lado, atribuible a su fuente via `rd_auditoria_reactivos`.
    """
    conn = db.connect(rd_db)
    try:
        fuente = conn.execute(
            "SELECT status, schema_version FROM rd_fuentes_registro "
            "WHERE source_id = 'reagent_audit_overlay_v0_1'"
        ).fetchone()
        assert fuente is not None
        assert fuente["status"] == "candidate_pending_rd_human_review"
        assert fuente["schema_version"] == "rd-reagent-audit-overlay-v0.1"

        row = conn.execute(
            "SELECT evidence_status, important_correction FROM rd_auditoria_reactivos "
            "WHERE reagent_id = 'liebermann'"
        ).fetchone()
        assert row["evidence_status"] == "conflicting"
        assert "levamisole" in row["important_correction"].lower()

        globales = {r["finding_id"] for r in conn.execute(
            "SELECT finding_id FROM rd_auditoria_hallazgos_globales")}
        assert "fentanyl_boundary" in globales

        # La fila retractada de la carta propia (Liebermann / cocaina cortada)
        # sigue ahi -- no se borra -- pero ahora carga la nota de conflicto.
        marcada = conn.execute(
            "SELECT auditoria_estado, auditoria_nota FROM reactivos "
            "WHERE reactivo = 'Liebermann' AND familia LIKE '%levamisol%'"
        ).fetchone()
        assert marcada["auditoria_estado"] == "conflicting"
        assert marcada["auditoria_nota"]

        # Marquis SI tiene auditoria cargada (partially_supported); un
        # reactivo sin fila en rd_auditoria_reactivos quedaria en NULL, no en
        # un estado inventado.
        marquis = conn.execute(
            "SELECT auditoria_estado FROM reactivos WHERE reactivo = 'Marquis' LIMIT 1"
        ).fetchone()
        assert marquis["auditoria_estado"] == "partially_supported"
    finally:
        conn.close()
