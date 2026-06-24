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
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
import time
import base64
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse, parse_qs, unquote

from ..paths import context_dir, repo_root, asset_root, workspace_root, is_packaged as _is_packaged, datadrops_dir

# analysis for datadrop metadata (colors + OCR via existing; privacy-safe local)
try:
    from ..analyze.colors import extract_palette
except Exception:
    extract_palette = None
try:
    from ..analyze.ocr import run_ocr, extract_hints_from_text
except Exception:
    run_ocr = None
    extract_hints_from_text = None
try:
    from PIL import Image
except Exception:
    Image = None

from ..brand import load_styles
from ..intake.email_parser import parse_email_content, parse_pedido_text  # real parsers
from ..intake.pipeline import _infer_type_and_size  # reuse heuristics if needed
from ..jobs.job import create_job, list_jobs  # real job creation / listing for hub API


def derive_visual_traits(ptype: str, palette: list, desc: str, hints: dict) -> str:
    traits = f"Pieza real terminada tipo {ptype}. "
    if palette:
        cols = [c.get("hex", "") for c in palette[:3] if isinstance(c, dict)]
        cols_str = ", ".join(cols)
        traits += f"Colores dominantes aprox: {cols_str}. "
    if desc:
        traits += f"Descripción: {desc[:120]}. "
    if hints:
        ks = list(hints.keys())[:3]
        traits += f"Hints extraídos (OCR): {ks}. "
    traits += "Patrón para IA: busca estos rasgos en briefs y generación para fidelidad a entregas reales."
    return traits


def build_for_future_ai(ptype: str, palette: list, desc: str, hints: dict, w: int, h: int) -> str:
    """Rich teaching note so future AI (esp. when reviewing for linea_editorial) knows exactly what to look for in real delivered work."""
    parts = []
    parts.append(f"EJEMPLO REAL ENTREGADO ({ptype}, dims {w}x{h}): foto subida por usuario de pieza ya impresa/terminada.")
    if palette:
        cols = [c.get("hex", "") for c in palette[:3] if isinstance(c, dict)]
        cols_str = ", ".join(cols)
        parts.append(f"Paleta dominante extraída (usar como referencia fiel): {cols_str}. En flyers/etiquetas reales rave/ONG: acentos de alto contraste sobre fondos oscuros suelen dominar.")
    if desc:
        parts.append(f"User notes reales: {desc[:150]}.")
    if hints:
        sample = str(list(hints.items())[:2])
        parts.append(f"OCR real reveló hints (fechas/mentions/textos): {sample}. Busca textos similares en briefs para matching.")
    parts.append("QUÉ BUSCAR LA IA: deriva layouts densos, proporciones exactas, contraste, densidad de iconos/texto de estas fotos + manifest. Valida vs linea_editorial (v4) en lugar de asumir. Esto es ground-truth de entregas, no specs teóricas. Úsalo para mejorar matching y evitar drift en generación.")
    return " ".join(parts)


def scan_incoming_datadrops(root_path = None) -> dict:
    from ..paths import datadrops_dir
    from pathlib import Path
    from datetime import datetime
    import json
    dd = datadrops_dir()
    incoming = dd / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    incoming_files = []
    for f in sorted(incoming.iterdir()):
        if f.is_file() and f.suffix.lower() in valid_exts:
            incoming_files.append(f)

    if not incoming_files:
        return {"ok": True, "processed": 0, "files": [], "ids": []}

    processed_count = 0
    processed_files = []
    processed_ids = []

    try:
        from PIL import Image
    except Exception:
        Image = None
    try:
        from ..analyze.colors import extract_palette
    except Exception:
        extract_palette = None
    try:
        from ..analyze.ocr import run_ocr, extract_hints_from_text
    except Exception:
        run_ocr = None
        extract_hints_from_text = None

    for i, img_file in enumerate(incoming_files):
        fname = img_file.name
        safe_name = "".join(c for c in fname if c.isalnum() or c in "._-") or "photo.jpg"
        if not any(safe_name.lower().endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
            safe_name += img_file.suffix.lower()

        desc = f"Foto real escaneada: {fname}"
        ptype = "flyer"
        if "etiqueta" in fname.lower() or "label" in fname.lower():
            ptype = "etiqueta"

        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        slug_src = fname.split(".")[0].replace(" ", "-").lower()
        slug_src = "".join(c for c in slug_src if c.isalnum() or c == "-") or "photo"

        # Unique directory
        drop_dir = dd / f"{ts}_{i}_{slug_src}"
        drop_dir.mkdir(parents=True, exist_ok=True)

        dest_path = drop_dir / safe_name
        try:
            img_bytes = img_file.read_bytes()
            dest_path.write_bytes(img_bytes)
            img_file.unlink()
        except Exception:
            continue

        w = h = 0
        palette = []
        ocr_text = ""
        hints = {}
        try:
            if Image:
                with Image.open(dest_path) as im:
                    w, h = im.size
            if extract_palette:
                pal = extract_palette(dest_path, n_colors=5)
                palette = pal.get("colors", [])
            if run_ocr:
                ocr_res = run_ocr(dest_path)
                if ocr_res.get("available"):
                    ocr_text = (ocr_res.get("text") or "")[:2000]
                    if extract_hints_from_text:
                        hints = extract_hints_from_text(ocr_text) or {}
        except Exception:
            pass

        traits = derive_visual_traits(ptype, palette, desc, hints)
        for_future_ai = build_for_future_ai(ptype, palette, desc, hints, w, h)

        manifest = {
            "id": drop_dir.name,
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
            "original_filename": fname,
            "image_path": f"datadrops/{drop_dir.name}/{safe_name}",
            "type": ptype,
            "dimensions": {"width": w, "height": h},
            "palette": palette,
            "ocr_text_snippet": ocr_text[:300] if ocr_text else "",
            "ocr_hints": hints,
            "description": desc,
            "linked_job": "",
            "visual_traits": traits,
            "tags": [ptype, "datadrop", "real-finished", "inverse-airdrop", "scanned"],
            "analysis_source": "local (src/flujo/analyze colors+ocr; no external)",
            "for_future_ai": for_future_ai,
        }

        (drop_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            (drop_dir / "analysis").mkdir(exist_ok=True)
            if palette:
                (drop_dir / "analysis" / "palette.json").write_text(json.dumps({"colors": palette}, indent=2, ensure_ascii=False), encoding="utf-8")
            if ocr_text:
                (drop_dir / "analysis" / "ocr.txt").write_text(ocr_text[:2000], encoding="utf-8")
        except Exception:
            pass

        processed_count += 1
        processed_files.append(fname)
        processed_ids.append(drop_dir.name)

    return {
        "ok": True,
        "processed": processed_count,
        "files": processed_files,
        "ids": processed_ids
    }



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

    def _resolve_under(self, base: Path, rel: str) -> Path | None:
        """Resolve a URL-relative path under base, rejecting traversal.

        The hub may be exposed on a LAN with `--host 0.0.0.0`; never allow
        `../`, absolute paths, backslash traversal or encoded traversal to read
        files outside the whitelisted static roots.
        """
        if base is None:
            return None
        try:
            decoded = unquote(rel or "").replace("\\", "/")
        except Exception:
            return None
        if "\x00" in decoded:
            return None
        decoded = decoded.lstrip("/")
        parts = [part for part in decoded.split("/") if part and part != "."]
        if any(part == ".." for part in parts):
            return None
        try:
            base_resolved = Path(base).resolve()
            candidate = (base_resolved / Path(*parts)).resolve()
            candidate.relative_to(base_resolved)
        except Exception:
            return None
        return candidate if candidate.is_file() else None

    def _resolve_static_file(self, rel: str) -> Path | None:
        """Resolve static assets from context first, then asset/repo root."""
        seen: set[str] = set()
        for base in (self.context_path, self.root):
            if not base:
                continue
            key = str(Path(base).resolve())
            if key in seen:
                continue
            seen.add(key)
            candidate = self._resolve_under(Path(base), rel)
            if candidate:
                return candidate
        return None

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

        # Datadrop (inverse airdrop) serving: user-uploaded finished work photos + manifests (from workspace/datadrops)
        # Works in both dev and packaged (workspace sibling writable)
        if path.startswith("/datadrops/"):
            try:
                dd = datadrops_dir()
                relp = path[len("/datadrops/"):]
                fpath = self._resolve_under(dd, relp)
                if fpath:
                    self._serve_file(fpath)
                    return
            except Exception:
                pass
            self.send_error(404)
            return

        # Servir archivos estáticos: context/ primero (hub + visualizers HTMLs), fallback a root/ (asset_root)
        # para assets bundled por `flujo package` (svg/, projects/flujo/ para brand json directo, etc).
        # Seguridad: no se permite traversal (`../`, encoded `%2e%2e`, ni rutas absolutas).
        rel = path.lstrip("/")
        file_path = self._resolve_static_file(rel)
        if file_path:
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

        # Datadrop (airdrop inverso): upload finished real photos of delivered work
        # POST json: {filename, b64: "data:image/jpeg;base64,....", description, piece_type, linked_job? }
        # Stores to workspace/datadrops/<date>_/ with image + rich manifest.json (palette, ocr, traits)
        # Privacy: analysis local only (colors+OCR optional). Suggest privacy scan for any text.
        if p == "/api/list-datadrops":
            try:
                result = self._list_datadrops()
                self._send_json(result)
            except Exception as e:
                self._send_json({"datadrops": [], "count": 0, "error": str(e)}, status=200)
            return

        if p == "/api/datadrop-upload":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = self._handle_datadrop_upload(data)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if p == "/api/datadrop-analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = self._handle_datadrop_analyze(data)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if p == "/api/datadrop-prepare-package":
            try:
                result = self._prepare_datadrop_review_package()
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if p == "/api/datadrop-scan-incoming":
            try:
                result = scan_incoming_datadrops(self.root)
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
        "flujo datadrop",
        "py -m flujo version", "py -m flujo health", "py -m flujo daily",
        "py -m flujo job list", "py -m flujo delegate", "py -m flujo datadrop",
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

    def _list_datadrops(self) -> dict:
        """List uploaded datadrops (real finished work photos) for hub viewer + future AI review."""
        dd = datadrops_dir()
        drops = []
        for d in sorted([p for p in dd.iterdir() if p.is_dir() if p.name != "incoming" and not p.name.startswith(".")], reverse=True):
            manifest = d / "manifest.json"
            if manifest.exists():
                try:
                    m = json.loads(manifest.read_text(encoding="utf-8"))
                    drops.append(m)
                except Exception:
                    drops.append({"id": d.name, "path": str(d), "note": "manifest parse error"})
            else:
                drops.append({"id": d.name, "path": str(d), "note": "no manifest (raw)"})

        # calculate pending_incoming
        incoming_dir = dd / "incoming"
        pending_incoming = 0
        if incoming_dir.exists() and incoming_dir.is_dir():
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            pending_incoming = sum(1 for f in incoming_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts)

        return {"datadrops": drops, "count": len(drops), "dir": str(dd), "pending_incoming": pending_incoming}

    def _handle_datadrop_upload(self, data: dict) -> dict:
        """Store photo of finished piece as datadrop (inverse airdrop).
        Creates datadrops/<YYYY-MM-DD_HHMMSS-slug>/ + image + manifest.json with analysis.
        """
        if not data.get("b64"):
            return {"error": "no image b64 provided (use JS FileReader base64)"}
        fname = (data.get("filename") or "photo.jpg").strip()
        safe_name = "".join(c for c in fname if c.isalnum() or c in "._-") or "photo.jpg"
        if not any(safe_name.lower().endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
            safe_name += ".jpg"
        desc = (data.get("description") or "").strip()[:500]
        ptype = (data.get("piece_type") or "flyer").strip()
        linked = data.get("linked_job") or ""
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        slug_src = (desc[:18] or safe_name.split(".")[0]).replace(" ", "-").lower()
        drop_dir = datadrops_dir() / f"{ts}_{slug_src}"
        drop_dir.mkdir(parents=True, exist_ok=True)
        # decode (data: prefix or raw)
        b64s = data["b64"]
        if "," in b64s:
            b64s = b64s.split(",", 1)[1]
        try:
            raw = base64.b64decode(b64s)
        except Exception as e:
            return {"error": f"bad base64: {e}"}
        img_path = drop_dir / safe_name
        img_path.write_bytes(raw)
        # extract metadata using existing analysis (local, privacy safe)
        w = h = 0
        palette = []
        ocr_text = ""
        hints = {}
        try:
            if Image and extract_palette:
                with BytesIO(raw) as bio:
                    im = Image.open(bio).convert("RGB")
                    w, h = im.size
                pal = extract_palette(img_path, n_colors=5)
                palette = pal.get("colors", [])
            if run_ocr:
                ocr_res = run_ocr(img_path)
                if ocr_res.get("available"):
                    ocr_text = (ocr_res.get("text") or "")[:2000]
                    if extract_hints_from_text:
                        hints = extract_hints_from_text(ocr_text) or {}
        except Exception:
            pass  # analysis best effort
        manifest = {
            "id": drop_dir.name,
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
            "original_filename": fname,
            "image_path": f"datadrops/{drop_dir.name}/{safe_name}",
            "type": ptype,
            "dimensions": {"width": w, "height": h},
            "palette": palette,
            "ocr_text_snippet": ocr_text[:300] if ocr_text else "",
            "ocr_hints": hints,
            "description": desc or "Foto real de pieza terminada (datadrop).",
            "linked_job": linked,
            "visual_traits": self._derive_visual_traits(ptype, palette, desc, hints),
            "tags": [ptype, "datadrop", "real-finished", "inverse-airdrop"],
            "analysis_source": "local (src/flujo/analyze colors+ocr; no external)",
            "for_future_ai": self._build_for_future_ai(ptype, palette, desc, hints, w, h),
        }
        (drop_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            (drop_dir / "analysis").mkdir(exist_ok=True)
            if palette:
                (drop_dir / "analysis" / "palette.json").write_text(json.dumps({"colors": palette}, indent=2, ensure_ascii=False), encoding="utf-8")
            if ocr_text:
                (drop_dir / "analysis" / "ocr.txt").write_text(ocr_text[:2000], encoding="utf-8")
        except Exception:
            pass
        return {"ok": True, "id": drop_dir.name, "path": str(drop_dir), "manifest": manifest, "note": "Datadrop almacenado. Listo para revisión por IA futura."}

    def _handle_datadrop_analyze(self, data: dict) -> dict:
        did = data.get("id")
        if not did:
            return {"error": "id required"}
        ddir = datadrops_dir() / did
        if not ddir.exists():
            return {"error": "datadrop not found"}
        img = None
        for c in list(ddir.glob("*.jpg")) + list(ddir.glob("*.jpeg")) + list(ddir.glob("*.png")):
            img = c
            break
        if not img:
            return {"error": "no image in datadrop"}
        try:
            pal = extract_palette(img, n_colors=5) if extract_palette else {}
            ocr_res = run_ocr(img) if run_ocr else {}
            mpath = ddir / "manifest.json"
            m = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
            m["palette"] = pal.get("colors", m.get("palette", [])) if pal else m.get("palette", [])
            if ocr_res.get("available"):
                m["ocr_text_snippet"] = (ocr_res.get("text") or "")[:300]
                if extract_hints_from_text:
                    m["ocr_hints"] = extract_hints_from_text(m["ocr_text_snippet"]) or {}
            m["reanalyzed_at"] = datetime.now().isoformat(timespec="seconds")
            # refresh teaching note with fresh data
            try:
                pw = m.get("dimensions", {}).get("width", 0)
                ph = m.get("dimensions", {}).get("height", 0)
                m["for_future_ai"] = self._build_for_future_ai(m.get("type","flyer"), m.get("palette",[]), m.get("description",""), m.get("ocr_hints",{}), pw, ph)
            except Exception:
                pass
            mpath.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"ok": True, "id": did, "manifest": m}
        except Exception as e:
            return {"error": str(e)}

    def _prepare_datadrop_review_package(self) -> dict:
        """Generate persistent review package (inverse airdrop) so other AI (linea_editorial improver etc) can read what real finished work looks like.
        Writes datadrops/_review_package.txt (and returns summary). Use manifests + photos to know 'qué buscar'.
        """
        dd = datadrops_dir()
        listed = self._list_datadrops()
        items = listed.get("datadrops", [])
        instructions = (
            "DATADROP REVIEW PACKAGE — Inverse airdrop for future AI review.\n"
            "Fuente: fotos reales de flyers/etiquetas/etc ya entregados por usuario.\n"
            "Usa: cada manifest.json (palette, ocr_hints, visual_traits, for_future_ai) + imagen real (datadrops/<id>/img).\n"
            "Objetivo: 'sabrá qué buscar' en briefs/análisis — patrones de paletas reales, contraste, densidad de layouts, textos que aparecen en entregas.\n"
            "Ej: si datadrops muestran magenta alto contraste en flyers rave oscuros + icon grids densos → valida que linea_editorial + generación lo use.\n"
            "Privacidad: local only. Coordina Brand Guardian / linea. Copia o cat este archivo + manifests cuando te unas a linea task.\n"
            "Generado via hub (`flujo app`) o CLI `py -m flujo datadrop prepare`.\n\n"
        )
        summary_lines = []
        for it in items:
            summary_lines.append(f"ID: {it.get('id')}\nType: {it.get('type')}\nDesc: {it.get('description','')}\nTraits: {(it.get('visual_traits') or '')[:200]}\nForAI: {(it.get('for_future_ai') or '')[:300]}\nPalette: {str((it.get('palette') or [])[:2])}\n---")
        pkg_text = instructions + "\n".join(summary_lines) + f"\n\nTotal: {len(items)} datadrops. Dir: {listed.get('dir')}\nRevisa imágenes directamente desde el hub o FS para ground truth visual."
        pkg_path = dd / "_review_package.txt"
        try:
            pkg_path.write_text(pkg_text, encoding="utf-8")
        except Exception:
            pass
        return {
            "ok": True,
            "package_file": str(pkg_path),
            "count": len(items),
            "summary": [ {"id": it.get("id"), "type": it.get("type"), "traits": (it.get("visual_traits") or "")[:80]} for it in items ],
            "note": "Review package escrito. Léelo para saber patrones reales de entregas terminadas."
        }

    def _derive_visual_traits(self, ptype: str, palette: list, desc: str, hints: dict) -> str:
        return derive_visual_traits(ptype, palette, desc, hints)

    def _build_for_future_ai(self, ptype: str, palette: list, desc: str, hints: dict, w: int, h: int) -> str:
        return build_for_future_ai(ptype, palette, desc, hints, w, h)

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

    # Datadrop (inverse airdrop) bridge for desktop pywebview
    def list_datadrops(self):
        try:
            h = self._ensure_handler()
            return h._list_datadrops()
        except Exception as e:
            return {"datadrops": [], "error": str(e)}

    def datadrop_upload(self, data: dict = None):
        try:
            h = self._ensure_handler()
            return h._handle_datadrop_upload(data or {})
        except Exception as e:
            return {"error": str(e)}

    def datadrop_analyze(self, data: dict = None):
        try:
            h = self._ensure_handler()
            return h._handle_datadrop_analyze(data or {})
        except Exception as e:
            return {"error": str(e)}

    def datadrop_prepare_package(self):
        try:
            h = self._ensure_handler()
            return h._prepare_datadrop_review_package()
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

    server = ThreadingHTTPServer((host, actual_port), HubRequestHandler)
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
