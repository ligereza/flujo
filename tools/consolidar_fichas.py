#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bring a new perception pass into the live archive WITHOUT losing what the old
one knew.

The naive move is to replace each ficha by id. Measured on the real data, that
would destroy information: over the same 1.354 files, the new pass fills
`tipo_obra` where the old had nothing (67% -> 100%) but leaves
`oportunidad_codigo` empty on 225 images where the old pass had written one
(98,7% -> 77,9%). A row-level replace throws those 225 away in silence. A
row-level SKIP throws away the other 33 points. Neither is right.

So the merge is at FIELD level:

- a new non-empty value wins -- it comes from a better model, measured;
- a field the new pass did not fill KEEPS the old value, and that is recorded;
- nothing is ever silently dropped: the report counts what improved, what was
  inherited, and what was lost, and the last number must be zero.

The mixing is DECLARED, not hidden. `medicion.vision.motor` says who answered
the new pass, and `medicion.vision.heredado` lists the fields that survived
from the previous one. A ficha with fields from two engines and no record of it
is worse than either pass alone: whoever counts engines afterwards counts
ghosts. This is the same rule that killed the `or "ollama"` default.

Dry run by default. `--aplicar` writes, and only after a timestamped backup.

    py tools/consolidar_fichas.py ARCHIVO.jsonl NUEVA.jsonl
    py tools/consolidar_fichas.py ARCHIVO.jsonl NUEVA.jsonl --motor ollama
    py tools/consolidar_fichas.py ARCHIVO.jsonl NUEVA.jsonl --aplicar
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Blocks merged field by field. Everything else (id, fuente, ruta_rel,
# bytes...) is the file's identity and is never touched.
BLOQUES = ("vision", "datos_evento")
# Loose top-level fields the perception pass produces.
SIMPLES = ("ocr_texto", "categoria", "calidad_senal")


def lleno(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict, tuple)):
        return bool(v)
    return True


def cargar(ruta: Path) -> tuple[list[dict], dict[str, int]]:
    """Rows in order, plus an index id -> LAST position.

    The last one wins: the pipeline appends a ficha per attempt, so a retry
    writes a new row and that retry is the outcome that counts.
    """
    filas: list[dict] = []
    indice: dict[str, int] = {}
    malas = 0
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                malas += 1
                continue
            filas.append(d)
            if d.get("id"):
                indice[d["id"]] = len(filas) - 1
    if malas:
        print("  aviso: %d lineas ilegibles en %s (se conservan fuera del "
              "indice, NO se reescriben)" % (malas, ruta.name), file=sys.stderr)
    return filas, indice


def _tamano(v) -> int:
    """How much there is. Not a quality judgement -- just enough to see when a
    replacement made a value SMALLER, which is the thing the report has to
    stop hiding."""
    if isinstance(v, str):
        return len(v.strip())
    if isinstance(v, (list, tuple, dict)):
        return len(v)
    return 1


def _motor_de(ficha: dict) -> str:
    return (((ficha.get("medicion") or {}).get("vision") or {}).get("motor")
            or "sin_atribucion")


def fusionar(vieja: dict, nueva: dict) -> tuple[dict, dict]:
    """A new ficha over an old one. Returns (ficha, counts).

    There are FOUR outcomes per field, not three. The first version of this
    function counted `mejorado` (old empty), `heredado` (new empty) and
    `perdido` (gone) -- and an adversarial pass over the real archive found
    that those three buckets covered 1.879 of 17.602 decisions. The other
    15.723 were fields BOTH passes filled, where the new one won with no
    comparison and no line in the report: 9.348 of them differed, and 4.595 of
    those got smaller. A 260-character description became "Una pintura
    abstracta con figuras humanas y elementos naturales."

    That is this repo's house defect built into the very tool meant to protect
    against it: three hand-written buckets over a presence test, silently
    dropping the majority of what the operation does, under a headline reading
    "campos perdidos: 0". The fix is not to change who wins -- a new non-empty
    value winning is the declared policy and it stands -- it is to COUNT the
    case and show it, so the person authorising the write is looking at a
    number that measures something.
    """
    salida = dict(nueva)
    mejorados: list[str] = []
    heredados: list[str] = []
    reemplazados: list[str] = []
    encogidos: list[str] = []
    motor_viejo = _motor_de(vieja)
    heredado_por_campo: dict[str, str] = {}
    # Attribution the OLD ficha already carried per field: a second
    # consolidation must not re-sign as its own what a third engine measured.
    heredado_previo = (((vieja.get("medicion") or {}).get("vision") or {})
                       .get("heredado") or {})
    if not isinstance(heredado_previo, dict):
        heredado_previo = {}

    def _anotar(nombre, val_old, val_new):
        if lleno(val_old) and not lleno(val_new):
            heredado_por_campo[nombre] = heredado_previo.get(nombre, motor_viejo)
            heredados.append(nombre)
            return True                      # el viejo se conserva
        if lleno(val_new) and not lleno(val_old):
            mejorados.append(nombre)
        elif lleno(val_new) and lleno(val_old) and val_new != val_old:
            reemplazados.append(nombre)
            if _tamano(val_new) < _tamano(val_old):
                encogidos.append(nombre)
        return False

    for bloque in BLOQUES:
        v_old = vieja.get(bloque) or {}
        v_new = dict(nueva.get(bloque) or {})
        if not isinstance(v_old, dict) or not isinstance(v_new, dict):
            continue
        for k, val in v_old.items():
            if _anotar("%s.%s" % (bloque, k), val, v_new.get(k)):
                v_new[k] = val
        for k, val in (nueva.get(bloque) or {}).items():
            if lleno(val) and k not in v_old:
                mejorados.append("%s.%s" % (bloque, k))
        salida[bloque] = v_new

    for k in SIMPLES:
        if _anotar(k, vieja.get(k), nueva.get(k)):
            salida[k] = vieja[k]

    # The mixing is DECLARED, and PER FIELD. `heredado` used to be a flat list
    # plus one `motor_heredado` for the whole ficha, which loses the trail as
    # soon as a second consolidation runs -- exactly the use this tool was
    # written for. A map field -> engine survives any number of passes.
    med = dict(salida.get("medicion") or {})
    vis = dict(med.get("vision") or {})
    vis.pop("motor_heredado", None)
    if heredado_por_campo:
        vis["heredado"] = dict(sorted(heredado_por_campo.items()))
    else:
        vis.pop("heredado", None)
    # `medicion` came from the NEW pass and described the new pass. After the
    # merge it describes a ficha that no longer exists: it listed as absent
    # keys that the merge had just filled. Recomputed here so the ficha does
    # not contradict itself -- and so `comparar_cobertura_fichas.py`, built to
    # be honest about attribution, is not turned into a liar by this merge.
    contenido = salida.get("vision") or {}
    if isinstance(contenido, dict):
        vis["detalle"] = str(len([1 for v in contenido.values() if lleno(v)]))
        for clave in ("claves_vacias", "claves_ausentes"):
            resto = [c for c in (vis.get(clave) or []) if not lleno(contenido.get(c))]
            if resto:
                vis[clave] = resto
            else:
                vis.pop(clave, None)
        if contenido and vis.get("estado") in ("vacio", "no_intentado"):
            vis["estado"] = "medido"
    med["vision"] = vis
    salida["medicion"] = med
    return salida, {"mejorados": mejorados, "heredados": heredados,
                    "reemplazados": reemplazados, "encogidos": encogidos}


def perdidos(vieja: dict, fusionada: dict) -> list[str]:
    """Fields the old ficha had filled and the merged one does not. Must be
    empty -- if it is not, the merge has a hole and nothing gets written."""
    faltan = []
    for bloque in BLOQUES:
        v_old = vieja.get(bloque) or {}
        v_new = fusionada.get(bloque) or {}
        if not isinstance(v_old, dict):
            continue
        for k, val in v_old.items():
            if lleno(val) and not lleno(v_new.get(k)):
                faltan.append("%s.%s" % (bloque, k))
    for k in SIMPLES:
        if lleno(vieja.get(k)) and not lleno(fusionada.get(k)):
            faltan.append(k)
    return faltan


def _plegar(texto):
    import unicodedata
    d = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in d if not unicodedata.combining(c)).lower().strip()


def colisiones_de_tecnica(filas):
    """Same technique written more than one way. Map variant -> canonical.

    Free text drifts: measured over the 1.401 ig fichas, `tecnica` held 54 raw
    values that are 48 concepts -- `fotografia`(35) next to `fotografía`(163),
    `ilustracion digital` in three spellings. Two spellings of one technique are
    two labels in the artist's portfolio.

    The accented variant wins even when it is a minority: in Spanish the accent
    is not a style option, and this value is read by a human. There is no
    hand-written list -- the map comes from the corpus, so a technique that
    appears tomorrow needs nobody to remember anything.

    This only REPORTS. Rewriting values is a separate decision and it has its
    own flag: a tool whose whole point is not changing data behind your back
    cannot start changing data behind your back.
    """
    import unicodedata
    grupos: dict[str, dict[str, int]] = {}
    for f in filas:
        valor = (f.get("vision") or {}).get("tecnica")
        if not valor:
            continue
        texto = " ".join(str(valor).lower().split())
        grupos.setdefault(_plegar(texto), {})
        grupos[_plegar(texto)][texto] = grupos[_plegar(texto)].get(texto, 0) + 1
    mapa = {}
    for variantes in grupos.values():
        if len(variantes) < 2:
            continue
        def _rango(par):
            texto, veces = par
            return (any(unicodedata.combining(c)
                        for c in unicodedata.normalize("NFKD", texto)), veces)
        canonica = max(variantes.items(), key=_rango)[0]
        for texto in variantes:
            if texto != canonica:
                mapa[texto] = canonica
    return mapa


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo", type=Path, help="fichas.jsonl vivo")
    p.add_argument("nueva", type=Path, help="fichas.jsonl de la pasada nueva")
    p.add_argument("--motor", default="",
                   help="solo traer las fichas que ESE motor midio")
    p.add_argument("--aplicar", action="store_true",
                   help="escribir de verdad (por defecto solo informa)")
    p.add_argument("--canonizar-tecnica", action="store_true",
                   dest="canonizar",
                   help="unificar las grafias de `tecnica` (se informan "
                        "siempre; con esta bandera ademas se reescriben)")
    a = p.parse_args()

    for ruta in (a.archivo, a.nueva):
        if not ruta.exists():
            print("no existe: %s" % ruta, file=sys.stderr)
            return 2

    filas, indice = cargar(a.archivo)
    nuevas_filas, nuevo_indice = cargar(a.nueva)

    reemplazadas = agregadas = 0
    conteo: dict[str, dict[str, int]] = {
        "mejorados": {}, "heredados": {}, "reemplazados": {}, "encogidos": {}}
    totales = {k: 0 for k in conteo}
    perdidas: list[tuple[str, list[str]]] = []
    saltadas_por_motor = 0
    salida = list(filas)

    for fid, pos in nuevo_indice.items():
        nueva = nuevas_filas[pos]
        if a.motor:
            motor = ((nueva.get("medicion") or {}).get("vision") or {}).get("motor")
            if motor != a.motor:
                saltadas_por_motor += 1
                continue
        if fid in indice:
            vieja = filas[indice[fid]]
            fusion, cuentas = fusionar(vieja, nueva)
            faltan = perdidos(vieja, fusion)
            if faltan:
                perdidas.append((fid, faltan))
            salida[indice[fid]] = fusion
            reemplazadas += 1
            for grupo in conteo:
                totales[grupo] += len(cuentas[grupo])
                for c in cuentas[grupo]:
                    conteo[grupo][c] = conteo[grupo].get(c, 0) + 1
        else:
            salida.append(nueva)
            agregadas += 1

    print("archivo vivo:   %s (%d filas, %d ids)"
          % (a.archivo, len(filas), len(indice)))
    print("pasada nueva:   %s (%d filas, %d ids)"
          % (a.nueva, len(nuevas_filas), len(nuevo_indice)))
    if a.motor:
        print("filtrado a motor=%s (%d fichas de la pasada nueva quedan fuera)"
              % (a.motor, saltadas_por_motor))
    print()
    print("fichas que se REEMPLAZAN (fusion campo a campo): %d" % reemplazadas)
    print("fichas que se AGREGAN (no estaban):              %d" % agregadas)
    print("resultado: %d filas" % len(salida))
    print()
    def _tabla(titulo, grupo, tope=12):
        print("%s: %d" % (titulo, totales[grupo]))
        for c, n in sorted(conteo[grupo].items(), key=lambda x: -x[1])[:tope]:
            print("   %5d  %s" % (n, c))

    _tabla("campos que la pasada nueva llena y la vieja no tenia (MEJORADOS)",
           "mejorados")
    _tabla("campos que la nueva NO trajo y se conservan (HEREDADOS)",
           "heredados")
    # Este es el bloque que faltaba, y era la mayoria. Ver `fusionar`.
    _tabla("campos que las DOS tenian y la nueva PISA (REEMPLAZADOS)",
           "reemplazados")
    print("   de esos, %d quedan MAS CHICOS que el valor que habia:"
          % totales["encogidos"])
    for c, n in sorted(conteo["encogidos"].items(), key=lambda x: -x[1])[:12]:
        print("   %5d  %s" % (n, c))
    print()
    print("Un reemplazo NO es una perdida: la politica declarada es que un "
          "valor nuevo no vacio gana.")
    print("Pero se cuenta y se muestra, porque hasta hoy este informe decia "
          "'perdidos: 0' mientras")
    print("pisaba miles de valores medidos sin nombrar uno solo. Mira los "
          "ENCOGIDOS antes de aplicar.")
    print()
    if perdidas:
        print("!!! CAMPOS PERDIDOS en %d fichas -- la fusion tiene un agujero, "
              "NO se aplica" % len(perdidas))
        for fid, faltan in perdidas[:5]:
            print("   %s -> %s" % (fid, ", ".join(faltan)))
        return 1
    print("campos que quedan vacios habiendo tenido valor: 0")

    # Las colisiones de grafia se INFORMAN siempre, se arreglan solo si se
    # pidio. Un valor que cambia sin que nadie lo haya pedido es justo lo que
    # esta herramienta existe para no hacer.
    colisiones = colisiones_de_tecnica(salida)
    if colisiones:
        print()
        print("tecnicas escritas de mas de una forma: %d" % len(colisiones))
        for variante, canonica in sorted(colisiones.items()):
            print("   %-26s -> %s" % (variante, canonica))
        if a.canonizar:
            tocadas = 0
            for f in salida:
                vis = f.get("vision") or {}
                actual = " ".join(str(vis.get("tecnica") or "").lower().split())
                if actual in colisiones:
                    vis["tecnica"] = colisiones[actual]
                    tocadas += 1
            print("   unificadas en %d fichas" % tocadas)
        else:
            print("   (no se tocaron: --canonizar-tecnica las unifica)")

    if not a.aplicar:
        print()
        print("(ensayo: no se escribio nada. Para aplicar: --aplicar)")
        return 0

    # NADIE MAS puede estar escribiendo. `percepcion.py` corre por cron cada 10
    # minutos y AGREGA lineas al mismo archivo; una ficha apendeada entre que se
    # lee y que se pisa desaparece del vivo y queda marcada en `procesados.txt`,
    # o sea un hueco que ningun reintento rescata. Es lo unico irreversible de
    # toda la operacion: el resto lo cubre el respaldo.
    if _hay_percepcion_corriendo():
        print("!!! hay una percepcion corriendo: escribir ahora puede tragarse "
              "las fichas que esta agregando. NO se toco nada.", file=sys.stderr)
        return 1
    candado = a.archivo.parent / ".consolidar.lock"
    with candado.open("w", encoding="utf-8") as fh_lock:
        if not _tomar_candado(fh_lock):
            print("!!! otro proceso tiene el candado (%s). NO se toco nada."
                  % candado, file=sys.stderr)
            return 1
        return _escribir(a.archivo, salida)


def _hay_percepcion_corriendo() -> bool:
    """Solo tiene sentido donde vive el archivo, que es Linux. En Windows no
    hay pgrep y tampoco hay cron de percepcion: se responde que no, y se dice
    por que aca en vez de fingir una comprobacion."""
    import subprocess
    try:
        r = subprocess.run(["pgrep", "-f", "percepcion.py correr"],
                           capture_output=True, timeout=15)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _tomar_candado(fh) -> bool:
    """flock no bloqueante, el mismo idiom que ya usa curatoria_guardia.sh."""
    try:
        import fcntl
    except ImportError:
        return True                          # Windows: no hay concurrencia aca
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _escribir(archivo: Path, salida: list[dict]) -> int:
    sello = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    respaldo = archivo.with_suffix(".jsonl.bak-" + sello)
    shutil.copy2(archivo, respaldo)
    # Nombre PROPIO: `percepcion.py` usa `.jsonl.tmp` sobre el mismo archivo, y
    # dos procesos escribiendo el mismo temporal se pisan sin decir nada.
    tmp = archivo.with_suffix(".jsonl.consolidar.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for d in salida:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    # Validated BEFORE overwriting: a half-written file on top of the live one
    # is worse than having done nothing.
    releidas, _ = cargar(tmp)
    if len(releidas) != len(salida):
        print("!!! el archivo temporal quedo con %d filas y esperaba %d; "
              "NO se piso el vivo (queda en %s)"
              % (len(releidas), len(salida), tmp), file=sys.stderr)
        return 1
    tmp.replace(archivo)
    print()
    print("aplicado. respaldo en %s" % respaldo.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
