"""Render del reporte en markdown y HTML."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from .scoring import ItemScore, Priority


PRIORITY_LABELS = {Priority.ALTA: "alta", Priority.MEDIA: "media", Priority.BAJA: "baja"}
PRIORITY_COLORS = {
    Priority.ALTA: "#ff4d4d",
    Priority.MEDIA: "#ffaa00",
    Priority.BAJA: "#4d94ff",
}


def render_markdown(items: List[ItemScore]) -> str:
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: List[str] = [
        f"# Daily report — {date}",
        "",
        "Resumen de próximas acciones ordenadas por prioridad.",
        "",
        f"- Total items: {len(items)}",
        f"- Alta: {sum(1 for i in items if i.priority == Priority.ALTA)}",
        f"- Media: {sum(1 for i in items if i.priority == Priority.MEDIA)}",
        f"- Baja: {sum(1 for i in items if i.priority == Priority.BAJA)}",
        "",
    ]
    if not items:
        lines.append("No hay items pendientes. 🎉")
        return "\n".join(lines)

    current = None
    lines.append("## Acciones prioritarias")
    lines.append("")
    for item in items:
        if item.priority != current:
            current = item.priority
            lines.append(f"### Prioridad {PRIORITY_LABELS[current]}")
            lines.append("")
        lines.append(f"- **[{item.type}]** `{item.name}` — {item.reason} (score: {item.score})")
        # extras
        if item.type == "job":
            pc = item.extra.get("pendientes_count", 0)
            if pc:
                lines.append(f"  - {pc} pendientes en brief.yaml")
        lines.append(f"  - Ruta: `{item.path}`")
        lines.append("")

    lines.extend([
        "## Comandos rápidos",
        "",
        "```bash",
        "flujo health",
        "flujo job-list",
        "flujo daily",
        "```",
    ])
    return "\n".join(lines)


def render_html(items: List[ItemScore]) -> str:
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    groups = {p: [i for i in items if i.priority == p] for p in Priority}

    def card(item: ItemScore) -> str:
        color = PRIORITY_COLORS[item.priority]
        extra_html = ""
        if item.type == "job":
            pc = item.extra.get("pendientes_count", 0)
            if pc:
                extra_html = f"<p class='muted'>{pc} pendientes</p>"
        return f"""
        <article class='card' style='border-left-color:{color}'>
          <span class='badge' style='background:{color}'>{item.priority.value.upper()}</span>
          <h3>{item.type.upper()} — {item.name}</h3>
          <p>{item.reason}</p>
          {extra_html}
          <code>{item.path}</code>
        </article>
        """

    sections = []
    for label, group in [("Alta", groups[Priority.ALTA]), ("Media", groups[Priority.MEDIA]), ("Baja", groups[Priority.BAJA])]:
        if not group:
            continue
        cards = "".join(card(i) for i in group)
        sections.append(f"<section><h2>Prioridad {label}</h2><div class='grid'>{cards}</div></section>")

    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Flujo Dashboard</title>
<style>
:root{{--bg:#f6efe3;--card:#fff8ed;--ink:#161513;--muted:#675f55}}
body{{margin:0;font-family:system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}}
header{{background:var(--ink);color:#fff;padding:24px 32px}}
header h1{{margin:0;font-size:1.8rem}}
header p{{margin:6px 0 0;opacity:.8}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:24px}}
.stat{{background:var(--card);padding:16px 20px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.08)}}
.stat b{{display:block;font-size:2rem}}
section h2{{margin:24px 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
.card{{background:var(--card);padding:18px;border-radius:18px;box-shadow:0 6px 20px rgba(0,0,0,.1);border-left:6px solid #ccc}}
.badge{{color:#fff;padding:4px 10px;border-radius:999px;font-size:.75rem;font-weight:700}}
.card h3{{margin:10px 0 6px;font-size:1.1rem}}
.card p{{margin:0;color:var(--muted)}}
.card code{{display:block;margin-top:10px;font-size:.8rem;word-break:break-all;background:#eee;padding:6px 8px;border-radius:6px}}
.muted{{color:var(--muted);font-size:.9rem}}
</style></head><body>
<header><h1>Flujo — Dashboard</h1><p>Actualizado: {date}</p></header>
<main>
<div class='stats'>
  <div class='stat'><b>{len(items)}</b>Total items</div>
  <div class='stat'><b style='color:#ff4d4d'>{len(groups[Priority.ALTA])}</b>Alta</div>
  <div class='stat'><b style='color:#ffaa00'>{len(groups[Priority.MEDIA])}</b>Media</div>
  <div class='stat'><b style='color:#4d94ff'>{len(groups[Priority.BAJA])}</b>Baja</div>
</div>
{''.join(sections)}
</main></body></html>"""
