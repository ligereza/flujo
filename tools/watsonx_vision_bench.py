#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which vision model reads the archive better than `gemma3:4b` does today.

Measured, with ground truth that already exists on disk and nobody had used.

The substrate is thin: over the 3.138 real fichas, `ocr_texto` is empty in 76%,
`datos_evento` in 69%. All of it was read by the smallest model in the house --
`gemma3:4b` on a 4 GB GTX 1650 -- at 31 s per image. The question is not whether
a bigger model is nicer. It is whether it fills fields that today come back
empty, without inventing what is not in the picture.

TWO GROUND TRUTHS, both already on disk:

1. **The OCR.** In 24% of fichas `ocr_texto` is NOT empty. Tesseract read those
   pixels with no model involved, so for that stratum the model's `texto_visible`
   can be scored against it: what fraction of the OCR's words does the model
   recover. That is a number, not an impression.
2. **The current ficha.** Whatever `gemma3:4b` produced is the bar to beat. A
   model that fills nothing new is not worth the token.

AND THE STRATUM THAT MATTERS MOST is the other one: the fichas that came back
EMPTY. A bench sampled only where the old model did well measures nothing --
that mistake was made once already today, probing with a flyer whose ficha was
one of the good ones (`calidad_senal: alta`).

INVENTION IS SCORED AGAINST, NOT FOR. On the first probe,
`llama-4-maverick` answered `productora: "street machine"` for a flyer that says
CUIDARTE, and read GUIDARTE. A model that fills `productora` with something
plausible is worse than one that leaves it empty: the RD database is fed from
this, and a wrong productora is a wrong client. So a filled field only counts
when it appears in the OCR or in today's ficha; otherwise it is flagged as
UNSUPPORTED.

Usage (on the MAK box, with the research environment loaded):
    set -a && . ~/n8n-local/research.env && set +a
    python3 tools/watsonx_vision_bench.py --muestras 12
    python3 tools/watsonx_vision_bench.py --modelos meta-llama/llama-3-2-11b-vision-instruct

Read-only: touches no ficha, no repo, no live chain.
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

try:
    from PIL import Image
except ImportError:
    Image = None

FICHAS = os.path.expanduser("~/curatoria/fichas/fichas.jsonl")
RAIZ_RD = os.path.expanduser("~/RD")
# Production resizes to 1280 (`percepcion.MAX_LADO_VISION`). This said 1024 with
# a comment claiming it was "the same as percepcion" -- it was not, and that
# turned every number this bench produced into a measurement of a size nobody
# runs. `--lado` exists so the question "do those 256 px buy anything" gets an
# answer instead of an assumption: the run pays roughly double the image tokens
# for them.
MAX_LADO = 1280

MODELOS = (
    "meta-llama/llama-3-2-11b-vision-instruct",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
)

PROMPT = (
    "Mira la imagen y responde SOLO con un objeto JSON, sin explicaciones.\n"
    '{"categoria": "flyer_evento|obra|logo|material_rd|foto_evento|otro",\n'
    ' "texto_visible": "todo el texto que se lee en la imagen, literal",\n'
    ' "colores": ["hasta 3 nombres de color"],\n'
    ' "productora": "", "venue": "", "fecha": "", "headliners": []}\n'
    "Reglas: si un campo no se lee EN LA IMAGEN, dejalo vacio. NO deduzcas, "
    "NO completes con lo que te parezca probable. Un campo vacio es una "
    "respuesta correcta; uno inventado no."
)

CAMPOS_EVENTO = ("productora", "venue", "fecha")


def _plegar(texto):
    """Minusculas sin diacriticos, para comparar palabras sin castigar tildes."""
    d = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in d if not unicodedata.combining(c)).lower()


def _palabras(texto, minimo=3):
    """Palabras significativas. Las cortas son ruido de OCR y no se puntuan."""
    return {p for p in re.findall(r"[a-z0-9]+", _plegar(texto)) if len(p) >= minimo}


def solape(ocr, dicho):
    """Que fraccion de las palabras del OCR recupera el modelo. 0..1."""
    a, b = _palabras(ocr), _palabras(dicho)
    if not a:
        return None
    return round(len(a & b) / len(a), 3)


def _token():
    cuerpo = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": os.environ.get("WATSONX_API_KEY", ""),
    }).encode()
    req = urllib.request.Request(
        "https://iam.cloud.ibm.com/identity/token", data=cuerpo,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def _b64(ruta, max_lado=MAX_LADO):
    """Igual que percepcion._imagen_a_b64: si no se achica, un PNG de 16 MB se
    va en 21 MB de base64 y la llamada tarda 36 s en vez de unos pocos."""
    if Image is not None:
        try:
            with Image.open(ruta) as im:
                im = im.convert("RGB")
                w, h = im.size
                if max(w, h) > max_lado:
                    e = max_lado / max(w, h)
                    im = im.resize((max(1, int(w * e)), max(1, int(h * e))),
                                   Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=85)
                return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:                        # noqa: BLE001 - cae a crudo
            pass
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def preguntar(token, modelo, b64, max_tok=700):
    base = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    cuerpo = {
        "model_id": modelo,
        "project_id": os.environ.get("WATSONX_PROJECT_ID", ""),
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url",
             "image_url": {"url": "data:image/jpeg;base64," + b64}}]}],
        "max_tokens": max_tok, "temperature": 0.1,
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/ml/v1/text/chat?version=2024-10-08",
        data=json.dumps(cuerpo).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json", "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.loads(r.read())
        uso = d.get("usage") or {}
        return (True, int((time.time() - t0) * 1000),
                (d["choices"][0]["message"]["content"] or "").strip(),
                uso.get("total_tokens", 0))
    except urllib.error.HTTPError as e:
        return (False, int((time.time() - t0) * 1000),
                "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:200]), 0)
    except Exception as e:                       # noqa: BLE001 - reported
        return False, int((time.time() - t0) * 1000), "%s: %s" % (type(e).__name__, e), 0


def parsear(texto):
    """Tolerante como el de percepcion: los modelos mandan ```json igual."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto or "")
    crudo = (m.group(1) if m else (texto or "")).strip()
    try:
        d = json.loads(crudo)
        return d if isinstance(d, dict) else None
    except ValueError:
        return None


def muestra(n):
    """Estratificada: mitad con OCR (hay con que puntuar) y mitad de las que
    hoy vuelven VACIAS, que son el 76% y el motivo entero de esto."""
    con_ocr, vacias = [], []
    with open(FICHAS, encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if d.get("tipo") != "imagen":
                continue
            ruta = os.path.join(RAIZ_RD, d.get("ruta_rel", ""))
            if not os.path.exists(ruta):
                continue
            if (d.get("ocr_texto") or "").strip():
                con_ocr.append((ruta, d))
            elif not (d.get("vision") or {}).get("texto_visible"):
                vacias.append((ruta, d))
    mitad = max(1, n // 2)
    # Deterministico: los primeros de cada estrato en el orden del archivo, sin
    # azar. Una muestra que cambia entre corridas no se puede comparar.
    return con_ocr[:mitad], vacias[:n - mitad]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--muestras", type=int, default=8)
    ap.add_argument("--modelos", default=",".join(MODELOS))
    ap.add_argument("--lado", type=int, default=MAX_LADO,
                    help="lado mayor al que se reescala la imagen antes de "
                         "mandarla (produccion usa %d)" % MAX_LADO)
    args = ap.parse_args()

    if not os.environ.get("WATSONX_API_KEY"):
        print("falta WATSONX_API_KEY (en la caja: . ~/n8n-local/research.env)")
        return 2
    if not os.path.exists(FICHAS):
        print("no encuentro " + FICHAS)
        return 2

    con_ocr, vacias = muestra(args.muestras)
    print("muestra: %d con OCR (verdad de referencia) + %d que hoy vuelven "
          "vacias\n" % (len(con_ocr), len(vacias)))
    token = _token()
    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]

    resumen = []
    for modelo in modelos:
        solapes, llenados, sin_respaldo, fallos, ms_tot, tok_tot = [], 0, 0, 0, 0, 0
        for etiqueta, grupo in (("con_ocr", con_ocr), ("vacia", vacias)):
            for ruta, ficha in grupo:
                ok, ms, texto, tokens = preguntar(token, modelo,
                                                  _b64(ruta, args.lado))
                ms_tot += ms
                tok_tot += tokens
                if not ok:
                    fallos += 1
                    print("  FALLA %-14s %s -- %s" % (etiqueta, os.path.basename(ruta)[:28], texto[:90]))
                    continue
                d = parsear(texto)
                if d is None:
                    fallos += 1
                    print("  NO-JSON %-13s %s" % (etiqueta, os.path.basename(ruta)[:28]))
                    continue
                ocr = ficha.get("ocr_texto") or ""
                s = solape(ocr, d.get("texto_visible", ""))
                if s is not None:
                    solapes.append(s)
                # A filled field only counts when its value APPEARS in the OCR
                # or in today's ficha. Otherwise it is invention, and invention
                # is worse than an empty field: the RD database is fed from
                # here, and a wrong productora is a wrong client.
                for c in CAMPOS_EVENTO:
                    v = str(d.get(c) or "").strip()
                    if not v:
                        continue
                    llenados += 1
                    apoyo = _plegar(ocr) + " " + _plegar(json.dumps(
                        ficha.get("datos_evento") or {}, ensure_ascii=False))
                    if not _palabras(v) & _palabras(apoyo):
                        sin_respaldo += 1
        n = len(con_ocr) + len(vacias)
        resumen.append({
            "modelo": modelo,
            "solape_ocr": round(sum(solapes) / len(solapes), 3) if solapes else None,
            "campos_llenos": llenados,
            "sin_respaldo": sin_respaldo,
            "fallos": fallos,
            "ms_prom": ms_tot // max(1, n),
            "tokens": tok_tot,
        })

    print("\n%-46s %8s %8s %8s %7s %9s %8s" % (
        "modelo", "solape", "llenos", "s/apoyo", "fallos", "ms/imagen", "tokens"))
    for r in resumen:
        print("%-46s %8s %8d %8d %7d %9d %8d" % (
            r["modelo"][:46],
            "-" if r["solape_ocr"] is None else r["solape_ocr"],
            r["campos_llenos"], r["sin_respaldo"], r["fallos"],
            r["ms_prom"], r["tokens"]))
    print("\nsolape: fraccion de palabras del OCR que el modelo recupera (mas alto mejor)")
    print("s/apoyo: campos llenados cuyo valor NO aparece ni en el OCR ni en la "
          "ficha de hoy -- invencion, y cuenta EN CONTRA")
    print(json.dumps({"version": 1, "muestra": len(con_ocr) + len(vacias),
                      "resumen": resumen}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
