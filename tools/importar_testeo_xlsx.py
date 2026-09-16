"""Convierte un libro de testeo RD al JSON de evidencia que lee `database.py`.

Produce exactamente el mismo esquema que `testeo_eventos_2025_evidence.json`,
para que `build_rd_db()` lo importe sin cambios. Existe porque el corpus 2024
—931 muestras en 25 jornadas— quedó fuera de la base: la planilla de Drive se
reusa año a año, y cuando alguien borró las hojas de 2024 para empezar 2025,
el importador ya nunca las vio.

Reglas que hace cumplir, todas heredadas de la política de la fuente:

- El color observado es la única afirmación. No se interpreta identidad,
  pureza, dosis ni seguridad.
- Nada se descarta. Los encabezados repetidos, las filas sin sustancia y los
  duplicados se conservan con su estado, igual que en la importación de 2025.
- Los duplicados se MARCAN, no se borran. La hoja `Mamisonga 8225` de 2025
  tiene 639 filas de las que 628 son la jornada anterior pegada 31 veces; el
  importador original las contó como muestras y por eso el panel dice 1.760
  donde hay 970. Acá cada fila lleva `row_duplicate_status` para que quien
  consuma decida, en vez de que el conteo mienta en silencio.

    python tools/importar_testeo_xlsx.py LIBRO.xlsx --periodo 2024 \
        --salida data/rd_fuentes/testeo_eventos_2024_evidence.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

import openpyxl

POLITICA_FILA = "observed_color_only_not_identity_purity_or_dose"
POLITICA_OBS = "contains_signal_only_no_claim_of_purity_or_dose"
ESQUEMA = "rd-testing-source-evidence-v0.1"

# Pares (test, resultado) por fila, tal como los trae la planilla.
PARES = ((2, 3), (4, 5), (6, 7), (8, 9))


def _id(prefijo: str, *partes: object) -> str:
    h = hashlib.sha256("|".join(str(p) for p in partes).encode("utf-8")).hexdigest()
    return f"{prefijo}-{h[:16]}"


def _clave(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def _texto(celda: object) -> str:
    return "" if celda is None else str(celda).strip()


def _es_encabezado(fila: list[str]) -> bool:
    return _clave(fila[0]).startswith("sustancia") or _clave(fila[0]).startswith("column")


def _fecha_del_nombre(nombre: str, periodo: str) -> tuple[str | None, str, str]:
    """Deduce la fecha del nombre de la hoja. Devuelve (iso, estado, confianza).

    Los nombres traen la fecha pegada y sin separador fijo: `DAME 1325`,
    `Dame 17-09-2025`, `hellbox 14-02-2025`. Cuando no se puede leer, la fecha
    NO se inventa: queda nula y el consumidor lo sabe por `date_confidence`.
    """
    # El periodo del libro es solo el default. `Testeo 2025` contiene hoy
    # jornadas de 2026, porque la planilla se sigue usando sin renombrarla:
    # el ano real de cada jornada sale de SU nombre, no del archivo.
    token = None
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})", nombre)
    if m:
        d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = a + 2000 if a < 100 else a
        try:
            return date(a, mes, d).isoformat(), "parsed_candidate", "medium"
        except ValueError:
            token = m.group(0)
    m = re.search(r"\b(\d{3,8})\b", nombre)
    if m:
        token = m.group(1)
        crudo = token
        # Se acepta el ano del libro y el siguiente: la planilla cruza el
        # cambio de ano sin que nadie la renombre.
        ventana = (periodo, str(int(periodo) + 1))
        # `1325` = 13/2/5 ; `18125` = 18/1/25 ; `2825` = 28/2/5 ;
        # `2612` = 26/12 (ano del libro) ; `30082025` = 30/08/2025.
        #
        # El orden de preferencia NO es arbitrario y `2825` vs `18125` lo
        # obliga: ambos parsean de dos formas validas.
        #   1. dia de DOS digitos primero -- la fecha se escribe dia-mes y un
        #      `28` es dia mucho antes que un `2`. Sin esto `2825` se leia
        #      2/8/25 y la jornada se movia cinco meses.
        #   2. a igual largo de dia, el ano MAS LARGO -- `18125` es 18/1/25
        #      (ano de dos digitos) y no 18/12/5.
        candidatos = sorted(
            ((d_len, m_len) for d_len in (2, 1) for m_len in (2, 1)
             if len(crudo) >= d_len + m_len),
            key=lambda dm: (-dm[0], -(len(crudo) - dm[0] - dm[1]), -dm[1]),
        )
        for d_len, m_len in candidatos:
            d = crudo[:d_len]
            mes = crudo[d_len:d_len + m_len]
            resto = crudo[d_len + m_len:]
            if not resto:
                anios = [periodo]
            elif len(resto) == 1:
                # Un solo digito es el ULTIMO del ano, no el ano 200X: `5` en
                # `2825` es 2025. Solo vale si identifica un ano de la ventana.
                anios = [a for a in ventana if a[-1] == resto]
            elif len(resto) == 2:
                anios = [str(int(resto) + 2000)]
            else:
                anios = [resto]
            for anio in anios:
                try:
                    iso = date(int(anio), int(mes), int(d)).isoformat()
                except ValueError:
                    continue
                if iso[:4] in ventana:
                    return iso, "parsed_from_sheet_name", "low"
    return None, ("not_found" if token is None else "unparsed_token"), "none"


def _tramo_ajeno(filas: list[tuple], otras: dict[str, list[tuple]],
                 minimo: int = 6) -> dict[int, str]:
    """Marca las filas que son un tramo contiguo copiado de OTRA hoja.

    Deduplicar dentro de la hoja no alcanza: quita las repeticiones del bloque
    pegado pero deja una copia entera. En `Mamisonga 8225` eso dejaba 25
    muestras donde hay 11, porque las otras 14 son la jornada de
    `Cachorros 18125` que el voluntario copio y no alcanzo a sobrescribir.

    Un solo renglon igual entre dos eventos no prueba nada —`Cocaina | Polvo
    blanco | Marquis | Negativo` se repite de verdad— asi que se exige un
    tramo CONTIGUO de al menos `minimo` filas. Devuelve {indice: hoja_origen}.

    El minimo es 6 y no 4 por medicion: con 4 se marcaba un tramo de
    `Fiesta Dame 504 mesa 1` que en realidad son tres MDMA «tesla rosada» con
    resultados DISTINTOS entre si —Naranjo/Rojo, Negro, Negro+Rojo—, o sea
    muestras reales del mismo diseno de pastilla. Los bloques pegados de
    verdad miden 16, 17, 28 y 71 filas, muy por encima del umbral.
    """
    marcadas: dict[int, str] = {}
    for nombre_otra, ajenas in otras.items():
        if not ajenas:
            continue
        posicion = {fila: i for i, fila in enumerate(ajenas)}
        i = 0
        while i < len(filas):
            if filas[i] not in posicion:
                i += 1
                continue
            j = posicion[filas[i]]
            largo = 0
            while (i + largo < len(filas) and j + largo < len(ajenas)
                   and filas[i + largo] == ajenas[j + largo]):
                largo += 1
            if largo >= minimo:
                for k in range(i, i + largo):
                    marcadas.setdefault(k, nombre_otra)
                i += largo
            else:
                i += 1
    return marcadas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("libro", type=Path)
    ap.add_argument("--periodo", required=True, help="etiqueta del periodo, p.ej. 2024")
    ap.add_argument("--salida", required=True, type=Path)
    args = ap.parse_args()

    if not args.libro.is_file():
        print(f"no existe {args.libro}", file=sys.stderr)
        return 1
    sha = hashlib.sha256(args.libro.read_bytes()).hexdigest()
    wb = openpyxl.load_workbook(args.libro, data_only=True)

    hojas, eventos, filas, observaciones = [], [], [], []
    # Firmas de dato por hoja, para detectar bloques copiados entre hojas.
    datos_por_hoja: dict[str, list[tuple]] = {}
    orden_por_hoja: dict[str, list[int]] = {}
    estados_fila: Counter = Counter()
    sustancias: Counter = Counter()
    reactivos: Counter = Counter()

    for indice, nombre in enumerate(wb.sheetnames, start=1):
        ws = wb[nombre]
        crudas = []
        for numero, fila in enumerate(ws.iter_rows(values_only=True), start=1):
            celdas = [_texto(c) for c in fila]
            if not any(celdas):
                continue
            crudas.append((numero, celdas + [""] * max(0, 11 - len(celdas))))

        datos_por_hoja[nombre] = [tuple(c[:8]) for _, c in crudas
                                  if c[0] and not _es_encabezado(c)]
        orden_por_hoja[nombre] = [n for n, c in crudas
                                  if c[0] and not _es_encabezado(c)]

        huella = hashlib.sha256(
            repr([c for _, c in crudas]).encode("utf-8")).hexdigest()
        hojas.append({
            "source_sheet_index": indice,
            "source_sheet_name": nombre,
            "data_row_count_including_anomalies": len(crudas),
            "source_sheet_hash": huella,
            "duplicate_group_id": "dup-" + huella[:16],
            "duplicate_group_size": 1,
            "duplicate_status": "unique_source_sheet",
        })

        event_id = _id("event", nombre, huella)
        iso, estado_fecha, confianza = _fecha_del_nombre(nombre, args.periodo)
        eventos.append({
            "event_id": event_id,
            "source_sheet_index": indice,
            "source_sheet_name": nombre,
            "event_label_candidate": nombre.strip(),
            "event_label_status": "source_sheet_name_only",
            # El periodo real de la jornada, no el del archivo.
            "source_period_label": (iso[:4] if iso else args.periodo),
            "date_raw_token": None,
            "date_iso_candidate": iso,
            "date_status": estado_fecha,
            "date_parse_style": "sheet_name" if iso else None,
            "date_confidence": confianza,
            "outside_filename_period_candidate": False,
            "is_source_copy_candidate": nombre.lower().startswith("copy of"),
            "duplicate_group_id": "dup-" + huella[:16],
            "duplicate_group_size": 1,
            "duplicate_status": "unique_source_sheet",
            "duplicate_canonical_sheet_candidate": nombre,
            "venue_id": None, "venue_name": None,
            "producer_id": None, "producer_name": None,
            "link_status": "unlinked",
            "link_evidence_ref": None,
            "link_confidence": "none",
            "link_review_status": "pending_human_link",
        })

        # Una fila identica repetida dentro de la misma hoja no son dos
        # muestras: es una pegada. Se marca, no se borra.
        vistas: dict[tuple, int] = {}
        for numero, celdas in crudas:
            firma = tuple(celdas[:10])
            repeticion = vistas.get(firma, 0)
            vistas[firma] = repeticion + 1

            if _es_encabezado(celdas):
                estado = "repeated_header"
            elif not celdas[0]:
                estado = "data_with_unresolved_substance"
            else:
                estado = "data"
            estados_fila[estado] += 1

            test_id = _id("test", event_id, numero)
            filas.append({
                "test_id": test_id,
                "event_id": event_id,
                "source_sheet_name": nombre,
                "source_row": numero,
                "row_status": estado,
                "substance_raw": celdas[0] or None,
                "substance_normalized_candidate": _clave(celdas[0]) or None if estado == "data" else None,
                "substance_map_status": "candidate_alias" if estado == "data" else estado,
                "format_raw": celdas[1] or None,
                "test_1_raw": celdas[2] or None, "result_1_raw": celdas[3] or None,
                "test_2_raw": celdas[4] or None, "result_2_raw": celdas[5] or None,
                "test_3_raw": celdas[6] or None, "result_3_raw": celdas[7] or None,
                "test_4_raw": celdas[8] or None, "result_4_raw": celdas[9] or None,
                "extra_1_raw": celdas[10] or None,
                "source_duplicate_group_id": "dup-" + huella[:16],
                "source_duplicate_status": "unique_source_sheet",
                # Lo que el importador de 2025 no tenia, y por eso Mamisonga
                # inflo el conteo del ano en un 84 %.
                "row_repeat_index": repeticion,
                "row_duplicate_status": "first_occurrence" if repeticion == 0
                                        else "repeat_within_sheet",
                "interpretation_policy": POLITICA_FILA,
            })
            if estado == "data":
                sustancias[celdas[0]] += 1

            for orden, (ct, cr) in enumerate(PARES, start=1):
                reactivo, resultado = celdas[ct], celdas[cr]
                if not reactivo and not resultado:
                    continue
                if estado == "data":
                    reactivos[reactivo] += 1
                observaciones.append({
                    "observation_id": _id("obs", test_id, orden),
                    "test_id": test_id,
                    "event_id": event_id,
                    "source_sheet_name": nombre,
                    "source_row": numero,
                    "observation_ordinal": orden,
                    "substance_raw": celdas[0] or None,
                    "substance_normalized_candidate": _clave(celdas[0]) or None if estado == "data" else None,
                    "reagent_raw": reactivo or None,
                    "reagent_normalized_candidate": _clave(reactivo) or None if estado == "data" else None,
                    "reagent_map_status": "candidate_alias" if estado == "data" else estado,
                    "result_raw": resultado or None,
                    "result_normalized_candidate": None,
                    "result_map_status": "observed_wording_only",
                    "observation_status": "source_observation_preserved",
                    "row_duplicate_status": "first_occurrence" if repeticion == 0
                                            else "repeat_within_sheet",
                    "interpretation_policy": POLITICA_OBS,
                })
    wb.close()

    # Bloques copiados de otra hoja. Se corre despues de leer todo el libro
    # porque hace falta el resto de las hojas para comparar. Marca la fila y
    # sus observaciones, y deja escrito DE DONDE salio: eso es evidencia, no
    # una limpieza a ciegas.
    ajenas_total = 0
    por_test: dict[str, dict] = {f["test_id"]: f for f in filas}
    for nombre, propias in datos_por_hoja.items():
        otras = {n: v for n, v in datos_por_hoja.items() if n != nombre}
        marcadas = _tramo_ajeno(propias, otras)
        # El tramo compartido aparece en las DOS hojas: hay que decidir de
        # cual es. Es de aquella donde ocupa la mayor parte del contenido.
        # `Cachorros 18125` son 20 filas y el bloque son 16 (80 %): la jornada
        # ES el bloque. En `Mamisonga 8225` son 16 de 639 (2 %): ahi el bloque
        # esta pegado. Sin esta regla el detector borraba al original.
        def _es_copia(mia: str, suya: str, tramo: int) -> bool:
            """True si el tramo pertenece a `suya` y quedo pegado en `mia`.

            Se compara contra el contenido DISTINTO de cada hoja, no contra su
            largo. `Mamisonga 8225` tiene 639 filas pero solo 25 distintas,
            porque repite su bloque 31 veces; medir contra 639 hacia ver a
            `Cachorros 18125` —el original— como si fuera la copia.

            El bloque es de quien lo tiene como mayor parte de su jornada:
            16 de las 16 filas distintas de Cachorros, contra 16 de las 25 de
            Mamisonga.
            """
            distintas_mias = len(set(propias)) or 1
            distintas_suyas = len(set(datos_por_hoja.get(suya, []))) or 1
            peso_mio = tramo / distintas_mias
            peso_suyo = tramo / distintas_suyas
            if abs(peso_mio - peso_suyo) > 0.05:
                return peso_mio < peso_suyo
            # Empate: dos hojas identicas. Desempata el nombre, que es lo unico
            # que queda — «Copy of Copy of X» es copia de «X».
            return mia.lower().count("copy of") > suya.lower().count("copy of")

        marcadas = {
            k: origen for k, origen in marcadas.items()
            if _es_copia(nombre, origen,
                         len({kk for kk, oo in marcadas.items() if oo == origen}))
        }
        if not marcadas:
            continue
        numeros = orden_por_hoja[nombre]
        for indice, origen in marcadas.items():
            numero = numeros[indice]
            for fila in filas:
                if fila["source_sheet_name"] == nombre and fila["source_row"] == numero:
                    # Una fila ya marcada como repeticion interna no se pisa:
                    # la primera aparicion del bloque es la que importa senalar.
                    if fila["row_duplicate_status"] == "first_occurrence":
                        fila["row_duplicate_status"] = "copied_from_other_sheet"
                        fila["copied_from_sheet"] = origen
                        ajenas_total += 1
                    break
    if ajenas_total:
        for obs in observaciones:
            fila = por_test.get(obs["test_id"])
            if fila and fila["row_duplicate_status"] == "copied_from_other_sheet":
                obs["row_duplicate_status"] = "copied_from_other_sheet"

    # Hojas identicas entre si: se agrupan, no se descartan.
    por_huella: dict[str, list[str]] = {}
    for h in hojas:
        por_huella.setdefault(h["source_sheet_hash"], []).append(h["source_sheet_name"])
    for h in hojas:
        grupo = por_huella[h["source_sheet_hash"]]
        if len(grupo) > 1:
            h["duplicate_group_size"] = len(grupo)
            h["duplicate_status"] = "exact_sheet_duplicate_candidate"
    for e in eventos:
        grupo = por_huella.get(e["duplicate_group_id"].replace("dup-", ""), [])
    for e in eventos:
        for h in hojas:
            if h["source_sheet_name"] == e["source_sheet_name"]:
                e["duplicate_group_size"] = h["duplicate_group_size"]
                e["duplicate_status"] = h["duplicate_status"]
                e["duplicate_canonical_sheet_candidate"] = sorted(
                    por_huella[h["source_sheet_hash"]])[0]

    unicas = sum(1 for f in filas
                 if f["row_status"] == "data" and f["row_duplicate_status"] == "first_occurrence")
    copiadas = sum(1 for f in filas
                   if f["row_duplicate_status"] == "copied_from_other_sheet")
    payload = {
        "schema_version": ESQUEMA,
        "generated_at": date.today().isoformat(),
        "language": "es",
        # Token de maquina, no prosa: `testing_evidence_summary()` lo expone
        # como `status` y hay consumidores que comparan contra el literal.
        # La frase en castellano vive en `principles`, que es donde se lee.
        "status": "candidate_evidence_pending_human_review",
        "source": {
            "file_name": args.libro.name,
            "source_copy": args.libro.name,
            "sha256": sha,
            "filename_period_label": args.periodo,
            "formula_count": 0,
        },
        "principles": [
            "Una observacion colorimetrica es una senal de presencia.",
            "No establece identidad, pureza, dosis ni seguridad.",
            "Nada de la fuente se descarta: lo anomalo se marca con su estado.",
            "Una fila repetida dentro de una hoja se marca, no se cuenta dos veces.",
            "El enlace a productora y venue espera revision humana.",
        ],
        "source_sheets": hojas,
        "events": eventos,
        "test_rows": filas,
        "observations": observaciones,
        "substance_map": [{"raw_label": k, "count": v,
                           "normalized_id": _clave(k), "mapping_status": "candidate_alias"}
                          for k, v in sustancias.most_common()],
        "reagent_map": [{"raw_label": k, "count": v,
                         "normalized_id": _clave(k), "mapping_status": "candidate_alias"}
                        for k, v in reactivos.most_common()],
        # Dos filas por jornada, no una: `testeo_enlaces_revision` declara
        # `link_id` PRIMARY KEY y `target_kind` NOT NULL, y el contrato de
        # integracion de mas abajo dice textualmente "keep event-to-venue and
        # event-to-producer as separate links". Una sola fila sin tipo dejaba
        # 67 link_id nulos y una cola de revision donde no se sabe QUE falta
        # revisar de cada jornada.
        "link_queue": [
            {"link_id": f"link-{e['event_id']}-{kind}",
             "event_id": e["event_id"],
             "source_sheet_name": e["source_sheet_name"],
             "target_kind": kind,
             "target_id": e.get(f"{kind}_id_candidate"),
             "target_name": e.get(f"{kind}_name_candidate"),
             "relation_type": f"event_{kind}",
             "evidence_ref": e["source_sheet_name"],
             "confidence": "none",
             "status": "unlinked",
             "review_status": "pending_human_link"}
            for e in eventos for kind in ("venue", "producer")
        ],
        "registries": {"venues": [], "producers": [], "reagents": []},
        "integration_contract": {
            "schema_version": "rd-testing-context-bridge-v0.1",
            "entity_keys": {"test": "test_id", "event": "event_id",
                            "venue": "venue_id", "producer": "producer_id"},
            "join_policy": [
                "Use stable IDs, never a display name as a foreign key.",
                "Keep event-to-venue and event-to-producer as separate links.",
                "A repeated row within a sheet is not a second sample.",
            ],
        },
        "coverage": {
            "source_sheet_count": len(hojas),
            "event_count": len(eventos),
            "test_row_count_including_repeated_headers": len(filas),
            "test_row_count_data": estados_fila["data"],
            "test_row_count_unique_data": unicas,
            "test_row_count_copied_from_other_sheet": copiadas,
            "observation_count": len(observaciones),
            "row_status_counts": dict(estados_fila),
            "exact_duplicate_sheet_groups": sum(
                1 for g in por_huella.values() if len(g) > 1),
        },
        "review_queue": [
            {"kind": "repeat_within_sheet",
             "count": estados_fila["data"] - unicas - copiadas,
             "note": "filas de dato repetidas dentro de su propia hoja"},
            {"kind": "copied_from_other_sheet",
             "count": copiadas,
             "note": "tramos contiguos que pertenecen a la jornada de otra hoja"},
        ],
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    c = payload["coverage"]
    print(f"{args.salida}")
    print(f"  {c['source_sheet_count']} hojas · {c['event_count']} eventos")
    print(f"  {c['test_row_count_data']} filas de dato · {c['test_row_count_unique_data']} unicas")
    print(f"  {c['observation_count']} observaciones")
    if c["test_row_count_data"] != c["test_row_count_unique_data"]:
        print(f"  repetidas dentro de su hoja: "
              f"{c['test_row_count_data'] - c['test_row_count_unique_data'] - copiadas}")
    if copiadas:
        print(f"  copiadas de otra hoja      : {copiadas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
