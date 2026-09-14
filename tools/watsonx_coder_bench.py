#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which watsonx model should lead the coder chain. MEASURED, never picked.

This exists because the name of a model is not evidence about the model. First
real run, 2026-07-31 against the user's account: of five candidates, the only
one labelled `code` -- `ibm/granite-8b-code-instruct` -- was the only one that
failed a case. Choosing by the name would have put the worst one first.

Each answer is EXECUTED, not read: it has to compile and satisfy the cases. A
model that writes plausible Python is not the same as one that writes Python
that runs, and that difference is the whole reason this file exists.

Usage (on the MAK box, with the research environment loaded):
    set -a && . ~/n8n-local/research.env && set +a
    python3 tools/watsonx_coder_bench.py
    python3 tools/watsonx_coder_bench.py --modelos ibm/granite-4-h-small,other

It touches neither the repo nor the live chain: it prints a table and exits.
Changing the chain means editing `_CODER_CHAIN_DEFAULT` or the `CODER_CHAIN`
environment variable.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

MODELOS = (
    "meta-llama/llama-3-3-70b-instruct",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
    "ibm/granite-3-8b-instruct",
    "ibm/granite-8b-code-instruct",
    "ibm/granite-4-h-small",
)

# The prompt stays in Spanish on purpose: it is what the live coder department
# actually sends, and measuring a model on a prompt it will never receive
# measures nothing.
SISTEMA = ("Eres un programador Python. Respondes SOLO con codigo Python, sin "
           "explicaciones y sin markdown. Stdlib unicamente.")

# The task discriminates on purpose. An easier one (normalising a slug) was
# solved 5 out of 5 and said nothing: if everybody passes, the exam measures
# nothing.
TAREA = """Escribe una funcion `fusionar(tramos)` que reciba una lista de
tuplas (inicio, fin) de enteros, posiblemente desordenada y con solapes, y
devuelva la lista MINIMA de tramos fusionados, ordenada por inicio.
Reglas:
- (1,3) y (3,5) se tocan y se fusionan en (1,5)
- (1,3) y (4,6) NO se fusionan
- un tramo con inicio > fin es invalido y se DESCARTA (no se corrige)
- lista vacia devuelve lista vacia
- no modifiques la lista de entrada
Devuelve una lista de tuplas. Define solo la funcion."""

CASOS = (
    ([(1, 3), (2, 6), (8, 10), (15, 18)], [(1, 6), (8, 10), (15, 18)]),
    ([(1, 3), (3, 5)], [(1, 5)]),
    ([(1, 3), (4, 6)], [(1, 3), (4, 6)]),
    ([(5, 1), (2, 4)], [(2, 4)]),          # invalid is dropped, never flipped
    ([], []),
    ([(3, 4), (1, 2), (2, 3)], [(1, 4)]),  # chained and out of order
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


def _chat(token, modelo, system, user, max_tok=900):
    base = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    req = urllib.request.Request(
        base.rstrip("/") + "/ml/v1/text/chat?version=2024-10-08",
        data=json.dumps({
            "model_id": modelo,
            "project_id": os.environ.get("WATSONX_PROJECT_ID", ""),
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": max_tok, "temperature": 0.1,
        }).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    return (d["choices"][0]["message"]["content"] or "").strip()


def _limpiar(texto):
    """They promise "no markdown" and send markdown anyway. Stripped here."""
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", texto)
    return (m.group(1) if m else texto).strip()


def probar(codigo):
    """Run it in a separate process with a timeout, so a `while True` from the
    model cannot hang the measurement. Returns (hits, first failure)."""
    guion = codigo + (
        "\nimport json\n"
        "print(json.dumps([[list(t) for t in fusionar(list(c))]"
        " for c, _ in %r]))\n" % (CASOS,))
    ruta = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8") as f:
            f.write(guion)
            ruta = f.name
        p = subprocess.run([sys.executable, ruta], capture_output=True,
                           text=True, encoding="utf-8", timeout=25)
        if p.returncode != 0:
            ultima = (p.stderr or "").strip().splitlines() or ["no stderr"]
            return 0, ultima[-1][:70]
        salida = json.loads((p.stdout or "").strip().splitlines()[-1])
    except Exception as e:                       # noqa: BLE001 - reported
        return 0, ("%s: %s" % (type(e).__name__, e))[:70]
    finally:
        if ruta:
            try:
                os.unlink(ruta)
            except OSError:
                pass

    aciertos, fallo = 0, ""
    for (entrada, esperado), obtenido in zip(CASOS, salida):
        # The model returns lists where tuples are expected: that is json, not
        # its mistake. Normalise before comparing -- not normalising was a
        # defect in this bench's first version, which reported a failure on
        # runs that had scored 6/6.
        got = [tuple(t) for t in obtenido]
        if got == [tuple(t) for t in esperado]:
            aciertos += 1
        elif not fallo:
            fallo = "%r -> %r (esperaba %r)" % (entrada, got, esperado)
    return aciertos, fallo


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modelos", default=",".join(MODELOS),
                    help="CSV of watsonx model ids to compare")
    args = ap.parse_args()

    if not os.environ.get("WATSONX_API_KEY"):
        print("falta WATSONX_API_KEY en el entorno "
              "(en la caja: . ~/n8n-local/research.env)")
        return 2
    token = _token()

    print("%-46s %7s %6s  %s" % ("modelo", "ms", "casos", "primer fallo"))
    for modelo in [m.strip() for m in args.modelos.split(",") if m.strip()]:
        t0 = time.time()
        try:
            salida = _chat(token, modelo, SISTEMA, TAREA)
        except Exception as e:                   # noqa: BLE001 - reported
            print("%-46s %7s %6s  %s" % (modelo[:46], "-", "-", str(e)[:60]))
            continue
        ms = int((time.time() - t0) * 1000)
        aciertos, fallo = probar(_limpiar(salida))
        print("%-46s %7d %3d/%d  %s"
              % (modelo[:46], ms, aciertos, len(CASOS), fallo[:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
