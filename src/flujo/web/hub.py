"""Servidor para el workspace HTML del hub (flujo_hub.html + visualizadores).

Transformación de HTMLs estáticos → aplicación local profesional real.

Arquitectura (free, Python-native preferida):
- stdlib http.server (cero deps runtime extra) + API endpoints reales.
- Integración profunda: intake real (parse_pedido_text), brand (flujo.json), jobs (create/list), svg scan, safe cmd runner.
- Desktop: pywebview (BSD, gratis) con js_api bridge (exposición directa de Python a JS), icono, tray.
- Cuando `flujo app` o --desktop: fetches usan /api o bridge directo → experiencia sin chrome browser, funcional (crear jobs reales, parse authoritativo, live lists).
- Fallback perfecto cuando abre HTML directo.

Todo gratis. `flujo package` (PyInstaller) genera .exe onefile/onedir profesional listo: icono embebido premium (Pillow rounded+F), noconsole, launcher directo a desktop pywebview + tray + bridge. Bundles context/ (HTMLs) + svg/ (cargan en viz) + projects/flujo (brand) + jobs/_template + templates. Jobs/data a flujo_workspace/ sibling (paths frozen). Servidor soporta assets /svg /projects para visualizers completos en packaged. Soporte onefile/onedir. Inno Setup gratis recomendado para full installer. Equivale a flujo app --desktop standalone.

Uso:
    flujo app
    flujo app --desktop   # ventana nativa premium + bridge + tray
    flujo package         # .exe standalone gratis (icon + noconsole + desktop directo)
"""

from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
import time
from urllib.parse import urlparse, parse_qs

from ..paths import context_dir, repo_root, asset_root, workspace_root, is_packaged as _is_packaged
from ..brand import load_styles
from ..intake.email_parser import parse_email_content, parse_pedido_text  # real parsers
from ..intake.pipeline import _infer_type_and_size  # reuse heuristics if needed
from ..jobs.job import create_job, list_jobs  # real job creation / listing for hub API


class HubRequestHandler(BaseHTTPRequestHandler):
    """Sirve estáticos + API ligera para hacer que el hub sea una app real.
    Endpoints reales conectan con intake, brand, svg scan y comandos seguros.
    """

    ROOT: Path = None
    CONTEXT: Path = None

    def __init__(self, *args, **kwargs):
        if HubRequestHandler.ROOT is None:
            # packaged desktop: prefer asset_root (bundled context/svg) for serving
            HubRequestHandler.ROOT = asset_root()
            HubRequestHandler.CONTEXT = context_dir()
        self.root = HubRequestHandler.ROOT
        self.context_path = HubRequestHandler.CONTEXT
        if args or kwargs:
            super().__init__(*args, **kwargs)
        # else: direct test/debug instantiation ok (attrs set)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/hub", "/index.html"):
            path = "/flujo_hub.html"
        elif path == "/visualizer":
            path = "/svg_visualizer.html"
        elif path == "/plano":
            path = "/plano_demo.html"

        # API endpoints (real backend)
        if path == "/api/ping":
            self._send_json({
                "status": "ok",
                "workspace": "flujo",
                "version": self._get_version(),
                "root": str(self.root),
                "connected": True,
                "mode": "http-server",
                "note": "real backend active — use from `flujo app`"
            })
            return
        if path in ("/api/brand", "/api/load-flujo-brand"):
            try:
                styles = load_styles()
                self._send_json({
                    "brand": styles,
                    "source": str(self.root / "projects" / "flujo" / "flujo.json"),
                    "connected": True
                })
            except Exception as e:
                self._send_json({"error": str(e), "fallback": True}, status=200)
            return
        if path == "/api/brand-validate":
            try:
                styles = load_styles()
                self._send_json({
                    "ok": True,
                    "message": "BRAND ENFORCED: usa el JS runBrandValidator() en flujo_hub.html (o visualizers) para escanear DOM/SVG/CSS. Paleta EXACTA projects/flujo/flujo.json. Llama /api/load-flujo-brand. Forbidden: neon/cyan/vibecoding/paper en chrome. Paper SOLO en SVGs print.",
                    "brand": styles,
                    "forbidden_examples": ["#00f0ff", "neon", "cyan", "#2ecc71", "light #f8f1e3 en UI", "hacker/glitch"],
                    "usage": "Ejecuta 'VALIDAR BRAND AHORA' (prominente en hub) ANTES de entregar cualquier visual. Refuerza Brand Guardian + validator en hub. Todo pro pasa por aquí.",
                    "action": "Abre hub → sección Brand Enforcement → botón grande VALIDAR BRAND AHORA + FORZAR GUARD. NO exportar hasta clean."
                })
            except Exception as e:
                self._send_json({"error": str(e)}, status=200)
            return
        if path == "/api/list-svg-works":
            try:
                data = self._list_svg_works()
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e), "groups": {}}, status=200)
            return
        if path == "/api/status":
            self._send_json(self._get_status())
            return
        if path == "/api/list-jobs":
            try:
                self._send_json(self._list_jobs_api())
            except Exception as e:
                self._send_json({"jobs": [], "count": 0, "error": str(e)}, status=200)
            return
        if path == "/api/agents-roles":
            self._send_json(self._get_agents_roles())
            return
        if path == "/manifest.json":
            self._serve_manifest()
            return
        if path == "/sw.js":
            self._serve_service_worker()
            return
        if path == "/api/events":
            self._serve_sse_events()
            return
        if path == "/api/export-tokens":
            try:
                self._send_json(self._export_design_tokens())
            except Exception as e:
                self._send_json({"error": str(e), "fallback": True}, status=200)
            return

        # Servir archivos estáticos: context/ primero (hub + visualizers HTMLs), fallback a root/ (asset_root)
        # para assets bundled por `flujo package` (svg/, projects/flujo/ para brand json directo, etc).
        # Esto asegura que en el .exe standalone (pywebview desktop) los visualizadores cargan SVGs reales
        # y los links a brand/assets funcionan (sin 404). Soporta links legacy con ../ .
        rel = path.lstrip("/")
        file_path = self.context_path / rel
        if not file_path.is_file() and getattr(self, "root", None):
            file_path = self.root / rel
        if not file_path.is_file() and rel.startswith("../"):
            rel2 = rel[3:].lstrip("/")
            file_path = self.context_path / rel2
            if not file_path.is_file() and getattr(self, "root", None):
                file_path = self.root / rel2
        if file_path.is_file():
            self._serve_file(file_path)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        p = parsed.path

        if p == "/api/parse-pedido" or p == "/api/parse-real-pedido":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                text = data.get("text", "") or data.get("pedido", "")
                result = self._real_parse_pedido(text)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if p == "/api/run-safe-command":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                cmd = (data.get("cmd") or data.get("command") or "").strip()
                out = self._run_safe_command(cmd)
                self._send_json(out)
            except Exception as e:
                self._send_json({"error": str(e), "cmd": cmd if 'cmd' in locals() else ""}, status=400)
            return

        if p == "/api/delegate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = self._handle_delegate(data)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if p == "/api/create-job-draft":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                text = data.get("text", "") or data.get("pedido", "")
                name = data.get("name", "")
                result = self._create_job_draft(text, name)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        self.send_error(404)

    def _serve_file(self, file_path: Path):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            if file_path.suffix == ".html":
                self.send_header("Content-type", "text/html")
            elif file_path.suffix == ".js":
                self.send_header("Content-type", "application/javascript")
            elif file_path.suffix == ".css":
                self.send_header("Content-type", "text/css")
            elif file_path.suffix == ".svg":
                self.send_header("Content-type", "image/svg+xml")
            else:
                self.send_header("Content-type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _get_version(self) -> str:
        try:
            from ..version import get_version
            return get_version()
        except Exception:
            return "unknown"

    def _get_status(self) -> dict:
        return {
            "status": "ok",
            "version": self._get_version(),
            "root": str(self.root),
            "has_svg": (self.root / "svg").exists(),
            "has_projects": (self.root / "projects").exists(),
            "connected": True,
            "time": time.time()
        }

    def _get_agents_roles(self) -> dict:
        """Central definition of specialized agent roles for delegation system.
        Exposed to hub UI and CLI. Supports parallel delegation.
        """
        return {
            "roles": [
                {
                    "id": "visual-polish",
                    "name": "Visual Polish Agent",
                    "short": "Enforce 'flujo' brand on all outputs",
                    "focus": "pulido visual, previews, HTMLs, SVGs, consistencia estética",
                    "prompt_template": "Tu rol: Visual Polish Agent.\n\nSigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.\n\nPunto de entrada OBLIGATORIO: ejecuta `flujo app` (o `flujo app --desktop`). Abre el hub pro. Lee context/LAST_HANDOFF.md + este manual primero (bajo token).\n\n[Tarea específica: {task}]\n\nTrabaja en tu clon separado. Entrega SOLO vía airdrop (incluye handoff actualizado + docs relevantes). Al final, actualiza LAST_HANDOFF con tareas pendientes. Usa siempre el flujo y brand. Revisa outputs de otros si aplica."
                },
                {
                    "id": "pipeline",
                    "name": "Pipeline & Integration Agent",
                    "short": "CLI, backend, jobs, packaging",
                    "focus": "Typer CLI, web/hub, jobs lifecycle, render/export, airdrop, tests, packaging",
                    "prompt_template": "Tu rol: Pipeline & Integration Agent.\n\nSigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.\n\nPunto de entrada OBLIGATORIO: ejecuta `flujo app`. Lee context/LAST_HANDOFF.md + este manual primero.\n\n[Tarea específica: {task}]\n\nUsa py en Windows. Prueba siempre: compileall, pytest -q, comandos manuales. Trabaja en clon. Entrega vía airdrop actualizando handoff, version.py si aplica y docs. Coordina con Brand si tocas UI/brand files."
                },
                {
                    "id": "brand",
                    "name": "Brand Guardian",
                    "short": "flujo.json + linea editorial",
                    "focus": "Custodio de identidad de marca. Valida Visual y Pipeline.",
                    "prompt_template": "Tu rol: Brand Guardian.\n\nSigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.\n\nPunto de entrada OBLIGATORIO: ejecuta `flujo app`. Lee context/LAST_HANDOFF.md + este manual primero. Abre projects/flujo/flujo.json y linea_editorial.md.\n\n[Tarea específica: {task}]\n\nFuente de verdad. Valida todo lo que otros agentes producen. No inventes; deriva de flujo.json. Entrega airdrop + actualiza handoff."
                },
                {
                    "id": "future",
                    "name": "Future/Modern Agent",
                    "short": "Nuevas integraciones tech",
                    "focus": "WebSockets, PWA, real-time, IMAP/webhooks, schemas, packaging futuro, arquitecturas",
                    "prompt_template": "Tu rol: Future/Modern Agent.\n\nSigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.\n\nPunto de entrada OBLIGATORIO: ejecuta `flujo app`. Lee context/LAST_HANDOFF.md + este manual primero.\n\n[Tarea específica: {task}]\n\nCoordina explícitamente: menciona en handoff qué revisó Brand/Pipeline. Entrega airdrop con prototipo + recomendaciones. Prioriza gratis y compatible con Python core. NO toques core sin revisión explícita."
                },
                {
                    "id": "packaging",
                    "name": "Packaging & Distribution Agent",
                    "short": "Empaquetado desktop gratis (.exe, pywebview, PyInstaller, Inno)",
                    "focus": "flujo package, launcher desktop, paths frozen, assets bundle (context/svg/brand), workspace persistente, onefile/onedir, icon, tray, instalador free",
                    "prompt_template": "Tu rol: Packaging & Distribution Agent.\n\nSigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.\n\nPunto de entrada OBLIGATORIO: ejecuta `flujo app` (o `flujo app --desktop`). Lee context/LAST_HANDOFF.md + este manual primero.\n\n[Tarea específica: {task}]\n\nUsa PyInstaller (gratis) + pywebview. Nunca rompas paths o assets bundled. Trabaja en clon. Entrega airdrop con pruebas de build simulado + nota de UX desktop. Coordina con Pipeline (core) + Brand (icon/identidad en exe). Prioriza gratis y Windows-first. Actualiza LAST_HANDOFF."
                }
            ],
            "note": "Agentes operan en paralelo en clones separados del workspace. Siempre incluye 'Abre flujo app + lee LAST_HANDOFF'. Actualiza LAST_HANDOFF al entregar."
        }

    def _handle_delegate(self, data: dict) -> dict:
        """Core of delegation system. Accepts role_id + task, returns precise prompt.
        Optionally can 'log' by suggesting handoff update or running safe cmd.
        Supports simultaneous by handling batch or single.
        """
        role_id = (data.get("role_id") or data.get("role") or "").strip()
        task = (data.get("task") or data.get("description") or "mejorar la funcionalidad X").strip()
        roles_data = self._get_agents_roles()["roles"]
        role = next((r for r in roles_data if r["id"] == role_id or r["name"].lower() == role_id.lower()), None)
        if not role:
            role = roles_data[0]  # default visual

        prompt = role["prompt_template"].format(task=task)
        full_context = f"Contexto base: Ejecuta `flujo app`. Lee LAST_HANDOFF + AGENT_OPERATING_MANUAL antes de empezar.\n\n{prompt}"

        # Log delegation attempt (to server stdout for traceability). Optional: could append to LAST_HANDOFF via handoff but keep read-only safe.
        print(f"[DELEGATE] {role['name']} <- {task[:80]}")

        # If client asks to log, suggest command
        log_cmd = None
        if data.get("log_to_handoff"):
            log_cmd = f"flujo handoff create -m \"Delegated to {role['name']}: {task[:50]}\""

        return {
            "role": role,
            "task": task,
            "prompt": prompt,
            "full_prompt": full_context,
            "log_cmd_suggested": log_cmd,
            "delegated_at": time.time(),
            "connected": True,
            "simultaneous_note": "Puedes delegar a múltiples roles en paralelo abriendo sesiones separadas."
        }

    def _serve_manifest(self):
        """PWA manifest served on-the-fly. Enables 'Add to desktop / install' feel without extra disk files."""
        manifest = {
            "name": "flujo • Workspace",
            "short_name": "flujo",
            "description": "Workspace pro para diseñador: intake, visualizers SVG/plano, CLI bridge, agent delegation.",
            "start_url": "/flujo_hub.html",
            "display": "standalone",
            "background_color": "#0a0a0a",
            "theme_color": "#2d5a4a",
            "icons": [
                {"src": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyIiBoZWlnaHQ9IjE5MiIgdmlld0JveD0iMCAwIDE5MiAxOTIiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjE5MiIgaGVpZ2h0PSIxOTIiIHJ4PSIxNiIgZmlsbD0iIzBhMGEwYSIvPjx0ZXh0IHg9Ijk2IiB5PSIxMTUiIGZvbnQtc2l6ZT0iODAiIGZpbGw9IiMyZDVhNGEiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtd2VpZ2h0PSI3MDAiPkY8L3RleHQ+PC9zdmc+", "sizes": "192x192", "type": "image/svg+xml"}
            ],
            "scope": "/"
        }
        self.send_response(200)
        self.send_header("Content-type", "application/manifest+json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(manifest, ensure_ascii=False).encode("utf-8"))

    def _serve_service_worker(self):
        """Minimal SW stub for PWA offline/install capability (local server focused)."""
        sw = """self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('fetch', e => e.respondWith(fetch(e.request).catch(() => new Response('flujo offline stub'))));"""
        self.send_response(200)
        self.send_header("Content-type", "application/javascript")
        self.end_headers()
        self.wfile.write(sw.encode("utf-8"))

    def _export_design_tokens(self) -> dict:
        """Modern free integration: export brand tokens as CSS vars + structured JSON.
        Ready for Figma (Tokens Studio / official tokens plugin import JSON), Framer, Tailwind, CSS.
        Uses the single source projects/flujo/flujo.json. Designer daily tool for brand sync.
        Zero deps, always in sync via /api.
        """
        try:
            styles = load_styles()
            ink = styles.get("ink", "#1f2a24")
            accent = styles.get("accent", "#2d5a4a")
            paper = styles.get("paper", "#f8f1e3")
            support = styles.get("support", "#675f55")
            alert = styles.get("alert", "#c2410f")
            css = f""":root {{
  --flujo-ink: {ink};
  --flujo-accent: {accent};
  --flujo-paper: {paper};
  --flujo-support: {support};
  --flujo-alert: {alert};
  /* typography + layout hints from brand */
  --flujo-display: Inter, system-ui, sans-serif;
}}"""
            tokens_json = {
                "source": "projects/flujo/flujo.json",
                "colors": {
                    "ink": ink, "accent": accent, "paper": paper,
                    "support": support, "alert": alert
                },
                "typography": styles.get("display") or styles.get("body") or "Inter / system sans",
                "layout": {"safeMargin": "10-15%"},
                "meta": {"name": "flujo", "version": self._get_version()}
            }
            scss = f"$flujo-ink: {ink};\n$flujo-accent: {accent}; /* etc */"
            return {
                "css": css,
                "json": tokens_json,
                "scss": scss,
                "figma_note": "Import the .json via Tokens plugin (free) or copy CSS into Figma variables.",
                "framer_note": "Paste JSON or use as theme tokens.",
                "connected": True
            }
        except Exception as e:
            return {"error": str(e)}

    def _serve_sse_events(self):
        """Enhanced Server-Sent Events for real-time / live features (jobs, SVG, status).
        Uses stdlib only. Hub JS reacts: auto-refresh lists, toasts, notifications.
        Periodic fresh data + change detection (no extra deps). Designer gets immediate feedback
        after commands, new jobs or file ops in visualizers.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            last_jobs = -1
            last_svg = -1
            # Send initial snapshots
            status = self._get_status()
            self.wfile.write(f"event: status\ndata: {json.dumps({'type':'status','data':status})}\n\n".encode())
            self.wfile.flush()
            svg_data = self._list_svg_works()
            self.wfile.write(f"event: svg\ndata: {json.dumps({'type':'svg-update','data':svg_data})}\n\n".encode())
            self.wfile.flush()
            jobs_data = self._list_jobs_api()
            self.wfile.write(f"event: jobs\ndata: {json.dumps({'type':'jobs','data':jobs_data})}\n\n".encode())
            self.wfile.flush()

            # Longer lived loop for real daily use ( ~60s before reconnect; JS auto-reopens)
            for i in range(30):
                time.sleep(2.0)
                # fresh data each tick
                status = self._get_status()
                hb = {"type": "heartbeat", "ts": time.time(), "tick": i}
                self.wfile.write(f"event: heartbeat\ndata: {json.dumps(hb)}\n\n".encode())
                self.wfile.flush()

                svg_data = self._list_svg_works()
                self.wfile.write(f"event: svg\ndata: {json.dumps({'type':'svg-update','data':svg_data})}\n\n".encode())
                self.wfile.flush()

                jobs_data = self._list_jobs_api()
                self.wfile.write(f"event: jobs\ndata: {json.dumps({'type':'jobs','data':jobs_data})}\n\n".encode())
                self.wfile.flush()

                # detect changes for targeted 'update' events
                cur_jobs = jobs_data.get("count", 0)
                cur_svg = svg_data.get("count", 0)
                changed = False
                if last_jobs >= 0 and cur_jobs != last_jobs:
                    changed = True
                    self.wfile.write(f"event: update\ndata: {json.dumps({'type':'job-change','count':cur_jobs,'prev':last_jobs,'data':jobs_data})}\n\n".encode())
                    self.wfile.flush()
                if last_svg >= 0 and cur_svg != last_svg:
                    changed = True
                    self.wfile.write(f"event: update\ndata: {json.dumps({'type':'svg-change','count':cur_svg,'prev':last_svg,'data':svg_data})}\n\n".encode())
                    self.wfile.flush()
                last_jobs = cur_jobs
                last_svg = cur_svg
                if changed:
                    # also a generic summary
                    self.wfile.write(f"event: update\ndata: {json.dumps({'type':'live-summary','jobs':cur_jobs,'svgs':cur_svg,'ts':time.time()})}\n\n".encode())
                    self.wfile.flush()
        except Exception:
            pass  # client disconnect is normal

    def _list_svg_works(self) -> dict:
        """Scan svg/ dir and group like svg_visualizer.html (top folders + key files)."""
        svg_root = self.root / "svg"
        if not svg_root.exists():
            return {"groups": {}, "count": 0, "root": "svg", "error": "no svg dir"}

        groups = {}
        total = 0
        for group_dir in sorted([p for p in svg_root.iterdir() if p.is_dir()]):
            gname = group_dir.name
            items = []
            # find svgs, prioritize editables then vector
            svgs = list(group_dir.rglob("*.svg"))
            for svgp in sorted(svgs, key=lambda p: (0 if "editable" in str(p).lower() else 1 if "vector" in str(p).lower() else 2, p.name)):
                rel = svgp.relative_to(self.root)
                rel_str = str(rel).replace("\\", "/")
                kind = "editable" if "editab" in rel_str.lower() else ("vectorizado" if "vector" in rel_str.lower() else "other")
                items.append({
                    "name": svgp.name,
                    "path": rel_str,
                    "kind": kind,
                    "group": gname
                })
                total += 1
            if items:
                groups[gname] = items[:8]  # limit per group for response size
        return {
            "groups": groups,
            "count": total,
            "root": "svg",
            "connected": True
        }

    def _real_parse_pedido(self, text: str) -> dict:
        """Full real parse using intake's parse_pedido_text (authoritative) + fallbacks.
        This makes the hub backend drive the real intake logic.
        """
        if not text or not text.strip():
            return {"error": "empty text", "tipo": "desconocido"}

        low = text.lower()
        try:
            base = parse_pedido_text(text)
        except Exception:
            # fallback to email parser + heuristics
            parsed = {}
            try:
                parsed = parse_email_content(text)
            except Exception:
                parsed = {"project_type": "unknown", "sections": {}, "warnings": []}
            inferred = None
            try:
                inferred = _infer_type_and_size(text)
            except Exception:
                pass
            base = {
                "tipo": parsed.get("project_type", "desconocido"),
                "medidas": (inferred and f"{inferred.get('ancho','?')}x{inferred.get('alto','?')}") or parsed.get("sections", {}).get("medidas", ""),
                "formato": "",
                "tool": "render",
                "pub": "interno" if ("interno" in low or "empresa" in low) else "productora",
                "vol": (re.search(r'(\d+)', text).group(1) if re.search(r'(\d+)', text) else "?"),
                "notas": text[:300],
                "sections": parsed.get("sections", {}),
            }

        # enrich with format match from known (shared logic)
        known = {
            'flyer':   {'tipo': 'flyer', 'medidas': '10x14', 'formato': 'evt_flyer_fisico_10x14', 'tool': 'render'},
            'etiqueta':{'tipo': 'etiqueta', 'medidas': '16.5x6.5', 'formato': 'sup_etiqueta_165x65', 'tool': 'render'},
            'plano':   {'tipo': 'plano', 'medidas': 'según evento', 'formato': 'plano_stand', 'tool': 'plano'},
            'stand':   {'tipo': 'plano', 'medidas': 'según evento', 'formato': 'plano_stand', 'tool': 'plano'},
            'rider':   {'tipo': 'rider', 'medidas': 'A4', 'formato': 'rider_eventos_a4', 'tool': 'plano'},
            'cotiz':   {'tipo': 'cotizacion', 'medidas': '', 'formato': 'cotizaciones', 'tool': 'cotizaciones'},
            'cartelera':{'tipo': 'cartelera', 'medidas': '1080x1920', 'formato': 'evt_cartelera', 'tool': 'render'},
            'ig':      {'tipo': 'post_ig', 'medidas': '1080x1350', 'formato': 'evt_post_ig', 'tool': 'render'},
            'suplemento':{'tipo': 'etiqueta', 'medidas': '16.5x6.5', 'formato': 'sup_etiqueta_165x65', 'tool': 'render'}
        }
        for k, m in known.items():
            if k in low:
                base["tipo"] = m["tipo"]
                base["medidas"] = base.get("medidas") or m["medidas"]
                base["formato"] = m["formato"]
                base["tool"] = m["tool"]
                break

        base.setdefault("match", bool(base.get("formato")))
        base["warnings"] = base.get("warnings") or []
        base["parsed"] = base.get("parsed") or {}
        base["inferred"] = base.get("inferred")
        base["connected"] = True
        base["source"] = "intake+hub"
        return base

    def _list_jobs_api(self) -> dict:
        """Real list of current jobs from disk using jobs module."""
        try:
            items = list_jobs(include_examples=False)
            jobs = []
            for j in items:
                jobs.append({
                    "name": j.name,
                    "path": str(j.path).replace("\\", "/"),
                    "estado": j.estado,
                    "tipo_pieza": j.tipo_pieza,
                    "proyecto": j.proyecto,
                    "pendientes": j.pendientes,
                })
            return {"jobs": jobs, "count": len(jobs), "connected": True, "source": "jobs"}
        except Exception as e:
            return {"jobs": [], "count": 0, "error": str(e)}

    def _create_job_draft(self, text: str, name: str = "") -> dict:
        """Real functionality: create a job draft folder using the real create_job.
        This turns the hub intake into an actual tool (creates jobs/YYYY-MM-DD_xxx/ + brief + pedido_original).
        """
        if not text.strip() and not name.strip():
            return {"error": "empty", "created": False}
        try:
            # derive sensible name
            nm = (name or "").strip()
            if not nm:
                # take first few words or from parsed
                low = text.lower()[:60]
                nm = "pedido " + (re.findall(r'\b\w{3,}\b', low)[:3] or ["general"])[0]
            job_path = create_job(nm, source_path=None)
            # write the original text into pedido_original.txt for traceability
            try:
                pedido_file = job_path / "pedido_original.txt"
                pedido_file.write_text(text.strip() or nm, encoding="utf-8")
            except Exception:
                pass
            # optionally enhance brief.yaml later (for now the template is good)
            return {
                "created": True,
                "job_path": str(job_path).replace("\\", "/"),
                "name": job_path.name,
                "next": f"flujo job prepare {job_path.name}",
                "connected": True,
                "source": "jobs.create_job"
            }
        except Exception as e:
            return {"error": str(e), "created": False}

    # Whitelist of safe flujo commands (prefix match after normalize). No arbitrary execution.
    # Extended for real backend use from hub (daily driver UX)
    SAFE_PREFIXES = [
        "flujo version", "flujo health", "flujo daily",
        "flujo brand", "flujo job list", "flujo job next",
        "flujo job-status", "flujo plano", "flujo render formats",
        "flujo privacy", "flujo handoff last", "flujo delegate",
        "flujo job prepare", "flujo job new", "flujo render run",
        "flujo cotizaciones",
        "py -m flujo version", "py -m flujo health", "py -m flujo daily",
        "py -m flujo job list", "py -m flujo delegate",
    ]

    def _is_safe_cmd(self, cmd: str) -> bool:
        c = cmd.lower().strip()
        if not c:
            return False
        for pref in self.SAFE_PREFIXES:
            if c.startswith(pref.lower()):
                return True
        # allow short safe ones
        if c in ("flujo version", "flujo health", "flujo daily"):
            return True
        return False

    def _run_safe_command(self, cmd: str) -> dict:
        if not self._is_safe_cmd(cmd):
            return {"error": "command not whitelisted for safety", "cmd": cmd, "allowed_prefixes": self.SAFE_PREFIXES[:5]}

        orig = cmd
        c = cmd.strip()
        # normalize 'py -m flujo ...' or 'flujo ...' to python -m flujo args
        if c.startswith("py -m flujo "):
            args = shlex.split(c)[3:]  # after py -m flujo
        elif c.startswith("flujo "):
            args = shlex.split(c)[1:]
        else:
            args = shlex.split(c)

        # Packaged standalone .exe: subprocess with sys.executable (the exe) would fail for -m.
        # Use direct in-process dispatch for whitelisted (bridge already covers parse/job create/list).
        if _is_packaged():
            try:
                low = " ".join(args).lower()
                if "version" in low:
                    from ..version import get_version
                    return {"cmd": orig, "stdout": get_version(), "success": True, "connected": True, "note": "direct (packaged)"}
                if "health" in low or "daily" in low:
                    return {"cmd": orig, "stdout": "flujo desktop packaged • hub running (use direct UI for jobs/intake). workspace: " + str(workspace_root()), "success": True, "connected": True, "note": "direct (packaged)"}
                if "job list" in low or "job next" in low:
                    from ..jobs.job import list_jobs
                    items = list_jobs(include_examples=False)[:10]
                    txt = "\n".join([f"{j.name} [{j.estado}]" for j in items]) or "(no jobs)"
                    return {"cmd": orig, "stdout": txt, "success": True, "connected": True, "note": "direct (packaged)"}
                return {
                    "cmd": orig,
                    "stdout": "(packaged .exe: full CLI subprocess skipped; core hub features use pywebview bridge directly)",
                    "success": True,
                    "note": "use /api or JS api for parse/create/delegate. For full cmds use python install + flujo app",
                    "connected": True
                }
            except Exception as e:
                return {"error": f"direct dispatch: {e}", "cmd": orig}

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "flujo"] + args,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=45,
                encoding="utf-8",
                errors="replace"
            )
            return {
                "cmd": orig,
                "args": args,
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "returncode": proc.returncode,
                "success": proc.returncode == 0,
                "connected": True
            }
        except subprocess.TimeoutExpired:
            return {"error": "timeout", "cmd": orig}
        except Exception as e:
            return {"error": str(e), "cmd": orig}

    def _simple_parse(self, text: str) -> dict:
        """Fallback simple (used if real intake fails)."""
        low = text.lower()
        tipo = "desconocido"
        if "flyer" in low:
            tipo = "flyer"
        elif "etiqueta" in low:
            tipo = "etiqueta"
        elif "plano" in low or "stand" in low:
            tipo = "plano"
        return {
            "tipo": tipo,
            "voluntarios": 7,
            "medidas": "por definir",
            "sugerencia": "Usar formato existente o crear en projects/flujo/",
            "nota": "Fallback local (no backend)"
        }

    def log_message(self, format, *args):
        if os.environ.get("FLUJO_WEB_DEBUG"):
            super().log_message(format, *args)


class _HubDesktopApi:
    """Python-to-JS bridge exposed only in --desktop pywebview mode.
    Allows the frontend JS to call `window.pywebview.api.xxx(...)` directly (seamless, no http fetch latency).
    All ops remain local & safe. Falls back to /api/* if not in webview.
    """
    def __init__(self, root: Path, port: int):
        self.root = root
        self.port = port
        # Reuse handler logic without network for key methods
        self._handler = None

    def _ensure_handler(self):
        if self._handler is None:
            # instantiate without calling super fully
            h = HubRequestHandler.__new__(HubRequestHandler)
            h.root = self.root or (asset_root() if _is_packaged() else repo_root())
            h.context_path = context_dir()
            HubRequestHandler.ROOT = h.root
            HubRequestHandler.CONTEXT = h.context_path
            self._handler = h
        return self._handler

    def ping(self):
        return {"status": "ok", "workspace": "flujo", "via": "pywebview-js-api", "root": str(self.root), "connected": True}

    def load_brand(self):
        try:
            styles = load_styles()
            return {"brand": styles, "source": str(self.root / "projects" / "flujo" / "flujo.json"), "connected": True}
        except Exception as e:
            return {"error": str(e), "fallback": True}

    def list_svg_works(self):
        try:
            h = self._ensure_handler()
            return h._list_svg_works()
        except Exception as e:
            return {"groups": {}, "error": str(e)}

    def list_jobs(self):
        try:
            h = self._ensure_handler()
            return h._list_jobs_api()
        except Exception as e:
            return {"jobs": [], "error": str(e)}

    def parse_pedido(self, text: str):
        try:
            h = self._ensure_handler()
            return h._real_parse_pedido(text or "")
        except Exception as e:
            return {"error": str(e), "tipo": "desconocido"}

    def create_job_draft(self, text: str = "", name: str = ""):
        try:
            h = self._ensure_handler()
            return h._create_job_draft(text or "", name or "")
        except Exception as e:
            return {"error": str(e), "created": False}

    def run_command(self, cmd: str):
        try:
            h = self._ensure_handler()
            return h._run_safe_command(cmd or "")
        except Exception as e:
            return {"error": str(e), "cmd": cmd}

    def get_status(self):
        try:
            h = self._ensure_handler()
            return h._get_status()
        except Exception as e:
            return {"status": "ok", "error": str(e)}

    def get_connected(self):
        """Small indicator helper for JS: always report true when bridge present (desktop)."""
        return {"connected": True, "via": "pywebview", "backend": "real", "note": "flujo app --desktop"}

    def export_tokens(self):
        try:
            h = self._ensure_handler()
            return h._export_design_tokens()
        except Exception as e:
            return {"error": str(e)}


def _find_free_port(host: str = "127.0.0.1", start_port: int = 8765, max_tries: int = 8) -> int:
    """Auto port detection for robust launch (no 'address in use' errors)."""
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return start_port  # fallback (will error later for clear msg)


def run_server(host: str = "127.0.0.1", port: int = 8765, root: Path | None = None):
    """Start the HTTP server. root passed from CLI for explicit context.
    Uses auto-detected free port when default is busy.
    In packaged: assets from asset_root, workspace writes go next to exe.
    """
    if root is not None:
        HubRequestHandler.ROOT = root
        HubRequestHandler.CONTEXT = context_dir()
        try:
            # chdir to workspace in packaged so user files land nicely; asset for reads
            chdir_target = workspace_root() if _is_packaged() else root
            os.chdir(str(chdir_target))
        except Exception:
            pass
    else:
        HubRequestHandler.ROOT = asset_root()
        HubRequestHandler.CONTEXT = context_dir()
        try:
            os.chdir(str(workspace_root() if _is_packaged() else HubRequestHandler.ROOT))
        except Exception:
            pass

    r = HubRequestHandler.ROOT or asset_root()
    actual_port = port
    if port == 8765:
        # Auto-detect only on default to keep explicit --port working
        actual_port = _find_free_port(host, port)
        if actual_port != port:
            print(f"[flujo] Puerto {port} ocupado → usando {actual_port}")

    server = HTTPServer((host, actual_port), HubRequestHandler)
    print(f"[flujo] Workspace app en http://{host}:{actual_port}")
    print(f"  - Repo root: {r}")
    print("  - Hub:      /flujo_hub.html  (UI Delegar: input tarea + botones copian prompts completos por rol)")
    print("  - SVG Viz:  /svg_visualizer.html")
    print("  - Plano:    /plano_demo.html")
    print("  - APIs:     /api/ping /api/load-flujo-brand /api/list-svg-works /api/list-jobs /api/parse-real-pedido (POST) /api/run-safe-command /api/create-job-draft (POST) /api/delegate /api/export-tokens /api/events (SSE live) /manifest.json")
    print("  - CLI extra: `flujo delegate <role> \"tarea\"` (usa mismos templates formales)")
    print("  - Status:   connected when fetches succeed (graceful static fallback)")
    print("  - Tray:     disponible si pystray + pywebview instalados (ver --desktop)")
    server.serve_forever()


def launch(
    host: str = "127.0.0.1",
    port: int = 8765,
    desktop: bool = False,
    open_browser: bool = True,
    root: Path | None = None,
):
    """Launch server thread + optional desktop or browser.
    root: explicit repo root passed from CLI to give full context to backend.
    Auto-port detection + optional tray for polished daily desktop use on Windows.
    In desktop mode: also exposes direct Python bridge (pywebview.api) for seamless calls (parse, jobs, brand, commands) from JS.
    """
    if root is None:
        root = asset_root() if _is_packaged() else repo_root()
    # Auto port detection (robust for designer daily use; avoids bind errors)
    actual_port = port
    if port == 8765:
        actual_port = _find_free_port(host, port)
        if actual_port != port:
            print(f"[flujo] Auto-port detection: {port} ocupado → {actual_port}")
    # start server passing root for APIs to use absolute context (also used by static pages)
    thread = Thread(target=run_server, args=(host, actual_port, root), daemon=True)
    thread.start()

    url = f"http://{host}:{actual_port}/flujo_hub.html"

    print(f"[flujo] Starting with repo context: {root}")

    if desktop:
        try:
            import webview
            api = _HubDesktopApi(root=root, port=actual_port)
            icon_path = _get_temp_icon()  # free, best-effort from PIL
            kw = dict(
                js_api=api,
                width=1400,
                height=900,
                resizable=True,
                min_size=(1000, 700),
                text_select=True,
            )
            if icon_path:
                kw['icon'] = icon_path
            window = webview.create_window(
                "flujo • Workspace",
                url,
                **kw
            )
            # Pro desktop polish: ensure title stays, allow easy close without confirm for daily use
            try:
                window.title = "flujo • Workspace"
            except Exception:
                pass
            # Tray (free via pystray). Improves launch UX: keep in tray, quick access.
            _try_start_tray(window, url)
            webview.start()
            return
        except ImportError:
            print("[flujo] pywebview no instalado → usando navegador.")
            print("        pip install pywebview   (gratis, BSD)")
            print("        Opcional tray: pip install pystray pillow")

    if open_browser:
        time.sleep(0.7)
        webbrowser.open(url)
        print(f"[flujo] Abierto: {url}")
        print("        (Ctrl+C para cerrar)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[flujo] App detenida.")


def _get_temp_icon() -> str | None:
    """Generate a temp .png icon for the desktop window (pywebview supports icon=).
    Uses brand accent. Returns path or None (no file pollution on failure).
    Professional geometric F on dark rounded block (free Pillow draw).
    """
    try:
        from PIL import Image, ImageDraw
        import tempfile, os
        accent = (45, 90, 74, 255)
        img = Image.new('RGBA', (256, 256), (10, 10, 10, 255))
        draw = ImageDraw.Draw(img)
        # Pro rounded outer block (flujo accent)
        draw.rounded_rectangle([28, 28, 228, 228], radius=26, fill=accent)
        # Stylized F in dark (clean bars, no font dep)
        dark = (10, 10, 10, 255)
        draw.rectangle([66, 60, 92, 196], fill=dark)   # stem
        draw.rectangle([92, 60, 190, 86], fill=dark)   # top bar
        draw.rectangle([92, 114, 172, 140], fill=dark) # mid bar
        fd, path = tempfile.mkstemp(suffix='.png', prefix='flujo-icon-')
        os.close(fd)
        img.save(path, 'PNG')
        # best effort cleanup on exit not critical for desktop session
        return path
    except Exception:
        return None

def _try_start_tray(window, url: str) -> None:
    """Best-effort tray icon for desktop mode (free pystray + pillow).
    Non-blocking thread. Tray provides show/hide/quit for pro desktop feel.
    If deps missing: no-op (no hard requirement, keeps zero new paid deps).
    """
    try:
        from PIL import Image
        import pystray
        from pystray import Menu, MenuItem
    except Exception:
        return  # silent; designer can pip install if wants tray

    # Procedural 16x16 icon (dark pro + flujo accent #2d5a4a) - no files on disk
    try:
        accent = (45, 90, 74)  # #2d5a4a
        img = Image.new('RGB', (16, 16), color=(10, 10, 10))
        for x in range(3, 13):
            for y in range(3, 13):
                if (x + y) % 3 != 0:  # clean geometric F-like mark
                    img.putpixel((x, y), accent)
    except Exception:
        img = Image.new('RGB', (16, 16), (23, 63, 47))

    def on_open(icon, item):
        try:
            window.show()
        except Exception:
            webbrowser.open(url)

    def on_hide(icon, item):
        try:
            window.hide()
        except Exception:
            pass

    def on_quit(icon, item):
        icon.stop()
        try:
            window.destroy()
        except Exception:
            pass

    menu = Menu(
        MenuItem('Abrir flujo Hub', on_open),
        MenuItem('Ocultar ventana', on_hide),
        MenuItem('Salir', on_quit),
    )
    tray_icon = pystray.Icon('flujo', img, 'flujo • Workspace', menu)

    t = Thread(target=tray_icon.run, daemon=True)
    t.start()
    print("[flujo] Tray icon activado (derecho-click en systray).")


if __name__ == "__main__":
    launch()
