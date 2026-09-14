#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Does watsonx accept an IMAGE. Read-only probe, run before wiring anything.

The whole re-perception plan rests on one assumption that has never been
tested: that `/ml/v1/text/chat` takes image content the way OpenAI-shaped APIs
do. The models were listed on 2026-07-31 and five of the account's 24 look
vision-capable by NAME and by their spec blob -- but `task_ids` declares no
vision task, so that is an inference, not a measurement. Same discipline as
`tools/watsonx_smoke.py`, which is why `_watsonx` was only added to the provider
chain after it answered 4/4 against the real account: a provider that was not
probed does not get wired.

It sends ONE real image with the REAL perception prompt, so what comes back is
what the box would actually get, not a toy answer to a toy question.

Usage (on the MAK box, with the research environment loaded):
    set -a && . ~/n8n-local/research.env && set +a
    python3 tools/watsonx_vision_smoke.py <imagen.jpg> [--modelo <id>] [--fuente rd|ig]

Touches nothing: no repo write, no ficha, no live chain.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CANDIDATOS = (
    "meta-llama/llama-3-2-11b-vision-instruct",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
)

# The real thing the box asks an image, trimmed to what a probe needs. The point
# is not to test a nice prompt: it is to see whether the shape that percepcion.py
# sends comes back as usable JSON.
PROMPT = (
    "Mira la imagen y responde SOLO con un objeto JSON, sin explicaciones.\n"
    '{"categoria": "flyer_evento|obra|logo|material_rd|foto_evento|otro",\n'
    ' "texto_visible": "todo el texto que se lee en la imagen, literal",\n'
    ' "colores": ["hasta 3 nombres de color"],\n'
    ' "productora": "", "venue": "", "fecha": "", "headliners": []}\n'
    "Si un campo no aplica, dejalo vacio. NO inventes."
)


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


def _b64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def probar(token, modelo, imagen_b64, prompt, max_tok=700):
    """Returns (ok, ms, texto|error). Never raises: an HTTP body is the answer
    here, not an accident."""
    base = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    cuerpo = {
        "model_id": modelo,
        "project_id": os.environ.get("WATSONX_PROJECT_ID", ""),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": "data:image/jpeg;base64," + imagen_b64}},
            ],
        }],
        "max_tokens": max_tok,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/ml/v1/text/chat?version=2024-10-08",
        data=json.dumps(cuerpo).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read())
        ms = int((time.time() - t0) * 1000)
        return True, ms, (d["choices"][0]["message"]["content"] or "").strip()
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        detalle = e.read().decode("utf-8", "replace")[:400]
        return False, ms, "HTTP %s: %s" % (e.code, detalle)
    except Exception as e:                       # noqa: BLE001 - reported
        return False, int((time.time() - t0) * 1000), "%s: %s" % (type(e).__name__, e)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("imagen")
    ap.add_argument("--modelo", default="", help="uno solo; por defecto prueba los candidatos")
    args = ap.parse_args()

    if not os.environ.get("WATSONX_API_KEY"):
        print("falta WATSONX_API_KEY (en la caja: . ~/n8n-local/research.env)")
        return 2
    if not os.path.exists(args.imagen):
        print("no existe la imagen: " + args.imagen)
        return 2

    b64 = _b64(args.imagen)
    print("imagen: %s (%d KB en base64)" % (args.imagen, len(b64) // 1024))
    token = _token()
    modelos = [args.modelo] if args.modelo else list(CANDIDATOS)

    algun_ok = False
    for m in modelos:
        ok, ms, texto = probar(token, m, b64, PROMPT)
        print("\n--- %s ---" % m)
        if not ok:
            print("  FALLA en %d ms: %s" % (ms, texto))
            continue
        algun_ok = True
        print("  OK en %d ms" % ms)
        # Se muestra crudo A PROPOSITO: lo que importa de esta sonda es la forma
        # exacta que devuelve, no una version limpia que oculte el problema.
        print("  " + texto.replace("\n", "\n  ")[:900])

    if not algun_ok:
        print("\nNINGUN modelo acepto la imagen. El plan de re-percepcion "
              "cambia entero, y eso es lo que esta sonda existe para decir "
              "en el primer minuto.")
        return 1
    print("\nwatsonx acepta imagenes: el transporte se puede escribir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
