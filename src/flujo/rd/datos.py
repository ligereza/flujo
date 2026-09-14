"""Ingesta privacy-first de datos de campo RD (testeo/atenciones/encuestas).

Escribe en `data/rd.db`, la unica DB de RD. Hasta el 2026-09-05 estas tres
tablas vivian aparte en `data/rd_datos.db`, y la razon era real: `rd.db` es una
proyeccion regenerable cuyo `build_rd_db()` BORRA el archivo y lo reescribe
entero, asi que un rebuild habria destruido registros de terreno que no existen
en ninguna otra parte.

El operador pidio una sola base. La separacion no se resolvio moviendo el
problema sino quitandolo: `build_rd_db()` ahora RESCATA las filas de estas tres
tablas antes de borrar el archivo y las REINSERTA despues, de modo que la
reconstruccion sigue siendo idempotente para lo derivado y no destructiva para
lo acumulado. Ver `_rescatar_acumulativas` en `src/flujo/rd/database.py`.

Lo acumulativo sigue siendo acumulativo: `conectar()` usa
`CREATE TABLE IF NOT EXISTS` y nunca borra filas.

El diseno de privacidad de abajo NO cambia con la fusion, porque nada de el
dependia del nombre del archivo: vive en el schema (que no tiene columnas de
identidad) y en el scan que corre antes de cada insercion.

Diseno de privacidad (no negociable, ver F3a del plan de liberacion):

- PII imposible POR SCHEMA: ninguna tabla tiene columnas de identidad
  (nombre/rut/telefono/email/nacimiento). Lo que no existe como columna no
  se puede filtrar por accidente.
- `fecha` es SIEMPRE `YYYY-MM-DD` (nunca hora): evita re-identificar a
  alguien por marca de tiempo fina (k-anonimato minimo por dia+evento).
- Toda fila pasa por `flujo.privacy.scan_text` ANTES de tocar la DB:
    - RUT chileno o numero de tarjeta detectado -> la fila se RECHAZA
      SIEMPRE, sin excepcion de policy. Se cuenta en `rechazadas_pii`; el
      contenido de la fila NUNCA se loguea ni se imprime, ni en el detalle
      de error (eso violaria el proposito del scan).
    - Otro tipo de PII (email/telefono/url/direccion):
        `policy="strict"` (default) -> la fila tambien se rechaza.
        `policy="sanitize"` -> los campos de texto libre se sanitizan
          (placeholders `[EMAIL]`/`[TELEFONO]`/... via
          `flujo.privacy.sanitize.REPLACEMENTS`) y la fila se persiste ya
          sanitizada.
"""
from __future__ import annotations

import calendar
import csv
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from ..privacy import scan_text
from ..privacy.sanitize import REPLACEMENTS

_REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = _REPO / "data" / "rd.db"
# La DB previa, conservada: es la fuente de migracion y no se borra. Si tiene
# filas y `rd.db` no, `build_rd_db()` las trae una sola vez.
LEGACY_DB_PATH = _REPO / "data" / "rd_datos.db"
# Las tres tablas que se acumulan. `build_rd_db()` las preserva por nombre.
TABLAS_ACUMULATIVAS: tuple[str, ...] = (
    "registros_testeo",
    "atenciones",
    "encuestas",
)

# Vocabulario cerrado de `atenciones.tipo`
TIPOS_ATENCION: tuple[str, ...] = ("hidratacion", "escucha", "derivacion", "informacion")

# Tipos de CSV que acepta ingest_csv (no confundir con TIPOS_ATENCION)
TIPOS_CSV: tuple[str, ...] = ("testeo", "atencion", "encuesta")

# Campos obligatorios (no vacios) por tipo de CSV, ademas de `fecha` (siempre obligatoria)
_CAMPOS_OBLIGATORIOS: dict[str, tuple[str, ...]] = {
    "testeo": ("sustancia_declarada", "reactivo"),
    "atencion": ("tipo",),
    "encuesta": ("pregunta_id", "respuesta"),
}

SCHEMA_ACUMULATIVO = """
CREATE TABLE IF NOT EXISTS registros_testeo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,               -- YYYY-MM-DD, nunca hora: k-anonimato
    evento TEXT,
    sustancia_declarada TEXT NOT NULL,
    reactivo TEXT NOT NULL,
    resultado_color TEXT,
    familia_detectada TEXT,
    coincide INTEGER,                  -- 1/0/NULL
    adulterante_sospechado TEXT,
    descartada INTEGER DEFAULT 0,
    notas TEXT                         -- solo texto ya sanitizado
);
CREATE TABLE IF NOT EXISTS atenciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    evento TEXT,
    tipo TEXT NOT NULL,                -- hidratacion|escucha|derivacion|informacion
    derivado_a TEXT,
    rango_etario TEXT,
    notas TEXT
);
CREATE TABLE IF NOT EXISTS encuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    evento TEXT,
    pregunta_id TEXT NOT NULL,
    respuesta TEXT NOT NULL
);
"""

_INSERTS: dict[str, str] = {
    "testeo": (
        "INSERT INTO registros_testeo(fecha, evento, sustancia_declarada, reactivo, "
        "resultado_color, familia_detectada, coincide, adulterante_sospechado, "
        "descartada, notas) VALUES (?,?,?,?,?,?,?,?,?,?)"
    ),
    "atencion": (
        "INSERT INTO atenciones(fecha, evento, tipo, derivado_a, rango_etario, notas) "
        "VALUES (?,?,?,?,?,?)"
    ),
    "encuesta": (
        "INSERT INTO encuestas(fecha, evento, pregunta_id, respuesta) VALUES (?,?,?,?)"
    ),
}


@dataclass
class IngestResult:
    """Resultado de `ingest_csv`. `detalle_invalidas` solo trae los primeros
    5 mensajes (errores de FORMA -- fecha/campos obligatorios -- nunca el
    contenido de una fila rechazada por PII)."""

    insertadas: int = 0
    rechazadas_pii: int = 0
    invalidas: int = 0
    detalle_invalidas: list[str] = field(default_factory=list)


def conectar(db: str | Path | None = None) -> sqlite3.Connection:
    """Abre (y crea si falta) la DB de datos de campo. NUNCA destructivo:
    usa `CREATE TABLE IF NOT EXISTS`, jamas borra el archivo existente."""
    path = Path(db) if db is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_ACUMULATIVO)
    conn.commit()
    return conn


def validar_fila(row: dict[str, Any], tipo: str) -> list[str]:
    """Errores de FORMA de una fila (lista vacia = fila valida): campos
    obligatorios, fecha ISO, vocabulario cerrado. No decide nada sobre PII
    -- eso es responsabilidad exclusiva de `ingest_csv` via `scan_text`."""
    if tipo not in TIPOS_CSV:
        return [f"tipo de CSV desconocido: {tipo!r} (usa {'/'.join(TIPOS_CSV)})"]

    errores: list[str] = []

    fecha = (row.get("fecha") or "").strip()
    if not fecha:
        errores.append("fecha vacia")
    else:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            errores.append(f"fecha no es ISO YYYY-MM-DD: {fecha!r}")

    for campo in _CAMPOS_OBLIGATORIOS[tipo]:
        if not (row.get(campo) or "").strip():
            errores.append(f"campo obligatorio vacio: {campo}")

    if tipo == "atencion":
        v = (row.get("tipo") or "").strip().lower()
        if v and v not in TIPOS_ATENCION:
            errores.append(
                f"tipo de atencion invalido: {v!r} (usa {'/'.join(TIPOS_ATENCION)})"
            )

    return errores


def _sanitize_campo(valor: str) -> str:
    """Aplica los reemplazos de PII de `flujo.privacy` SIN el header de
    documento (`SANITIZE_HEADER` es para archivos sueltos, no para una
    columna de DB): solo la sustitucion de patrones -> placeholders."""
    out = valor
    for pat, repl in REPLACEMENTS:
        out = pat.sub(repl, out)
    return out


def _to_bool_int(value: Any) -> int | None:
    """'1'/'true'/'si'/'yes' -> 1, '0'/'false'/'no' -> 0, vacio/otro -> None."""
    v = str(value).strip().lower() if value not in (None, "") else ""
    if v in ("1", "true", "si", "sí", "yes"):
        return 1
    if v in ("0", "false", "no"):
        return 0
    return None


def _insertar_fila(conn: sqlite3.Connection, tipo: str, row: dict[str, Any]) -> None:
    fecha = row["fecha"].strip()
    evento = (row.get("evento") or "").strip() or None
    if tipo == "testeo":
        conn.execute(
            _INSERTS["testeo"],
            (
                fecha,
                evento,
                row["sustancia_declarada"].strip(),
                row["reactivo"].strip(),
                (row.get("resultado_color") or "").strip() or None,
                (row.get("familia_detectada") or "").strip() or None,
                _to_bool_int(row.get("coincide")),
                (row.get("adulterante_sospechado") or "").strip() or None,
                _to_bool_int(row.get("descartada")) or 0,
                (row.get("notas") or "").strip() or None,
            ),
        )
    elif tipo == "atencion":
        conn.execute(
            _INSERTS["atencion"],
            (
                fecha,
                evento,
                row["tipo"].strip().lower(),
                (row.get("derivado_a") or "").strip() or None,
                (row.get("rango_etario") or "").strip() or None,
                (row.get("notas") or "").strip() or None,
            ),
        )
    elif tipo == "encuesta":
        conn.execute(
            _INSERTS["encuesta"],
            (
                fecha,
                evento,
                row["pregunta_id"].strip(),
                row["respuesta"].strip(),
            ),
        )


def ingest_csv(
    path: str | Path,
    tipo: str,
    db: str | Path | None = None,
    policy: str = "strict",
) -> IngestResult:
    """Ingesta un CSV de terreno a la DB de datos de campo, fila por fila.

    Cada fila:
      1. se valida por FORMA (`validar_fila`) -- si falla, cuenta como
         `invalidas` (mensaje de forma, nunca contenido sensible se omite
         porque el mensaje de forma no incluye PII por construccion salvo el
         propio valor de fecha/tipo, que no son PII);
      2. se escanea COMPLETA con `flujo.privacy.scan_text` antes de insertar:
         - RUT chileno o tarjeta -> rechazo SIEMPRE (se cuenta, contenido
           JAMAS logueado);
         - otro PII bajo `policy="strict"` (default) -> tambien rechazo;
         - otro PII bajo `policy="sanitize"` -> se sanitizan los campos de
           texto libre y se persiste la fila sanitizada.
    """
    if policy not in ("strict", "sanitize"):
        raise ValueError(f"policy invalida: {policy!r} (usa strict|sanitize)")
    if tipo not in TIPOS_CSV:
        raise ValueError(f"tipo invalido: {tipo!r} (usa {'/'.join(TIPOS_CSV)})")

    csv_path = Path(path)
    resultado = IngestResult()
    conn = conectar(db)
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for n, row in enumerate(reader, start=2):  # fila 1 = header
                errores = validar_fila(row, tipo)
                if errores:
                    resultado.invalidas += 1
                    if len(resultado.detalle_invalidas) < 5:
                        resultado.detalle_invalidas.append(
                            f"fila {n}: {'; '.join(errores)}"
                        )
                    continue

                # Escaneo de privacidad sobre TODOS los valores de la fila
                texto_completo = "\n".join(str(v) for v in row.values() if v)
                scan = scan_text(texto_completo)

                if "rut_chile" in scan.matches or "tarjeta" in scan.matches:
                    # Nunca se loguea el contenido -- solo se cuenta.
                    resultado.rechazadas_pii += 1
                    continue

                if scan.total_pii > 0:
                    if policy == "strict":
                        resultado.rechazadas_pii += 1
                        continue
                    # policy == "sanitize": el scan corrio sobre TODA la fila
                    # (cualquier columna es texto libre tipeado por un
                    # operador -- incluido `evento`), asi que la limpieza
                    # tambien cubre TODA la fila, no solo `notas`. Aplicar
                    # los reemplazos a campos estructurados (fecha, tipo,
                    # coincide, descartada, ...) es un no-op seguro: no
                    # tienen forma de email/RUT/telefono/tarjeta/URL.
                    for campo, valor in list(row.items()):
                        if valor:
                            row[campo] = _sanitize_campo(str(valor))

                _insertar_fila(conn, tipo, row)
                resultado.insertadas += 1
        conn.commit()
    finally:
        conn.close()
    return resultado


# ---------------------------------------------------------------------------
# Agregaciones (F3b) -- funciones puras de solo lectura sobre `conectar()`.
# Ninguna columna de identidad existe en el schema (ver docstring del
# modulo), asi que ninguna agregacion puede filtrar PII: son GROUP BY sobre
# columnas cerradas (sustancia/tipo/fecha) o conteos.
# ---------------------------------------------------------------------------

_TRIMESTRE_RE = re.compile(r"^(\d{4})-Q([1-4])$")


def rango_trimestre(trimestre: str) -> tuple[str, str]:
    """Convierte 'YYYY-Q1'..'YYYY-Q4' al rango ISO inclusive
    (fecha_inicio, fecha_fin) de ese trimestre. Lanza ValueError si el
    formato no calza (nunca adivina un trimestre)."""
    m = _TRIMESTRE_RE.match(trimestre.strip().upper())
    if not m:
        raise ValueError(
            f"trimestre invalido: {trimestre!r} (usa 'YYYY-Q1'..'YYYY-Q4')"
        )
    anio = int(m.group(1))
    q = int(m.group(2))
    mes_inicio = (q - 1) * 3 + 1
    mes_fin = mes_inicio + 2
    ultimo_dia = calendar.monthrange(anio, mes_fin)[1]
    return f"{anio:04d}-{mes_inicio:02d}-01", f"{anio:04d}-{mes_fin:02d}-{ultimo_dia:02d}"


def _filtro_trimestre(trimestre: str | None) -> tuple[str, tuple[str, ...]]:
    """SQL fragment ('' o 'WHERE fecha BETWEEN ? AND ?') + params."""
    if trimestre is None:
        return "", ()
    inicio, fin = rango_trimestre(trimestre)
    return "WHERE fecha BETWEEN ? AND ?", (inicio, fin)


def tendencias(
    conn: sqlite3.Connection, trimestre: str | None = None
) -> list[dict[str, Any]]:
    """Conteo de `registros_testeo` por mes (YYYY-MM) y sustancia
    declarada. `trimestre` opcional ('YYYY-Q1'..'YYYY-Q4') filtra el rango.
    Orden: mes ascendente, conteo descendente."""
    where, params = _filtro_trimestre(trimestre)
    sql = (
        "SELECT strftime('%Y-%m', fecha) AS mes, sustancia_declarada, "
        "COUNT(*) AS conteo FROM registros_testeo "
        f"{where} GROUP BY mes, sustancia_declarada "
        "ORDER BY mes ASC, conteo DESC"
    )
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def tasa_adulteracion(
    conn: sqlite3.Connection, trimestre: str | None = None
) -> list[dict[str, Any]]:
    """Tasa de no-coincidencia por sustancia declarada: filas donde el
    reactivo NO confirmo la sustancia declarada (`coincide = 0`) sobre el
    total de filas testeadas para esa sustancia. `tasa` en [0, 1]; 0.0
    cuando `total` es 0 (nunca division por cero)."""
    where, params = _filtro_trimestre(trimestre)
    sql = (
        "SELECT sustancia_declarada, "
        "SUM(CASE WHEN coincide = 0 THEN 1 ELSE 0 END) AS no_coincide, "
        "COUNT(*) AS total FROM registros_testeo "
        f"{where} GROUP BY sustancia_declarada "
        "ORDER BY sustancia_declarada"
    )
    rows = conn.execute(sql, params).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["tasa"] = (d["no_coincide"] / d["total"]) if d["total"] else 0.0
        out.append(d)
    return out


def atenciones_por_tipo(
    conn: sqlite3.Connection, trimestre: str | None = None
) -> list[dict[str, Any]]:
    """Conteo de `atenciones` por `tipo` (vocabulario cerrado
    `TIPOS_ATENCION`). Orden: conteo descendente."""
    where, params = _filtro_trimestre(trimestre)
    sql = (
        "SELECT tipo, COUNT(*) AS conteo FROM atenciones "
        f"{where} GROUP BY tipo ORDER BY conteo DESC"
    )
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
