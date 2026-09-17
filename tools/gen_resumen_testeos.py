#!/usr/bin/env python3
"""Genera el resumen de testeos RD como un HTML de un archivo.

Para que sirve: mostrarle al equipo que la planilla heredada quedo ordenada, y
que de ella salen cifras que se pueden leer. Se abre con doble clic, no
necesita internet ni servidor -- igual que el resto de lo que se entrega al
area (ver docs/rd/MAPA_RD.md).

Que NO hace, y no es un olvido: no dice que sustancia hay en ninguna muestra.
Un reactivo marca presencia posible de una familia quimica; no identifica, no
mide pureza y no mide dosis. El veredicto lo da la persona a cargo de la mesa,
de viva voz, y no queda registrado. Por eso cada cifra de aca dice que reactivo
se aplico y que color se vio, y ninguna dice que era.

    py tools/gen_resumen_testeos.py [--out <ruta.html>]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from flujo.rd.colorimetria import HEX  # noqa: E402
from flujo.rd.colorimetria import normalizar as normalizar_color  # noqa: E402
from flujo.rd.ensayos import normalizar_reactivo, normalizar_sustancia  # noqa: E402
from flujo.rd.paths import rd_db_path  # noqa: E402

# Filas que son dato. `repeated_header` son encabezados de la planilla que
# quedaron guardados como filas: contarlos infla el total de muestras.
_FILAS_DATO = ("data", "data_with_unresolved_substance")

# Paleta de RD, derivada de sus propios reactivos (projects/cultura/identidad/
# reactivos.json, bloque `marca`). No se elige un color por gusto: el violeta
# es Marquis sobre MDMA, el magenta es Ehrlich sobre LSD, el naranjo es
# Mandelin sobre ketamina, y el papel es el blanco que no confirma nada.
MARCA = {
    "primario": "#3b1a4a",
    "secundario": "#7a1f5a",
    "acento": "#d47a1a",
    "alerta": "#b5651d",
    "vida": "#4a7c3a",
    "papel": "#efe9dd",
}

ETIQUETA_SUSTANCIA = {
    "MDMA": "MDMA", "KETAMINA": "Ketamina", "COCAINA": "Cocaína",
    "2C_B": "2C-B", "TUSI": "Tusi", "CANNABIS": "Cannabis", "GHB": "GHB",
    "HONGOS": "Hongos", "MEFEDRONA": "Mefedrona", "LSD": "LSD",
    "ANFETAMINA": "Anfetamina", "METANFETAMINA": "Metanfetamina",
    "MDA": "MDA", "BENZODIACEPINA": "Benzodiacepina", "CAFEINA": "Cafeína",
    "POPPER": "Popper", "DMT": "DMT",
    "NO_DECLARA": "sin declarar", "NO_SABE": "no sabe qué es",
}

# Lo que NO es un reactivo colorimetrico. Se dibuja distinto porque es otra
# cosa: la propia auditoria de RD dice que un reactivo de color no puede
# tratarse como prueba de fentanilo -- para eso hace falta una tira.
NO_COLORIMETRICOS = ("TIRA_FENTANILO", "TIRA_XYLAZINA", "TIRA_BENZODIACEPINAS",
                     "TEST_GHB")

ETIQUETA_COLOR = {
    "NEGRO": "negro", "AZUL": "azul", "CELESTE": "celeste", "MORADO": "morado",
    "AMARILLO": "amarillo", "NARANJO": "naranjo", "ROJO": "rojo",
    "VERDE": "verde", "ROSADO": "rosado", "CAFE": "café", "GRIS": "gris",
    "BLANCO": "blanco", "SIN_REACCION": "sin reacción",
    "NO_INTERPRETABLE": "no interpretable",
}


def _conectar(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _etiquetas_de_muestra(conn: sqlite3.Connection) -> frozenset[str]:
    """Nombres de troquel sacados de la columna de formato.

    `Cupra morada` en la columna de resultado es la pastilla, no un reactivo
    que viro a morado. Las dos columnas traen nombres de color y se confunden
    de vista, asi que el vocabulario de sellos se lee del propio corpus.
    """
    import re
    import unicodedata

    from flujo.rd.colorimetria import COLORES

    def clave(texto: str) -> str:
        t = unicodedata.normalize("NFKD", str(texto or "").lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", "", t)

    etiquetas: set[str] = set()
    for fila in conn.execute(
        "SELECT DISTINCT format_raw FROM testeo_filas_fuente "
        "WHERE format_raw IS NOT NULL AND TRIM(format_raw) <> ''"
    ):
        for token in re.split(r"[^\wÁÉÍÓÚÑáéíóúñ]+", str(fila[0])):
            k = clave(token)
            if len(k) < 4 or k.isdigit():
                continue
            if normalizar_color(k)["status"] == "canonico":
                continue
            if any(k == c.lower() for c in COLORES):
                continue
            etiquetas.add(k)
    return frozenset(etiquetas)


def _fiestas(conn: sqlite3.Connection, eventos: list[str]) -> dict[str, tuple]:
    """A que FIESTA pertenece cada hoja.

    Una hoja no es una fiesta: `Fiesta Dame 504 mesa 1` y `mesa 2` son dos
    mesas de la misma noche, `Dame tresor 181025 A` y `B` dos tablas, y
    `Copy of Dame 22-8` una copia. Contar hojas inflaba 2025 de 29 a 38.

    Dos reglas mas, que el reporte oficial 2024 valida al dar exactamente 22:
    una hoja SIN fecha hereda la de su gemela con el mismo nombre base
    (`Stgo hardtechno A` es la mesa A de `Santiago Hardtechno B 267`), y una
    hoja cuyo nombre es SOLO la fecha es otra tabla de la fiesta de ese dia
    (` 2408` junto a `Dame 248 A` y `B`).
    """
    import re
    import unicodedata

    def base(nombre: str) -> str:
        n = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
        n = n.lower().strip()
        n = re.sub(r"^(copy of )+", "", n)
        n = re.sub(r"\b(mesa|team)\s*\d+\b", "", n)
        n = re.sub(r"\s+[ab]\b", "", n)
        n = re.sub(r"\bstgo\b", "santiago", n)
        return re.sub(r"\d+$", "", re.sub(r"[^a-z0-9]+", "", n))

    meta = {
        r["event_id"]: (r["source_sheet_name"], r["date_iso_candidate"])
        for r in conn.execute(
            "SELECT event_id, source_sheet_name, date_iso_candidate FROM testeo_eventos_fuente")
    }
    fechas_por_base: dict[str, set] = defaultdict(set)
    for ev in eventos:
        nombre, fecha = meta[ev]
        if fecha:
            fechas_por_base[base(nombre)].add(fecha)

    salida: dict[str, tuple] = {}
    for ev in eventos:
        nombre, fecha = meta[ev]
        b = base(nombre)
        if not fecha and len(fechas_por_base.get(b, ())) == 1:
            fecha = next(iter(fechas_por_base[b]))
        if not b:
            hermanas = {base(meta[o][0]) for o in eventos
                        if meta[o][1] == fecha and base(meta[o][0])}
            if len(hermanas) == 1:
                b = next(iter(hermanas))
        salida[ev] = (fecha or "sin fecha", b)
    return salida


def _paneles(muestras: list, troqueles) -> dict:
    """Por sustancia declarada: cobertura de cada reactivo y sus colores."""
    por = defaultdict(list)
    for _ev, f in muestras:
        por[normalizar_sustancia(f["substance_raw"])["canonico"] or "NO_DECLARA"].append(f)

    salida = {}
    for sus, filas in por.items():
        n = len(filas)
        if n < 12:
            continue
        reactivos: dict[str, dict] = {}
        for f in filas:
            for t, r in (("test_1_raw", "result_1_raw"), ("test_2_raw", "result_2_raw"),
                         ("test_3_raw", "result_3_raw"), ("test_4_raw", "result_4_raw")):
                rea = normalizar_reactivo(f[t])["canonico"]
                if not rea:
                    continue
                d = reactivos.setdefault(rea, {"muestras": 0, "colores": Counter()})
                d["muestras"] += 1
                lectura = normalizar_color(f[r], troqueles)
                if lectura["status"] in ("encabezado_o_reactivo", "vacio",
                                         "descripcion_de_muestra"):
                    continue
                d["colores"][lectura.get("clave") or lectura["outcome"]] += 1
        salida[sus] = {
            "muestras": n,
            "reactivos": {
                k: {"muestras": v["muestras"], "colores": dict(v["colores"].most_common(6))}
                for k, v in sorted(reactivos.items(), key=lambda kv: -kv[1]["muestras"])
                if v["muestras"] >= max(3, n * 0.04)
            },
        }
    return dict(sorted(salida.items(), key=lambda kv: -kv[1]["muestras"]))


def reunir(db: Path, *, detalle: bool = False) -> dict:
    """`detalle=True` agrega la tabla ordenada fila por fila."""
    conn = _conectar(db)
    try:
        troqueles = _etiquetas_de_muestra(conn)

        periodo_de = {
            r["event_id"]: (r["source_period_label"] or "sin periodo")
            for r in conn.execute(
                "SELECT event_id, source_period_label FROM testeo_eventos_fuente")
        }
        fecha_de = {
            r["event_id"]: r["date_iso_candidate"]
            for r in conn.execute(
                "SELECT event_id, date_iso_candidate FROM testeo_eventos_fuente")
        }
        nombre_de = {
            r["event_id"]: (r["event_label_candidate"] or r["source_sheet_name"])
            for r in conn.execute(
                "SELECT event_id, event_label_candidate, source_sheet_name "
                "FROM testeo_eventos_fuente")
        }

        # --- El desorden heredado, medido antes de normalizar nada ----------
        crudo_reactivo = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT reagent_raw FROM testeo_observaciones_fuente "
                "WHERE reagent_raw IS NOT NULL AND TRIM(reagent_raw) <> ''")}
        crudo_color = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT result_raw FROM testeo_observaciones_fuente "
                "WHERE result_raw IS NOT NULL AND TRIM(result_raw) <> ''")}
        crudo_sustancia = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT substance_raw FROM testeo_filas_fuente "
                "WHERE substance_raw IS NOT NULL AND TRIM(substance_raw) <> ''")}

        # --- Las muestras: se CONSULTAN, no se vuelven a decidir --------
        #
        # Los cinco filtros y la agrupacion en fiestas viven en `database.py`
        # y quedan escritos en la base (`clasificacion`, `fiesta_id`). Este
        # generador solo lee: dos lecturas de la misma fuente con logica
        # separada terminan dando dos cifras distintas, y la cifra es el
        # producto.
        muestras = [(f["event_id"], f) for f in conn.execute(
            "SELECT * FROM v_testeo_muestras")]
        propias = {
            f["test_id"]: {
                "evento": ev,
                "periodo": f["periodo"],
                "sustancia": normalizar_sustancia(f["substance_raw"])["canonico"] or "NO_DECLARA",
            }
            for ev, f in muestras
        }
        sustancias = Counter(x["sustancia"] for x in propias.values())
        muestras_periodo = Counter(x["periodo"] for x in propias.values())
        fiestas_periodo = Counter()
        for r in conn.execute("SELECT periodo, fiestas FROM v_testeo_resumen_periodo"):
            fiestas_periodo[r["periodo"]] = r["fiestas"]

        clasificacion = Counter()
        for r in conn.execute(
                "SELECT clasificacion, SUM(filas) n FROM v_testeo_clasificacion "
                "WHERE clasificacion IS NOT NULL GROUP BY 1"):
            clasificacion[r["clasificacion"]] = r["n"]
        sin_reactivo = clasificacion.get("sin_analisis", 0)
        rotulos = clasificacion.get("rotulo_de_sala", 0)
        copiadas_de_hermana = clasificacion.get("hoja_copy_of_duplicada", 0)
        procedencia = Counter(clasificacion)
        sin_nombre = sum(
            1 for _ev, f in muestras
            if not any(normalizar_reactivo(f[k])["canonico"]
                       for k in ("test_1_raw", "test_2_raw", "test_3_raw", "test_4_raw")))
        fecha_de = {f["event_id"]: f["fecha"] for _ev, f in muestras}
        nombre_de = {f["event_id"]: f["hoja"] for _ev, f in muestras}
        periodo_de = {f["event_id"]: f["periodo"] for _ev, f in muestras}
        fiesta_de = {f["event_id"]: (f["fiesta_id"] or "", f["fiesta_id"] or "")
                     for _ev, f in muestras}

        # --- Las observaciones, solo de las filas que son muestra ------
        reactivos = Counter()
        colores = Counter()
        color_por_reactivo: dict[str, Counter] = defaultdict(Counter)
        for o in conn.execute(
            "SELECT test_id, reagent_raw, result_raw FROM testeo_observaciones_fuente "
            "WHERE observation_status = 'source_observation_preserved'"
        ):
            if o["test_id"] not in propias:
                continue
            rea = normalizar_reactivo(o["reagent_raw"])["canonico"]
            if not rea:
                continue
            reactivos[rea] += 1
            lectura = normalizar_color(o["result_raw"], troqueles)
            if lectura["status"] in ("encabezado_o_reactivo", "vacio",
                                     "descripcion_de_muestra"):
                continue
            clave = lectura.get("clave") or lectura["outcome"]
            colores[clave] += 1
            color_por_reactivo[rea][clave] += 1

        return {
            "desorden": {
                "reactivo_crudo": len(crudo_reactivo),
                "color_crudo": len(crudo_color),
                "sustancia_cruda": len(crudo_sustancia),
                "reactivo_real": len(reactivos),
                "color_real": len(colores),
                "sustancia_real": len(sustancias),
            },
            # Que paso con cada fila de la planilla, de arriba a abajo.
            "procedencia": {
                "muestras analizadas": len(propias),
                "atendidas sin análisis": sin_reactivo,
                "repetidas o copiadas": (clasificacion.get("repetida_en_racha", 0)
                                         + clasificacion.get("copiada_de_otra_jornada", 0)
                                         + copiadas_de_hermana),
            },
            "descartes": {
                "repetidas dentro de la hoja": clasificacion.get("repetida_en_racha", 0),
                "copiadas de otra jornada": clasificacion.get("copiada_de_otra_jornada", 0),
                "hoja Copy of duplicada": copiadas_de_hermana,
                "rotulos de sala": rotulos,
                "encabezados repetidos": clasificacion.get("encabezado_repetido", 0),
            },
            "jornadas": dict(sorted(fiestas_periodo.items())),
            "muestras_periodo": dict(sorted(muestras_periodo.items())),
            "atendidas_sin_reactivo": sin_reactivo,
            "sin_reactivo_nombrado": sin_nombre,
            "totales": {
                "jornadas": sum(fiestas_periodo.values()),
                "muestras": len(propias),
                "observaciones": int(sum(reactivos.values())),
                "filas_fuente": int(sum(clasificacion.values())),
            },
            "sustancias": dict(sustancias.most_common()),
            # El panel de cada sustancia: que reactivo se le aplico, a que
            # fraccion de sus muestras, y que colores dio. El agregado de
            # todos los reactivos junta cosas que no se promedian -- Marquis
            # sobre MDMA da negro el 65% y sobre cocaina el 4%.
            "por_sustancia": _paneles(muestras, troqueles),
            "reactivos": dict(reactivos.most_common()),
            "colores": dict(colores.most_common()),
            "color_por_reactivo": {k: dict(v.most_common())
                                   for k, v in color_por_reactivo.items()},
            "hex": dict(HEX),
            "no_colorimetricos": list(NO_COLORIMETRICOS),
            "etiqueta_sustancia": ETIQUETA_SUSTANCIA,
            "etiqueta_color": ETIQUETA_COLOR,
            "marca": MARCA,
            # La tabla ordenada: una fila por muestra, con su origen exacto
            # para que cualquiera la pueda ir a ver a la planilla.
            "tabla": [
                {
                    "periodo": f["periodo"],
                    "fecha": f["fecha"],
                    "fiesta": f["fiesta_id"] or nombre_de[ev].strip(),
                    "hoja": (f["hoja"] or "").strip(),
                    "fila": f["fila"],
                    "sustancia": normalizar_sustancia(f["substance_raw"])["canonico"] or "NO_DECLARA",
                    "sustancia_cruda": f["substance_raw"],
                    "formato": f["format_raw"],
                    "ensayos": [
                        {
                            "reactivo": normalizar_reactivo(f[t])["canonico"],
                            "reactivo_crudo": f[t],
                            "color": (normalizar_color(f[r], troqueles).get("clave")
                                      or normalizar_color(f[r], troqueles)["outcome"]),
                            "color_crudo": f[r],
                        }
                        for t, r in (("test_1_raw", "result_1_raw"), ("test_2_raw", "result_2_raw"),
                                     ("test_3_raw", "result_3_raw"), ("test_4_raw", "result_4_raw"))
                        if (f[t] or "").strip() or (f[r] or "").strip()
                    ],
                    "reactivo_sin_nombrar": not any(
                        normalizar_reactivo(f[k])["canonico"]
                        for k in ("test_1_raw", "test_2_raw",
                                  "test_3_raw", "test_4_raw")),
                }
                for ev, f in muestras
            ] if detalle else [],
        }
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=None, help="ruta a rd.db")
    ap.add_argument("--out", default=str(_REPO / "dist_compartir" / "resumen_testeos_rd.html"))
    ap.add_argument("--json", default=None, help="ademas, escribe el payload crudo")
    args = ap.parse_args()

    db = Path(args.db) if args.db else rd_db_path(_REPO)
    if not db.is_file():
        print(f"no existe la base: {db}\ncorre primero: py -m flujo rd-db build")
        return 1

    datos = reunir(db)
    if args.json:
        Path(args.json).write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    plantilla = (_REPO / "tools" / "plantillas" / "resumen_testeos_rd.html").read_text(
        encoding="utf-8")
    html = plantilla.replace(
        "/*__DATOS__*/null",
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    t = datos["totales"]
    print(f"{out}  ({out.stat().st_size // 1024} KB)")
    print(f"  {t['jornadas']} jornadas · {t['muestras']} muestras · "
          f"{t['observaciones']} ensayos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
