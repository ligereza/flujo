"""Quotations for an RD event, in two audiences.

- `productora`: the external document a venue or promoter receives.
- `interno`: the detailed breakdown for the NGO / worker / company.

Both read their money from the same place as the rider: the service-pack tariff
in `data/rd_packs.json`, through `flujo.plano.resumen_costos`. No price is
written here.

**The palette is a starting point, never a rule** (user's words, 2026-07-26:
"como info sirve, como limitante o restriccion no"). Colours resolve in this
order, first one wins:

    1. the `estilo` argument passed by the caller
    2. an `estilo` block inside the event's own JSON
    3. the palette in `projects/flujo/flujo.json`

So a piece can be made in a different aesthetic, or the flyers can change,
without touching this file. Before 2026-07-26 the colours were read straight
from the palette with no way to override them, and the external document also
printed the hex codes and the words "Usa flujo para consistencia de marca" --
internal jargon inside a document that goes to a client.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from flujo.plano import load_evento, resumen_costos
from flujo.brand import load_styles

# Only these keys are read from a palette; anything else in the file is ignored.
_CLAVES_COLOR = ("ink", "accent", "paper")


def resolver_estilo(ev: Dict[str, Any], estilo: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Resolve the colours for one quotation: caller > event > palette default."""
    colores = {k: v for k, v in load_styles().items() if k in _CLAVES_COLOR}
    for fuente in (ev.get("estilo"), estilo):
        if isinstance(fuente, dict):
            colores.update({k: str(v) for k, v in fuente.items() if k in _CLAVES_COLOR and v})
    return colores


def generar_cotizacion(
    evento_path: Path,
    audiencia: str = "productora",
    output_dir: Path | None = None,
    estilo: Optional[Dict[str, str]] = None,
) -> dict:
    """Write the quotation files for one event and return their paths."""
    ev = load_evento(evento_path)
    costos = resumen_costos(ev)
    nombre = ev.get("nombre", "Evento")

    if output_dir is None:
        output_dir = Path("exports") / f"cotizacion_{str(nombre).lower().replace(' ', '_')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if audiencia != "productora":
        # Internal breakdown. It used to end with "Notas internas: ajustar
        # precios reales", which stopped being true once the tariff became a
        # real, editable file: the figures below ARE the rates in use.
        contenido = f"""COTIZACIÓN INTERNA — {nombre}
Para: equipo Reduciendo Daño

{costos}

Tarifa vigente: data/rd_packs.json (misma fuente que el rider).
"""
        destino = output_dir / "cotizacion_interno.txt"
        destino.write_text(contenido, encoding="utf-8")
        return {"files": [str(destino)], "audiencia": "interno"}

    colores = resolver_estilo(ev, estilo)
    ink = colores.get("ink", "#1f2a24")
    accent = colores.get("accent", "#2d5a4a")
    paper = colores.get("paper", "#f8f1e3")

    # `costos` already opens with "COTIZACION -- <nombre>", so neither the text
    # nor the HTML repeats it: the document used to print the same title twice.
    texto = f"""Reduciendo Daño

{costos}

{ev.get('notas', '')}
"""
    (output_dir / "cotizacion_productora.txt").write_text(texto, encoding="utf-8")

    html = f"""<!doctype html>
<html lang="es"><meta charset="utf-8">
<title>Cotización — {nombre}</title>
<body style="background:{paper};color:{ink};font-family:system-ui,sans-serif;margin:0;padding:2.5rem">
<h1 style="color:{accent};margin:0 0 2rem">Reduciendo Daño</h1>
<pre style="font-size:1rem;line-height:1.6;white-space:pre-wrap">{costos}</pre>
<p style="margin-top:2rem">{ev.get('notas', '')}</p>
</body></html>"""
    (output_dir / "cotizacion_productora.html").write_text(html, encoding="utf-8")

    return {
        "files": [
            str(output_dir / "cotizacion_productora.txt"),
            str(output_dir / "cotizacion_productora.html"),
        ],
        "audiencia": "productora",
        "colores": colores,
    }


if __name__ == "__main__":
    print(generar_cotizacion(Path("projects/plano/ejemplos/evento_ejemplo.json"), "productora"))
