#!/usr/bin/env python3
"""Las librerias de la cara visible de iskvw, empaquetadas para un sitio estatico.

Por que existe. La piel de iskvw se publica como HTML estatico: no hay build al
desplegar, no se puede depender de un CDN y tiene que abrir sin internet. Las
librerias que sirven (thi.ng) son paquetes ESM de npm con dependencias, asi que
un `<script src>` no alcanza. Este script las deja como UN modulo ESM
autocontenido por libreria, y la piel las importa con un import normal.

Que se agrega y que no lo decide `data/iskvw_librerias.json`, que edita el
usuario. Agregar una libreria es agregar una entrada ahi y correr esto:

    py tools/vendorizar_iskvw.py
    py tools/vendorizar_iskvw.py --verificar   # no baja nada, solo audita

Necesita node y npx (esbuild se baja solo). Si no estan, no se inventa un
bundle: se falla diciendo que falta.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MANIFIESTO = RAIZ / "data" / "iskvw_librerias.json"
DESTINO = RAIZ / "iskvw" / "piel" / "lib"


def leer(ruta: Path = MANIFIESTO) -> list[dict]:
    """Las entradas del manifiesto, validadas. Una entrada incompleta se dice.

    No se rellena un default silencioso: una libreria sin version es una
    libreria que cambia sola debajo de una pieza, que es como una pieza se
    rompe sin que nadie haya tocado nada.
    """
    d = json.loads(ruta.read_text(encoding="utf-8"))
    libs = d.get("librerias") or []
    for i, e in enumerate(libs):
        faltan = [k for k in ("nombre", "paquete", "version", "para")
                  if not e.get(k)]
        if faltan:
            raise ValueError(
                f"{ruta.name}: la entrada {i} no declara {', '.join(faltan)}. "
                f"Si no se puede escribir para que sirve, no entra")
    nombres = [e["nombre"] for e in libs]
    dup = {n for n in nombres if nombres.count(n) > 1}
    if dup:
        raise ValueError(f"{ruta.name}: nombres repetidos: {', '.join(sorted(dup))}")
    return libs


def huerfanos(libs: list[dict], destino: Path = DESTINO) -> list[str]:
    """Bundles VENDORIZADOS en disco que ya no estan declarados. Se informan,
    no se borran.

    Un bundle vendorizado se reconoce por su `<nombre>.README.md` al lado --
    la misma convencion que escribe `vendorizar()`. Sin ese filtro, cualquier
    `.js` escrito a mano en la carpeta destino se reporta como sobrante:
    medido el 2026-07-30 sobre `docs/cultura/lib/`, donde vive
    `compilador.js`, el gemelo de navegador del motor semantico. Decirle
    "sobra y no esta declarado" a un archivo escrito a mano es la clase de
    aviso por la que alguien lo borra.
    """
    if not destino.is_dir():
        return []
    declarados = {e["nombre"] + ".js" for e in libs}
    return sorted(p.name for p in destino.glob("*.js")
                  if p.name not in declarados
                  and p.with_suffix(".README.md").is_file())


def _npx() -> str:
    for cmd in ("npx.cmd", "npx"):
        if shutil.which(cmd):
            return cmd
    raise RuntimeError("no encuentro npx: hace falta node para empaquetar")


def vendorizar(entrada: dict, destino: Path = DESTINO) -> Path:
    """Un paquete npm -> un modulo ESM autocontenido, con la version fijada."""
    npx = _npx()
    salida = destino / f"{entrada['nombre']}.js"
    destino.mkdir(parents=True, exist_ok=True)
    spec = f"{entrada['paquete']}@{entrada['version']}"
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        entrada_js = t / "entrada.js"
        exporta = entrada.get("exporta") or "*"
        entrada_js.write_text(
            f'export {exporta} from "{entrada["paquete"]}";\n', encoding="utf-8")
        subprocess.run(
            ["npm.cmd" if shutil.which("npm.cmd") else "npm",
             "install", "--silent", "--no-audit", "--no-fund", spec],
            cwd=t, check=True, capture_output=True, text=True)
        subprocess.run(
            [npx, "--yes", "esbuild", str(entrada_js), "--bundle",
             "--format=esm", "--platform=browser", "--minify",
             f"--outfile={salida}"],
            cwd=t, check=True, capture_output=True, text=True)

        # El README viaja al lado del bundle. Medido el 2026-07-27: el bundle
        # minificado no dice como se llama a nada, y adivinar la firma cuesta
        # tiempo y produce codigo que "compila" y no hace lo que se cree --
        # `new TSNE(data, opts)` no es `new TSNE({data})`, y la dimension de
        # salida no es un parametro obvio. Con el README al lado, el proximo que
        # la use lee la fuente en vez de especular, y funciona sin internet.
        raiz_pkg = t / "node_modules" / Path(*entrada["paquete"].split("/"))
        for nombre in ("README.md", "readme.md"):
            doc = raiz_pkg / nombre
            if doc.is_file():
                (salida.with_suffix(".README.md")).write_text(
                    doc.read_text(encoding="utf-8", errors="replace"),
                    encoding="utf-8")
                break
    return salida


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifiesto", type=Path, default=MANIFIESTO)
    ap.add_argument("--destino", type=Path, default=DESTINO)
    ap.add_argument("--verificar", action="store_true",
                    help="no baja nada: dice que falta y que sobra")
    ap.add_argument("--solo", default=None, help="un nombre del manifiesto")
    args = ap.parse_args()
    # --destino tiene que ser ABSOLUTO: esbuild corre con cwd en un directorio
    # temporal, asi que un `--outfile=docs/cultura/lib/x.js` relativo se
    # resuelve contra ESE temporal y el bundle se escribe donde nadie lo ve
    # (medido el 2026-07-30: quedo el README y no quedo el .js).
    args.destino = args.destino.resolve()

    try:
        libs = leer(args.manifiesto)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.solo:
        libs = [e for e in libs if e["nombre"] == args.solo]
        if not libs:
            print(f"error: '{args.solo}' no esta en el manifiesto", file=sys.stderr)
            return 1

    sobrantes = huerfanos(leer(args.manifiesto), args.destino)
    if sobrantes:
        print("sobran en disco y no estan declarados: " + ", ".join(sobrantes),
              file=sys.stderr)

    if args.verificar:
        faltan = [e["nombre"] for e in libs
                  if not (args.destino / f"{e['nombre']}.js").is_file()]
        for e in libs:
            p = args.destino / f"{e['nombre']}.js"
            estado = f"{p.stat().st_size / 1024:.1f} KB" if p.is_file() else "FALTA"
            print(f"  {e['nombre']:<10} {e['paquete']}@{e['version']:<10} {estado}")
        if faltan:
            print("faltan por vendorizar: " + ", ".join(faltan), file=sys.stderr)
            return 1
        return 0

    fallos = 0
    for e in libs:
        try:
            p = vendorizar(e, args.destino)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            detalle = getattr(exc, "stderr", "") or str(exc)
            print(f"  {e['nombre']:<10} FALLO: {detalle.strip()[:200]}",
                  file=sys.stderr)
            fallos += 1
            continue
        try:
            mostrar = p.relative_to(RAIZ)
        except ValueError:          # un destino fuera del repo sigue siendo valido
            mostrar = p
        print(f"  {e['nombre']:<10} {e['paquete']}@{e['version']} -> "
              f"{mostrar} ({p.stat().st_size / 1024:.1f} KB)")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
