#!/usr/bin/env python3
"""Interfaz web local para flujo con Gradio.

Uso:
  py scripts/app.py

Abre http://localhost:7860
"""
import subprocess
import sys
from pathlib import Path

import gradio as gr

from _common import repo_root

ROOT = repo_root()
PY = sys.executable

def run(cmd):
    try:
        result = subprocess.run(
            cmd, cwd=ROOT, text=True, capture_output=True, timeout=120, check=True
        )
        return result.stdout or "OK"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.returncode}\n{e.stdout}\n{e.stderr}"
    except Exception as e:
        return f"ERROR: {e}"

def nuevo_pedido(nombre, correo):
    if not nombre or not correo:
        return "Faltan nombre o correo."
    path = ROOT / "inbox" / f"pedido_{nombre.replace(' ', '_').lower()}.txt"
    path.write_text(correo, encoding="utf-8")
    return run([PY, "scripts/flujo_pipeline.py", nombre, str(path), "--confirm"])

def nuevo_flyer(correo):
    if not correo:
        return "Falta el correo con links."
    path = ROOT / "inbox" / "flyer_links.txt"
    path.write_text(correo, encoding="utf-8")
    return run([PY, "scripts/flyer_from_email.py", str(path)])

def generar_pieza(config_path):
    if not config_path:
        return "Selecciona un config.json."
    return run([PY, "scripts/piezas_generar.py", config_path])

def actualizar_dashboard():
    return run([PY, "scripts/flujo_daily.py"])

def health_check():
    return run([PY, "scripts/flujo_health.py"])

def limpiar():
    return run(["bash", "scripts/limpiar_basura.sh"])

def listar_configs():
    configs = sorted((ROOT / "projects" / "piezas_vectoriales").glob("*/config.json"))
    return [str(c) for c in configs]

CSS = """
/* =====================================================================
   BRAND ENFORCED — legacy Gradio (scripts/app.py) — from projects/flujo/flujo.json
   =====================================================================
   Dark pro ONLY. EXACT colors: ink #1f2a24, accent #2d5a4a, paper #f8f1e3 (print), support #675f55, alert #c2410f.
   No neon/cyan/magenta/hacker/light outside paper. ALL UIs must pass Brand Validator in hub.
   Legacy Gradio: marked; main pro experience = context/ HTMLs via `flujo app`.
   Primary accent #2d5a4a. Generous pro spacing implicit via radius/panels.
*/
:root { --bg: #0a0a0a; --panel: #141414; --panel2: #1a1a1a; --border: #2a2a2a; --text: #e8e8e8; --muted: #888; --accent: #2d5a4a; --flujo-ink: #1f2a24; --flujo-accent: #2d5a4a; --flujo-paper: #f8f1e3; --flujo-support: #675f55; --flujo-alert: #c2410f; }
body { background-color: var(--bg) !important; color: var(--text) !important; font-family: 'Inter', system-ui, sans-serif !important; }
.gradio-container { background-color: var(--bg) !important; color: var(--text) !important; }
.tabs { background-color: var(--panel) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
.tab-nav { background-color: #0d0d0d !important; border-bottom: 1px solid var(--border) !important; }
.tab-nav button { color: var(--muted) !important; font-weight: 500 !important; letter-spacing: 0.05em; text-transform: uppercase; font-size: 0.75rem; }
.tab-nav button.selected { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }
button.primary { background: linear-gradient(135deg, var(--accent), #1a3f2e) !important; color: #fff !important; border: none !important; border-radius: 5px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.05em; }
button.secondary { background-color: var(--panel) !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 5px !important; }
input, textarea, .textbox, .dropdown { background-color: var(--panel2) !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 5px !important; }
input:focus, textarea:focus { border-color: var(--accent) !important; outline: none !important; }
h1, h2, h3 { color: #fff !important; font-weight: 700 !important; letter-spacing: -0.02em; }
.block { background-color: var(--panel) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
"""

def build():
    with gr.Blocks(theme=gr.themes.Base()) as demo:
        gr.HTML(f"<style>{CSS}</style>")
        gr.Markdown("# FLUJO // Dimensiones del Orden")
        gr.Markdown("**LEGACY Gradio** — main pro workspace = `flujo app` → context/flujo_hub.html (brand enforced dark from projects/flujo/flujo.json). Este es fallback.")

        with gr.Tab("DASHBOARD"):
            gr.Markdown("## Estado actual")
            btn_daily = gr.Button("Generar / Actualizar", variant="primary")
            out_daily = gr.Textbox(label="Resultado", lines=8)
            btn_daily.click(actualizar_dashboard, outputs=out_daily)

            gr.Markdown("### Abrir dashboard en navegador")
            gr.Button("Abrir dashboard.html", variant="secondary").click(
                lambda: run(["bash", "scripts/abrir_dashboard.sh"]), outputs=out_daily
            )

        with gr.Tab("NUEVO PEDIDO"):
            gr.Markdown("## Crear job desde correo")
            nombre = gr.Textbox(label="Nombre del pedido", placeholder="etiquetas suplemento")
            correo = gr.Textbox(label="Texto del correo", lines=8, placeholder="Pega aquí el correo del pedido...")
            btn = gr.Button("Crear job + proyecto", variant="primary")
            out = gr.Textbox(label="Resultado", lines=12)
            btn.click(nuevo_pedido, inputs=[nombre, correo], outputs=out)

        with gr.Tab("NUEVO FLYER"):
            gr.Markdown("## Crear flyers desde links de Instagram")
            links = gr.Textbox(label="Correo con links de Instagram", lines=8, placeholder="Pega links de Instagram...")
            btn = gr.Button("Crear flyers", variant="primary")
            out = gr.Textbox(label="Resultado", lines=12)
            btn.click(nuevo_flyer, inputs=links, outputs=out)

        with gr.Tab("GENERAR PIEZA"):
            gr.Markdown("## Generar SVGs desde config.json")
            configs = listar_configs()
            config = gr.Dropdown(label="Config", choices=configs, value=configs[0] if configs else None)
            btn = gr.Button("Generar", variant="primary")
            out = gr.Textbox(label="Resultado", lines=12)
            btn.click(generar_pieza, inputs=config, outputs=out)
            gr.Button("Refrescar lista", variant="secondary").click(
                lambda: gr.Dropdown(choices=listar_configs()), outputs=config
            )

        with gr.Tab("MANTENIMIENTO"):
            gr.Markdown("## Health check y limpieza")
            btn_health = gr.Button("Health check", variant="secondary")
            out_health = gr.Textbox(label="Resultado", lines=12)
            btn_health.click(health_check, outputs=out_health)

            btn_clean = gr.Button("Limpiar basura", variant="secondary")
            out_clean = gr.Textbox(label="Resultado", lines=8)
            btn_clean.click(limpiar, outputs=out_clean)

    return demo

if __name__ == "__main__":
    demo = build()
    demo.launch(
        server_name="0.0.0.0",
        share=False,
        show_error=True,
        css=CSS
    )
