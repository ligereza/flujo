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
  GET  /api/materials/<id>/download -> stub de descarga
  POST /api/plano/render         -> {evento} -> {layout, rider, costos}

Uso:
  py -m flujo serve            # http://127.0.0.1:8777
  py -m flujo serve --port 9000 --open

Reglas: stdlib only, ASCII-only, no toca archivos del usuario, no guarda tokens.
"""

import json
import os
import sys
import argparse
import webbrowser

from flujo.eventos.presets import apply_event_preset, infer_event_preset, list_event_presets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# raiz del repo = 3 niveles arriba de este archivo (src/flujo/serve/ -> repo)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTEXT_DIR = os.path.join(REPO, "context")

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
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
            groups[group_name] = found[:8]
    return {"groups": groups, "count": total, "root": "svg", "connected": True}


def api_plano_render(evento):
    """Misma forma que el demo del HTML: {layout, rider, costos}."""
    ev = apply_event_preset(evento or {})
    nombre = str(ev.get("nombre", "Evento"))
    dur = float(ev.get("duracion_horas", 6) or 6)
    vol = int(ev.get("voluntarios", 7) or 7)
    asis = int(ev.get("asistentes_estimados", 0) or 0)
    testeo = bool(ev.get("incluye_testeo", True))
    masivo = bool(ev.get("masivo", False))
    layout_mode = str(ev.get("layout_mode", "grid_2x"))

    scale = 92
    stand_w, stand_h, pasillo = 3.5, 3.0, 1.2
    standW, standH = int(stand_w * scale), int(stand_h * scale)
    mesas = 1 + (vol - 1) // 5
    baseX, baseY = 40, 60

    zones = [{"type": "stand", "x": baseX, "y": baseY, "w": standW, "h": standH,
              "label": "STAND INFORMATIVO"}]
    for i in range(min(mesas, 4)):
        zones.append({"type": "mesa", "x": baseX + 12 + (i % 2) * 80,
                      "y": baseY + 50 + (i // 2) * 30, "w": 45, "h": 22,
                      "label": "mesa%d" % (i + 1)})
    if testeo:
        zones.append({"type": "testeo", "x": baseX + 160, "y": baseY + 20,
                      "w": 100, "h": 80, "label": "TESTEO"})
    if masivo:
        zones.append({"type": "descanso", "x": baseX + 160, "y": baseY + 120,
                      "w": 100, "h": 70, "label": "DESCANSO"})

    layout = {"w": 640, "h": 480,
              "title": "%s (%s)" % (nombre, layout_mode),
              "sub": "%gh . %d personas . ~%d asistentes" % (dur, vol, asis),
              "preset": ev.get("preset"),
              "preset_label": ev.get("preset_label"),
              "zones": zones}

    rider = "RIDER INTERVENCION RD - %s\n" % nombre
    rider += "=" * 56 + "\n\n"
    rider += "Preset: %s\n" % ev.get("preset_label", "Evento BASE")
    rider += "Duracion: %gh | Voluntarios: %d | Asistentes ~%d\n\n" % (dur, vol, asis)
    rider += "SERVICIOS:\n- Stand Informativo: %gx%gm\n" % (stand_w, stand_h)
    if testeo:
        rider += "- Stand Testeo: analisis colorimetrico\n"
    if masivo:
        rider += "- Zona Contencion/Descanso\n"
    rider += "\nMesas: %d unt.\n" % int(ev.get("preset_operativo", {}).get("mesas", mesas))
    rider += "Sillas: %d unt.\n" % int(ev.get("preset_operativo", {}).get("sillas", max(2, vol)))
    rider += "Electricidad: %s\n" % ev.get("preset_operativo", {}).get("electricidad", "1 punto electrico")
    rider += "Luz: %s\n" % ev.get("preset_operativo", {}).get("luz", "luz de apoyo")
    if dur > 5:
        rider += "Alimentacion: obligatoria\n"

    total = 180000 + (95000 if testeo else 0) + (65000 if dur > 5 else 0)
    costos = "COTIZACION INTERVENCION RD\n\n"
    costos += "Equipo: %d personas x %gh\nStand: ~$180.000\n" % (vol, dur)
    if testeo:
        costos += "Testeo: ~$95.000\n"
    if dur > 5:
        costos += "Alimentacion: ~$65.000\n"
    costos += "\nTOTAL ESTIMADO: desde $%s\n" % format(total, ",d").replace(",", ".")

    return {"layout": layout, "rider": rider, "costos": costos, "total": total, "preset": ev.get("preset"), "preset_operativo": ev.get("preset_operativo")}


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
        if path.startswith("/api/materials/") and path.endswith("/download"):
            mid = path[len("/api/materials/"):-len("/download")]
            return self._json({"ok": True, "msg": "stub descarga", "id": mid})
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
        if path in ("/api/parse-pedido", "/api/parse-real-pedido"):
            return self._json(api_parse_pedido(payload.get("text", "") or payload.get("pedido", "")))
        if path == "/api/create-job-draft":
            return self._json({"created": False, "error": "create-job-draft requiere py -m flujo app (backend completo)"}, 501)
        return self._json({"error": "endpoint no encontrado"}, 404)

    def _serve_repo_file(self, rel):
        rel = rel.replace("\\", "/").lstrip("/")
        full = os.path.normpath(os.path.join(REPO, rel))
        allowed = os.path.join(REPO, "svg")
        if not full.startswith(allowed):
            return self._send(403, "403", "text/plain")
        if not os.path.isfile(full):
            return self._send(404, "404 - " + rel, "text/plain; charset=utf-8")
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def _serve_file(self, rel):
        rel = rel.replace("\\", "/").lstrip("/")
        # anti path-traversal
        full = os.path.normpath(os.path.join(CONTEXT_DIR, rel))
        if not full.startswith(CONTEXT_DIR):
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
