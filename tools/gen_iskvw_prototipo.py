"""Generates docs/iskvw/prototipo.html -- the ISKVW portfolio prototype.

WHAT IT IS
----------
A visual proposal joining the two references the user had on disk and treats as
references, not as competing options:

1. The live site (`ISKVW - Archivo digital`), whose IDENTITY is respected: it
   calls itself an archive, not a showcase, and its real navigation is
   Obra / Dibujo / Reactiva / Proyectos / Basurero / Sobre.
2. The "Portfolio Cyber Terminal 2D ISKVW 3D" prototype the user generated on
   2026-07-22, whose LANGUAGE is respected: scientific terminal, neon green,
   HUD telemetry, node networks.

THE RULE THAT JOINS THEM (thesis of projects/cultura/doublecup)
---------------------------------------------------------------
"An illustration holds potential information that has to be READ for it to take
on value". Plus its hard criterion: if an element claims to encode a datum and
does not, it is a lie even when it looks right.

So there is NO decorative telemetry here. Every HUD number is measured from
`tools/portfolio/proyectos.json` and from the repo at generation time. And the
node network is NOT generative noise: each node is a real project and each edge
is a tag shared between two projects. When a datum is missing the document says
"sin medir" instead of drawing something pretty.

Language: the OUTPUT is a deliverable a human reads, so its copy is correct
Spanish with accents and enes. This source file, like all repo code, is
documented in English.

Usage:
    py tools/gen_iskvw_prototipo.py --out docs/iskvw/prototipo.html
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def medir_repo(raiz: Path) -> dict:
    """Repo facts measured at generation time. Whatever cannot be measured says so."""
    def git(*args: str) -> str | None:
        try:
            r = subprocess.run(
                ["git", *args], cwd=str(raiz), capture_output=True, text=True, timeout=20
            )
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    # Only real pieces: a cache directory is not artwork. Caught on 2026-07-26,
    # when the HUD jumped from 7 to 8 because `__pycache__` had just been
    # created -- exactly the lie this prototype claims not to tell.
    cultura_dir = raiz / "projects" / "cultura"
    piezas = (
        sorted(
            p.name
            for p in cultura_dir.iterdir()
            if p.is_dir() and not p.name.startswith((".", "_"))
        )
        if cultura_dir.is_dir()
        else []
    )
    return {
        "sha": git("rev-parse", "--short", "HEAD"),
        "fecha_commit": git("log", "-1", "--format=%ad", "--date=short"),
        "commits": git("rev-list", "--count", "HEAD"),
        "piezas_cultura": piezas,
    }


def cargar_proyectos(ruta: Path) -> list[dict]:
    d = json.loads(ruta.read_text(encoding="utf-8"))
    salida = []
    for p in d.get("proyectos", []):
        salida.append({
            "id": p.get("id", ""),
            "nombre": p.get("nombre", p.get("id", "sin nombre")),
            "linea": p.get("linea", "sin linea"),
            "estado": p.get("estado", "sin estado"),
            "descripcion": p.get("descripcion", ""),
            "ruta": p.get("ruta", ""),
            "tags": p.get("tags", []),
        })
    return salida


PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ISKVW · archivo — prototipo</title>
<style>
:root{
  --fondo:#050707; --panel:#0b1110; --linea:#16302a;
  --verde:#41ffb0; --verde-tenue:#1d6b52; --tinta:#d8f5e9; --gris:#6d8b82;
  --alerta:#ffd166;
}
*{box-sizing:border-box;}
body{
  margin:0; background:var(--fondo); color:var(--tinta);
  font-family:"Consolas","DejaVu Sans Mono",monospace; line-height:1.5;
  font-size:14px;
}
a{ color:var(--verde); }

/* ---- top HUD: identity + measured telemetry ---- */
.hud{
  position:sticky; top:0; z-index:10; background:rgba(5,7,7,.94);
  border-bottom:1px solid var(--linea); backdrop-filter:blur(6px);
}
.hud-fila{
  display:flex; align-items:center; gap:1rem; flex-wrap:wrap;
  padding:.7rem 1.1rem; max-width:1180px; margin:0 auto;
}
.marca{ font-size:1.05rem; letter-spacing:.22em; color:var(--verde); text-transform:uppercase; }
.marca sup{ font-size:.55em; letter-spacing:.1em; color:var(--gris); margin-left:.25em; }
nav.principal{ display:flex; gap:.15rem; flex-wrap:wrap; margin-left:auto; }
nav.principal a{
  text-decoration:none; color:var(--gris); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.09em; padding:.35rem .6rem; border:1px solid transparent; border-radius:3px;
}
nav.principal a[aria-current]{ color:var(--verde); border-color:var(--verde-tenue); }
nav.principal a:hover, nav.principal a:focus-visible{ color:var(--tinta); border-color:var(--linea); }

.telemetria{
  display:flex; gap:0; flex-wrap:wrap; border-top:1px solid var(--linea);
  max-width:1180px; margin:0 auto; padding:0 1.1rem;
}
.tele{
  padding:.45rem .9rem .5rem 0; margin-right:1.4rem; font-size:.72rem; color:var(--gris);
  text-transform:uppercase; letter-spacing:.07em; white-space:nowrap;
}
.tele b{ color:var(--verde); font-size:1rem; letter-spacing:0; margin-right:.35em; }
.tele.sin-medir b{ color:var(--alerta); }

main{ max-width:1180px; margin:0 auto; padding:2rem 1.1rem 4rem; }
section{ margin-top:3rem; }
h1{ font-size:1.15rem; letter-spacing:.06em; color:var(--verde); margin:0 0 .4rem; }
h2{
  font-size:.82rem; text-transform:uppercase; letter-spacing:.14em; color:var(--gris);
  border-bottom:1px solid var(--linea); padding-bottom:.4rem; margin-bottom:1.1rem;
}
h2 span{ color:var(--verde); }
p.intro{ color:var(--gris); max-width:70ch; font-size:.86rem; }

/* ---- node network: each node is a real project ---- */
.mapa-envoltura{ position:relative; border:1px solid var(--linea); border-radius:4px; background:var(--panel); }
canvas#mapa{ display:block; width:100%; height:420px; }
.mapa-pie{
  display:flex; gap:1.2rem; flex-wrap:wrap; padding:.6rem .9rem;
  border-top:1px solid var(--linea); font-size:.72rem; color:var(--gris);
}
.llave{ display:flex; align-items:center; gap:.4rem; }
.punto{ width:9px; height:9px; border-radius:50%; display:inline-block; }
#detalle{
  position:absolute; pointer-events:none; opacity:0; transition:opacity .12s;
  background:#04100c; border:1px solid var(--verde-tenue); border-radius:3px;
  padding:.5rem .65rem; font-size:.74rem; max-width:280px; color:var(--tinta);
}
#detalle b{ color:var(--verde); display:block; margin-bottom:.2rem; }
#detalle i{ color:var(--gris); font-style:normal; }

/* ---- project cards ---- */
.rejilla{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:.9rem; }
.ficha{
  border:1px solid var(--linea); border-radius:4px; background:var(--panel);
  padding:.9rem 1rem; position:relative;
}
.ficha:hover{ border-color:var(--verde-tenue); }
.ficha h3{ font-size:.95rem; margin:.1rem 0 .35rem; color:var(--tinta); }
.ficha .meta{ font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; color:var(--gris); margin-bottom:.5rem; }
.ficha .meta b{ color:var(--verde); }
.ficha p{ font-size:.8rem; color:var(--gris); margin:.4rem 0 0; }
.etiquetas{ display:flex; flex-wrap:wrap; gap:.3rem; margin-top:.6rem; }
.etiqueta{ font-size:.66rem; color:var(--gris); border:1px solid var(--linea); border-radius:10px; padding:.1rem .5rem; }
.estado{ position:absolute; top:.9rem; right:1rem; font-size:.64rem; letter-spacing:.08em; text-transform:uppercase; }
.estado.activo{ color:var(--verde); }
.estado.investigacion{ color:var(--alerta); }
.estado.archivo, .estado.v0{ color:var(--gris); }

.nota{
  border-left:2px solid var(--verde-tenue); padding:.8rem 1rem; background:var(--panel);
  font-size:.82rem; color:var(--gris); border-radius:0 4px 4px 0;
}
.nota b{ color:var(--tinta); }
footer{
  border-top:1px solid var(--linea); margin-top:3.5rem; padding:1.4rem 1.1rem;
  font-size:.72rem; color:var(--gris); text-align:center;
}
@media (max-width:640px){
  canvas#mapa{ height:320px; }
  nav.principal{ margin-left:0; width:100%; }
}
@media (prefers-reduced-motion: reduce){
  /* The map stops animating: drawn once, resolved. */
}
</style>
</head>
<body>

<header class="hud">
  <div class="hud-fila">
    <span class="marca">ISKVW<sup>archivo</sup></span>
    <nav class="principal" aria-label="Navegación principal">
      <a href="#" aria-current="page">Obra</a>
      <a href="#">Dibujo</a>
      <a href="#">Reactiva</a>
      <a href="#">Proyectos</a>
      <a href="#">Basurero</a>
      <a href="#">Sobre</a>
    </nav>
  </div>
  <div class="telemetria" id="telemetria"></div>
</header>

<main>

<section id="entrada" style="margin-top:1.6rem;">
  <h1>Prototipo de archivo</h1>
  <p class="intro">
    Prueba de dirección: la identidad del archivo con el lenguaje de terminal.
    Todo lo que se ve afirma un dato medido en el momento de generar este
    documento. No hay telemetría de adorno: si un número no se puede medir,
    aparece en ámbar y dice que no se midió.
  </p>
</section>

<section id="mapa-seccion">
  <h2>Mapa de proyectos · <span id="mapa-conteo"></span></h2>
  <div class="mapa-envoltura">
    <canvas id="mapa"></canvas>
    <div id="detalle" role="status" aria-live="polite"></div>
    <div class="mapa-pie" id="leyenda"></div>
  </div>
  <p class="intro" style="margin-top:.7rem;">
    Cada nodo es un proyecto del catálogo curado. Cada línea une dos proyectos
    que comparten al menos una etiqueta: no es una distribución estética, es la
    relación declarada en los datos. El color marca la línea de trabajo; el
    tamaño, cuántas etiquetas tiene.
  </p>
</section>

<section id="proyectos">
  <h2>Catálogo · <span id="cat-conteo"></span></h2>
  <div class="rejilla" id="fichas"></div>
</section>

<section id="lectura">
  <h2>Cómo se lee</h2>
  <div class="nota">
    <p><b>El archivo manda, el terminal sirve.</b> El sitio se llama archivo y no
    vitrina: las seis secciones de arriba son las que ya existen, no una
    invención de este prototipo. Lo que aporta el lenguaje de terminal es una
    forma de mostrar el estado real del trabajo sin decorarlo.</p>
    <p><b>Si el dato falla, se ve.</b> Este documento hereda el criterio de la
    pieza <i>vaso semántico</i>: un elemento que dice codificar un dato y no lo
    hace es una mentira, aunque quede bien. Por eso los números en ámbar no son
    un error de diseño: son la marca de que ahí no hay medición.</p>
  </div>
</section>

</main>

<footer>
  ISKVW · prototipo generado por <code>tools/gen_iskvw_prototipo.py</code> desde
  <code>tools/portfolio/proyectos.json</code> y el estado real del repositorio.
  Se regenera con un comando.
</footer>

<script>
const PROYECTOS = __PROYECTOS__;
const REPO = __REPO__;

/* ---------- telemetry: measured data only ---------- */
function pintarTelemetria(){
  const lineas = new Set(PROYECTOS.map(p => p.linea));
  const activos = PROYECTOS.filter(p => p.estado === "activo").length;
  const etiquetas = new Set(PROYECTOS.flatMap(p => p.tags));
  const items = [
    ["proyectos", PROYECTOS.length, true],
    ["activos", activos, true],
    ["líneas", lineas.size, true],
    ["etiquetas", etiquetas.size, true],
    ["piezas de cultura", REPO.piezas_cultura.length, REPO.piezas_cultura.length > 0],
    ["commits", REPO.commits, REPO.commits !== null],
    ["revisión", REPO.sha, REPO.sha !== null]
  ];
  document.getElementById("telemetria").innerHTML = items.map(([etiqueta, valor, medido]) =>
    `<div class="tele ${medido ? "" : "sin-medir"}"><b>${medido ? valor : "sin medir"}</b>${etiqueta}</div>`
  ).join("");
  document.getElementById("mapa-conteo").textContent = `${PROYECTOS.length} nodos`;
  document.getElementById("cat-conteo").textContent = `${PROYECTOS.length} proyectos`;
}

/* ---------- map: nodes = projects, edges = shared tag ---------- */
const COLORES = {};
const PALETA = ["#41ffb0", "#ffd166", "#7aa2ff", "#ff7ab6", "#9df06a", "#c3a6ff"];
[...new Set(PROYECTOS.map(p => p.linea))].forEach((l, i) => { COLORES[l] = PALETA[i % PALETA.length]; });

const lienzo = document.getElementById("mapa");
const ctx = lienzo.getContext("2d");
const detalle = document.getElementById("detalle");
let nodos = [], aristas = [], animar = true;

if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) animar = false;

function construirGrafo(){
  nodos = PROYECTOS.map((p, i) => {
    const ang = (i / PROYECTOS.length) * Math.PI * 2;
    return {
      p,
      x: 0.5 + Math.cos(ang) * 0.3,
      y: 0.5 + Math.sin(ang) * 0.3,
      vx: 0, vy: 0,
      r: 5 + Math.min(p.tags.length, 5) * 1.6
    };
  });
  aristas = [];
  for (let i = 0; i < nodos.length; i++){
    for (let j = i + 1; j < nodos.length; j++){
      const comunes = nodos[i].p.tags.filter(t => nodos[j].p.tags.includes(t));
      if (comunes.length) aristas.push({ a: i, b: j, n: comunes.length, tags: comunes });
    }
  }
}

function paso(){
  // Node repulsion + per-edge attraction. Deterministic, no randomness:
  // the final layout is decided by the real relationship between tags.
  for (const n of nodos){ n.vx *= 0.86; n.vy *= 0.86; }
  for (let i = 0; i < nodos.length; i++){
    for (let j = i + 1; j < nodos.length; j++){
      const dx = nodos[j].x - nodos[i].x, dy = nodos[j].y - nodos[i].y;
      const d2 = Math.max(dx*dx + dy*dy, 0.0004);
      const f = 0.00025 / d2;
      nodos[i].vx -= dx * f; nodos[i].vy -= dy * f;
      nodos[j].vx += dx * f; nodos[j].vy += dy * f;
    }
  }
  for (const e of aristas){
    const a = nodos[e.a], b = nodos[e.b];
    const dx = b.x - a.x, dy = b.y - a.y;
    const f = 0.0016 * e.n;
    a.vx += dx * f; a.vy += dy * f;
    b.vx -= dx * f; b.vy -= dy * f;
  }
  for (const n of nodos){
    n.vx += (0.5 - n.x) * 0.0035;
    n.vy += (0.5 - n.y) * 0.0035;
    n.x = Math.min(0.97, Math.max(0.03, n.x + n.vx));
    n.y = Math.min(0.95, Math.max(0.05, n.y + n.vy));
  }
}

function dibujar(){
  const an = lienzo.width, al = lienzo.height;
  ctx.clearRect(0, 0, an, al);
  ctx.lineWidth = 1;
  for (const e of aristas){
    const a = nodos[e.a], b = nodos[e.b];
    ctx.strokeStyle = `rgba(65,255,176,${0.06 + Math.min(e.n, 3) * 0.05})`;
    ctx.beginPath();
    ctx.moveTo(a.x * an, a.y * al);
    ctx.lineTo(b.x * an, b.y * al);
    ctx.stroke();
  }
  for (const n of nodos){
    const c = COLORES[n.p.linea] || "#41ffb0";
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.arc(n.x * an, n.y * al, n.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(216,245,233,.72)";
    ctx.font = "11px Consolas, monospace";
    ctx.fillText(n.p.nombre, n.x * an + n.r + 5, n.y * al + 4);
  }
}

function ajustar(){
  const rect = lienzo.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  lienzo.width = rect.width * dpr;
  lienzo.height = rect.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  lienzo.width = rect.width; lienzo.height = rect.height;
}

function bucle(){
  paso();
  dibujar();
  if (animar) requestAnimationFrame(bucle);
}

lienzo.addEventListener("mousemove", ev => {
  const rect = lienzo.getBoundingClientRect();
  const mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
  let encontrado = null;
  for (const n of nodos){
    const dx = n.x * lienzo.width - mx, dy = n.y * lienzo.height - my;
    if (dx*dx + dy*dy < (n.r + 7) ** 2){ encontrado = n; break; }
  }
  if (!encontrado){ detalle.style.opacity = 0; return; }
  const p = encontrado.p;
  detalle.innerHTML = `<b>${p.nombre}</b><i>${p.linea} · ${p.estado}</i><br>${p.tags.join(" · ")}` +
                      (p.ruta ? `<br><i>${p.ruta}</i>` : "");
  detalle.style.left = Math.min(mx + 14, rect.width - 290) + "px";
  detalle.style.top = (my + 14) + "px";
  detalle.style.opacity = 1;
});
lienzo.addEventListener("mouseleave", () => { detalle.style.opacity = 0; });

function pintarLeyenda(){
  document.getElementById("leyenda").innerHTML =
    Object.entries(COLORES).map(([linea, color]) =>
      `<span class="llave"><span class="punto" style="background:${color}"></span>${linea}</span>`
    ).join("") +
    `<span class="llave" style="margin-left:auto">aristas: ${aristas.length} · relación por etiqueta compartida</span>`;
}

function pintarFichas(){
  document.getElementById("fichas").innerHTML = PROYECTOS.map(p => `
    <article class="ficha">
      <span class="estado ${p.estado}">${p.estado}</span>
      <h3>${p.nombre}</h3>
      <div class="meta">línea <b>${p.linea}</b></div>
      <p>${p.descripcion || "Sin descripción registrada."}</p>
      <div class="etiquetas">${p.tags.map(t => `<span class="etiqueta">${t}</span>`).join("")}</div>
    </article>`).join("");
}

pintarTelemetria();
construirGrafo();
ajustar();
pintarLeyenda();
pintarFichas();
bucle();
window.addEventListener("resize", () => { ajustar(); });
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--proyectos", type=Path, default=Path("tools/portfolio/proyectos.json"))
    args = ap.parse_args()

    raiz = Path(__file__).resolve().parent.parent
    proyectos = cargar_proyectos(args.proyectos)
    repo = medir_repo(raiz)

    html = (
        PAGE
        .replace("__PROYECTOS__", json.dumps(proyectos, ensure_ascii=False))
        .replace("__REPO__", json.dumps(repo, ensure_ascii=False))
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(
        "OK -> %s (%d proyectos, %d piezas de cultura, rev %s)"
        % (args.out, len(proyectos), len(repo["piezas_cultura"]), repo["sha"] or "sin medir")
    )


if __name__ == "__main__":
    main()
