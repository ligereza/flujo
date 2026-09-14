#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base de venues: sembrar, validar, listar y publicar.

La base NO son renders: son archivos JSON en git. Los planos, los renders y el
export MVR son derivados regenerables. Un colaborador corrige una cota y todo se
vuelve a generar.

La regla que ordena todo el modulo: **de memoria no es medido**. Sembrar desde
tres anios de gira produce datos `aportado`, no `medido`. `medido` lo escribe
quien estuvo en la sala con instrumento y firma. Ese salto de tier es lo unico
que no es gratis.

Uso:
    py tools/venue.py sembrar semillas.txt      # de memoria -> JSON (aportado)
    py tools/venue.py validar                   # esquema + coherencia
    py tools/venue.py listar                    # tabla, con % de completitud
    py tools/venue.py geometria                 # numeros del bloque geometria
    py tools/venue.py sitio                     # HTML unico, offline, telefono
    py tools/venue.py proyeccion SETUP.xml <id> # propone la topologia medida
                                                # desde un ScreenSetup de Resolume

Formato de semilla (una sala por linea, `#` es comentario). Campos vacios: `-`

    ciudad | nombre | tipo | ancho | prof | truss | tiro | notas

    Santiago | Sala Ejemplo | teatro | 10 | 4.5 | 6.2 | 9 | columna a un tercio
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIR_VENUES = REPO / "data" / "venues"
DIR_PROPUESTAS = REPO / "data" / "venues_propuestas"
ESQUEMA = REPO / "schemas" / "venue.schema.json"
SALIDA_SITIO = REPO / "web" / "venues" / "index.html"

TIPOS = ("teatro", "club", "galpon", "casa", "multiuso", "aire_libre", "otro")
CAMPOS_SEMILLA = ("ciudad", "nombre", "tipo", "ancho", "prof", "truss", "tiro", "notas")


# --------------------------------------------------------------------------- utilidades
def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return re.sub(r"-{2,}", "-", t) or "sin-nombre"


def _medida(valor: str, metodo: str = "memoria", confianza: str = "aportado") -> dict | None:
    v = (valor or "").strip().replace(",", ".")
    if not v or v == "-":
        return None
    try:
        n = float(v)
    except ValueError:
        return None
    if n <= 0:
        return None
    return {"m": n, "confianza": confianza, "metodo": metodo}


def _limpio(v: str) -> str:
    v = (v or "").strip()
    return "" if v == "-" else v


def cargar_todos() -> list[dict]:
    if not DIR_VENUES.exists():
        return []
    salida = []
    for p in sorted(DIR_VENUES.glob("*.json")):
        try:
            salida.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            print(f"  ROTO {p.name}: {e}", file=sys.stderr)
    return salida


# --------------------------------------------------------------------------- sembrar
def parsear_semilla(linea: str) -> dict | None:
    """Una linea de semilla -> dict de venue. None si es comentario o vacia."""
    linea = linea.strip()
    if not linea or linea.startswith("#"):
        return None
    partes = [p.strip() for p in linea.split("|")]
    partes += [""] * (len(CAMPOS_SEMILLA) - len(partes))
    ciudad, nombre, tipo, ancho, prof, truss, tiro, notas = partes[:8]
    if not _limpio(nombre) or not _limpio(ciudad):
        raise ValueError(f"faltan ciudad o nombre: {linea!r}")

    tipo = _limpio(tipo).lower() or "otro"
    if tipo not in TIPOS:
        raise ValueError(f"tipo invalido {tipo!r} (validos: {', '.join(TIPOS)})")

    v: dict = {
        "id": f"{slug(ciudad)}-{slug(nombre)}",
        "nombre": _limpio(nombre),
        "ciudad": _limpio(ciudad),
        "tipo": tipo,
        "publico": True,
        "fecha_captura": date.today().isoformat(),
        # de memoria NO es medicion, y el archivo lo dice de si mismo
        "fuente_datos": "memoria",
        "licencia": "ODbL-1.0",
    }

    esc = {}
    if (m := _medida(ancho)):
        esc["ancho"] = m
    if (m := _medida(prof)):
        esc["profundidad"] = m
    if esc:
        v["escenario"] = esc

    sala = {}
    if (m := _medida(truss)):
        sala["altura_truss"] = m
    if (m := _medida(tiro)):
        sala["tiro_proyeccion"] = m
    if sala:
        v["sala"] = sala

    if _limpio(notas):
        v["notas"] = _limpio(notas)
    return v


def sembrar(ruta: Path) -> int:
    DIR_VENUES.mkdir(parents=True, exist_ok=True)
    n = 0
    for i, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        try:
            v = parsear_semilla(linea)
        except ValueError as e:
            print(f"  linea {i}: {e}", file=sys.stderr)
            continue
        if not v:
            continue
        destino = DIR_VENUES / f"{v['id']}.json"
        if destino.exists():
            print(f"  ya existe, no se pisa: {destino.name}")
            continue
        destino.write_text(
            json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  + {destino.name}")
        n += 1
    return n


# --------------------------------------------------------------------------- geometria
# The viewer's declared default edge budget (iskvw/piel/venue/index.html, TOPE).
# A venue over it still renders, but the viewer will crop it -- loudly. The
# number lives here too so `geometria`/`validar` can say it BEFORE anyone opens
# a browser.
TOPE_VISOR = 800
# Declared measure vs drawn extent: past this gap, one of the two is wrong.
TOLERANCIA_COTA_M = 0.15


def medir_geometria(v: dict) -> dict | None:
    """Numbers about the `geometria` block. None when the venue has none.

    Everything here is counted, not judged: edge totals per confianza tier,
    bounding box, closed/open polylines, zero-length segments. The judging
    happens in `coherencia()`, on top of these numbers.
    """
    g = v.get("geometria")
    if not isinstance(g, dict):
        return None
    polilineas = g.get("polilineas") or []
    por_confianza: dict[str, int] = {}
    aristas_por_capa: dict[str, int] = {}
    bb_por_capa: dict[str, list[list[float]]] = {}
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    puntos = aristas = degenerados = cerradas = abiertas = 0
    for pl in polilineas:
        ps = pl.get("puntos") or []
        puntos += len(ps)
        n = max(0, len(ps) - 1)
        aristas += n
        conf = pl.get("confianza", "no_verificado")
        por_confianza[conf] = por_confianza.get(conf, 0) + n
        capa = pl.get("capa") or "sin_capa"
        aristas_por_capa[capa] = aristas_por_capa.get(capa, 0) + n
        bb = bb_por_capa.setdefault(
            capa, [[float("inf")] * 3, [float("-inf")] * 3])
        for q in ps:
            for k in range(3):
                if q[k] < mn[k]:
                    mn[k] = q[k]
                if q[k] > mx[k]:
                    mx[k] = q[k]
                if q[k] < bb[0][k]:
                    bb[0][k] = q[k]
                if q[k] > bb[1][k]:
                    bb[1][k] = q[k]
        # a zero-length segment draws nothing and still spends edge budget
        degenerados += sum(1 for a, b in zip(ps, ps[1:]) if a == b)
        if len(ps) >= 3 and ps[0] == ps[-1]:
            cerradas += 1
        elif ps:
            abiertas += 1
    if not puntos:
        mn = mx = [0.0, 0.0, 0.0]
    dim = [round(mx[k] - mn[k], 3) for k in range(3)]
    dim_por_capa = {
        c: [round(b[1][k] - b[0][k], 3) for k in range(3)]
        for c, b in bb_por_capa.items()
    }
    return {
        "polilineas": len(polilineas),
        "puntos": puntos,
        "aristas": aristas,
        "por_confianza": por_confianza,
        "aristas_por_capa": aristas_por_capa,
        "dim": dim,
        "dim_por_capa": dim_por_capa,
        "degenerados": degenerados,
        "cerradas": cerradas,
        "abiertas": abiertas,
    }


def geometria() -> int:
    """Numeric report per venue with geometry. Fails only on hard defects."""
    venues = cargar_todos()
    con_geo = fallas = 0
    for v in sorted(venues, key=lambda x: x.get("id", "")):
        m = medir_geometria(v)
        if not m:
            continue
        con_geo += 1
        vid = v.get("id", "?")
        print(f"{vid}: {m['polilineas']} polilineas · {m['aristas']} aristas · "
              f"{m['dim'][0]} x {m['dim'][1]} x {m['dim'][2]} m")
        print(f"  cerradas {m['cerradas']} · abiertas {m['abiertas']} · "
              f"segmentos de largo cero {m['degenerados']}")
        for k in sorted(m["por_confianza"]):
            print(f"  {k:<15} {m['por_confianza'][k]:>4} aristas")
        for c in sorted(m["aristas_por_capa"]):
            d = m["dim_por_capa"][c]
            print(f"  capa {c:<18} {m['aristas_por_capa'][c]:>4} aristas · "
                  f"{d[0]} x {d[1]} x {d[2]} m")
        if m["degenerados"]:
            fallas += 1
        if m["aristas"] > TOPE_VISOR:
            print(f"  aviso: {m['aristas']} aristas superan el tope del visor "
                  f"({TOPE_VISOR}): recortara avisando")
    print(f"\n{con_geo} de {len(venues)} venues con geometria · "
          f"{fallas} con segmentos de largo cero")
    return 1 if fallas else 0


# --------------------------------------------------------------------------- validar
def coherencia(v: dict) -> list[str]:
    """Chequeos que el esquema no puede hacer. Avisan, no corrigen."""
    avisos = []
    vid = v.get("id", "?")

    if v.get("publico") is False and v.get("direccion"):
        avisos.append(f"{vid}: publico=false pero tiene direccion. Sacala.")

    if v.get("firmado_por"):
        medidos = [
            k
            for grupo in ("escenario", "sala", "acceso")
            for k, m in (v.get(grupo) or {}).items()
            if isinstance(m, dict) and m.get("confianza") == "medido"
        ]
        if not medidos:
            avisos.append(f"{vid}: firmado pero sin un solo dato 'medido'. La firma no aplica.")

    if v.get("fuente_datos") == "memoria":
        for grupo in ("escenario", "sala", "acceso"):
            for k, m in (v.get(grupo) or {}).items():
                if isinstance(m, dict) and m.get("confianza") == "medido":
                    avisos.append(
                        f"{vid}: {grupo}.{k} dice 'medido' pero fuente_datos=memoria. "
                        "De memoria no es medido."
                    )
        # La misma regla en la geometria: dibujar de memoria es dibujar, no medir.
        n = sum(
            1
            for pl in ((v.get("geometria") or {}).get("polilineas") or [])
            if pl.get("confianza") == "medido"
        )
        if n:
            avisos.append(
                f"{vid}: {n} polilineas dicen 'medido' pero fuente_datos=memoria. "
                "De memoria no es medido."
            )

    esc = v.get("escenario") or {}
    sala = v.get("sala") or {}
    if (a := esc.get("ancho")) and (p := esc.get("profundidad")):
        if a["m"] < p["m"]:
            avisos.append(f"{vid}: escenario mas profundo que ancho. Raro; confirmar.")
    if (t := sala.get("altura_truss")) and (li := sala.get("altura_libre")):
        if li["m"] > t["m"]:
            avisos.append(f"{vid}: altura_libre mayor que altura_truss. Imposible.")

    for c in v.get("citas") or []:
        if not (c.get("fuente") or "").strip():
            avisos.append(f"{vid}: una cita sin fuente. Se cita o se marca no_verificado.")

    # Geometry, measured: these checks are numbers, not opinions.
    m = medir_geometria(v)
    if m:
        if m["degenerados"]:
            avisos.append(
                f"{vid}: {m['degenerados']} segmentos de largo cero en la "
                "geometria. No dibujan nada y gastan presupuesto de aristas."
            )
        if m["aristas"] > TOPE_VISOR:
            avisos.append(
                f"{vid}: {m['aristas']} aristas superan el tope del visor "
                f"({TOPE_VISOR}). El visor recorta avisando, pero recorta."
            )
        # The declared stage measure and the drawn stage layer have to agree:
        # a data sheet that contradicts its own drawing is worse than either.
        dim_esc = m["dim_por_capa"].get("escenario")
        if dim_esc:
            declarado = v.get("escenario") or {}
            for eje, clave in ((0, "ancho"), (1, "profundidad")):
                d = declarado.get(clave)
                if isinstance(d, dict) and isinstance(d.get("m"), (int, float)):
                    delta = abs(dim_esc[eje] - d["m"])
                    if delta > TOLERANCIA_COTA_M:
                        avisos.append(
                            f"{vid}: escenario.{clave} declara {d['m']} m pero "
                            f"la capa 'escenario' dibuja {dim_esc[eje]} m "
                            f"(delta {round(delta, 3)} m). Uno de los dos miente."
                        )
    return avisos


def validar() -> int:
    try:
        import jsonschema
    except ImportError:
        print("falta jsonschema (esta en requirements.txt)", file=sys.stderr)
        return 2
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    validador = jsonschema.Draft202012Validator(esquema)

    venues, errores, avisos = cargar_todos(), 0, 0
    for v in venues:
        for e in sorted(validador.iter_errors(v), key=lambda e: list(e.path)):
            ruta = "/".join(str(x) for x in e.path) or "(raiz)"
            print(f"  ERROR {v.get('id','?')} {ruta}: {e.message}")
            errores += 1
        for a in coherencia(v):
            print(f"  aviso {a}")
            avisos += 1

    print(f"\n{len(venues)} venues · {errores} errores · {avisos} avisos")
    return 1 if errores else 0


# --------------------------------------------------------------------------- listar
CLAVES_UTILES = (
    ("escenario", "ancho"),
    ("escenario", "profundidad"),
    ("sala", "altura_truss"),
    ("sala", "altura_libre"),
    ("sala", "tiro_proyeccion"),
    ("acceso", "puerta_ancho"),
)


def completitud(v: dict) -> int:
    tiene = sum(1 for g, k in CLAVES_UTILES if isinstance((v.get(g) or {}).get(k), dict))
    return round(100 * tiene / len(CLAVES_UTILES))


def listar() -> int:
    venues = cargar_todos()
    if not venues:
        print("no hay venues todavia. Sembra: py tools/venue.py sembrar semillas.txt")
        return 0
    print(f"{'ciudad':<14} {'nombre':<28} {'tipo':<10} {'datos':>6} {'aristas':>8}  firma")
    print("-" * 82)
    for v in sorted(venues, key=lambda x: (x.get("ciudad", ""), x.get("nombre", ""))):
        firma = v.get("firmado_por") or "-"
        m = medir_geometria(v)
        aristas = str(m["aristas"]) if m else "-"
        print(
            f"{v.get('ciudad','')[:14]:<14} {v.get('nombre','')[:28]:<28} "
            f"{v.get('tipo','')[:10]:<10} {completitud(v):>5}% {aristas:>8}  {firma}"
        )
    print(f"\n{len(venues)} venues.")
    return 0


# --------------------------------------------------------------------------- sitio
PLANTILLA = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Salas -- base abierta</title>
<style>
:root{--bg:#0f1218;--fg:#e8e6e1;--dim:#8a8f98;--line:#242a33;--ok:#7fd1a3;--warn:#ffcc00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;padding:16px}
h1{font-size:19px;margin:0 0 2px}
p.sub{color:var(--dim);font-size:13px;margin:0 0 14px}
input{width:100%;padding:13px;font-size:16px;background:#161b22;color:var(--fg);
border:1px solid var(--line);border-radius:10px;margin-bottom:14px}
.v{border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:10px;background:#131820}
.v h2{font-size:16px;margin:0 0 2px}
.meta{color:var(--dim);font-size:12px;margin-bottom:8px}
.d{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #1b212a;font-size:14px}
.d:last-child{border:0}
.d span:last-child{font-variant-numeric:tabular-nums}
.c{font-size:10px;padding:1px 5px;border-radius:4px;margin-left:6px;vertical-align:middle}
.medido{background:#1d3a2b;color:var(--ok)}
.aportado{background:#3a3520;color:var(--warn)}
.citado{background:#22303f;color:#8ab4d8}
.firma{color:var(--ok);font-size:12px;margin-top:8px}
.nofirma{color:var(--dim);font-size:12px;margin-top:8px}
footer{color:var(--dim);font-size:12px;margin-top:22px;border-top:1px solid var(--line);padding-top:12px}
</style>
<h1>Salas</h1>
<p class="sub">Base abierta. Funciona sin conexión. __N__ salas · ODbL-1.0</p>
<input id="q" placeholder="buscar por ciudad, nombre o tipo..." autocomplete="off">
<div id="lista"></div>
<footer>
<strong>aportado</strong> = alguien lo dijo, útil y no verificado ·
<strong>medido</strong> = instrumento en la sala, alguien firma ·
<strong>citado</strong> = de documentación certificada del venue.<br>
Cargas, rigging y eléctrico se <strong>citan</strong>, nunca se derivan de una medición propia.<br>
¿Falta tu sala o hay un dato malo? Corregilo: es de todos.
</footer>
<script>
const V = __DATOS__;
const ET = {ancho:"ancho escenario",profundidad:"profundidad escenario",
altura_sobre_sala:"altura escenario",altura_truss:"altura truss",altura_libre:"altura libre",
tiro_proyeccion:"tiro de proyección",ancho_minimo_paso:"paso mínimo",
puerta_ancho:"ancho puerta carga",puerta_alto:"alto puerta carga"};
function filas(v){let h="";
for(const g of ["escenario","sala","acceso"]){const o=v[g]||{};
for(const k in o){const m=o[k];if(!m||typeof m.m!=="number")continue;
h+=`<div class="d"><span>${ET[k]||k}<span class="c ${m.confianza}">${m.confianza}</span></span><span>${m.m} m</span></div>`;}}
for(const c of v.citas||[]) h+=`<div class="d"><span>${c.afirmacion}<span class="c citado">citado</span></span><span>${c.fuente}</span></div>`;
return h||'<div class="d"><span>sin datos todavía</span><span>--</span></div>';}
function pinta(t=""){const q=t.toLowerCase().trim();
document.getElementById("lista").innerHTML=V
.filter(v=>!q||[v.nombre,v.ciudad,v.tipo,v.comuna].join(" ").toLowerCase().includes(q))
.map(v=>`<div class="v"><h2>${v.nombre}</h2>
<div class="meta">${v.ciudad}${v.comuna?" · "+v.comuna:""} · ${v.tipo} · ${v.fecha_captura}</div>
${filas(v)}${v.notas?`<div class="meta" style="margin:8px 0 0">${v.notas}</div>`:""}
<div class="${v.firmado_por?"firma":"nofirma"}">${v.firmado_por?"OK medido y firmado por "+v.firmado_por:"sin firma -- datos aportados, no verificados"}</div>
</div>`).join("")||'<p class="sub">nada coincide.</p>';}
document.getElementById("q").addEventListener("input",e=>pinta(e.target.value));
pinta();
</script>
"""


def sitio() -> int:
    venues = [v for v in cargar_todos() if v.get("publico") is not False]
    datos = json.dumps(
        sorted(venues, key=lambda v: (v.get("ciudad", ""), v.get("nombre", ""))),
        ensure_ascii=False,
    )
    html = PLANTILLA.replace("__DATOS__", datos).replace("__N__", str(len(venues)))
    SALIDA_SITIO.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_SITIO.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    try:
        donde = SALIDA_SITIO.relative_to(REPO)
    except ValueError:  # salida fuera del repo (tests, o ruta absoluta a mano)
        donde = SALIDA_SITIO
    print(f"{donde} · {len(venues)} salas · {kb:.0f} KB")
    ocultos = len(cargar_todos()) - len(venues)
    if ocultos:
        print(f"({ocultos} con publico=false: NO se publicaron)")
    return 0


# --------------------------------------------------------------------------- cli
def propose_projection(setup_path: Path, venue_id: str,
                       apply_now: bool = False) -> int:
    """Proponer el bloque `proyeccion` de un venue desde un ScreenSetup real.

    La regla del modulo es "de memoria no es medido". Un ScreenSetup no es
    memoria: es el archivo que el operador construyo parado en la sala, y su
    topologia de superficies esta medida en pixeles. Lo que NO trae es escala
    metrica, asi que nada fisico se deriva de aca y el residuo lo dice.

    Quien nombra la sala es la persona: el `venue_id` se pasa a mano. Por eso
    esto PROPONE en un archivo aparte y solo escribe el registro con --aplicar.
    """
    sys.path.insert(0, str(REPO / "src"))
    from flujo.venues.resolume_screen_setup import (
        parse_screen_setup, projection_residues, to_projection_fragment,
    )

    record_path = DIR_VENUES / f"{venue_id}.json"
    if not record_path.is_file():
        print(f"no existe el venue {venue_id!r} en {DIR_VENUES}", file=sys.stderr)
        print("la maquina no crea la identidad de una sala: primero "
              "`venue.py sembrar`", file=sys.stderr)
        return 2
    target = json.loads(record_path.read_text(encoding="utf-8"))
    record = parse_screen_setup(setup_path)
    fragment = to_projection_fragment(record)
    new_residues = projection_residues(record)

    candidate = Path(record.source_name).stem
    proposal = {
        "venue_id": venue_id,
        "nombre_actual": target.get("nombre"),
        "fuente": record.source_path,
        "identidad_en_el_archivo": {"candidato": candidate,
                                    "estado": "no_verificado"},
        "coincide_nombre_archivo_con_venue": (
            slug(candidate) in (venue_id, slug(str(target.get("nombre", ""))))),
        "proyeccion_actual": target.get("proyeccion"),
        "proyeccion_propuesta": fragment,
        "residuos_a_agregar": new_residues,
        "firma_requerida": "un humano confirma que este ScreenSetup es de esta sala",
    }
    # Una propuesta NO es un registro de sala. Medido al escribirla dentro de
    # data/venues/: cargar_todos() recorre ese directorio con glob("*.json") y
    # `venue.py validar` la leyo como un venue invalido, 8 errores de esquema.
    # Las propuestas viven al lado, nunca dentro.
    DIR_PROPUESTAS.mkdir(parents=True, exist_ok=True)
    out_path = DIR_PROPUESTAS / f"{venue_id}.proyeccion-propuesta.json"
    out_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=1)
                        + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in proposal.items()
                      if k != "residuos_a_agregar"}, ensure_ascii=False, indent=1))
    print(f"\npropuesta -> {out_path}")
    if not proposal["coincide_nombre_archivo_con_venue"]:
        print(f"AVISO: el archivo se llama {candidate!r} y el venue "
              f"{target.get('nombre')!r}: la correspondencia la afirma el humano,"
              " no el nombre del archivo")
    if not apply_now:
        print("no se escribio el registro. Revisar y volver con --aplicar")
        return 0
    target["proyeccion"] = fragment
    residues = list(target.get("residuos") or [])
    seen = {r.get("descripcion") for r in residues}
    residues.extend(r for r in new_residues
                    if r["descripcion"] not in seen)
    target["residuos"] = residues
    record_path.write_text(json.dumps(target, ensure_ascii=False, indent=1)
                       + "\n", encoding="utf-8")
    print(f"escrito {record_path} ({len(residues)} residuo(s))")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "sembrar":
        if len(argv) < 3:
            print("uso: venue.py sembrar <archivo.txt>", file=sys.stderr)
            return 2
        n = sembrar(Path(argv[2]))
        print(f"\n{n} venues nuevos (confianza: aportado -- de memoria no es medido)")
        return 0
    if cmd == "validar":
        return validar()
    if cmd == "listar":
        return listar()
    if cmd == "geometria":
        return geometria()
    if cmd == "sitio":
        return sitio()
    if cmd == "proyeccion":
        if len(argv) < 4:
            print("uso: venue.py proyeccion <ScreenSetup.xml> <venue-id> "
                  "[--aplicar]", file=sys.stderr)
            return 2
        return propose_projection(Path(argv[2]), argv[3],
                                  "--aplicar" in argv)
    print(__doc__)
    return 0 if cmd in ("", "-h", "--help") else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
