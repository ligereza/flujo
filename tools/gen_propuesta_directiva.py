"""Generates docs/rd/propuesta_directiva.html -- the formal proposal to the
Reduciendo Dano board.

What it is: a self-contained HTML document (no CDN, no external JS, real inline
vector logo) answering four board questions in this order: what RD offers today,
who it works with, what data it keeps and how it protects it, and what it needs
the board to approve.

Where the data comes from: EVERYTHING is read from `data/rd.db`, the regenerable
sqlite projection (`py -m flujo rd-db build`) over the hand-editable JSON files.
No figure is written by hand here: if the database changes, the document
changes. If the database lacks a datum, the document says so -- it never invents
one.

Language: the OUTPUT is a deliverable a human reads, so its copy is correct
Spanish with accents and enes. The ASCII-only rule covers operational .md files,
never this (a title reading "reduciendo ano" is not a typo, it is a firing).
This source file, like all repo code, is documented in English.

Usage:
    py -m flujo rd-db build
    py tools/gen_propuesta_directiva.py --out docs/rd/propuesta_directiva.html
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

LOGO_VARIANT = "blanco"  # fondo oscuro -> logo blanco (regla dura taller-svg-rd)


def inline_logo(svg_path: Path) -> str:
    raw = svg_path.read_text(encoding="utf-8")
    return raw[raw.index("<svg"):]


def _tabla_existe(con: sqlite3.Connection, nombre: str) -> bool:
    row = con.execute(
        "select 1 from sqlite_master where type='table' and name=?", (nombre,)
    ).fetchone()
    return row is not None


def _filas(con: sqlite3.Connection, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def leer_db(db_path: Path) -> dict:
    """Read the sqlite projection. Returns only what actually exists."""
    if not db_path.exists():
        raise SystemExit(
            "No existe %s. Construilo antes con: py -m flujo rd-db build" % db_path
        )
    con = sqlite3.connect(db_path)
    datos: dict = {"packs": [], "reactivos": [], "suplementos": [], "productoras": []}

    if _tabla_existe(con, "packs"):
        datos["packs"] = _filas(con, "select * from packs order by orden")
        tiene_inclusiones = _tabla_existe(con, "inclusiones")
        for p in datos["packs"]:
            if not tiene_inclusiones:
                p["inclusiones"] = []
                continue
            cur = con.execute(
                "select texto from inclusiones where pack_id = ? order by orden",
                (p["id"],),
            )
            p["inclusiones"] = [r[0] for r in cur.fetchall() if r[0]]

    if _tabla_existe(con, "reactivos"):
        datos["reactivos"] = _filas(con, "select * from reactivos")
    if _tabla_existe(con, "suplementos"):
        datos["suplementos"] = _filas(con, "select * from suplementos")
    if _tabla_existe(con, "productoras"):
        datos["productoras"] = _filas(con, "select * from productoras order by nombre")
    datos["venues"] = _filas(con, "select * from venues") if _tabla_existe(con, "venues") else []
    # Real events of each promoter -- NOT the quoting templates in `eventos`.
    # The distinction is documented in the schema; conflating them would make
    # the board read demo rows as real work.
    datos["productora_eventos"] = (
        _filas(con, "select * from productora_eventos order by productora_slug")
        if _tabla_existe(con, "productora_eventos")
        else []
    )
    datos["logos"] = (
        _filas(con, "select * from productora_logos") if _tabla_existe(con, "productora_logos") else []
    )
    con.close()
    return datos


def _columnas(con: sqlite3.Connection, tabla: str) -> list[str]:
    return [r[1] for r in con.execute("pragma table_info(%s)" % tabla)]


PAGE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Propuesta a la Directiva — Reduciendo Daño</title>
<style>
:root{
  --bg:#0A0A0A; --panel:#161318; --ink:#F2F2F2; --muted:#9c98a3;
  --magenta:#C800C8; --amarillo:#FFD21F; --linea:#2a2530;
}
*{box-sizing:border-box;}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family: Arial, Helvetica, sans-serif; line-height:1.55;
}
header.hero{
  padding:3rem 1.5rem 2rem; text-align:center;
  border-bottom:1px solid var(--linea);
}
header.hero .logo{ width:110px; height:auto; margin:0 auto 1rem; display:block; }
header.hero h1{
  font-size:1.6rem; letter-spacing:.04em; text-transform:uppercase;
  color:var(--amarillo); text-shadow:0 0 18px rgba(255,210,31,.35);
  margin:.2rem 0;
}
header.hero p{ color:var(--muted); max-width:680px; margin:.7rem auto 0; font-size:.92rem; }
main{ max-width:1080px; margin:0 auto; padding:2rem 1.25rem 4rem; }
section{ margin-top:2.75rem; }
h2{
  font-size:1.05rem; text-transform:uppercase; letter-spacing:.06em;
  color:var(--amarillo); border-left:3px solid var(--magenta); padding-left:.6rem;
  margin-bottom:1rem;
}
h3{ font-size:1rem; margin:.1rem 0 .4rem; }
p{ font-size:.92rem; }
.panel{
  background:var(--panel); border-radius:10px; padding:1.2rem 1.4rem;
  font-size:.9rem; color:var(--muted);
}
.panel b, .panel strong{ color:var(--ink); }
.stat-row{ display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1.2rem; }
.stat{ background:var(--panel); border-radius:8px; padding:.85rem 1.15rem; min-width:132px; }
.stat .n{ font-size:1.6rem; color:var(--amarillo); font-weight:700; line-height:1.1; }
.stat .l{ font-size:.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
.grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:1rem; }
.card{
  background:var(--panel); border-radius:10px; padding:1.15rem;
  position:relative; overflow:hidden;
}
.card::before, .card::after{
  content:""; position:absolute; inset:0; border-radius:10px; pointer-events:none;
}
.card::before{ box-shadow:inset 0 0 0 1.5px rgba(200,0,200,.16); }
.card::after{ box-shadow:inset 0 0 0 1px rgba(200,0,200,.55); }
.precio{ color:var(--amarillo); font-weight:700; font-size:1.05rem; margin:.2rem 0 .5rem; }
.card ul{ margin:.4rem 0 0 1.05rem; padding:0; font-size:.83rem; color:var(--muted); }
.card li{ margin:.25rem 0; }
.chips{ display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.4rem; }
.chip{
  font-size:.72rem; padding:.2rem .55rem; border-radius:12px;
  background:#241f29; color:var(--muted);
}
.pide{ counter-reset:pide; }
.pide .item{
  background:var(--panel); border-radius:10px; padding:1.1rem 1.3rem 1.1rem 3.2rem;
  position:relative; margin-bottom:.9rem; font-size:.9rem; color:var(--muted);
}
.pide .item::before{
  counter-increment:pide; content:counter(pide);
  position:absolute; left:1.1rem; top:1rem;
  color:var(--amarillo); font-weight:700; font-size:1.2rem;
}
.pide .item b{ color:var(--ink); }
.aviso{
  background:#1a1416; border-left:3px solid var(--magenta);
  border-radius:0 10px 10px 0; padding:1.1rem 1.3rem; font-size:.86rem; color:var(--muted);
}
.aviso b{ color:var(--ink); }
footer{
  text-align:center; padding:2rem 1rem; color:var(--muted); font-size:.75rem;
  border-top:1px solid var(--linea);
}
footer .logo{ width:52px; height:auto; margin:0 auto .6rem; display:block; opacity:.8; }
a{ color:var(--amarillo); }
@media print{
  body{ background:#fff; color:#000; }
  .panel, .card, .stat, .pide .item{ background:#f4f4f4; color:#000; }
  h1, h2, .stat .n, .precio{ color:#000 !important; text-shadow:none !important; }
}
</style>
</head>
<body>
<header class="hero">
  __LOGO__
  <h1>Propuesta a la Directiva</h1>
  <p>Qué ofrece Reduciendo Daño hoy, con quién trabaja, qué datos guarda y cómo los
  protege, y qué necesita que la directiva apruebe para seguir. Documento autónomo:
  no depende de internet ni de ningún servicio externo para abrirse.</p>
</header>

<main>

<section id="resumen">
  <h2>En una mirada</h2>
  <div class="stat-row" id="stats"></div>
  <div class="panel">
    Todas las cifras de este documento se leen de la base de datos del proyecto en el
    momento de generarlo. No hay números escritos a mano: si un dato no está en la
    base, acá aparece como <b>sin dato</b> en vez de inventarse.
  </div>
</section>

<section id="servicios">
  <h2>Qué ofrecemos</h2>
  <div class="grid" id="packs"></div>
</section>

<section id="capacidad">
  <h2>Con qué contamos</h2>
  <div class="grid" id="capacidad-cards"></div>
</section>

<section id="datos">
  <h2>Qué datos guardamos y cómo los protegemos</h2>
  <div class="panel">
    <p><b>La identidad no se puede filtrar porque no existe.</b> La base de datos de
    campo no tiene columnas de nombre, RUT, teléfono ni correo. No es una regla de
    uso que alguien pueda saltarse: es el diseño de la tabla. Lo que no existe como
    columna no se puede consultar, exportar ni filtrar por accidente.</p>
    <p><b>La fecha se guarda sin hora.</b> Registrar la hora exacta permitiría volver
    a identificar a una persona cruzando el dato con quién estuvo dónde. Se guarda el
    día, que es lo que sirve para vigilancia epidemiológica, y nada más fino.</p>
    <p><b>El texto libre pasa por un filtro antes de guardarse.</b> Si alguien escribe
    un dato personal en una observación, el sistema lo rechaza o lo limpia antes de
    que llegue a la base.</p>
    <p>Este patrón es el mismo que usan las bases de datos de testeo de referencia
    internacional. No hubo que inventarlo: ya está construido y funcionando.</p>
  </div>
</section>

<section id="pedimos">
  <h2>Qué necesitamos de la directiva</h2>
  <div class="pide">
    <div class="item">
      <b>Un acta de acuerdo sobre datos.</b> Que la directiva apruebe formalmente qué
      datos de campo se registran —hoy ya sin información personal por diseño— y quién
      puede ver el panel agregado. Esto se firma antes de construir el panel, no
      después.
    </div>
    <div class="item">
      <b>Validación legal profesional.</b> Encargar a un abogado con experiencia en
      Ley 20.000 y en ONG de salud que revise qué puede y qué no puede hacer la
      organización en terreno. Lo que hoy tenemos sobre ese tema es un punto de
      partida generado automáticamente, no asesoría, y así está marcado.
    </div>
    <div class="item">
      <b>Definir quién mira el panel.</b> El panel para la directiva se expone de
      forma privada, sin filas individuales sensibles y sin publicarlo al público.
      Falta decidir quiénes son sus destinatarios y por qué vía acceden.
    </div>
  </div>
</section>

<section id="honestidad">
  <h2>Nota de honestidad</h2>
  <div class="aviso">
    <b>Lo que este documento no es.</b> Los informes de investigación que respaldan
    el marco legal se generaron con herramientas automáticas gratuitas que fallaron
    por cuota durante toda la corrida. Sus fuentes son metodológicas y genéricas, no
    normativa chilena verificada. Ningún punto de este documento reemplaza una lectura
    de abogado. Se dice acá y no en una nota al pie porque la directiva merece saber
    con qué calidad de información está decidiendo.
  </div>
</section>

</main>

<footer>
  __LOGO_FOOT__
  <div>Reduciendo Daño — documento generado por <code>tools/gen_propuesta_directiva.py</code>
  desde <code>data/rd.db</code>. Se regenera con un comando cada vez que cambian los datos.</div>
</footer>

<script>
const DATOS = __DATA_JSON__;

function stat(n, l){
  return `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`;
}

function texto(v, alt){
  if (v === null || v === undefined || v === "") return alt || "sin dato";
  return v;
}

// La tabla `reactivos` guarda un par reactivo x familia por fila: 23 filas NO son
// 23 reactivos distintos, son 23 reacciones registradas sobre ~7 reactivos. Contar
// filas y llamarlas "reactivos" seria afirmar un dato que la base no dice.
function reactivosUnicos(){
  const vistos = new Map();
  for (const r of DATOS.reactivos){
    const nombre = r.reactivo;
    if (!nombre) continue;
    vistos.set(nombre, (vistos.get(nombre) || 0) + 1);
  }
  return [...vistos.entries()].map(([nombre, familias]) => ({ nombre, familias }));
}

function pintarStats(){
  const el = document.getElementById("stats");
  const eventosSinFuentePrimaria = DATOS.productora_eventos.filter(e => Number(e.sin_fuente_primaria || 0) === 1).length;
  el.innerHTML = [
    stat(DATOS.packs.length, "paquetes de servicio"),
    stat(DATOS.productoras.length, "productoras y spots"),
    stat(DATOS.venues.length, "venues registrados"),
    stat(reactivosUnicos().length, "reactivos en catálogo"),
    stat(DATOS.reactivos.length, "reacciones registradas"),
    stat(DATOS.suplementos.length, "suplementos"),
    stat(DATOS.logos.length, "logos oficiales"),
    stat(DATOS.productora_eventos.length, "eventos registrados"),
    stat(eventosSinFuentePrimaria, "eventos sin fuente primaria")
  ].join("");
}

function pintarPacks(){
  const el = document.getElementById("packs");
  if (!DATOS.packs.length){
    el.innerHTML = '<div class="panel">La base no tiene paquetes cargados todavía.</div>';
    return;
  }
  el.innerHTML = DATOS.packs.map(p => {
    const nombre = texto(p.label || p.nombre, "Paquete sin nombre");
    const precio = p.precio ? Number(p.precio).toLocaleString("es-CL") : null;
    const vol = p.voluntarios ? `${p.voluntarios} voluntarios` : null;
    let h = `<h3>${nombre}</h3>`;
    h += precio ? `<div class="precio">$${precio} CLP</div>`
                : `<div class="precio">Precio sin registrar</div>`;
    if (p.descripcion) h += `<div>${p.descripcion}</div>`;
    if (p.inclusiones && p.inclusiones.length){
      h += "<ul>" + p.inclusiones.filter(Boolean).map(i => `<li>${i}</li>`).join("") + "</ul>";
    }
    if (vol) h += `<div class="chips"><span class="chip">${vol}</span></div>`;
    return `<div class="card">${h}</div>`;
  }).join("");
}

function pintarCapacidad(){
  const el = document.getElementById("capacidad-cards");
  const reactivos = reactivosUnicos().map(r =>
    r.familias > 1 ? `${r.nombre} (${r.familias} familias)` : r.nombre);
  const suplementos = DATOS.suplementos.map(s => texto(s.titulo, "")).filter(Boolean);
  const productoras = DATOS.productoras.map(p => texto(p.nombre, "")).filter(Boolean);

  function tarjeta(titulo, items, nota){
    let h = `<h3>${titulo}</h3>`;
    h += `<div class="precio">${items.length}</div>`;
    if (items.length){
      h += '<div class="chips">' + items.slice(0, 24).map(i => `<span class="chip">${i}</span>`).join("") + '</div>';
      if (items.length > 24) h += `<div class="chips"><span class="chip">y ${items.length - 24} más</span></div>`;
    } else {
      h += "<div>Sin datos cargados todavía.</div>";
    }
    if (nota) h += `<ul><li>${nota}</li></ul>`;
    return `<div class="card">${h}</div>`;
  }

  const eventos = DATOS.productora_eventos.map(e => {
    const cuando = e.fecha && !String(e.fecha).includes("needs_confirmation") ? ` · ${e.fecha}` : " · fecha sin confirmar";
    const fuente = Number(e.sin_fuente_primaria || 0) === 1 ? " · sin fuente primaria" : " · fuente primaria";
    return `${e.nombre}${cuando}${fuente}`;
  });

  el.innerHTML = [
    tarjeta("Productoras y spots", productoras,
      "Cada ficha guarda de dónde salió el dato. Lo no confirmado queda marcado como pendiente, no se da por cierto."),
    tarjeta("Eventos registrados", eventos,
      "Eventos reales de las productoras, con su fuente. No son ejemplos de cotización: eso se cuenta aparte."),
    tarjeta("Reactivos", reactivos,
      "Reactivos colorimétricos con los que se trabaja en terreno. Entre paréntesis, sobre cuántas familias de sustancias hay reacción registrada."),
    tarjeta("Suplementos", suplementos,
      "Línea de suplementos con sus fichas y contraportadas.")
  ].join("");
}

pintarStats();
pintarPacks();
pintarCapacidad();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--db", type=Path, default=Path("data/rd.db"))
    ap.add_argument("--logo-dir", type=Path, default=Path("assets/logo"))
    args = ap.parse_args()

    datos = leer_db(args.db)
    logo_svg = inline_logo(args.logo_dir / f"RD_logo_vector_{LOGO_VARIANT}.svg")
    logo_hero = logo_svg.replace("<svg ", '<svg class="logo" ', 1)
    logo_foot = logo_svg.replace("<svg ", '<svg class="logo" ', 1)

    html = (
        PAGE
        .replace("__LOGO__", logo_hero)
        .replace("__LOGO_FOOT__", logo_foot)
        .replace("__DATA_JSON__", json.dumps(datos, ensure_ascii=False))
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(
        "OK -> %s (%d paquetes, %d productoras, %d reactivos, %d suplementos)"
        % (
            args.out,
            len(datos["packs"]),
            len(datos["productoras"]),
            len(datos["reactivos"]),
            len(datos["suplementos"]),
        )
    )


if __name__ == "__main__":
    main()
