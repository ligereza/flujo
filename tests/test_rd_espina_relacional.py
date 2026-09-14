"""La espina que une evento, productora(s), venue y mesa de testeo.

Hasta el 2026-09-05 los 42 eventos del cuaderno de testeo 2025 estaban
`unlinked`, sin un solo candidato de productora ni de venue: el testeo y el
catalogo de productoras eran dos islas dentro del mismo archivo. Estos tests
fijan el puente y, sobre todo, fijan lo que el puente NO debe hacer.

La forma del dato viene de la realidad y no al reves. Un evento puede tener
varias productoras -- "Espacio Riesco con THE GRID + SUNDECK + GLOVOX" es una
fecha en colaboracion, no tres eventos ni un error de tipeo -- y cual de ellas
es la anfitriona es algo que se averigua. Por eso `evento_productoras` es una
relacion de muchos a muchos con rol, y el rol arranca `sin_determinar`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from flujo.rd import database as db


@pytest.fixture()
def rd_db(tmp_path: Path) -> Path:
    return db.build_rd_db(tmp_path / "rd.db")


def _filas(path: Path, sql: str, *args):
    conn = db.connect(path)
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


class TestElPuenteExiste:
    def test_los_eventos_del_cuaderno_2025_dejaron_de_estar_sueltos(self, rd_db: Path):
        enlazados = _filas(
            rd_db,
            "SELECT count(*) n FROM testeo_eventos_fuente"
            " WHERE link_status = 'candidate_from_label'",
        )[0]["n"]
        assert enlazados > 0, (
            "ningun evento de testeo quedo vinculado: el puente no corrio"
        )

    def test_cada_vinculo_dice_de_donde_salio(self, rd_db: Path):
        for fila in _filas(rd_db, "SELECT * FROM evento_productoras"):
            assert fila["metodo"] in {"MEDIDO", "DERIVADO", "SUPUESTO"}
            assert fila["evidencia"], (
                f"{fila['evento_ref']} -> {fila['productora_slug']} sin evidencia: "
                "un vinculo sin el token que lo produjo no se puede revisar"
            )
            assert fila["confianza"] in {"alta", "media", "baja"}

    def test_la_productora_vinculada_existe_en_el_catalogo(self, rd_db: Path):
        huerfanos = _filas(
            rd_db,
            "SELECT ep.productora_slug FROM evento_productoras ep"
            " LEFT JOIN productoras p ON p.slug = ep.productora_slug"
            " WHERE p.slug IS NULL",
        )
        assert not huerfanos, f"vinculos a productoras inexistentes: {huerfanos}"


class TestNoInventaNada:
    def test_un_evento_sin_alias_conocido_queda_sin_vinculo(self, rd_db: Path):
        # De los 42, varios nombran productoras que no estan en el catalogo
        # (Kore, Mamisonga, Raverunners, hellbox...). Que queden sueltos es el
        # resultado correcto: son productoras por registrar, no un fallo.
        sueltos = _filas(
            rd_db,
            "SELECT count(*) n FROM testeo_eventos_fuente WHERE link_status = 'unlinked'",
        )[0]["n"]
        assert sueltos > 0, (
            "todos los eventos quedaron vinculados: si el emparejador nunca se "
            "abstiene, esta atando por parecido y no por evidencia"
        )

    def test_ningun_vinculo_se_aprueba_solo(self, rd_db: Path):
        # `data/rd_fuentes/README.md` exige revision humana con evidencia antes
        # de publicar un enlace. Derivarlo no es aprobarlo.
        for tabla in ("evento_productoras", "evento_venues"):
            estados = {
                f["estado_revision"] for f in _filas(rd_db, f"SELECT * FROM {tabla}")
            }
            assert estados <= {"pendiente_revision_humana"}, (
                f"{tabla} trae vinculos ya aprobados: {estados}"
            )

    def test_el_rol_no_se_adivina(self, rd_db: Path):
        roles = {f["rol"] for f in _filas(rd_db, "SELECT * FROM evento_productoras")}
        assert roles <= {"sin_determinar"}, (
            "el emparejador decidio quien es anfitriona; eso no sale del nombre"
        )

    def test_el_venue_por_habito_nunca_se_presenta_como_medido(self, rd_db: Path):
        for fila in _filas(
            rd_db, "SELECT * FROM evento_venues WHERE origen = 'habitual_de_productora'"
        ):
            assert fila["metodo"] == "SUPUESTO", (
                "que una productora suela tocar en un lugar no prueba que esa "
                "fecha haya sido ahi"
            )
            assert fila["confianza"] == "baja"


class TestUnEventoPuedeTenerVariasProductoras:
    """El caso que el operador nombro: Espacio Riesco, THE GRID + SUNDECK + GLOVOX.

    En el cuaderno 2025 no hay ninguna etiqueta que nombre a dos productoras, asi
    que la colaboracion no queda ejercitada por los datos historicos. Se ejercita
    aqui, porque la app que viene si va a registrarlas y el esquema tiene que
    aguantarlo antes de que llegue el primer dato real.
    """

    TRES = ("thegrid", "sundeck", "glovox")

    def test_las_tres_productoras_del_ejemplo_existen(self, rd_db: Path):
        slugs = {f["slug"] for f in _filas(rd_db, "SELECT slug FROM productoras")}
        faltan = [s for s in self.TRES if s not in slugs]
        assert not faltan, f"faltan en el catalogo: {faltan}"

    def test_tres_productoras_caben_en_un_solo_evento(self, rd_db: Path):
        conn = db.connect(rd_db)
        try:
            for slug in self.TRES:
                conn.execute(
                    "INSERT INTO evento_productoras"
                    "(evento_ref, evento_origen, productora_slug, rol, metodo,"
                    " evidencia, confianza)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (
                        "evento-riesco-demo",
                        "canonico",
                        slug,
                        "sin_determinar",
                        "MEDIDO",
                        "declarado por el operador",
                        "alta",
                    ),
                )
            conn.commit()
            filas = [
                dict(r)
                for r in conn.execute(
                    "SELECT productora_slug, rol FROM evento_productoras"
                    " WHERE evento_ref = 'evento-riesco-demo' ORDER BY 1"
                )
            ]
        finally:
            conn.close()

        assert [f["productora_slug"] for f in filas] == sorted(self.TRES)
        assert {f["rol"] for f in filas} == {"sin_determinar"}, (
            "cual de las tres es anfitriona y cual colabora es un dato que se "
            "averigua; el esquema no debe forzar una respuesta"
        )

    def test_la_misma_productora_no_entra_dos_veces_al_mismo_evento(self, rd_db: Path):
        import sqlite3

        conn = db.connect(rd_db)
        try:
            fila = (
                "evento-riesco-demo",
                "canonico",
                "thegrid",
                "sin_determinar",
                "MEDIDO",
                "declarado por el operador",
                "alta",
            )
            sql = (
                "INSERT INTO evento_productoras"
                "(evento_ref, evento_origen, productora_slug, rol, metodo,"
                " evidencia, confianza) VALUES (?,?,?,?,?,?,?)"
            )
            conn.execute(sql, fila)
            conn.commit()
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql, fila)
        finally:
            conn.close()


class TestLaMesaDeTesteo:
    def test_la_mesa_sale_de_la_etiqueta_cuando_la_etiqueta_la_dice(self, rd_db: Path):
        # El cuaderno trae "Fiesta Dame 504 mesa 1" y "mesa 2": un mismo evento
        # con dos mesas, cada una con su planilla. Sin esto se leen como dos
        # eventos distintos.
        numeros = sorted(
            f["numero"] for f in _filas(rd_db, "SELECT numero FROM mesas_testeo")
        )
        assert numeros == [1, 2], f"mesas detectadas: {numeros}"

    @pytest.mark.parametrize(
        "etiqueta,esperado",
        [
            ("Fiesta Dame 504 mesa 1", 1),
            ("Fiesta Dame 504 MESA 2", 2),
            ("algo mesa  3 mas", 3),
            ("Cachorros 0407", None),
            ("mesada 9", None),
        ],
    )
    def test_el_lector_de_mesa_no_confunde_palabras_parecidas(
        self, etiqueta: str, esperado: int | None
    ):
        numero, _ = db._mesa_desde_etiqueta(etiqueta)
        assert numero == esperado


class TestLaCadenaCompletaSirveParaLaAppQueViene:
    def test_de_una_muestra_se_puede_llegar_al_evento_y_sus_productoras(
        self, rd_db: Path
    ):
        """Muestra -> mesa -> evento -> productoras. Es la consulta de la app."""
        conn = db.connect(rd_db)
        try:
            mesa = conn.execute(
                "SELECT id, evento_ref, evento_origen FROM mesas_testeo LIMIT 1"
            ).fetchone()
            assert mesa is not None, "no hay ninguna mesa de la que colgar la muestra"
            conn.execute(
                "INSERT INTO muestras(fecha, mesa_id, evento_ref, evento_origen,"
                " codigo_muestra, sustancia_declarada, tipo_muestra, color)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    "2026-09-05",
                    mesa["id"],
                    mesa["evento_ref"],
                    mesa["evento_origen"],
                    "M-001",
                    "MDMA",
                    "comprimido",
                    "beige",
                ),
            )
            muestra_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO muestra_resultados(muestra_id, reactivo, resultado_color,"
                " familia_detectada, coincide_con_declarada, orden)"
                " VALUES (?,?,?,?,?,?)",
                (muestra_id, "Marquis", "violeta a negro", "MDMA / MDA", 1, 1),
            )
            conn.commit()

            fila = conn.execute(
                "SELECT m.codigo_muestra, m.sustancia_declarada, r.reactivo,"
                " r.familia_detectada, r.limitacion, e.event_label_candidate,"
                " ep.productora_slug"
                " FROM muestras m"
                " JOIN muestra_resultados r ON r.muestra_id = m.id"
                " JOIN mesas_testeo t ON t.id = m.mesa_id"
                " JOIN testeo_eventos_fuente e ON e.event_id = t.evento_ref"
                " LEFT JOIN evento_productoras ep ON ep.evento_ref = t.evento_ref"
                " WHERE m.id = ?",
                (muestra_id,),
            ).fetchone()
        finally:
            conn.close()

        assert fila is not None, (
            "la cadena muestra -> mesa -> evento -> productora se corta en algun "
            "punto: eso es exactamente lo que esta espina existe para evitar"
        )
        assert fila["codigo_muestra"] == "M-001"
        assert fila["event_label_candidate"]
        assert fila["productora_slug"]

    def test_el_resultado_lleva_su_limitacion_pegada(self, rd_db: Path):
        """Que sea presuntivo viaja con el dato, no solo en un README.

        Una reaccion colorimetrica es senal de presencia: no identifica, no mide
        pureza ni dosis. Un consumidor que lea la tabla y no el README tiene que
        encontrarse igual con la advertencia.
        """
        conn = db.connect(rd_db)
        try:
            conn.execute(
                "INSERT INTO muestras(fecha, sustancia_declarada) VALUES (?,?)",
                ("2026-09-05", "ketamina"),
            )
            mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO muestra_resultados(muestra_id, reactivo) VALUES (?,?)",
                (mid, "Froehde"),
            )
            conn.commit()
            limitacion = conn.execute(
                "SELECT limitacion FROM muestra_resultados WHERE muestra_id = ?",
                (mid,),
            ).fetchone()[0]
        finally:
            conn.close()
        assert "presuntivo" in limitacion.lower()
        assert "pureza" in limitacion.lower()

    def test_las_muestras_sobreviven_a_una_reconstruccion(self, tmp_path: Path):
        # Son datos de terreno: no se rederivan de ninguna fuente canonica.
        ruta = tmp_path / "rd.db"
        db.build_rd_db(ruta)
        conn = db.connect(ruta)
        try:
            conn.execute(
                "INSERT INTO muestras(fecha, sustancia_declarada, codigo_muestra)"
                " VALUES (?,?,?)",
                ("2026-09-05", "2C-B", "M-042"),
            )
            conn.commit()
        finally:
            conn.close()

        db.build_rd_db(ruta)

        conn = db.connect(ruta)
        try:
            filas = [dict(r) for r in conn.execute("SELECT * FROM muestras")]
        finally:
            conn.close()
        assert len(filas) == 1, "el rebuild borro la muestra"
        assert filas[0]["codigo_muestra"] == "M-042"


class TestLaPrivacidadNoSeAflojaConLaAppNueva:
    def test_ninguna_tabla_nueva_tiene_columna_de_identidad(self, rd_db: Path):
        prohibidas = {
            "nombre_persona", "rut", "dni", "telefono", "email", "correo",
            "nacimiento", "direccion", "apellido",
        }
        conn = db.connect(rd_db)
        try:
            for tabla in ("muestras", "muestra_resultados", "evento_productoras",
                          "evento_venues", "mesas_testeo"):
                cols = {r[1].lower() for r in conn.execute(f"PRAGMA table_info({tabla})")}
                assert not (cols & prohibidas), (
                    f"{tabla} declara una columna de identidad: lo que no existe "
                    "como columna no se puede filtrar por accidente"
                )
        finally:
            conn.close()

    def test_la_foto_se_guarda_por_referencia_y_no_en_la_base(self, rd_db: Path):
        conn = db.connect(rd_db)
        try:
            cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(muestras)")}
        finally:
            conn.close()
        assert "foto_ref" in cols, "falta la referencia a la foto"
        assert cols["foto_ref"].upper() == "TEXT", (
            "la foto se guarda como ruta o hash, nunca como BLOB en la base"
        )
