#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Un CONJUNTO de iconos: validarlo y construir su galeria.

    py tools/iconos_conjunto.py validar   --raiz docs/cultura/ensayos/rave
    py tools/iconos_conjunto.py construir --raiz docs/cultura/ensayos/rave

Un conjunto es una carpeta con esta forma:

    <raiz>/iconos/*.svg      la FUENTE, editable a mano
    <raiz>/iconos.json       el manifiesto: n, archivo, slug, titulo,
                             descripcion, estilo (uno por concepto nombrable)
    <raiz>/galeria.html      GENERADO por `construir`. No se edita a mano.

Viene de las tres herramientas que traia el sistema de iconos del ensayo rave,
unificadas y parametrizadas por `--raiz`: eran tres scripts que resolvian sus
rutas con `__file__.parent.parent` y por lo tanto solo servian a SU carpeta.
Ahora sirven a cualquier conjunto, que es lo que hace falta si MAK va a producir
un anexo iconografico por ensayo.

El estilo NO se unifica entre iconos a proposito: cada tema pide su propia
presentacion (decision del usuario, 2026-07-30). El validador cuida que no se
ROMPAN, no que se parezcan.

NO hay subcomando de exportar a PNG, y es deliberado (usuario, 2026-07-30): un
humano ve un SVG. El rasterizado existe UNA sola vez y en el unico lugar donde
hace falta -- `motor_semantico/rasterizador.py`, como organo del critico
perceptual, que mide sobre pixeles porque "hay jerarquia" o "sobrevive a 24px"
no se deducen del codigo.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO / "cultura" / "mak_codex"))

OK, AVISO, ERROR = "  OK", "  ! ", "  x "


# --------------------------------------------------------------------------
# validar
# --------------------------------------------------------------------------
def revisar(ruta: Path) -> tuple[list[str], list[str]]:
    """Las siete clases de error de un icono editado a mano.

    La clase 3 (una var(--x) usada y no declarada) es la que atrapo el defecto
    de quien escribio el validador: una refactorizacion automatica sustituyo
    `4s` dentro de `3.4s` y produjo `3.var(--vel)`. Un validador que encuentra
    el error de su propio autor es la mejor senal de que sirve.
    """
    txt = ruta.read_text(encoding="utf-8")
    errores: list[str] = []
    avisos: list[str] = []

    # 1. XML bien formado
    try:
        ET.fromstring(txt.split("?>", 1)[-1])
    except ET.ParseError as e:
        return ["XML mal formado: %s" % e], avisos   # lo demas no tiene sentido

    # 2. viewBox
    vb = re.search(r'viewBox="([^"]+)"', txt)
    if not vb:
        errores.append("falta viewBox")
    elif vb.group(1).split() != ["0", "0", "120", "120"]:
        avisos.append('viewBox cambiado a "%s" (el original es 0 0 120 120)'
                      % vb.group(1))

    # 3. variables CSS declaradas contra usadas
    declaradas = set(re.findall(r"--([a-z0-9-]+)\s*:", txt))
    usadas = set(re.findall(r"var\(--([a-z0-9-]+)\)", txt))
    for v in sorted(usadas - declaradas):
        errores.append("var(--%s) usada pero NO declarada en la paleta" % v)
    for v in sorted(declaradas - usadas):
        avisos.append("--%s declarada pero sin usar (inofensivo)" % v)

    # 4. animation -> @keyframes
    kf = set(re.findall(r"@keyframes\s+([A-Za-z0-9_-]+)", txt))
    ref = set(re.findall(r"animation:\s*([A-Za-z][A-Za-z0-9_-]*)", txt))
    for k in sorted(ref - kf):
        errores.append("animation llama a '%s' y no existe @keyframes %s" % (k, k))
    for k in sorted(kf - ref):
        avisos.append("@keyframes %s definido y nadie lo usa" % k)

    # 5. clases del CSS contra clases del marcado
    estilo = "".join(re.findall(r"<style>(.*?)</style>", txt, re.S))
    css_cls = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", estilo))
    marcado = re.sub(r"<style>.*?</style>", "", txt, flags=re.S)
    usa_cls: set[str] = set()
    for grupo in re.findall(r'class="([^"]+)"', marcado):
        usa_cls.update(grupo.split())
    for c in sorted(css_cls - usa_cls):
        avisos.append("regla .%s sin elementos que la usen (animacion muerta)" % c)
    for c in sorted(usa_cls - css_cls):
        avisos.append('class="%s" sin regla CSS (elemento sin animar)' % c)

    # 6. ids duplicados
    ids = re.findall(r'\sid="([^"]+)"', txt)
    for i in sorted({x for x in ids if ids.count(x) > 1}):
        errores.append('id="%s" duplicado' % i)

    # 7. url(#x) que no apunta a nada
    for r in sorted(set(re.findall(r"url\(#([^)]+)\)", txt))):
        if r not in ids:
            errores.append("url(#%s) apunta a un id inexistente" % r)

    return errores, avisos


def cmd_validar(raiz: Path, _args) -> int:
    archivos = sorted((raiz / "iconos").glob("*.svg"))
    if not archivos:
        print("no hay .svg en %s/iconos" % raiz, file=sys.stderr)
        return 1
    tot_e = tot_a = 0
    for f in archivos:
        e, a = revisar(f)
        tot_e += len(e)
        tot_a += len(a)
        if e or a:
            print("\n%s" % f.name)
            for m in e:
                print(ERROR + m)
            for m in a:
                print(AVISO + m)
        else:
            print(OK + " " + f.name)
    print("\n%s\n%d archivos - %d errores - %d avisos"
          % ("-" * 54, len(archivos), tot_e, tot_a))
    if tot_e:
        print("Los errores (x) rompen el icono; los avisos (!) no.")
        return 1
    print("Todo en orden. `construir` regenera la galeria.")
    return 0


# --------------------------------------------------------------------------
# construir
# --------------------------------------------------------------------------
CSS = """
:root{--bg:#08080b;--panel:#101017;--line:#23232e;--ink:#f2f2f5;--dim:#8b8b9c;--acid:#d7ff2e}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(900px 500px at 15% -10%,#16162150,transparent 70%),
 radial-gradient(800px 500px at 95% 10%,#1c0f2050,transparent 70%),var(--bg);
 color:var(--ink);font-family:"Inter","Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
header{padding:56px 32px 26px;max-width:1400px;margin:0 auto}
.eyebrow{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.34em;color:var(--acid);text-transform:uppercase}
h1{font-size:clamp(30px,5.2vw,58px);line-height:.98;margin:16px 0 10px;letter-spacing:-.03em;font-weight:800}
h1 span{color:var(--dim);font-weight:300}
.sub{color:var(--dim);max-width:72ch;font-size:15px;line-height:1.6;margin:0}
.bar{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
button{background:#15151d;color:var(--ink);border:1px solid var(--line);padding:9px 15px;border-radius:999px;
 cursor:pointer;font:600 12px/1 ui-monospace,Menlo,monospace;letter-spacing:.06em;transition:.18s}
button:hover{border-color:var(--acid);color:var(--acid)}
button.on{background:var(--acid);color:#000;border-color:var(--acid)}
main{max-width:1400px;margin:0 auto;padding:14px 32px 90px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:22px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:18px 18px 16px;
 display:flex;flex-direction:column;gap:12px;transition:.22s;position:relative;overflow:hidden}
.card:hover{border-color:#3a3a4a;transform:translateY(-3px)}
.num{position:absolute;top:14px;right:16px;font:700 11px/1 ui-monospace,Menlo,monospace;color:#3c3c4c;letter-spacing:.1em}
.ico{width:100%;aspect-ratio:1;display:block;border-radius:14px;background:#000;overflow:hidden}
.meta h2{font-size:15.5px;margin:0 0 5px;letter-spacing:-.01em;line-height:1.25}
.meta p{margin:0;font-size:12.5px;line-height:1.5;color:var(--dim)}
.tags{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:auto;padding-top:4px}
.style{font:600 9.5px/1 ui-monospace,Menlo,monospace;letter-spacing:.13em;color:#5f5f72;text-transform:uppercase}
.dl{background:none;border:1px solid var(--line);padding:6px 10px;font-size:9.5px;border-radius:8px;letter-spacing:.1em}
body.paused .ico *{animation-play-state:paused!important}
footer{max-width:1400px;margin:0 auto;padding:0 32px 70px;color:#54546a;font-size:12px;line-height:1.7}
.taller{max-width:1400px;margin:0 auto;padding:0 32px 70px}
.taller h2{font-size:20px;letter-spacing:-.01em;margin:0 0 6px}
.taller p{color:var(--dim);font-size:13px;line-height:1.6;max-width:74ch;margin:0 0 14px}
.taller .fila{display:grid;grid-template-columns:minmax(280px,1fr) 260px;gap:18px;align-items:start}
.taller textarea{width:100%;min-height:210px;background:#0c0c12;color:var(--ink);border:1px solid var(--line);
 border-radius:14px;padding:14px;font:12.5px/1.55 ui-monospace,Menlo,monospace;resize:vertical}
.taller .salida{background:#000;border:1px solid var(--line);border-radius:14px;aspect-ratio:1;overflow:hidden}
.taller .salida svg{width:100%;height:100%;display:block}
.taller .aviso{font:12px/1.6 ui-monospace,Menlo,monospace;color:#8b8b9c;white-space:pre-wrap;margin-top:10px}
.taller .aviso.mal{color:#ff7a9c}
@media(max-width:760px){.taller .fila{grid-template-columns:1fr}}
@media(max-width:640px){header{padding:34px 18px 18px}main{padding:8px 18px 60px}footer{padding:0 18px 50px}
 .taller{padding:0 18px 50px}}
"""

JS = """
document.getElementById('toggle').addEventListener('click',e=>{
  document.body.classList.toggle('paused');
  const p=document.body.classList.contains('paused');
  e.target.textContent=p?'\\u25b6 REANUDAR ANIMACIONES':'\\u23f8 PAUSAR ANIMACIONES';
  e.target.classList.toggle('on',p);
});
document.getElementById('light').addEventListener('click',e=>{
  const l=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()!=='#ececef';
  const s=document.documentElement.style;
  s.setProperty('--bg',l?'#ececef':'#08080b');
  s.setProperty('--panel',l?'#ffffff':'#101017');
  s.setProperty('--line',l?'#dcdce2':'#23232e');
  s.setProperty('--ink',l?'#101014':'#f2f2f5');
  s.setProperty('--dim',l?'#63636f':'#8b8b9c');
  e.target.classList.toggle('on',l);
});
function grab(svg){
  const c=svg.cloneNode(true);
  c.setAttribute('xmlns','http://www.w3.org/2000/svg');
  c.removeAttribute('class');
  return new Blob(['<?xml version="1.0" encoding="UTF-8"?>\\n'+c.outerHTML],{type:'image/svg+xml'});
}
function save(blob,name){
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),3000);
}
document.querySelectorAll('.dl').forEach(b=>b.addEventListener('click',()=>{
  const svg=b.closest('.card').querySelector('svg');
  save(grab(svg),svg.dataset.name+'.svg');
}));
document.getElementById('dlall').addEventListener('click',()=>{
  document.querySelectorAll('.card svg').forEach((s,i)=>setTimeout(()=>save(grab(s),s.dataset.name+'.svg'),i*280));
});
"""

# El taller: el MISMO spec que compila el motor en la caja, compilado aca en el
# navegador sobre @thi.ng/hiccup-svg. Se carga con import() dinamico y si la
# libreria no esta, el panel se esconde y la galeria sigue funcionando: una
# pagina estatica no puede depender de que alguien haya corrido un script.
JS_TALLER = """
(async () => {
  const panel = document.getElementById('taller');
  if (!panel) return;
  try {
    const [{compilar, ErrorSemantico}, vocab] = await Promise.all([
      import('__LIB__/compilador.js'),
      fetch('__LIB__/vocabulario.json').then(r => r.json()),
    ]);
    const area = document.getElementById('spec');
    const salida = document.getElementById('salida');
    const aviso = document.getElementById('aviso');
    const pintar = () => {
      try {
        const spec = JSON.parse(area.value);
        const {svg, avisos} = compilar(spec, vocab, spec.slug || 'taller');
        salida.innerHTML = svg;
        aviso.className = 'aviso';
        aviso.textContent = avisos.length
          ? 'compilado, con avisos:\\n- ' + avisos.join('\\n- ')
          : 'compilado sin avisos.';
      } catch (e) {
        aviso.className = 'aviso mal';
        aviso.textContent = (e instanceof ErrorSemantico)
          ? 'rechazado por el motor:\\n' + e.message
          : 'JSON invalido: ' + e.message;
      }
    };
    area.addEventListener('input', pintar);
    document.getElementById('compilar').addEventListener('click', pintar);
    panel.hidden = false;
    pintar();
  } catch (e) {
    // La galeria no se rompe por esto: el taller es un extra.
    panel.hidden = true;
  }
})();
"""

SPEC_EJEMPLO = {
    "slug": "muro-que-emite",
    "titulo": "El muro que se parte",
    "brief": "dos muros se abren y liberan una onda",
    "composicion": "confrontacion",
    "tono": "concreto",
    "capas": [
        {"rol": "lado_izq", "figura": "muro", "gesto": "desplazar_fuera",
         "ritmo": "lento"},
        {"rol": "lado_der", "figura": "muro", "gesto": "desplazar_fuera",
         "ritmo": "lento"},
        {"rol": "protagonista", "figura": "onda", "gesto": "emanar",
         "ritmo": "rapido"},
    ],
}


def _escapar(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def inyectar(svg_txt: str) -> str:
    """Prepara el SVG para vivir dentro del HTML sin colisionar."""
    svg = svg_txt.split("?>", 1)[-1].strip()
    return re.sub(r"<svg ", '<svg class="ico" ', svg, count=1)


def cmd_construir(raiz: Path, args) -> int:
    manifiesto_path = raiz / "iconos.json"
    if not manifiesto_path.is_file():
        print("falta %s" % manifiesto_path, file=sys.stderr)
        return 1
    manifiesto = json.loads(manifiesto_path.read_text(encoding="utf-8"))
    titulo = args.titulo or raiz.name.upper()

    tarjetas, faltantes = [], []
    for it in manifiesto:
        ruta = raiz / "iconos" / it["archivo"]
        if not ruta.is_file():
            faltantes.append(it["archivo"])
            continue
        svg = inyectar(ruta.read_text(encoding="utf-8"))
        svg = svg.replace("<svg class=\"ico\" ",
                          '<svg class="ico" data-name="%s" ' % it["slug"], 1)
        tarjetas.append(
            '<article class="card"><span class="num">%s</span>\n%s\n'
            '<div class="meta"><h2>%s</h2><p>%s</p></div>\n'
            '<div class="tags"><span class="style">%s</span>'
            '<button class="dl">SVG</button></div>\n</article>'
            % (_escapar(it["n"]), svg, _escapar(it["titulo"]),
               _escapar(it["descripcion"]), _escapar(it["estilo"])))

    # ruta relativa desde la galeria hasta docs/cultura/lib
    lib = Path("docs/cultura/lib")
    try:
        rel = "/".join([".."] * len(raiz.resolve().relative_to(
            (RAIZ_REPO / "docs" / "cultura").resolve()).parts)) + "/lib"
    except ValueError:
        rel = str((RAIZ_REPO / lib).resolve().as_uri())

    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(titulo)s - %(n)d iconos animados</title>
<style>%(css)s</style>
</head>
<body>
<header>
  <div class="eyebrow">Anexo iconografico - %(n)d piezas - SVG animado</div>
  <h1>%(titulo)s <span>/ un icono por concepto nombrable</span></h1>
  <p class="sub">Galeria GENERADA desde <code>iconos/</code> y
  <code>iconos.json</code>. Edita cualquier <code>.svg</code> y vuelve a correr
  <code>py tools/iconos_conjunto.py construir</code>. Cada pieza tiene su propio
  lenguaje visual a proposito: cada tema pide su propia presentacion.</p>
  <div class="bar">
    <button id="toggle">&#9208; PAUSAR ANIMACIONES</button>
    <button id="light">&#9689; FONDO CLARO</button>
    <button id="dlall">&#10515; DESCARGAR TODOS LOS SVG</button>
  </div>
</header>
<main><div class="grid">
%(tarjetas)s
</div></main>
<section class="taller" id="taller" hidden>
  <h2>Taller: el motor semantico, aca mismo</h2>
  <p>Los 16 de arriba estan escritos a mano. Esto es lo otro: una spec de
  SIGNIFICADO -- vocabulario cerrado, sin coordenadas ni colores -- compilada a
  SVG animado <strong>en tu navegador</strong>, con el mismo vocabulario que usa
  el motor en la caja. Cambia una palabra y mira lo que pasa; si escribes una
  que no existe, el motor te dice cuales son las validas.</p>
  <div class="fila">
    <div>
      <textarea id="spec" spellcheck="false">%(ejemplo)s</textarea>
      <button id="compilar">COMPILAR</button>
      <div class="aviso" id="aviso"></div>
    </div>
    <div class="salida" id="salida"></div>
  </div>
</section>
<footer></footer>
<script>%(js)s</script>
<script type="module">%(js_taller)s</script>
</body>
</html>
""" % {"titulo": _escapar(titulo), "n": len(tarjetas), "css": CSS,
       "tarjetas": "\n".join(tarjetas), "js": JS,
       "js_taller": JS_TALLER.replace("__LIB__", rel),
       "ejemplo": _escapar(json.dumps(SPEC_EJEMPLO, ensure_ascii=False,
                                      indent=1))}

    salida = raiz / "galeria.html"
    salida.write_text(html, encoding="utf-8")
    print("OK %s (%d iconos, %.1f KB, taller -> %s)"
          % (salida, len(tarjetas), len(html.encode("utf-8")) / 1024, rel))
    if faltantes:
        print("! declarados en el manifiesto y no encontrados: %s"
              % ", ".join(faltantes), file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------
# animar
# --------------------------------------------------------------------------
def resolver_vars(svg: str) -> str:
    """Sustituye cada var(--x) por su valor declarado.

    Los iconos escritos a mano declaran su paleta como variables CSS. El
    backend cairosvg no las implementa y dibujaria todo en negro; un navegador
    no lo necesita. Aplicarlo siempre mantiene el resultado identico entre los
    dos backends, que es la condicion para que el GIF sirva de prueba.
    """
    valores = dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;}\n]+)", svg))

    def _reemplazo(m):
        return valores.get(m.group(1), m.group(0)).strip()

    return re.sub(r"var\(--([a-z0-9-]+)\)", _reemplazo, svg)


def cmd_animar(raiz: Path, args) -> int:
    """GIF animado por icono. NO es un entregable: es la unica forma de
    verificar que la animacion existe -- un cuadro suelto no distingue quieto
    de animado, y el artefacto es una animacion (usuario, 2026-07-30). Sale al
    scratchpad o a donde diga --salida, nunca al repo."""
    from motor_semantico import rasterizador

    if rasterizador.backend_disponible(anima=True) is None:
        print("no hay backend que ejecute animaciones CSS en esta maquina "
              "(hay para rasterizar: %s). Medir movimiento pide un navegador: "
              "Edge o Chrome/Chromium." % (rasterizador.backend_disponible()
                                           or "ninguno"), file=sys.stderr)
        return 1
    destino = (args.salida or (raiz / "_animados")).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    archivos = sorted((raiz / "iconos").glob("*.svg"))
    if not archivos:
        print("no hay .svg en %s/iconos" % raiz, file=sys.stderr)
        return 1
    quietos, fallos = [], 0
    for f in archivos:
        svg = resolver_vars(f.read_text(encoding="utf-8"))
        try:
            ruta, n, distintos = rasterizador.animar(
                svg, destino / (f.stem + ".gif"), cuadros=args.cuadros,
                tam=args.tam)
        except (rasterizador.RasterizadorNoDisponibleError, ValueError) as e:
            print(ERROR + "%s: %s" % (f.name, e), file=sys.stderr)
            fallos += 1
            continue
        if distintos <= 1:
            quietos.append(f.stem)
        print("%s %s (%d/%d cuadros distintos, %.1f KB)"
              % (AVISO if distintos <= 1 else OK, ruta.name, distintos, n,
                 ruta.stat().st_size / 1024))
    print("\n%d GIF en %s" % (len(archivos) - fallos, destino))
    if quietos:
        print("! sin movimiento medido (%d): %s" % (len(quietos),
                                                    ", ".join(quietos)),
              file=sys.stderr)
    return 1 if fallos else 0


# --------------------------------------------------------------------------
COMANDOS = {"validar": cmd_validar, "construir": cmd_construir,
            "animar": cmd_animar}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=sorted(COMANDOS))
    ap.add_argument("--raiz", type=Path, required=True,
                    help="carpeta del conjunto (con iconos/ y iconos.json)")
    ap.add_argument("--titulo", default=None, help="titulo de la galeria")
    ap.add_argument("--cuadros", type=int, default=12,
                    help="cuadros del GIF (animar)")
    ap.add_argument("--tam", type=int, default=256, help="px del GIF (animar)")
    ap.add_argument("--salida", type=Path, default=None,
                    help="donde dejar los GIF; por defecto <raiz>/_animados, "
                         "que NO entra al repo")
    a = ap.parse_args()
    raiz = a.raiz.resolve()
    if not raiz.is_dir():
        print("no existe %s" % raiz, file=sys.stderr)
        return 1
    return COMANDOS[a.comando](raiz, a)


if __name__ == "__main__":
    raise SystemExit(main())
