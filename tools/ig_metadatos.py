#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The artist's own words about his own work, sitting unused next to the media.

Perception asks a model to describe 1.401 images. The Instagram export shipped
with those images already carries, for most of them, the DATE the work was
published and the TEXT the artist wrote about it. Measured on the real export:
1.014 of 1.125 media files have an associated text, and the dates span
2018-11-29 to 2026-06-16.

A model looking at a render can say "abstract 3D composition". The artist wrote
"Animacion 3D para @sweettoothskully. Meses de ensayo y error" -- which names
the technique, the client, the duration and the intent. No vision model
recovers that from pixels, because it is not in the pixels.

TWO THINGS THIS FILE REFUSES TO DO, and both matter more than the feature:

1. **It does not touch personal data.** The export also contains private
   messages, likes and story interactions. Only `your_instagram_activity/media/`
   is read -- the artist's own published work, which is a PRODUCT and already
   passed that filter. Any other directory is rejected by name, out loud. The
   repository privacy rule (2026-07-31): new input with personal data does not
   enter; what is already a product can be reviewed.

2. **It does not pass along mangled text.** Instagram writes UTF-8 bytes and
   the export decodes them as latin-1, so "coleccion" arrives as
   "colecciA3n" and every emoji is garbage. Recovering it is one round trip --
   `s.encode("latin-1").decode("utf-8")` -- and skipping it would put the exact
   defect class of "reduciendo ano" into text the artist shows people. When the
   round trip fails, the raw text is kept and the entry SAYS the encoding is
   suspect, instead of shipping something that looks fine and is not.

Usage:
    py tools/ig_metadatos.py "RUTA/DEL/EXPORT"                 # informe
    py tools/ig_metadatos.py "RUTA" --salida datos/ig_meta.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# Only what the artist PUBLISHED. Every other folder of the export is left out
# BY NAME, not by care: private messages, likes and story interactions live
# right next to this one.
ARCHIVOS = ("posts_1.json", "posts.json", "archived_posts.json", "reels.json",
            "igtv_videos.json", "profile_photos.json")
PROHIBIDAS = ("messages", "likes", "story_interactions", "connections",
              "personal_information", "ads_information", "logged_information",
              "security_and_login_information", "preferences",
              "apps_and_websites_off_of_instagram")

# Characters that only show up when UTF-8 was read as latin-1. If any survive
# the repair, the text is still broken and that has to be said.
# The last one is escaped on purpose: it is U+FFFD, and the Windows cp1252
# console cannot print it -- a `print` carrying that glyph kills the command
# halfway. Same data; what changes is that this file can be run on the user's
# machine. (Found by the repo's own printability ratchet, which then killed the
# script trying to report it.)
SOSPECHOSOS = (chr(0xC3), chr(0xC2), chr(0xE2) + chr(0x80), chr(0xFFFD))


def reparar(texto: str) -> tuple[str, bool]:
    """Returns (text, suspect). One round trip, verified."""
    if not texto:
        return "", False
    try:
        arreglado = texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        arreglado = texto
    # Keeps whichever version carries FEWER mojibake marks. Repairing text
    # that was already fine mangles it, and here that reaches a product.
    def marcas(t):
        return sum(t.count(c) for c in SOSPECHOSOS)
    if marcas(arreglado) > marcas(texto):
        arreglado = texto
    return arreglado, marcas(arreglado) > 0


def _fecha(ts) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).date().isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def _entradas(dato):
    """The export mixes shapes: a bare list, or a dict with ONE key holding it
    (`ig_reels_media`, `ig_archived_post_media`...). The list is FOUND, its name
    is not assumed: a key written by hand here goes stale at the next export."""
    if isinstance(dato, list):
        return dato
    if isinstance(dato, dict):
        for valor in dato.values():
            if isinstance(valor, list):
                return valor
    return []


def leer_export(raiz: Path, incluir_historias: bool = False) -> tuple[dict, dict]:
    """filename -> {fecha, texto, ...}, plus a report of what was measured."""
    base = raiz / "info" / "your_instagram_activity" / "media"
    if not base.is_dir():
        base = raiz if raiz.name == "media" else base
    if not base.is_dir():
        raise SystemExit("no encuentro your_instagram_activity/media en %s" % raiz)
    partes = {p.lower() for p in base.parts}
    prohibida = partes & set(PROHIBIDAS)
    if prohibida:
        raise SystemExit("esa ruta pasa por %s, que tiene datos personales y "
                         "no se lee" % ", ".join(sorted(prohibida)))

    mapa: dict[str, dict] = {}
    informe = {"archivos_leidos": [], "sin_leer": [], "publicaciones": 0,
               "medios": 0, "con_texto": 0, "con_fecha": 0, "sospechosos": 0}

    archivos = ARCHIVOS + (("stories.json",) if incluir_historias else ())
    for nombre in archivos:
        ruta = base / nombre
        if not ruta.exists():
            informe["sin_leer"].append(nombre)
            continue
        try:
            dato = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            informe["sin_leer"].append("%s (%s)" % (nombre, e))
            continue
        entradas = _entradas(dato)
        informe["archivos_leidos"].append("%s (%d)" % (nombre, len(entradas)))
        for indice_publicacion, pub in enumerate(entradas):
            if not isinstance(pub, dict):
                continue
            informe["publicaciones"] += 1
            titulo_pub = (pub.get("title") or "").strip()
            ts_pub = pub.get("creation_timestamp")
            medios_publicacion = [m for m in (pub.get("media") or [])
                                  if isinstance(m, dict)]
            if nombre == "stories.json" and not medios_publicacion and pub.get("uri"):
                medios_publicacion = [pub]
            for indice_medio, medio in enumerate(medios_publicacion):
                if not isinstance(medio, dict):
                    continue
                uri = medio.get("uri") or ""
                clave = uri.rsplit("/", 1)[-1]
                if not clave:
                    continue
                informe["medios"] += 1
                # The MEDIA title wins over the post's: in a carousel a piece
                # may carry its own. If it does not, it inherits the post's,
                # which is what the artist wrote about the set.
                crudo = (medio.get("title") or "").strip() or titulo_pub
                texto, sospechoso = reparar(crudo)
                fecha = _fecha(medio.get("creation_timestamp") or ts_pub)
                if texto:
                    informe["con_texto"] += 1
                if fecha:
                    informe["con_fecha"] += 1
                if sospechoso:
                    informe["sospechosos"] += 1
                previo = mapa.get(clave)
                # If the same file shows up twice, the one WITH text wins:
                # losing it to an empty duplicate would silently drop the only
                # data that matters.
                if previo and previo.get("texto") and not texto:
                    continue
                mapa[clave] = {
                    "fecha": fecha,
                    "texto": texto,
                    "hereda_del_post": bool(crudo and crudo == titulo_pub
                                            and not (medio.get("title") or "").strip()),
                    "encoding_sospechoso": sospechoso,
                    "uri": uri,
                    "publicacion_id": "%s:%d" % (nombre, indice_publicacion),
                    "publicacion_archivo": nombre,
                    "medio_indice": indice_medio,
                    "medio_total": len(medios_publicacion),
                    "tipo_contenido": "story" if nombre == "stories.json" else "published_media",
                }
    return mapa, informe


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("export", type=Path,
                   help="carpeta del export de Instagram (la que tiene info/ y media/)")
    p.add_argument("--salida", type=Path, default=None,
                   help="escribir el mapa a un JSON")
    p.add_argument("--incluir-historias", action="store_true",
                   help="incluir stories.json; solo metadata de historias publicadas")
    a = p.parse_args()

    mapa, informe = leer_export(a.export, incluir_historias=a.incluir_historias)

    print("archivos leidos: %s" % ", ".join(informe["archivos_leidos"]))
    if informe["sin_leer"]:
        print("no estaban:     %s" % ", ".join(informe["sin_leer"]))
    print()
    print("publicaciones:            %d" % informe["publicaciones"])
    print("archivos de media:        %d" % informe["medios"])
    print("archivos unicos mapeados: %d" % len(mapa))
    con_texto = sum(1 for v in mapa.values() if v["texto"])
    con_fecha = sum(1 for v in mapa.values() if v["fecha"])
    heredados = sum(1 for v in mapa.values() if v["hereda_del_post"])
    n = max(1, len(mapa))
    print("  con texto del artista:  %d (%.0f%%), de los cuales %d heredados "
          "del post" % (con_texto, 100.0 * con_texto / n, heredados))
    print("  con fecha exacta:       %d (%.0f%%)" % (con_fecha, 100.0 * con_fecha / n))
    if informe["sospechosos"]:
        print("  !! con encoding aun sospechoso: %d -- se marcan, no se limpian"
              % informe["sospechosos"])
    fechas = sorted(v["fecha"] for v in mapa.values() if v["fecha"])
    if fechas:
        print("  rango: %s -> %s" % (fechas[0], fechas[-1]))

    if a.salida:
        a.salida.parent.mkdir(parents=True, exist_ok=True)
        a.salida.write_text(
            json.dumps({"formato": "ig_metadatos/1", "total": len(mapa),
                        "medios": mapa}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print()
        print("escrito: %s" % a.salida)
    else:
        print()
        print("(informe solamente. Para guardarlo: --salida datos/ig_meta.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
