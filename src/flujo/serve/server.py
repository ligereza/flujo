#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flujo.serve.server  -  Servidor local del hub (stdlib, sin dependencias)

Sirve los HTML del hub (context/) y expone los endpoints /api que sacan a los
dashboards del "modo demo". 100% biblioteca estandar de Python (http.server),
para no agregar Flask/FastAPI ni dependencias.

Endpoints:
  GET  /                         -> redirige a /context/flujo_hub.html
  GET  /context/...              -> sirve los HTML/CSS/JS del hub
  GET  /api/health/stats         -> tarjetas de estado del hub (lee jobs/ si existe)
  GET  /api/materials            -> material RD (lee context/data/materials.json o demo)
  GET  /api/rd/topics            -> temas RD separados desde la proyeccion canonica
  GET  /api/rd-db                 -> productoras y venues read-only
  POST /api/plano/render         -> {evento} -> {layout, rider, costos}

Uso:
  py -m flujo serve            # http://127.0.0.1:8777
  py -m flujo serve --port 9000 --open

Reglas: stdlib only, ASCII-only, no toca archivos del usuario, no guarda tokens.
"""

import json
import os
import re
import sys
import argparse
import webbrowser
from pathlib import Path

from flujo.eventos.presets import infer_event_preset, list_event_presets
from flujo.cotizaciones_base import generar_cotizacion_base
from flujo.departments import rd_cultura_relations, rd_crosswalk, rd_summary, rd_topics
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# Global request-body cap (VCD-06). 8 MB: large enough for a photo sent to the
# tracer, small enough that an unbounded body cannot exhaust memory.
MAX_BODY_BYTES = 8 * 1024 * 1024

# raiz del repo = 3 niveles arriba de este archivo (src/flujo/serve/ -> repo)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTEXT_DIR = os.path.join(REPO, "context")

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".woff2": "font/woff2", ".ico": "image/x-icon",
}


# ---------------- logica de negocio de los endpoints ----------------

def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def api_health_stats():
    """Cuenta jobs por estado si existe jobs/, si no devuelve demo."""
    jobs_dir = os.path.join(REPO, "jobs")
    if os.path.isdir(jobs_dir):
        abiertos = en_diseno = por_rev = 0
        for name in os.listdir(jobs_dir):
            estado = os.path.join(jobs_dir, name, "estado.md")
            if not os.path.isfile(estado):
                continue
            try:
                txt = open(estado, encoding="utf-8", errors="replace").read().lower()
            except Exception:
                continue
            abiertos += 1
            if "diseno" in txt or "en-diseno" in txt:
                en_diseno += 1
            if "revis" in txt or "por-revisar" in txt:
                por_rev += 1
        return [
            {"k": "Pedidos abiertos", "v": str(abiertos), "s": "carpeta jobs/"},
            {"k": "En diseno", "v": str(en_diseno), "s": "activos"},
            {"k": "Por revisar", "v": str(por_rev), "s": "pendientes"},
            {"k": "Fuente", "v": "real", "s": "jobs/"},
        ]
    return [
        {"k": "Pedidos abiertos", "v": "4", "s": "2 eventos . 2 suplementos"},
        {"k": "En diseno", "v": "2", "s": "flyer + etiqueta"},
        {"k": "Por revisar", "v": "1", "s": "pendon suplementos"},
        {"k": "Entregados (mes)", "v": "11", "s": "demo"},
    ]


def api_materials():
    """Lee context/data/materials.json si existe; si no, demo minimo."""
    path = os.path.join(CONTEXT_DIR, "data", "materials.json")
    data = _read_json(path, None)
    if data and isinstance(data, dict) and data.get("items"):
        return data
    return {"items": [
        {"id": "rider-operativo", "category": "rider", "title": "Rider Operativo RD",
         "desc": "Protocolo setup stand + atencion.", "meta": "6 pags . PDF . 2023",
         "tags": ["operativo", "protocolo"]},
        {"id": "flyer-testeo", "category": "flyer", "title": "Flyer Testeo Quimico",
         "desc": "Info sobre analisis colorimetrico.", "meta": "A4 . 2022",
         "tags": ["testeo", "quimico"]},
    ]}


def api_rd_summary():
    """Read-only canonical RD database summary for ``flujo serve``."""
    return rd_summary(Path(REPO))


def api_rd_topics():
    """Read-only thematic RD projection shared with the main Hub."""
    return rd_topics(Path(REPO))


def api_rd_crosswalk():
    """Read-only RD/portfolio entity crosswalk."""
    return rd_crosswalk(Path(REPO))


def api_rd_cultura_relations():
    """Read-only RD/Cultura candidate relation graph."""
    return rd_cultura_relations(Path(REPO))


def api_rd_db():
    """Serve the existing RD panel projection without enabling mutations."""
    from flujo.rd.panel import datos_panel

    data = datos_panel(Path(REPO))
    data["read_only"] = True
    data["source"] = "flujo-serve"
    data["canonical_projection"] = "data/rd.db"
    return data


def _rd_logo_path(slug):
    """Resolve a known RD logo under the allowlisted logos directory."""
    if not re.fullmatch(r"[a-z0-9_-]{1,64}", slug or ""):
        return None
    root = Path(REPO)
    profile_path = root / "data" / "productoras" / (slug + ".json")
    ref = ""
    try:
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
        logos = raw.get("logos") or []
        if logos and isinstance(logos[0], dict):
            knowledge = str(logos[0].get("knowledge") or "")
            if knowledge.endswith(".yaml"):
                ref = Path(knowledge).stem
    except (OSError, ValueError, TypeError):
        pass
    from flujo.rd.panel import _candidatos_logo

    base = root / "knowledge" / "logos"
    for candidate in _candidatos_logo(base, slug, ref):
        if candidate.is_file() and candidate.suffix.lower() in MIME:
            return candidate
    return None


def api_index_brief():
    """Si existe un index_rd.json generado por flujo.index, devuelve un resumen.
    Si no, indica que hay que generarlo. No escanea aqui (eso lo hace 'index build')."""
    candidatos = [
        os.path.join(REPO, "src", "flujo", "index", "index_rd.json"),
        os.path.join(REPO, "index_rd.json"),
    ]
    for c in candidatos:
        data = _read_json(c, None)
        if data and data.get("_meta"):
            m = data["_meta"]
            return {"disponible": True, "base": m.get("base"),
                    "n_archivos": m.get("n_archivos"),
                    "peso": m.get("peso_total_human"),
                    "generado": m.get("generado")}
    return {"disponible": False,
            "msg": "Genera el indice con: py -m flujo index build --hash"}


def api_list_jobs():
    """Lista jobs de forma liviana para el hub React en el servidor stdlib."""
    jobs_dir = os.path.join(REPO, "jobs")
    jobs = []
    if not os.path.isdir(jobs_dir):
        return {"jobs": [], "count": 0, "connected": True, "source": "jobs", "note": "no jobs dir"}
    for name in sorted(os.listdir(jobs_dir)):
        if name.startswith(".") or name == "_template":
            continue
        path = os.path.join(jobs_dir, name)
        if not os.path.isdir(path):
            continue
        estado_path = os.path.join(path, "estado.md")
        estado_txt = ""
        if os.path.isfile(estado_path):
            try:
                estado_txt = open(estado_path, encoding="utf-8", errors="replace").read()[:1200]
            except Exception:
                estado_txt = ""
        low = estado_txt.lower()
        estado = "borrador"
        for candidate in ["entregado", "revision", "por-revisar", "en-diseno", "pendiente", "listo"]:
            if candidate in low:
                estado = candidate
                break
        jobs.append({
            "name": name,
            "path": os.path.relpath(path, REPO).replace("\\", "/"),
            "estado": estado,
            "tipo_pieza": "",
            "proyecto": "",
            "pendientes": [],
        })
    return {"jobs": jobs, "count": len(jobs), "connected": True, "source": "jobs"}


def api_parse_pedido(text):
    """Heuristica minima para `flujo hub serve`; el backend completo vive en flujo app."""
    low = (text or "").lower()
    tipo = "flyer"
    formato = "evt_flyer_fisico_10x14"
    tool = "render"
    medidas = "10x14"
    if "suplement" in low or "etiqueta" in low:
        tipo = "etiqueta"; formato = "sup_etiqueta_165x65"; medidas = "16.5x6.5"
    if "plano" in low or "rider" in low or "stand" in low:
        tipo = "plano"; formato = "plano_stand"; medidas = "segun evento"; tool = "plano"
    if "instagram" in low or "post" in low:
        tipo = "post_ig"; formato = "evt_post_ig"; medidas = "1080x1350"
    preset = infer_event_preset(text) if ("evento" in low or "rider" in low or "cartelera" in low or "instagram" in low) else None
    return {
        "tipo": tipo, "medidas": medidas, "formato": formato, "tool": tool,
        "area": "eventos" if preset else ("suplementos" if tipo == "etiqueta" else "comun"),
        "event_preset": preset,
        "match": True, "warnings": ["Parser liviano de hub serve; usa py -m flujo app para parser completo"],
        "source": "serve-heuristic", "connected": True
    }


def api_list_svg_works():
    """Escanea svg/ y devuelve grupos consumibles por el visualizador React."""
    svg_root = os.path.join(REPO, "svg")
    if not os.path.isdir(svg_root):
        return {"groups": {}, "count": 0, "root": "svg", "error": "no svg dir"}
    groups = {}
    total = 0
    for group_name in sorted(os.listdir(svg_root)):
        group_dir = os.path.join(svg_root, group_name)
        if not os.path.isdir(group_dir):
            continue
        found = []
        for base, _dirs, files in os.walk(group_dir):
            for name in files:
                if not name.lower().endswith(".svg"):
                    continue
                full = os.path.join(base, name)
                rel = os.path.relpath(full, REPO).replace("\\", "/")
                low = rel.lower()
                kind = "editable" if "editab" in low else ("vectorizado" if "vector" in low else "other")
                found.append({"name": name, "path": rel, "kind": kind, "group": group_name})
                total += 1
        if found:
            found.sort(key=lambda item: (0 if item["kind"] == "editable" else 1 if item["kind"] == "vectorizado" else 2, item["name"]))
            groups[group_name] = found[:50]
    return {"groups": groups, "count": total, "root": "svg", "connected": True}


def api_plano_render(evento):
    """Misma forma que el demo del HTML: {layout, rider, costos}.

    Fuente unica: flujo.plano (engine + costs), armado a partir del pack RD
    contratado (INFO/TESTEO/COMPLETO, flujo.plano.packs) en vez del viejo
    preset de tamano de evento (under/base/mainstream). Antes este endpoint
    reimplementaba mesas/costos con valores propios que ya estaban
    desincronizados del motor (tercera copia de la regla de mesas).
    """
    from ..plano.costs import calcular_costos
    from ..plano.engine import mesas_requeridas, reglas_rider, solve_layout, validate_evento
    from ..plano.packs import ev_desde_pack, normalize_pack_id

    evento = evento or {}
    pack_id = normalize_pack_id(evento.get("pack") or evento.get("preset"))
    nombre = str(evento.get("nombre", "Evento"))
    dur = float(evento.get("duracion_horas", 0) or 0)
    asis = int(evento.get("asistentes_estimados", 0) or 0)
    layout_mode = str(evento.get("layout_mode", "grid_2x"))
    ev_motor = ev_desde_pack(pack_id, nombre=nombre, duracion_horas=dur,
                              asistentes_estimados=asis, layout_mode=layout_mode)
    vol = ev_motor["voluntarios"]
    testeo = ev_motor["incluye_testeo"]

    scale = 92
    baseX, baseY = 40, 60

    cajas, _ancho_m, _alto_m = solve_layout(ev_motor)
    zones = []
    n_mesa = 0
    for caja in cajas:
        if caja.rol == "zona":
            ztype = "descanso"
        elif "testeo" in caja.nombre.lower():
            ztype = "testeo"
        else:
            ztype = "stand"
        cx, cy = baseX + caja.x * scale, baseY + caja.y * scale
        zones.append({"type": ztype, "x": int(cx), "y": int(cy),
                      "w": int(caja.w * scale), "h": int(caja.h * scale),
                      "label": caja.nombre.upper()})
        for hijo in caja.hijos:
            if hijo.rol != "mesa":
                continue  # sillas no tienen tipo de zona en el hub
            n_mesa += 1
            zones.append({"type": "mesa", "x": int(cx + hijo.x * scale),
                          "y": int(cy + hijo.y * scale),
                          "w": int(hijo.w * scale), "h": int(hijo.h * scale),
                          "label": "mesa%d" % n_mesa})

    layout = {"w": 640, "h": 480,
              "title": "%s (%s)" % (nombre, layout_mode),
              "sub": "%gh . %d personas . ~%d asistentes" % (dur, vol, asis),
              "pack": ev_motor.get("pack"),
              "pack_label": ev_motor.get("pack_label"),
              "zones": zones}

    mesas = mesas_requeridas(vol, incluye_testeo=testeo)
    rider = "RIDER INTERVENCION RD - %s\n" % nombre
    rider += "=" * 56 + "\n\n"
    rider += "Pack: %s\n" % ev_motor.get("pack_label", "")
    rider += "Duracion: %gh | Voluntarios: %d | Asistentes ~%d\n\n" % (dur, vol, asis)
    rider += "REQUERIMIENTOS (reglas del motor):\n"
    for req in reglas_rider(ev_motor):
        rider += "- %s\n" % req
    rider += "\nMesas: %d unt.\n" % mesas

    c = calcular_costos(ev_motor)
    total = int(c["total"])
    costos = "COTIZACION INTERVENCION RD\n\n"
    costos += "%s: $%s\n" % (c["pack_label"], format(int(c["precio"]), ",d").replace(",", "."))
    for item in c["desglose"]:
        costos += "%s (%s%%): $%s\n" % (item["label"], item["pct"], format(int(item["monto"]), ",d").replace(",", "."))
    costos += "\nTOTAL: $%s\n" % format(total, ",d").replace(",", ".")

    validacion = validate_evento(ev_motor)
    result = {"layout": layout, "rider": rider, "costos": costos, "total": total,
            "pack": ev_motor.get("pack"), "pack_label": ev_motor.get("pack_label"),
            "validacion": {"ok": validacion["ok"], "errors": validacion["errors"],
                           "warnings": validacion["warnings"]}}
    if evento.get("zone_overlay") is not None:
        from ..vj.zone_overlay import prepare_zone_overlay
        result["overlay"] = prepare_zone_overlay(evento["zone_overlay"])
    return result


# ---------------- handler HTTP ----------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silencioso

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # CSP defensiva (los HTML son self-contained + shared local)
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                         "style-src 'self' 'unsafe-inline'; img-src 'self' data:")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=True))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/context/flujo_hub.html")
            self.end_headers()
            return
        if path == "/api/health/stats":
            return self._json(api_health_stats())
        if path == "/api/materials":
            return self._json(api_materials())
        if path == "/api/rd/summary":
            return self._json(api_rd_summary())
        if path == "/api/rd/topics":
            return self._json(api_rd_topics())
        if path == "/api/rd/crosswalk":
            return self._json(api_rd_crosswalk())
        if path == "/api/rd/cultura-relations":
            return self._json(api_rd_cultura_relations())
        if path == "/api/rd-db":
            try:
                return self._json(api_rd_db())
            except Exception as exc:
                return self._json({"productoras": [], "venues": [], "error": type(exc).__name__}, 200)
        if path == "/api/rd-db/logo":
            slug = (parse_qs(urlparse(self.path).query).get("slug") or [""])[0].strip().lower()
            logo = _rd_logo_path(slug)
            if logo is None:
                return self._send(404, "404 - logo", "text/plain; charset=utf-8")
            return self._send(200, logo.read_bytes(), MIME[logo.suffix.lower()])
        if path in ("/api/list-svg-works", "/api/svg-index"):
            return self._json(api_list_svg_works())
        if path == "/api/event-presets":
            return self._json({"presets": list_event_presets(), "connected": True})
        if path == "/api/list-jobs":
            return self._json(api_list_jobs())
        if path == "/api/dashboard-summary":
            return self._json({"total_jobs": api_list_jobs().get("count", 0), "total_svg": api_list_svg_works().get("count", 0), "connected": True})
        if path == "/api/index/brief":
            return self._json(api_index_brief())
        if path.startswith("/context/"):
            return self._serve_file(path[len("/context/"):])
        if path.startswith("/svg/"):
            return self._serve_repo_file(path.lstrip("/"))
        if path.startswith("/api/"):
            return self._json({"error": "endpoint no encontrado"}, 404)
        self._send(404, "404", "text/plain; charset=utf-8")

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BODY_BYTES:
            return self._json({"error": "cuerpo demasiado grande"}, 413)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json({"error": "JSON invalido"}, 400)
        if path == "/api/plano/render":
            try:
                return self._json(api_plano_render(payload.get("evento", payload)))
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        if path == "/api/cotizacion/render":
            try:
                return self._json(generar_cotizacion_base(payload.get("evento", payload), incluir_cartelera=payload.get("incluir_cartelera", True), incluir_flyer_impreso=payload.get("incluir_flyer_impreso", False)))
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        if path in ("/api/parse-pedido", "/api/parse-real-pedido"):
            return self._json(api_parse_pedido(payload.get("text", "") or payload.get("pedido", "")))
        if path == "/api/create-job-draft":
            return self._json({"created": False, "error": "create-job-draft requiere py -m flujo app (backend completo)"}, 501)
        return self._json({"error": "endpoint no encontrado"}, 404)

    def _serve_repo_file(self, rel):
        rel = rel.replace("\\", "/").lstrip("/")
        full = os.path.normpath(os.path.join(REPO, rel))
        allowed = os.path.join(REPO, "svg")
        # Boundary con separador: 'svg' no debe autorizar hermanos como 'svg_export/'.
        if full != allowed and not full.startswith(allowed + os.sep):
            return self._send(403, "403", "text/plain")
        if not os.path.isfile(full):
            return self._send(404, "404 - " + rel, "text/plain; charset=utf-8")
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def _serve_file(self, rel):
        rel = rel.replace("\\", "/").lstrip("/")
        # anti path-traversal: boundary con separador para no autorizar hermanos
        # como 'context_old/' cuyo nombre solo comparte el prefijo 'context'.
        full = os.path.normpath(os.path.join(CONTEXT_DIR, rel))
        if full != CONTEXT_DIR and not full.startswith(CONTEXT_DIR + os.sep):
            return self._send(403, "403", "text/plain")
        if not os.path.isfile(full):
            return self._send(404, "404 - " + rel, "text/plain; charset=utf-8")
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)


def run(port=8777, open_browser=False, host="127.0.0.1"):
    if not os.path.isdir(CONTEXT_DIR):
        print("AVISO: no existe", CONTEXT_DIR, "- el hub no se servira (faltan HTML).")
    srv = ThreadingHTTPServer((host, port), Handler)
    url = "http://%s:%d/" % (host, port)
    print("flujo serve  ->  " + url)
    print("  hub:       " + url + "context/flujo_hub.html")
    print("  api stats: " + url + "api/health/stats")
    print("  (Ctrl+C para detener)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\ndetenido.")
        srv.server_close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flujo serve")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--open", action="store_true", help="abrir navegador")
    args = ap.parse_args(argv)
    run(port=args.port, open_browser=args.open, host=args.host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
