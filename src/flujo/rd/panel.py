"""Los datos de RD que ve un panel, con su allowlist de privacidad.

Vivia dentro del handler del hub. Se saco a un modulo porque ahora lo necesitan
DOS lugares: el hub, que lo sirve en vivo, y el empaquetado del HTML suelto,
que lo hornea adentro para que funcione sin servidor. Duplicar esta funcion
seria duplicar la allowlist, y esa es la peor duplicacion posible: un campo de
contacto agregado manana entraria por la copia que nadie recuerda.
"""
from __future__ import annotations

import json
import sqlite3
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .colorimetria import COLORES, HEX as COLOR_HEX, normalizar as normalizar_color
from .paths import rd_db_path


def _event_key(productora_slug: str, nombre: str, fecha: str = "") -> str:
    """Stable key for an RD event card; never uses a display-name lookup."""
    def token(value: str) -> str:
        plain = unicodedata.normalize("NFD", str(value or "").lower())
        plain = "".join(c for c in plain if unicodedata.category(c) != "Mn")
        return re.sub(r"[^a-z0-9]+", "-", plain).strip("-") or "sin-dato"
    return f"rd:{token(productora_slug)}:{token(nombre)}:{token(fecha)}"


def _norm_link_value(value: object) -> str:
    """Normalize only values used to compare two existing DB projections."""
    plain = unicodedata.normalize("NFD", str(value or "").lower())
    plain = "".join(c for c in plain if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def _venue_link_key(value: object) -> str:
    """Normalize a venue label without turning a guess into an identity.

    Event sources sometimes append editorial evidence to the venue (for
    example ``-- confirmado por el usuario`` or ``(needs_confirmation)``).
    Those annotations are not part of the venue name.  The comparison keeps
    the actual place text and removes only those unambiguous suffixes plus a
    trailing country word.  It does not use fuzzy matching.
    """
    text = str(value or "").strip()
    if not text or text.lower() == "needs_confirmation":
        return ""
    text = re.split(r"\s+--\s+", text, maxsplit=1)[0]
    text = re.sub(r"\s*\([^)]*\)", "", text)
    key = _norm_link_value(text)
    if key.endswith(" chile"):
        key = key[:-6].rstrip()
    return key


def _database_event_link(root: Path, productora_slug: str, event: dict) -> dict:
    """Check the event card against the existing SQLite projection.

    ``data/productoras/*.json`` remains the source of truth.  SQLite is a
    regenerable projection, so this function never writes to it and never
    turns a missing row into a new event.  The three stable keys are the
    productora slug, the literal event name and the literal source date.
    """
    result = {
        "status": "unavailable",
        "source": "data/rd.db",
        "table": "productora_eventos",
        "keys": ["productora_slug", "nombre", "fecha"],
    }
    db_path = rd_db_path(root)
    if not db_path.is_file():
        result["reason"] = "la proyección SQLite no está construida"
        return result

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            ("productora_eventos",),
        ).fetchone()
        if table is None:
            result["reason"] = "la tabla productora_eventos no existe"
            return result
        rows = conn.execute(
            "SELECT id, productora_slug, nombre, fecha, venue, estado, fuente, "
            "fuentes_primarias, sin_fuente_primaria "
            "FROM productora_eventos "
            "WHERE productora_slug=? AND nombre=? AND fecha IS ? "
            "ORDER BY id",
            (productora_slug, event.get("nombre", ""), event.get("fecha")),
        ).fetchall()
        if len(rows) == 0:
            result["status"] = "missing"
            result["reason"] = "la ficha JSON no tiene una fila correspondiente en SQLite"
            return result
        if len(rows) > 1:
            result["status"] = "ambiguous"
            result["row_ids"] = [int(row["id"]) for row in rows]
            result["reason"] = "más de una fila para la misma clave estable"
            return result

        row = dict(rows[0])
        same_identity = all(
            _norm_link_value(row.get(field)) == _norm_link_value(event.get(field))
            for field in ("nombre", "fecha", "venue", "estado")
        )
        result["status"] = "exact" if same_identity else "divergent"
        result["id"] = int(row["id"])
        result["row"] = {
            "productora_slug": row["productora_slug"],
            "nombre": row["nombre"],
            "fecha": row["fecha"],
            "venue": row["venue"],
            "estado": row["estado"],
            "fuente": row["fuente"],
            "fuentes_primarias": _json_list(row.get("fuentes_primarias")),
            "sin_fuente_primaria": bool(row.get("sin_fuente_primaria")),
        }
        if not same_identity:
            result["reason"] = "la clave existe, pero venue/estado no coincide"
        return result
    except (OSError, sqlite3.Error) as exc:
        result["reason"] = f"no se pudo leer SQLite en modo solo lectura: {exc}"
        return result
    finally:
        if conn is not None:
            conn.close()


def _database_venue_link(root: Path, productora_slug: str, event: dict) -> dict:
    """Resolve an event venue against the existing productora_venues rows.

    This is deliberately separate from the canonical venue catalogue.  A
    productora can have a declared venue that still lacks a curated
    ``venue_id``; that is useful evidence, but it is not a canonical venue
    identity.  The read-only relation prevents the panel from silently
    creating or merging venues.
    """
    result = {
        "status": "pending_review",
        "source": "data/rd.db",
        "table": "productora_venues",
        "keys": ["productora_slug", "venue_nombre"],
    }
    venue_key = _venue_link_key(event.get("venue"))
    if not venue_key:
        result["reason"] = "el evento no tiene un venue identificable"
        return result
    db_path = rd_db_path(root)
    if not db_path.is_file():
        result["status"] = "unavailable"
        result["reason"] = "la proyección SQLite no está construida"
        return result

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            ("productora_venues",),
        ).fetchone()
        if table is None:
            result["status"] = "unavailable"
            result["reason"] = "la tabla productora_venues no existe"
            return result
        rows = conn.execute(
            "SELECT id, venue_nombre, venue_id, preferido, estado "
            "FROM productora_venues WHERE productora_slug=? ORDER BY id",
            (productora_slug,),
        ).fetchall()
        matches = [row for row in rows if _venue_link_key(row["venue_nombre"]) == venue_key]
        if not matches:
            result["reason"] = "el venue del evento no está declarado para la productora"
            return result
        if len(matches) > 1:
            result["status"] = "ambiguous"
            result["row_ids"] = [int(row["id"]) for row in matches]
            result["reason"] = "hay más de una declaración del mismo venue"
            return result
        row = matches[0]
        result["status"] = "exact"
        result["id"] = int(row["id"])
        result["name"] = row["venue_nombre"]
        result["venue_id"] = row["venue_id"]
        result["preferido"] = bool(row["preferido"])
        result["estado"] = row["estado"]
        return result
    except (OSError, sqlite3.Error) as exc:
        result["status"] = "unavailable"
        result["reason"] = f"no se pudo leer productora_venues en modo solo lectura: {exc}"
        return result
    finally:
        if conn is not None:
            conn.close()


def _json_list(value: object) -> list:
    """Decode a JSON list from the DB without letting malformed evidence leak."""
    if isinstance(value, list):
        return value
    try:
        decoded = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def _wire_event_links(
    productora_slug: str,
    event: dict,
    venues: list[dict],
    declared_venues: list[dict] | None = None,
) -> None:
    """Add deterministic links without guessing a venue or rider asset.

    An exact normalized venue match is safe to automate. Rider/layout files
    are only linked when the source event explicitly provides their refs;
    otherwise the UI receives a generated key and a review status.
    """
    event["event_key"] = _event_key(productora_slug, event.get("nombre", ""), event.get("fecha_iso") or event.get("fecha", ""))
    event_venue = str(event.get("venue") or "").strip()
    def norm(value: str) -> str:
        plain = unicodedata.normalize("NFD", value.lower())
        plain = "".join(c for c in plain if unicodedata.category(c) != "Mn")
        return re.sub(r"[^a-z0-9]+", " ", plain).strip()
    venue_map = {norm(v.get("nombre", "")): v for v in venues if v.get("nombre")}
    matched = venue_map.get(norm(event_venue)) if event_venue else None
    venue_link = {"status": "exact" if matched else "pending_review"}
    if matched and matched.get("id"):
        venue_link["id"] = matched["id"]
    if matched:
        venue_link["name"] = matched["nombre"]
    elif event_venue:
        # Conservar el texto de origen sólo cuando existe; no emitir una
        # cadena vacía como si fuera un dato de venue.
        venue_link["name"] = event_venue
    event["venue_link"] = venue_link
    declared_venues = declared_venues or []
    declared_matches = [
        v for v in declared_venues
        if _venue_link_key(v.get("nombre")) == _venue_link_key(event_venue)
    ]
    source_venue_link = {
        "status": "pending_review",
        "source": "data/productoras",
        "reason": "el venue del evento no coincide exactamente con una declaración de la productora",
    }
    if len(declared_matches) == 1 and _venue_link_key(event_venue):
        declared = declared_matches[0]
        source_venue_link = {
            "status": "exact",
            "name": declared.get("nombre"),
            "venue_id": declared.get("venue_id"),
            "estado": declared.get("estado"),
            "preferido": bool(declared.get("preferido")),
            "source": "data/productoras",
        }
    elif len(declared_matches) > 1:
        source_venue_link = {
            "status": "ambiguous",
            "source": "data/productoras",
            "reason": "la productora declara el mismo venue más de una vez",
        }
    event["venue_source_link"] = source_venue_link
    flyer_ref = str(event.get("flyer_ref") or "").strip()
    flyer_link = {
        "status": "explicit" if flyer_ref else "pending_review",
        "generated_key": event["event_key"] + ":flyer",
    }
    if flyer_ref:
        flyer_link["ref"] = flyer_ref
    event["flyer_link"] = flyer_link
    rider_ref = str(event.get("rider_ref") or "").strip()
    layout_ref = str(event.get("layout_ref") or "").strip()
    rider_link = {
        "status": "explicit" if rider_ref else "pending_review",
        "generated_key": event["event_key"] + ":rider",
    }
    if rider_ref:
        rider_link["ref"] = rider_ref
    layout_link = {
        "status": "explicit" if layout_ref else "pending_review",
        "generated_key": event["event_key"] + ":layout",
    }
    if layout_ref:
        layout_link["ref"] = layout_ref
    event["rider_link"] = rider_link
    event["layout_link"] = layout_link


def rd_event_link(root: Path, event_key: str, overrides: dict | None = None) -> dict:
    """Resolve one exact RD event and consume the existing Plano engine.

    This is a read/render projection, not a second database.  A generated key
    is not treated as proof that a rider or layout exists: rendering remains
    ``pending_review`` until the source event has the real pack and operating
    parameters.  Optional overrides are for the operator's current draft and
    never get written back to the catalogue.
    """
    wanted = str(event_key or "").strip()
    if not wanted:
        return {"status": "invalid", "error": "event_key es obligatorio"}
    catalog = datos_panel(Path(root))
    found = None
    for productora in catalog["productoras"]:
        for event in productora.get("eventos", []):
            if event.get("event_key") == wanted:
                found = (productora, event)
                break
        if found:
            break
    if not found:
        return {"status": "not_found", "event_key": wanted,
                "error": "event_key no existe en la ficha RD"}

    productora, event = found
    draft = dict(event)
    supplied = overrides if isinstance(overrides, dict) else {}
    for key in ("pack", "preset", "duracion_horas", "asistentes_estimados",
                "voluntarios", "layout_mode"):
        value = supplied.get(key, event.get(key))
        if value is not None and str(value).strip() != "":
            draft[key] = value

    required = ("pack", "duracion_horas", "asistentes_estimados")
    missing = [key for key in required if draft.get(key) in (None, "")]
    links = {
        "flyer": event.get("flyer_link"),
        "venue": event.get("venue_link"),
        "venue_source": event.get("venue_source_link"),
        "rider": event.get("rider_link"),
        "layout": event.get("layout_link"),
        "database": event.get("database_link"),
    }
    result = {
        "status": "pending_review" if missing else "ready",
        "event_key": wanted,
        "productora_slug": productora["slug"],
        "productora": productora["nombre"],
        "event": event,
        "missing": missing,
        "links": links,
        "triangulacion": event.get("triangulacion"),
    }
    if not missing:
        from ..serve.server import api_plano_render
        result["render"] = api_plano_render(draft)
        # The existing engine rendered the two documents for this exact
        # event.  Mark them generated in this response only; the catalogue is
        # not mutated and no fake file reference is persisted.
        for asset in ("rider", "layout"):
            link = result["links"].get(asset)
            if isinstance(link, dict) and link.get("status") == "pending_review":
                result["links"][asset] = {
                    **link,
                    "status": "generated",
                    "generated_from": "flujo.plano",
                }
    return result


def _candidatos_logo(base, slug: str, ref: str = "") -> list:
    """Archivos donde puede estar el logo de `slug`, en orden de preferencia.

    El nombre del archivo NO siempre es el slug: en disco conviven
    `grid_system.svg` (slug `gridsystem`) y `club_freedom.svg` (slug
    `freedom`). El resumen de la base ya resolvia asi, pero este endpoint
    buscaba solo por slug: contaba el logo como existente y despues no podia
    servirlo, o sea que el panel decia "logo vectorial" sobre un recuadro
    vacio.
    """
    norm = slug.replace("_", "").replace("-", "").lower()
    candidatos = [base / "vector" / f"{slug}.svg"]
    if ref:
        candidatos.append(base / "vector" / f"{ref}.svg")
    vector = base / "vector"
    if vector.is_dir():
        candidatos += [p for p in sorted(vector.glob("*.svg"))
                       if p.stem.replace("_", "").replace("-", "").lower() == norm]
    descargas = base / "descargas"
    if descargas.is_dir():
        candidatos += sorted(descargas.glob(f"{slug}.*"))
        if ref:
            candidatos += sorted(descargas.glob(f"{ref}.*"))
        candidatos += [p for p in sorted(descargas.glob("*"))
                       if p.stem.replace("_", "").replace("-", "").lower() == norm]
    return candidatos

# ── Symbols the events manager adds from the app ──────────────────
_SIMBOLO_MAX_BYTES = 512 * 1024


def datos_panel(root) -> dict:
    """Base de datos RD (productoras + venues) para el panel del hub.

    Fuente de verdad: `data/productoras/*.json` + `knowledge/venues/*.yaml`
    (no `data/rd.db`, que es una proyeccion regenerable y gitignored).

    REGLA DE PRIVACIDAD (2026-07-25, pedido del area de eventos RD): este
    endpoint arma cada registro campo por campo con una ALLOWLIST explicita.
    Nunca hace `**dict` del json de origen. Si manana alguien agrega un campo
    de contacto al json, NO se filtra solo: hay que agregarlo aca a proposito.
    Campos deliberadamente excluidos: `instagram` y cualquier dato de
    contacto. Ver tambien PlanoTool.tsx (el rider no lleva bloque de
    contactos).
    """
    prods: list[dict] = []
    pdir = root / "data" / "productoras"
    logos_dir = root / "knowledge" / "logos"
    if pdir.is_dir():
        for f in sorted(pdir.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            slug = f.stem
            # Estado del logo: el json referencia el id; el archivo real vive
            # en knowledge/logos/. Se reporta lo que existe en disco, no lo
            # que el json dice que deberia existir.
            logos = d.get("logos") or []
            estado_logo = "sin_ficha"
            ref_yaml = ""
            if logos and isinstance(logos[0], dict):
                estado_logo = str(logos[0].get("estado") or "sin_estado")
                ref_yaml = str(logos[0].get("knowledge") or "")
            # El nombre del archivo de logo NO siempre es el slug: en disco
            # conviven `grid_system.svg` (slug `gridsystem`) y
            # `club_freedom.svg` (slug `freedom`). Resolver solo por slug
            # reportaba "sin vector" sobre logos que si existian, y por eso
            # el estado de la DB se veia peor de lo que era.
            # Orden: 1) el yaml que referencia el propio json, 2) el slug,
            # 3) comparacion normalizada (sin guiones ni guiones bajos).
            cand: list[str] = []
            if ref_yaml.endswith(".yaml"):
                cand.append(Path(ref_yaml).stem)
            cand.append(slug)
            tiene_vector = any((logos_dir / "vector" / f"{c}.svg").exists() for c in cand)
            if not tiene_vector and (logos_dir / "vector").is_dir():
                norm = slug.replace("_", "").replace("-", "").lower()
                tiene_vector = any(
                    v.stem.replace("_", "").replace("-", "").lower() == norm
                    for v in (logos_dir / "vector").glob("*.svg")
                )
            venues_raw = d.get("venues") or []
            venues = [
                {
                    "nombre": str(v.get("nombre") or ""),
                    "venue_id": str(v.get("venue_id") or "") or None,
                    "estado": str(v.get("estado") or ""),
                    "preferido": bool(v.get("preferido")),
                }
                for v in venues_raw
                if isinstance(v, dict)
            ]
            # Eventos normalizados: fecha a ISO y lineup como campo propio.
            # Sin esto la triangulacion (fecha + headliner -> productora) no
            # tiene dos campos que cruzar.
            eventos_norm: list[dict] = []
            try:
                from ..rd.database import _event_source_gate
                from ..rd.eventos import normalizar_productora
                norm, _avisos = normalizar_productora(d)
                for ev in (norm.get("eventos") or []):
                    if isinstance(ev, dict):
                        fuentes_primarias, sin_fuente_primaria = _event_source_gate(
                            ev.get("fuente")
                        )
                        eventos_norm.append({
                            "nombre": str(ev.get("nombre") or ""),
                            "fecha": str(ev.get("fecha") or ""),
                            "fecha_iso": ev.get("fecha_iso"),
                            "fecha_confianza": str(ev.get("fecha_confianza") or ""),
                            "venue": str(ev.get("venue") or ""),
                            "estado": str(ev.get("estado") or ""),
                            "fuente": str(ev.get("fuente") or ""),
                            "fuentes_primarias": json.loads(fuentes_primarias),
                            "sin_fuente_primaria": bool(sin_fuente_primaria),
                            "lineup": [str(x) for x in (ev.get("lineup") or [])],
                            "co_organiza": [str(x) for x in (ev.get("co_organiza") or [])],
                        })
                        if ev.get("rider_ref"):
                            eventos_norm[-1]["rider_ref"] = str(ev["rider_ref"])
                        if ev.get("layout_ref"):
                            eventos_norm[-1]["layout_ref"] = str(ev["layout_ref"])
                        if ev.get("flyer_ref"):
                            eventos_norm[-1]["flyer_ref"] = str(ev["flyer_ref"])
                        for key in ("pack", "preset", "duracion_horas",
                                    "asistentes_estimados", "voluntarios",
                                    "layout_mode"):
                            if ev.get(key) not in (None, ""):
                                eventos_norm[-1][key] = ev[key]
            except Exception:
                eventos_norm = []

            prods.append({
                "slug": slug,
                "nombre": str(d.get("name") or slug),
                # Declarado en la ficha: false = no pertenece al corpus RD.
                "rd_scope": d.get("rd_scope"),
                "tipo": d.get("tipo"),
                "aliases": [str(a) for a in (d.get("aliases") or [])],
                "tipos": [str(t) for t in (d.get("tipos_fecha") or [])],
                "venues": venues,
                # `archivo` dice si hay algo que servir. El panel pedia el
                # logo de las 20 productoras aunque 14 no tienen ninguno, y
                # eso dejaba 18 errores 404 en la consola del navegador:
                # ruido que se lee como si la app estuviera fallando.
                "logo": {
                    "estado": estado_logo,
                    "vector": tiene_vector,
                    "archivo": any(
                        c.is_file() for c in _candidatos_logo(
                            logos_dir, slug,
                            Path(ref_yaml).stem if ref_yaml.endswith(".yaml") else "")
                    ),
                },
                "confirmada": bool(str(d.get("confirmed") or "").strip()),
                "confirmacion": str(d.get("confirmed") or ""),
                "fuente": str(d.get("fuente_datos") or ""),
                "eventos": eventos_norm,
            })

    venues_cat: list[dict] = []
    vdir = root / "knowledge" / "venues"
    if vdir.is_dir():
        for f in sorted(vdir.glob("*.yaml")):
            try:
                raw = f.read_text(encoding="utf-8")
            except Exception:
                continue
            # Parseo minimo de las claves planas que interesan: evita
            # depender de PyYAML en el proceso del servidor.
            info = {"id": f.stem, "nombre": f.stem, "tipo": "", "escala": "", "capacidad": ""}
            for line in raw.splitlines():
                if line.startswith("name:"):
                    info["nombre"] = line.split(":", 1)[1].strip()
                elif line.startswith("type:"):
                    info["tipo"] = line.split(":", 1)[1].strip()
                elif line.startswith("scale_default:"):
                    info["escala"] = line.split(":", 1)[1].strip()
                elif line.startswith("capacity_bucket:"):
                    info["capacidad"] = line.split(":", 1)[1].strip()
            venues_cat.append(info)

    # Vinculos deterministicos para la ficha: el evento se puede automatizar
    # sin convertir una coincidencia de nombre en una afirmacion. Solo el
    # venue normalizado exacto se marca como seguro; rider/layout requieren un
    # ref explicito en la fuente y, mientras tanto, conservan una clave estable
    # para que el operador pueda completar el enlace sin crear otro evento.
    for productora in prods:
        for evento in productora["eventos"]:
            _wire_event_links(productora["slug"], evento, venues_cat, productora["venues"])
            # The JSON catalog is authoritative; this is a read-only
            # consistency check against its existing SQLite projection.
            db_link = _database_event_link(root, productora["slug"], evento)
            db_venue_link = _database_venue_link(root, productora["slug"], evento)
            db_link["venue"] = db_venue_link
            evento["database_link"] = db_link
            evento["triangulacion"] = {
                "status": db_link["status"],
                "event_key": evento["event_key"],
                "catalogo": {"status": "exact", "source": "data/productoras"},
                "base_datos": db_link,
                "venue_fuente": evento.get("venue_source_link"),
                "venue_db": db_venue_link,
                "venue_canonico": evento.get("venue_link"),
                # This is identity triangulation only. Plano/Rider assets
                # remain separate links and are not fabricated here.
                "identidad_completa": (
                    db_link["status"] == "exact"
                    and db_venue_link["status"] == "exact"
                ),
            }

    # Estado de la triangulacion: cuantos eventos se pueden cruzar de verdad
    # (necesitan fecha ISO Y lineup). Es el numero que dice si esa tarea
    # puede avanzar o si primero hay que completar datos.
    todos_ev = [e for p in prods for e in p["eventos"]]
    triangulables = [e for e in todos_ev if e.get("fecha_iso") and e.get("lineup")]
    sin_fuente_primaria = [e for e in todos_ev if e.get("sin_fuente_primaria")]
    db_exactos = [e for e in todos_ev if e.get("database_link", {}).get("status") == "exact"]
    venue_db_exactos = [
        e for e in todos_ev
        if e.get("triangulacion", {}).get("venue_db", {}).get("status") == "exact"
    ]
    venue_canonicos = [
        e for e in todos_ev
        if e.get("triangulacion", {}).get("venue_canonico", {}).get("status") == "exact"
    ]
    identidad_completa = [
        e for e in todos_ev if e.get("triangulacion", {}).get("identidad_completa")
    ]

    # Este directorio cataloga tambien artistas y clientes VJ, no solo
    # productoras de RD. `database.py` ya tenia la regla —`_es_productora_rd`,
    # que excluye `rd_scope: false` y los `tipo` de artista— pero el panel leia
    # los JSON por su cuenta y no la aplicaba: por eso un cliente de VJ
    # aparecia en la pestana de RD aunque nunca estuviera en la tabla. Se usa
    # la MISMA funcion, para que la vista y la base no puedan divergir.
    from .database import _es_productora_rd

    fuera_de_rd = [p for p in prods if not _es_productora_rd(p)]
    prods = [p for p in prods if _es_productora_rd(p)]

    evidencia_periodos = _evidencia_periodos(root)
    return {
        "productoras": prods,
        "fuera_de_rd": len(fuera_de_rd),
        "venues": venues_cat,
        "evidencia_periodos": evidencia_periodos,
        # Kept for older standalone bundles and consumers.
        "evidencia_2025": evidencia_periodos.get("2025", []),
        "colorimetria": _colorimetria_periodos(root),
        # Las observaciones atomicas: la interfaz agrega desde aca, asi
        # que cada cifra del grafico se puede abrir hasta la celda.
        "ensayos": _ensayos_fuente(root),
        "resumen": {
            "productoras": len(prods),
            "con_vector": sum(1 for p in prods if p["logo"]["vector"]),
            "confirmadas": sum(1 for p in prods if p["confirmada"]),
            "venues": len(venues_cat),
            "eventos": len(todos_ev),
            "eventos_triangulables": len(triangulables),
            "eventos_sin_fuente_primaria": len(sin_fuente_primaria),
            "eventos_sin_fecha_iso": sum(1 for e in todos_ev if not e.get("fecha_iso")),
            "eventos_sin_lineup": sum(1 for e in todos_ev if not e.get("lineup")),
            "eventos_db_exactos": len(db_exactos),
            "eventos_db_pendientes": len(todos_ev) - len(db_exactos),
            "eventos_venue_db_exactos": len(venue_db_exactos),
            "eventos_venue_canonicos": len(venue_canonicos),
            "eventos_triangulacion_completa": len(identidad_completa),
        },
        "excluido_a_proposito": ["instagram", "contactos"],
        "connected": True,
    }


# Etiqueta legible de la sustancia declarada. La clave sigue siendo el id
# canonico que la fuente ya trae en `substance_normalized_candidate`.
_ETIQUETA_SUSTANCIA = {
    "mdma": "MDMA", "ketamine": "Ketamina", "cocaine": "Cocaína",
    "two_c_b": "2C-B", "tusi": "Tusi", "ghb_gbl": "GHB / GBL",
    "mephedrone": "Mefedrona", "cannabis": "Cannabis",
    "ketamine_plus_unspecified_m": "Ketamina + otro",
    "unknown": "declarada desconocida", "sin_declarar": "sin declarar",
    "sin_mapear": "sin mapear",
}
_ETIQUETA_REACTIVO = {
    "sin_reactivo": "sin reactivo", "cbd_thc": "CBD/THC",
    "fentanyl_strip": "tira fentanilo",
}
# Filas que son dato. `repeated_header` son encabezados de la planilla original
# que quedaron preservados como filas: contarlos inflaria el total de muestras.
_FILAS_DATO = ("data", "data_with_unresolved_substance")

# La `familia` del catalogo de reactivos, mapeada al id canonico de sustancia
# declarada. Es una tabla chica y cerrada: lo que no esta aca simplemente no
# genera expectativa, y eso se dice en la salida en vez de inventarla.
_FAMILIA_A_SUSTANCIA = {
    "mdma": "mdma",
    "mdma / mda": "mdma",
    "mdma (amina 2a)": "mdma",
    "cocaina": "cocaine",
    "cocaina cortada (levamisol / lidocaina)": "cocaine",
    "ketamina": "ketamine",
    "2c-b": "two_c_b",
    "2c-x": "two_c_b",
}
# Familias que describen un corte o una alerta, no la sustancia declarada.
_FAMILIA_ALERTA = frozenset({"cocaina cortada (levamisol / lidocaina)"})


def _clave_nombre(value: object) -> str:
    """Nombre a clave comparable: minuscula, sin tildes, solo alfanumerico."""
    texto = unicodedata.normalize("NFKD", str(value or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", texto)


def _distancia(a: str, b: str) -> int:
    """Levenshtein acotada; solo se usa para decidir si dos tokens cortos son
    la misma palabra escrita distinto (`tecnoyouth` vs `technoyouth`)."""
    if abs(len(a) - len(b)) > 2:
        return 99
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1,
                              previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def _productora_candidata(nombre_hoja: str, claves: dict,
                          abreviaturas: dict | None = None) -> dict:
    """Propone a que productora pertenece una hoja, por su nombre.

    Es una PROPUESTA, no un enlace. La fuente marca estas hojas como
    `pending_human_link` y esta funcion no cambia eso: solo evita que la
    interfaz muestre catorce filas sueltas llamadas «Dame ...» sin decir que
    son la misma productora. Nada de esto se escribe en la base.

    `exacto`: el alias aparece literal dentro del nombre de la hoja.
    `aproximado`: un token del nombre esta a una o dos letras de un alias, que
    es lo que pasa con `tecno youth` frente a `technoyouth`. Se marca distinto
    a proposito para que una persona lo confirme.
    """
    clave_hoja = _clave_nombre(nombre_hoja)
    if not clave_hoja:
        return {"slug": None, "match": "sin_identificar"}
    for slug, alias in claves.items():
        if any(a in clave_hoja for a in alias):
            return {"slug": slug, "match": "exacto"}
    todos = [_clave_nombre(t) for t in re.split(r"[\s()\-_]+", nombre_hoja or "")]
    tokens = [t for t in todos if len(t) >= 4 and not t.isdigit()]
    for slug, alias in claves.items():
        for a in alias:
            for token in tokens:
                if _distancia(token, a) <= 2:
                    return {"slug": slug, "match": "aproximado"}
            # `tecno youth` son dos tokens que juntos forman el alias.
            for i in range(len(tokens) - 1):
                if _distancia(tokens[i] + tokens[i + 1], a) <= 2:
                    return {"slug": slug, "match": "aproximado"}
    # Ultimo recurso: la abreviatura que la ficha declara, y SOLO como palabra
    # entera y exacta. `TY` dentro de «hotties» o «party» no dice nada; `TY`
    # como token suelto es lo que la ficha llama su alias. Estado propio para
    # que una persona lo confirme: la sigla puede ser de mas de una productora.
    sueltos = {t for t in todos if t and not t.isdigit()}
    for slug, cortas in (abreviaturas or {}).items():
        if sueltos & cortas:
            return {"slug": slug, "match": "abreviatura"}
    return {"slug": None, "match": "sin_identificar"}


def _etiquetas_de_muestra(conn) -> frozenset:
    """Nombres de troquel sacados de la columna de formato del propio corpus.

    Los tokens que NO son un color, ni un matiz, ni una palabra de
    presentacion son el nombre del sello (`cupra`, `tesla`, `gucci`). Si uno
    de esos aparece en la columna de RESULTADO, la celda describe la pastilla
    y su color no es una reaccion. No se pueden enumerar en el codigo: cada
    temporada trae troqueles nuevos, y la lista la conoce el dato.
    """
    salida: set[str] = set()
    try:
        filas = conn.execute(
            "SELECT DISTINCT format_raw FROM testeo_filas_fuente "
            "WHERE format_raw IS NOT NULL AND TRIM(format_raw) <> ''")
    except sqlite3.Error:
        return frozenset()
    for fila in filas:
        for token in re.split(r"[^\wÁÉÍÓÚÑáéíóúñ]+", str(fila[0])):
            clave = _clave_nombre(token)
            if len(clave) < 4 or clave.isdigit():
                continue
            if normalizar_color(clave)["status"] == "canonico":
                continue
            # Un color mal escrito no es un troquel: `amarillos`, `blancos` y
            # `azil` estan a una letra del vocabulario canonico.
            if any(_distancia(clave, c.lower()) <= 2 for c in COLORES):
                continue
            salida.add(clave)
    return frozenset(salida)


def _claves_productoras(root) -> tuple[dict, dict]:
    """Alias por productora, leidos de las fichas. Nunca inventados."""
    claves_prod: dict[str, set] = {}
    abreviaturas_prod: dict[str, set] = {}
    carpeta = Path(root) / "data" / "productoras"
    if not carpeta.is_dir():
        return claves_prod, abreviaturas_prod
    for ficha in sorted(carpeta.glob("*.json")):
        try:
            datos = json.loads(ficha.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if datos.get("rd_scope") is False:
            continue
        candidatos = {_clave_nombre(ficha.stem), _clave_nombre(datos.get("name"))}
        candidatos |= {_clave_nombre(a) for a in (datos.get("aliases") or [])}
        claves = {c for c in candidatos if len(c) >= 4}
        cortas = {c for c in candidatos if 2 <= len(c) < 4}
        if claves or cortas:
            claves_prod[ficha.stem] = claves
            if cortas:
                abreviaturas_prod[ficha.stem] = cortas
    return claves_prod, abreviaturas_prod

def _ensayos_fuente(root) -> dict:
    """Las observaciones ATOMICAS, para que el grafico las agregue el mismo.

    Un ensayo es: REACTIVO X dio COLOR C sobre una muestra que la persona
    declaro como S. Nada mas. No dice que sustancia hay, no mide pureza ni
    dosis, y no compara lo observado contra lo esperado: ese veredicto es de
    la persona a cargo de la mesa, no del sistema.

    Por que va crudo y no agregado: un total precocinado obliga a creerle al
    backend. Aca viaja una fila por observacion, con el texto original de la
    celda y su coordenada en la planilla, y la interfaz calcula cada cifra a
    partir de eso. Cualquier barra del grafico se puede abrir y mostrar las
    celdas que la formaron -- trazabilidad por construccion, no por promesa.

    La normalizacion que se aplica es SOLO ortografica (`ensayos.py`,
    `colorimetria.py`) y viaja al lado del crudo, nunca en su lugar.
    """
    from .ensayos import normalizar_reactivo, normalizar_sustancia

    db_path = rd_db_path(root)
    if not db_path.is_file():
        return {}
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row

        etiquetas_muestra = _etiquetas_de_muestra(conn)

        claves_prod, abreviaturas_prod = _claves_productoras(root)
        jornadas: list[dict] = []
        indice_jornada: dict[str, int] = {}
        for ev in conn.execute(
            "SELECT event_id, source_sheet_name, event_label_candidate, "
            "source_period_label, date_iso_candidate, date_status, date_confidence "
            "FROM testeo_eventos_fuente "
            "ORDER BY source_period_label, COALESCE(date_iso_candidate, ''), "
            "source_sheet_index"
        ):
            nombre = ev["event_label_candidate"] or ev["source_sheet_name"]
            cand = _productora_candidata(nombre, claves_prod, abreviaturas_prod)
            indice_jornada[ev["event_id"]] = len(jornadas)
            jornadas.append({
                "hoja": ev["source_sheet_name"],
                "nombre": nombre,
                "periodo": ev["source_period_label"] or "sin_periodo",
                "fecha": ev["date_iso_candidate"],
                "estado_fecha": ev["date_status"],
                "confianza_fecha": ev["date_confidence"] or "none",
                "productora": cand["slug"],
                "match_productora": cand["match"],
            })

        # Diccionarios de texto crudo: cada celda distinta se guarda UNA vez y
        # las observaciones la referencian por indice. Sin esto, 8.436 filas
        # repetirian «Negro» miles de veces.
        crudos: dict[str, list] = {"sustancia": [], "reactivo": [], "resultado": []}
        indices: dict[str, dict] = {"sustancia": {}, "reactivo": {}, "resultado": {}}
        mapa: dict[str, list] = {"sustancia": [], "reactivo": [], "resultado": []}
        estado: dict[str, list] = {"sustancia": [], "reactivo": [], "resultado": []}

        def _ref(campo: str, valor, normalizador) -> int:
            texto = "" if valor is None else str(valor)
            if texto in indices[campo]:
                return indices[campo][texto]
            lectura = normalizador(texto)
            idx = len(crudos[campo])
            indices[campo][texto] = idx
            crudos[campo].append(texto)
            if campo == "resultado":
                mapa[campo].append(lectura.get("clave") or lectura.get("outcome"))
            else:
                mapa[campo].append(lectura.get("canonico"))
            estado[campo].append(lectura.get("status"))
            return idx

        PROCEDENCIA = ("first_occurrence", "repeat_within_sheet",
                       "copied_from_other_sheet")
        obs: list[list] = []
        for row in conn.execute(
            "SELECT o.event_id, o.source_row, o.substance_raw, o.reagent_raw, "
            "o.result_raw, f.row_duplicate_status, f.format_raw "
            "FROM testeo_observaciones_fuente o "
            "JOIN testeo_filas_fuente f USING(test_id) "
            "WHERE f.row_status <> 'repeated_header' "
            "ORDER BY o.event_id, o.source_row, o.observation_ordinal"
        ):
            j = indice_jornada.get(row["event_id"])
            if j is None:
                continue
            proc = row["row_duplicate_status"] or "first_occurrence"
            obs.append([
                j,
                int(row["source_row"] or 0),
                _ref("sustancia", row["substance_raw"], normalizar_sustancia),
                _ref("reactivo", row["reagent_raw"], normalizar_reactivo),
                _ref("resultado", row["result_raw"],
                     lambda v: normalizar_color(v, etiquetas_muestra)),
                PROCEDENCIA.index(proc) if proc in PROCEDENCIA else 0,
            ])
        conn.close()
    except sqlite3.Error:
        return {}

    return {
        "politica": ("un ensayo es: el reactivo X dio el color C. No identifica "
                     "sustancia, no mide pureza ni dosis, y no emite veredicto: "
                     "eso lo hace la persona a cargo de la mesa."),
        "jornadas": jornadas,
        "crudo": crudos,
        "mapa": mapa,
        "estado": estado,
        "procedencia": list(PROCEDENCIA),
        "obs": obs,
        "hex": dict(COLOR_HEX),
    }


def _expectativa_catalogo(conn) -> dict:
    """Que color espera el catalogo de RD para cada sustancia x reactivo.

    Se lee de la tabla `reactivos`, que es la fuente curada de la ONG, y se
    traduce con el mismo normalizador que lee las observaciones: asi la
    expectativa y lo observado hablan el mismo vocabulario. Una familia que no
    esta en el mapa no genera expectativa, y eso se reporta en vez de suponerla.
    """
    esperado: dict = {}
    for row in conn.execute("SELECT reactivo, familia, reaccion, hex FROM reactivos"):
        familia = (row["familia"] or "").strip().lower()
        sustancia = _FAMILIA_A_SUSTANCIA.get(familia)
        if not sustancia:
            continue
        reactivo = (row["reactivo"] or "").strip().lower()
        # `Simon` en el catalogo, `simons` en las observaciones importadas.
        if reactivo == "simon":
            reactivo = "simons"
        lectura = normalizar_color(row["reaccion"])
        colores = lectura.get("colores") or []
        if lectura["outcome"] == "SIN_REACCION":
            colores = ["SIN_REACCION"]
        if not colores:
            continue
        entrada = esperado.setdefault(sustancia, {}).setdefault(
            reactivo, {"colores": [], "notas": [], "alerta": []})
        for color in colores:
            if color not in entrada["colores"]:
                entrada["colores"].append(color)
        nota = {"familia": row["familia"], "reaccion": row["reaccion"], "hex": row["hex"]}
        entrada["notas"].append(nota)
        if familia in _FAMILIA_ALERTA:
            entrada["alerta"].append(nota)
    return esperado


def _concordancia(matriz: dict, esperado: dict) -> list[dict]:
    """Donde el color observado no coincide con lo que el catalogo espera.

    NO dice que la sustancia sea otra. Dice que la observacion no calza con la
    reaccion esperada de lo declarado, que es un motivo para mirar la muestra,
    no una conclusion sobre su contenido. Un resultado colorimetrico sigue
    siendo presuntivo aunque coincida.
    """
    filas: list[dict] = []
    for sustancia, reactivos in matriz.items():
        for reactivo, colores in reactivos.items():
            expect = esperado.get(sustancia, {}).get(reactivo)
            if not expect:
                continue
            ok = set(expect["colores"])
            total = sum(colores.values())
            coincide = sin_reaccion = discrepa = 0
            discrepancias: Counter = Counter()
            for clave, n in colores.items():
                if clave == "NO_INTERPRETABLE":
                    continue
                partes = set(clave.split("+"))
                if partes & ok:
                    coincide += n
                elif clave == "SIN_REACCION":
                    sin_reaccion += n
                    discrepancias[clave] += n
                else:
                    discrepa += n
                    discrepancias[clave] += n
            evaluadas = coincide + sin_reaccion + discrepa
            if evaluadas < 10:
                continue
            filas.append({
                "sustancia": sustancia,
                "reactivo": reactivo,
                "total": total,
                "evaluadas": evaluadas,
                "coincide": coincide,
                "sin_reaccion": sin_reaccion,
                "discrepa": discrepa,
                "esperado": expect["colores"],
                "reaccion_texto": "; ".join(n["reaccion"] for n in expect["notas"]),
                "alerta": [n["reaccion"] for n in expect["alerta"]],
                "top_discrepancias": dict(discrepancias.most_common(4)),
            })
    filas.sort(key=lambda f: -(f["sin_reaccion"] + f["discrepa"]))
    return filas


def _colorimetria_periodos(root) -> dict:
    """Matriz multi-periodo de sustancia x reactivo x color observado.

    Lo que esta proyeccion agrega sobre la evidencia historica: el COLOR. La fuente
    guarda el resultado unicamente en `result_raw`, en crudo y con 136
    variantes de escritura para unos pocos resultados reales;
    `result_normalized_candidate` viene NULL en la gran mayoria de las filas.
    Sin normalizar eso no hay forma de graficar nada, y por eso la pestana
    mostraba la evidencia como texto suelto.

    Reglas que se respetan aca, no por estetica sino por el dominio:

    - Un resultado compuesto (`negro y naranjo`) son DOS colores y se conserva
      como dos. Colapsarlo al primero seria inventar una observacion.
    - El orden en que se escribio no cambia el agrupamiento: `negro y naranjo`
      y `naranjo y negro` caen en la misma celda.
    - Lo que no se pudo leer no se descarta: queda en `pendientes` con su valor
      crudo, para que una persona lo resuelva.
    - Un nombre de sustancia escrito en la columna de color se marca aparte:
      es una identificacion presuntiva puesta donde va una observacion, y
      contradice la politica de la propia fuente.
    - El color de la MUESTRA no es el color del TEST. `Cupra morada` en la
      columna de resultado es la pastilla, no un reactivo que viro a morado.
      Las dos columnas contienen nombres de color y se confunden de vista, asi
      que el vocabulario de troqueles se lee de `format_raw` -- del propio
      corpus, porque cada temporada trae troqueles nuevos -- y esas celdas
      quedan fuera de la matriz, no adentro.

    Un color observado no identifica una sustancia, no mide pureza y no mide
    dosis.
    """
    db_path = rd_db_path(root)
    if not db_path.is_file():
        return {}
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        # El periodo de cada evento: sin esto la matriz sumaba todos los anos en
        # la misma celda y el panel mostraba 2.762 muestras como si fueran de
        # un ano. Dos corpus distintos no se promedian en silencio.
        # Vocabulario de troquel, sacado de la columna de formato: los tokens
        # que NO son un color ni un matiz ni una palabra de presentacion son
        # el nombre del sello (`cupra`, `tesla`, `gucci`). Si uno de esos
        # aparece en la columna de resultado, la celda describe la muestra.
        etiquetas_muestra: set[str] = set()
        for fila in conn.execute(
                "SELECT DISTINCT format_raw FROM testeo_filas_fuente "
                "WHERE format_raw IS NOT NULL AND TRIM(format_raw) <> ''"):
            for token in re.split(r"[^\wÁÉÍÓÚÑáéíóúñ]+", str(fila[0])):
                clave = _clave_nombre(token)
                if len(clave) < 4 or clave.isdigit():
                    continue
                if normalizar_color(clave)["status"] == "canonico":
                    continue
                # Un color mal escrito no es un troquel: `amarillos`, `blancos`
                # y `azil` estan a una letra del vocabulario canonico. Sin este
                # filtro entrarian a la lista de sellos y una lectura legitima
                # se marcaria como descripcion de la muestra.
                if any(_distancia(clave, c.lower()) <= 2 for c in COLORES):
                    continue
                etiquetas_muestra.add(clave)
        etiquetas_muestra = frozenset(etiquetas_muestra)

        periodo_de: dict[str, str] = {
            r["event_id"]: (r["source_period_label"] or "sin_periodo")
            for r in conn.execute(
                "SELECT event_id, source_period_label FROM testeo_eventos_fuente")
        }

        filas: dict[str, dict] = {}
        for row in conn.execute(
            "SELECT test_id, event_id, substance_normalized_candidate, substance_raw, "
            "row_status, row_duplicate_status "
            "FROM testeo_filas_fuente"
        ):
            if row["row_status"] not in _FILAS_DATO:
                continue
            clave = (row["substance_normalized_candidate"] or "").strip()
            if not clave:
                clave = "sin_declarar" if not (row["substance_raw"] or "").strip() else "sin_mapear"
            filas[row["test_id"]] = {"sustancia": clave, "cruda": row["substance_raw"],
                                     "evento": row["event_id"],
                                     "procedencia": row["row_duplicate_status"] or "sin_clasificar",
                                     "periodo": periodo_de.get(row["event_id"], "sin_periodo")}

        matriz: dict[str, dict[str, Counter]] = {}
        por_color: Counter = Counter()
        por_reactivo: Counter = Counter()
        por_sustancia: Counter = Counter()
        variantes: dict[str, Counter] = {}
        estados: Counter = Counter()
        pendientes: list[dict] = []
        # Colores observados por evento: lo que alimenta la tira de cada hoja.
        por_evento: dict[str, Counter] = {}
        # Y por periodo, para no sumar dos anos en la misma cifra.
        por_periodo: dict[str, Counter] = {}
        muestras_periodo: dict[str, set] = __import__("collections").defaultdict(set)
        jornadas_periodo: dict[str, set] = __import__("collections").defaultdict(set)
        # Conjuntos de test_id, no contadores de observacion: una muestra deja
        # varias observaciones (una por reactivo), asi que contar aca por
        # observacion daba 2.131 filas "propias" en 2024 al lado de 920
        # muestras del mismo periodo -- dos unidades distintas bajo nombres
        # hermanos, que es como se lee una contradiccion.
        procedencia_periodo: dict[str, dict] = __import__("collections").defaultdict(
            lambda: __import__("collections").defaultdict(set))

        for row in conn.execute(
            "SELECT test_id, reagent_normalized_candidate, reagent_raw, result_raw "
            "FROM testeo_observaciones_fuente "
            "WHERE observation_status='source_observation_preserved'"
        ):
            fila = filas.get(row["test_id"])
            if fila is None:
                continue
            lectura = normalizar_color(row["result_raw"], etiquetas_muestra)
            estados[lectura["status"]] += 1
            if lectura["revisar"] and lectura["status"] != "vacio":
                pendientes.append({
                    "crudo": lectura["raw"],
                    "estado": lectura["status"],
                    "sin_reconocer": lectura.get("sin_reconocer") or [],
                    "identidades": lectura.get("identidades") or [],
                })
            if lectura["status"] in ("encabezado_o_reactivo", "vacio",
                                     "descripcion_de_muestra"):
                continue
            reactivo = (row["reagent_normalized_candidate"]
                        or row["reagent_raw"] or "sin_reactivo")
            clave_color = lectura.get("clave") or lectura["outcome"]
            sustancia = fila["sustancia"]
            procedencia_periodo[fila["periodo"]][fila["procedencia"]].add(row["test_id"])
            matriz.setdefault(sustancia, {}).setdefault(reactivo, Counter())[clave_color] += 1
            por_color[clave_color] += 1
            por_reactivo[reactivo] += 1
            por_sustancia[sustancia] += 1
            variantes.setdefault(sustancia, Counter())[fila["cruda"] or ""] += 1
            por_periodo.setdefault(fila["periodo"], Counter())[clave_color] += 1
            muestras_periodo[fila["periodo"]].add(row["test_id"])
            if fila["evento"]:
                jornadas_periodo[fila["periodo"]].add(fila["evento"])
            if fila["evento"]:
                por_evento.setdefault(fila["evento"], Counter())[clave_color] += 1

        paleta: dict[str, list] = {}
        for row in conn.execute("SELECT reactivo, familia, reaccion, hex FROM reactivos"):
            paleta.setdefault(row["reactivo"].lower(), []).append({
                "familia": row["familia"], "reaccion": row["reaccion"], "hex": row["hex"],
            })
        esperado = _expectativa_catalogo(conn)
        conn.close()
    except sqlite3.Error:
        return {}

    if not matriz:
        return {}
    matriz_plana = {s: {r: dict(c) for r, c in reactivos.items()}
                    for s, reactivos in matriz.items()}
    return {
        "matriz": matriz_plana,
        "esperado": esperado,
        "concordancia": _concordancia(matriz_plana, esperado),
        "por_evento": {e: dict(c.most_common()) for e, c in por_evento.items()},
        "por_periodo": {p: dict(c.most_common()) for p, c in por_periodo.items()},
        "muestras_por_periodo": {p: len(v) for p, v in muestras_periodo.items()},
        "jornadas_por_periodo": {p: len(v) for p, v in jornadas_periodo.items()},
        "procedencia_por_periodo": {p: {k: len(v) for k, v in c.items()}
                                    for p, c in procedencia_periodo.items()},
        "por_color": dict(por_color.most_common()),
        "por_reactivo": dict(por_reactivo.most_common()),
        "por_sustancia": dict(por_sustancia.most_common()),
        "variantes": {s: dict(v.most_common()) for s, v in variantes.items()},
        "estados": dict(estados),
        "pendientes": pendientes[:40],
        "pendientes_total": len(pendientes),
        "muestras": len(filas),
        "observaciones": int(sum(por_color.values())),
        "etiquetas": _ETIQUETA_SUSTANCIA,
        "etiquetas_reactivo": _ETIQUETA_REACTIVO,
        "hex": COLOR_HEX,
        "paleta_rd": paleta,
        "limitacion": ("un color observado no identifica una sustancia, "
                       "no mide pureza ni dosis"),
    }


def _evidencia_periodos(root) -> dict[str, list[dict]]:
    """Read-only projection of the testing evidence, split by source period.

    This is deliberately separate from ``productora_eventos``: the imported
    workbook still has pending event/producer/venue links and the sheet name
    is not enough evidence to invent one.  The web panel may therefore show
    the historical source event and its exact ``event_id`` without attaching
    it to the wrong producer.  Values are source wording only; no colour is
    interpreted as identity, purity, dose or safety.
    """
    db_path = rd_db_path(root)
    if not db_path.is_file():
        return {}

    # Alias por productora, para proponer a cual pertenece cada hoja. Se leen
    # de las fichas, no se inventan, y se descartan los tokens de menos de 4
    # letras porque generarian falsos positivos dentro de cualquier nombre.
    claves_prod: dict[str, set] = {}
    abreviaturas_prod: dict[str, set] = {}
    carpeta = Path(root) / "data" / "productoras"
    if carpeta.is_dir():
        for ficha in sorted(carpeta.glob("*.json")):
            try:
                datos = json.loads(ficha.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if datos.get("rd_scope") is False:
                continue
            candidatos = {_clave_nombre(ficha.stem), _clave_nombre(datos.get("name"))}
            candidatos |= {_clave_nombre(a) for a in (datos.get("aliases") or [])}
            claves = {c for c in candidatos if len(c) >= 4}
            # Una abreviatura declarada en la ficha no se tira: `tycircle.json`
            # dice que `TY` es su alias y el filtro de 4 letras la borraba, asi
            # que `TY 1510` y `Hotties X TY 3110` quedaban sin identificar
            # teniendo la ficha el dato. Se guarda aparte porque solo puede
            # matchear como palabra entera; como subcadena aparece en
            # cualquier nombre.
            cortas = {c for c in candidatos if 2 <= len(c) < 4}
            if claves or cortas:
                claves_prod[ficha.stem] = claves
                if cortas:
                    abreviaturas_prod[ficha.stem] = cortas

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        events = conn.execute(
            "SELECT event_id, source_sheet_index, source_sheet_name, "
            "event_label_candidate, source_period_label, date_iso_candidate, "
            "date_status, duplicate_status, duplicate_group_size, "
            "venue_name_candidate, producer_name_candidate, link_status "
            "FROM testeo_eventos_fuente "
            "ORDER BY source_period_label, COALESCE(date_iso_candidate, ''), "
            "source_sheet_index"
        ).fetchall()
        out: dict[str, list[dict]] = {}
        for event in events:
            rows = conn.execute(
                "SELECT format_raw, result_1_raw, result_2_raw, result_3_raw, "
                "result_4_raw, row_duplicate_status, copied_from_sheet "
                "FROM testeo_filas_fuente "
                "WHERE event_id = ? AND row_status IN "
                "('data', 'data_with_unresolved_substance') ORDER BY source_row",
                (event["event_id"],),
            ).fetchall()
            declared = Counter()
            results = Counter()
            procedencia = Counter()
            origenes = Counter()
            for row in rows:
                label = str(row["format_raw"] or "").strip() or "sin registro"
                declared[label] += 1
                estado_fila = row["row_duplicate_status"] or "sin_clasificar"
                procedencia[estado_fila] += 1
                if row["copied_from_sheet"]:
                    origenes[str(row["copied_from_sheet"])] += 1
                for field in ("result_1_raw", "result_2_raw", "result_3_raw", "result_4_raw"):
                    value = str(row[field] or "").strip()
                    if value:
                        results[value] += 1

            def distribution(counter: Counter) -> list[dict]:
                total = sum(counter.values())
                return [
                    {"valor": value, "conteo": count,
                     "porcentaje": round((count / total) * 100, 1) if total else 0}
                    for value, count in counter.most_common()
                ]

            candidata = _productora_candidata(
                event["event_label_candidate"] or event["source_sheet_name"],
                claves_prod, abreviaturas_prod)
            periodo = event["source_period_label"] or "sin_periodo"
            out.setdefault(periodo, []).append({
                "productora_candidata": candidata["slug"],
                "match_candidata": candidata["match"],
                "event_id": event["event_id"],
                "hoja": event["source_sheet_name"],
                "indice_hoja": event["source_sheet_index"],
                "nombre": event["event_label_candidate"] or event["source_sheet_name"],
                "periodo": event["source_period_label"],
                "fecha_iso": event["date_iso_candidate"],
                "estado_fecha": event["date_status"],
                "estado_duplicado": event["duplicate_status"],
                "tamano_grupo_duplicado": event["duplicate_group_size"],
                "venue_fuente": event["venue_name_candidate"],
                "productora_fuente": event["producer_name_candidate"],
                "estado_enlace": event["link_status"],
                "filas": len(rows),
                "muestra_declarada": {
                    "campo": "format_raw",
                    "total": sum(declared.values()),
                    "distribucion": distribution(declared),
                },
                "resultados_colorimetricos": {
                    "campos": ["result_1_raw", "result_2_raw", "result_3_raw", "result_4_raw"],
                    "total": sum(results.values()),
                    "distribucion": distribution(results),
                },
                "procedencia": {
                    "filas_brutas": len(rows),
                    "primera_aparicion": procedencia.get("first_occurrence", 0),
                    "repetidas_en_hoja": procedencia.get("repeat_within_sheet", 0),
                    "copiadas_de_otra_jornada": procedencia.get("copied_from_other_sheet", 0),
                    "sin_clasificar": procedencia.get("sin_clasificar", 0),
                    "origenes": dict(origenes),
                },
            })
        conn.close()
        return out
    except (OSError, sqlite3.Error):
        return {}


def _evidencia_2025(root) -> list[dict]:
    """Compatibility view for consumers that still request only 2025."""
    return _evidencia_periodos(root).get("2025", [])
