"""Genera docs/rd/presentacion_db.html -- presentacion formal (web) de la DB
de productoras RD para la directiva de la ONG.

Autocontenido: cero CDN, cero PDF/imagen, DB embebida como JSON, render por
JS puro. Linea editorial v4.1 sistema RAVE (dark/neon), logo RD vectorial
inline real (nunca regenerado con IA).

Fuente de datos: data/productoras/*.json (la unica fuente de verdad
editable a mano por el usuario). No se embebe la salida cruda de
triangulacion (ruidosa, no committeada) -- solo lo que ya paso a los json
de productora.

Uso:
    py tools/gen_presentacion_db.py --out docs/rd/presentacion_db.html
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import mimetypes
from pathlib import Path

LOGO_VARIANT = "blanco"  # fondo oscuro -> logo blanco (regla dura taller-svg-rd)


def inline_logo(svg_path: Path) -> str:
    raw = svg_path.read_text(encoding="utf-8")
    return raw[raw.index("<svg"):]


def _data_uri(path_str: str | None) -> str | None:
    """Convierte un archivo de logo (svg/png/jpg) a data-uri autocontenido.

    Devuelve None si el path no viene, no existe, o es un tipo no soportado --
    nunca se fabrica un logo, solo se embebe el archivo real ya descargado
    (PR #254, knowledge/logos/{vector,descargas}).
    """
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        return None
    mime, _ = mimetypes.guess_type(path.name)
    if not mime or not mime.startswith("image/"):
        return None
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def build_db(productoras_dir: Path) -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(productoras_dir / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        slug = Path(f).stem
        logos = d.get("logos", [])
        logo_estado = logos[0]["estado"] if logos else "sin_dato"
        # Preferir vector (archivo, svg) sobre raster para la miniatura.
        logo0 = logos[0] if logos else {}
        logo_img = _data_uri(logo0.get("archivo")) or _data_uri(logo0.get("raster"))
        out.append({
            "slug": slug,
            "nombre": d.get("name", slug),
            "tipo": d.get("tipo", "productora"),
            "aliases": d.get("aliases", []),
            "instagram": d.get("instagram", ""),
            "tipos_fecha": d.get("tipos_fecha", []),
            "logo_estado": logo_estado,
            "logo_img": logo_img,
            "logo_fuente": logo0.get("fuente", ""),
            "venues": [v.get("nombre") for v in d.get("venues", []) if v.get("nombre")],
            "eventos": d.get("eventos", []),
            "relaciones": d.get("relaciones", []),
            "confirmed": d.get("confirmed", ""),
            "fuente_datos": d.get("fuente_datos", ""),
        })
    return out


PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reduciendo Daño — DB de Productoras RD</title>
<style>
:root{
  --bg:#0A0A0A; --panel:#161318; --ink:#F2F2F2; --muted:#9c98a3;
  --magenta:#C800C8; --amarillo:#FFD21F; --linea:#2a2530;
}
*{box-sizing:border-box;}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family: Arial, Helvetica, sans-serif; line-height:1.5;
}
header.hero{
  padding:3rem 1.5rem 2rem; text-align:center; position:relative;
  border-bottom:1px solid var(--linea);
}
header.hero .logo{ width:110px; height:auto; margin:0 auto 1rem; display:block; }
header.hero h1{
  font-size:1.6rem; letter-spacing:.04em; text-transform:uppercase;
  color:var(--amarillo); text-shadow:0 0 18px rgba(255,210,31,.35);
  margin:.2rem 0;
}
header.hero p{ color:var(--muted); max-width:640px; margin:.6rem auto 0; font-size:.92rem; }
main{ max-width:1180px; margin:0 auto; padding:2rem 1.25rem 4rem; }
section{ margin-top:2.5rem; }
h2{
  font-size:1.05rem; text-transform:uppercase; letter-spacing:.06em;
  color:var(--amarillo); border-left:3px solid var(--magenta); padding-left:.6rem;
  margin-bottom:1rem;
}
.controls{ display:flex; flex-wrap:wrap; gap:.6rem; margin-bottom:1.2rem; }
.controls input, .controls select{
  background:var(--panel); color:var(--ink); border:1px solid var(--linea);
  border-radius:6px; padding:.5rem .7rem; font-size:.85rem;
}
.controls input{ flex:1; min-width:180px; }
.grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(270px,1fr)); gap:1rem; }
.card{
  background:var(--panel); border-radius:10px; padding:1.1rem;
  position:relative; overflow:hidden;
}
.card::before, .card::after{
  content:""; position:absolute; inset:0; border-radius:10px; pointer-events:none;
}
.card::before{ box-shadow:inset 0 0 0 1.5px rgba(200,0,200,.16); }
.card::after{ box-shadow:inset 0 0 0 1px rgba(200,0,200,.55); }
.card h3{ margin:.1rem 0 .3rem; font-size:1.05rem; color:var(--ink); }
.logo-thumb{
  width:64px; height:64px; object-fit:contain; background:#fff; border-radius:6px;
  padding:.3rem; margin-bottom:.5rem; display:block;
}
.tipo-pill{
  display:inline-block; font-size:.68rem; text-transform:uppercase; letter-spacing:.04em;
  padding:.15rem .5rem; border-radius:12px; background:#241f29; color:var(--muted);
  margin-bottom:.5rem;
}
.tipo-pill.spot{ background:#2a1f10; color:var(--amarillo); }
.row{ font-size:.8rem; color:var(--muted); margin:.2rem 0; }
.row b{ color:var(--ink); font-weight:600; }
.badge{
  display:inline-block; font-size:.68rem; padding:.12rem .45rem; border-radius:4px;
  margin:.15rem .25rem .15rem 0;
}
.badge.pendiente{ background:#3a1414; color:#ff9d9d; }
.badge.ok{ background:#123a1e; color:#7ee787; }
.badge.needs{ background:#3a2e10; color:var(--amarillo); }
.evento{ margin-top:.5rem; padding:.5rem .6rem; background:#0f0d12; border-radius:6px; font-size:.78rem; }
.evento b{ color:var(--ink); }
.evento .fuente{ display:block; color:var(--muted); margin-top:.2rem; font-style:italic; }
.rel-list{ font-size:.75rem; color:var(--muted); margin-top:.4rem; }
.empty{ color:var(--muted); font-size:.85rem; padding:1rem; }
.metodologia, .disclaimer{
  background:var(--panel); border-radius:10px; padding:1.2rem 1.4rem; font-size:.88rem; color:var(--muted);
}
.metodologia b, .disclaimer b{ color:var(--ink); }
.metodologia ul{ margin:.5rem 0 0 1.1rem; padding:0; }
.metodologia li{ margin:.3rem 0; }
.stat-row{ display:flex; gap:1.2rem; flex-wrap:wrap; margin-bottom:1rem; }
.stat{ background:var(--panel); border-radius:8px; padding:.8rem 1.1rem; min-width:130px; }
.stat .n{ font-size:1.5rem; color:var(--amarillo); font-weight:700; }
.stat .l{ font-size:.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
footer{ text-align:center; padding:2rem 1rem; color:var(--muted); font-size:.75rem; border-top:1px solid var(--linea); }
footer .logo{ width:52px; height:auto; margin:0 auto .6rem; display:block; opacity:.8; }
a{ color:var(--amarillo); }
@media (prefers-color-scheme: light){
  /* La pieza es RAVE/oscura por linea editorial -- se mantiene fija, no responde a tema del sistema. */
}
</style>
</head>
<body>
<header class="hero">
  __LOGO__
  <h1>DB de Productoras -- Reduciendo Daño</h1>
  <p>Presentación formal para la directiva. Base de datos de productoras, spots y eventos
  del ecosistema electrónico chileno con el que RD trabaja, construida a partir de
  curatoría de material propio y confirmación directa del equipo. Documento HTML
  autónomo, pensado para integrarse después a reduciendodano.cl.</p>
</header>

<main>

<section id="resumen">
  <h2>Resumen</h2>
  <div class="stat-row" id="stats"></div>
</section>

<section id="productoras">
  <h2>Productoras y spots</h2>
  <div class="controls">
    <input id="buscar" type="text" placeholder="Buscar por nombre, alias o venue...">
    <select id="filtroTipo"><option value="">Todos los tipos</option></select>
    <select id="filtroLogo">
      <option value="">Logo: cualquier estado</option>
      <option value="ok">Logo conseguido</option>
      <option value="pendiente">Logo pendiente</option>
    </select>
  </div>
  <div class="grid" id="grid"></div>
</section>

<section id="metodologia">
  <h2>Metodología</h2>
  <div class="metodologia">
    <p><b>Curatoría de base:</b> 1731 fichas curadas manualmente (obras del archivo
    RD) sirvieron para armar la primera pasada de la DB (identidad, venues, eventos
    con fecha confirmada por revisión humana).</p>
    <p><b>Triangulación automática:</b> sobre un corpus ampliado de 2440 fichas
    (OCR + descripción por visión de cada imagen), una herramienta propia
    (<code>tools/triangular_fichas.py</code>) cruza productora/venue/fecha/lineup por
    ficha y agrupa las que corresponden al mismo evento (misma fecha ±1 día,
    mismo venue o mismo lineup). De 821 fichas con alguna señal utilizable salieron
    101 agrupaciones candidatas y 348 nombres de productora candidatos.</p>
    <p><b>Curación final:</b> solo lo verificado (confirmado por el equipo o con
    evidencia clara y no ambigua) pasa a <code>data/productoras/*.json</code>, que es
    la única fuente que alimenta esta página. La salida cruda de la
    triangulación queda como cola de trabajo interna, no se expone acá tal cual
    porque incluye ruido de OCR (texto girado, imágenes de producto RD mezcladas con
    flyers) y agrupaciones que a veces fusionan varias ediciones reales de una misma
    serie.</p>
    <ul>
      <li>Ningún dato se inventa: lo no confirmado queda marcado
      <span class="badge needs">needs_confirmation</span> o
      <span class="badge pendiente">PENDIENTE</span>.</li>
      <li>Los logos se buscan siempre en la fuente oficial (perfil de Instagram o sitio
      web de la productora) -- nunca se recortan de un flyer.</li>
    </ul>
  </div>
</section>

<section id="disclaimer">
  <h2>Nota de infraestructura</h2>
  <div class="disclaimer">
    <p>Esta herramienta y la base de datos que presenta se construyen sobre
    <b>infraestructura pro-bono</b>: procesamiento y curatoría corren en
    equipos donados/aportados al proyecto, sin costo para Reduciendo Daño.
    El objetivo de diseño es que, una vez la ONG lo decida, este mismo archivo
    HTML se pueda incrustar tal cual en <a href="https://reduciendodano.cl" target="_blank" rel="noopener">reduciendodano.cl</a>
    sin dependencias externas ni servidores adicionales.</p>
  </div>
</section>

</main>

<footer>
  __LOGO_FOOT__
  <div>Reduciendo Daño -- documento generado por <code>tools/gen_presentacion_db.py</code>. Datos: data/productoras/*.json.</div>
</footer>

<script>
const DB = __DATA_JSON__;

function estadoLogo(estado){
  const okStates = ["source_needed", "candidato_sin_copiar", "candidato_sin_confirmar"];
  if (!estado || estado === "sin_dato" || estado === "no_encontrado" || estado === "PENDIENTE") return "pendiente";
  if (okStates.includes(estado)) return "needs";
  return "ok";
}

function render(list){
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  if (!list.length){
    grid.innerHTML = '<div class="empty">Sin resultados para el filtro actual.</div>';
    return;
  }
  for (const p of list){
    const card = document.createElement("div");
    card.className = "card";
    const cls = estadoLogo(p.logo_estado);
    const tipoCls = p.tipo === "spot" ? "spot" : "";
    let html = "";
    if (p.logo_img){
      html += `<img class="logo-thumb" src="${p.logo_img}" alt="Logo ${p.nombre}" title="Fuente: ${p.logo_fuente || 'sin registrar'}">`;
    }
    html += `<span class="tipo-pill ${tipoCls}">${p.tipo}</span>`;
    html += `<h3>${p.nombre}</h3>`;
    html += `<div class="row"><b>Instagram:</b> ${p.instagram || "sin dato"}</div>`;
    html += `<div class="row"><b>Venues:</b> ${p.venues.length ? p.venues.join(", ") : "sin dato"}</div>`;
    html += `<div class="row"><b>Logo:</b> <span class="badge ${cls}">${p.logo_estado}</span></div>`;
    if (p.relaciones && p.relaciones.length){
      html += '<div class="rel-list">' + p.relaciones.map(r => `${r.tipo} <b>${r.objetivo}</b>`).join(" &middot; ") + '</div>';
    }
    if (p.eventos && p.eventos.length){
      html += p.eventos.map(e => `
        <div class="evento">
          <b>${e.nombre || "Evento"}</b><br>
          ${e.fecha || "fecha sin confirmar"} -- ${e.venue || "venue sin confirmar"}<br>
          <span class="fuente">Fuente: ${e.fuente || "sin fuente registrada"}</span>
        </div>`).join("");
    }
    card.innerHTML = html;
    grid.appendChild(card);
  }
}

function applyFilters(){
  const q = document.getElementById("buscar").value.trim().toLowerCase();
  const tipo = document.getElementById("filtroTipo").value;
  const logo = document.getElementById("filtroLogo").value;
  const filtered = DB.filter(p => {
    if (tipo && p.tipo !== tipo) return false;
    if (logo && estadoLogo(p.logo_estado) !== logo && !(logo === "pendiente" && estadoLogo(p.logo_estado) === "pendiente")) return false;
    if (q){
      const hay = [p.nombre, ...(p.aliases||[]), ...(p.venues||[])].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  render(filtered);
}

function initStats(){
  const nProd = DB.filter(p => p.tipo !== "spot").length;
  const nSpots = DB.filter(p => p.tipo === "spot").length;
  const nEventos = DB.reduce((a,p) => a + (p.eventos ? p.eventos.length : 0), 0);
  const nLogosOk = DB.filter(p => estadoLogo(p.logo_estado) === "ok").length;
  const stats = [
    [nProd, "Productoras"],
    [nSpots, "Spots"],
    [nEventos, "Eventos registrados"],
    [nLogosOk + "/" + DB.length, "Logos conseguidos"],
  ];
  document.getElementById("stats").innerHTML = stats.map(([n,l]) =>
    `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");
}

function initFilters(){
  const tipos = [...new Set(DB.map(p => p.tipo))].sort();
  const sel = document.getElementById("filtroTipo");
  for (const t of tipos){
    const opt = document.createElement("option");
    opt.value = t; opt.textContent = t;
    sel.appendChild(opt);
  }
  document.getElementById("buscar").addEventListener("input", applyFilters);
  document.getElementById("filtroTipo").addEventListener("change", applyFilters);
  document.getElementById("filtroLogo").addEventListener("change", applyFilters);
}

initStats();
initFilters();
render(DB);
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--productoras-dir", type=Path, default=Path("data/productoras"))
    ap.add_argument("--logo-dir", type=Path, default=Path("assets/logo"))
    args = ap.parse_args()

    db = build_db(args.productoras_dir)
    logo_svg = inline_logo(args.logo_dir / f"RD_logo_vector_{LOGO_VARIANT}.svg")
    logo_hero = logo_svg.replace("<svg ", '<svg class="logo" ', 1)
    logo_foot = logo_svg.replace("<svg ", '<svg class="logo" ', 1)

    html = (
        PAGE
        .replace("__LOGO__", logo_hero)
        .replace("__LOGO_FOOT__", logo_foot)
        .replace("__DATA_JSON__", json.dumps(db, ensure_ascii=False))
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"OK -> {args.out} ({len(db)} productoras/spots)")


if __name__ == "__main__":
    main()
