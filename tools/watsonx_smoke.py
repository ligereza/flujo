#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica que el recurso watsonx quedo bien provisionado, y devuelve el codigo.

Se corre UNA vez, apenas existen las credenciales, ANTES de tocar
`research_lib.py`. Responde las cuatro preguntas que si no se contestan ahora se
contestan despues a ciegas dentro del organismo:

    1. La API key sirve? (cambio por bearer IAM)
    2. El proyecto existe y el modelo esta disponible ahi?
    3. Cuanto tarda de verdad una llamada desde Chile?
    4. Cuantos tokens consume y cuanto cuesta eso?

Si las cuatro pasan, imprime el metodo `_watsonx` listo para pegar en
`research_lib.py`. La verificacion ES la fuente del codigo: no se pega un metodo
que no se probo.

Sin dependencias: solo stdlib (urllib), igual que `research_lib._http_json`.
El UA custom va porque Cloudflare devolvia 403 code 1010 al UA de urllib.

Uso:
    py tools/watsonx_smoke.py                       # lee el env
    py tools/watsonx_smoke.py --env ~/n8n-local/research.env
    py tools/watsonx_smoke.py --modelos             # lista lo disponible
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "flujo-mak-research/1.0"
IAM = "https://iam.cloud.ibm.com/identity/token"
VERSION_API = "2024-10-08"

# USD por millon de tokens (watsonx.ai pay-as-you-go, jul 2026).
# Se copia igual a cuotas.py. Si IBM cambia precios, se cambia en los dos lados.
TARIFAS = {
    "ibm/granite-4-h-small": (0.0636, 0.265),
    "mistralai/mistral-small-3-1-24b-instruct-2503": (0.106, 0.318),
    "meta-llama/llama-3-3-70b-instruct": (0.7526, 0.7526),
    "mistralai/mistral-large-2512": (0.636, 1.908),
}
POR_DEFECTO = (0.7526, 0.7526)

OK, MAL, AVISO = "  OK   ", "  FALLA", "  aviso"


# --------------------------------------------------------------------------- env
def cargar_env(ruta: Path | None) -> None:
    """Lee KEY=valor. No pisa lo que ya este en el entorno."""
    candidatas = [ruta] if ruta else [
        Path(os.environ.get("RESEARCH_ENV", "")),
        Path.home() / "n8n-local" / "research.env",
        Path.home() / "research.env",
    ]
    for c in candidatas:
        if c and str(c) and c.expanduser().is_file():
            for linea in c.expanduser().read_text(encoding="utf-8").splitlines():
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            print(f"       env: {c}")
            return
    print("       env: ninguno encontrado, se usa el entorno actual")


def _pedir(url: str, datos: bytes | None, headers: dict, timeout: int = 90):
    req = urllib.request.Request(url, data=datos, headers={"User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _explicar(e: Exception) -> str:
    """Traduce el error de IBM a que hay que tocar. Sin esto se pierden horas."""
    if isinstance(e, urllib.error.HTTPError):
        try:
            cuerpo = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            cuerpo = ""
        pistas = {
            400: "revisa project_id y model_id (el modelo puede no estar habilitado en ese proyecto)",
            401: "la API key no sirve o no se cambio por bearer IAM",
            403: "la key no tiene permiso sobre ese proyecto, o falta asociar watsonx.ai Runtime al proyecto",
            404: "URL o region equivocada (deberia ser us-south si creaste en Dallas)",
            429: "rate limit -- el plan Lite del Runtime permite 2 req/s",
        }
        return f"HTTP {e.code}: {pistas.get(e.code, 'sin pista')}\n         {cuerpo}"
    return f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------- pasos
def paso_token(key: str) -> str | None:
    print("\n[1/4] cambiar la API key por un bearer IAM")
    cuerpo = urllib.parse.urlencode(
        {"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": key}
    ).encode()
    t0 = time.time()
    try:
        d = _pedir(
            IAM,
            cuerpo,
            {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            timeout=30,
        )
    except Exception as e:
        print(f"{MAL} {_explicar(e)}")
        return None
    ms = int((time.time() - t0) * 1000)
    print(f"{OK} bearer obtenido en {ms} ms · vence en {d.get('expires_in', '?')} s")
    print("       (el token vence a la hora: por eso el metodo lo cachea)")
    return d["access_token"]


def paso_modelos(base: str, tok: str, listar_todo: bool) -> list[str]:
    print("\n[2/4] modelos disponibles")
    url = f"{base}/ml/v1/foundation_model_specs?version={VERSION_API}&limit=200"
    try:
        d = _pedir(url, None, {"Authorization": f"Bearer {tok}"}, timeout=60)
    except Exception as e:
        print(f"{AVISO} no se pudo listar ({_explicar(e).splitlines()[0]}); no es fatal")
        return []
    ids = sorted(m.get("model_id", "") for m in d.get("resources", []))
    print(f"{OK} {len(ids)} modelos visibles")
    if listar_todo:
        for i in ids:
            print(f"       {i}")
    else:
        for i in ids:
            if any(p in i for p in ("llama-3-3-70b", "granite", "mistral-small", "embedding")):
                print(f"       {i}")
    return ids


def paso_chat(base: str, tok: str, proyecto: str, modelo: str) -> dict | None:
    print(f"\n[3/4] una llamada real de chat  ({modelo})")
    url = f"{base}/ml/v1/text/chat?version={VERSION_API}"
    payload = {
        "model_id": modelo,
        "project_id": proyecto,
        "messages": [
            {"role": "system", "content": "Respondes en una linea, en espanol, sin adornos."},
            {"role": "user", "content": "Decime OK y nada mas."},
        ],
        "max_tokens": 20,
        "temperature": 0.3,
    }
    t0 = time.time()
    try:
        d = _pedir(
            url,
            json.dumps(payload).encode("utf-8"),
            {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        )
    except Exception as e:
        print(f"{MAL} {_explicar(e)}")
        return None
    ms = int((time.time() - t0) * 1000)
    txt = (d.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    print(f"{OK} respondio en {ms} ms: {txt!r}")
    if ms > 8000:
        print(f"{AVISO} {ms} ms es alto, pero contra los 44.3 s por producto que mide")
        print("       USO.md sigue siendo ruido. No optimizar esto.")
    return {"uso": d.get("usage", {}), "ms": ms}


def paso_costo(uso: dict, modelo: str) -> None:
    print("\n[4/4] cuanto cuesta")
    ent = uso.get("prompt_tokens", 0)
    sal = uso.get("completion_tokens", 0)
    if not (ent or sal):
        print(f"{AVISO} la respuesta no trajo 'usage'; no se puede estimar")
        return
    p_in, p_out = TARIFAS.get(modelo, POR_DEFECTO)
    usd = ent / 1e6 * p_in + sal / 1e6 * p_out
    print(f"{OK} {ent} entrada + {sal} salida = {ent + sal} tokens · ${usd:.6f}")
    print(f"       tarifa: ${p_in}/1M entrada, ${p_out}/1M salida")
    # Escalas que importan para decidir, no para impresionar.
    producto = (15_000 / 1e6) * p_in + (4_000 / 1e6) * p_out
    print(f"\n       un producto de research (~15k in + 4k out): ${producto:.4f}")
    print(f"       20 dias a MAX_DIA=24 (480 productos):        ${producto * 480:.2f}")
    print(f"       los 300.000 tokens gratis del Runtime Lite:  ~{300_000 // 19_000} productos")
    print("       -> la Etapa 1 entera entra en el tier gratis. El credito queda para la Etapa 2.")


SNIPPET = '''
# ---------------------------------------------------------------- watsonx
# Verificado por tools/watsonx_smoke.py el {fecha}.
# Token IAM: vence a la hora, por eso el cache.
_WX_TOK = {{"t": None, "exp": 0.0}}


def _wx_token():
    import time
    if _WX_TOK["t"] and time.time() < _WX_TOK["exp"] - 60:
        return _WX_TOK["t"]
    body = urllib.parse.urlencode({{
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": os.environ.get("WATSONX_API_KEY", ""),
    }}).encode()
    req = urllib.request.Request(
        "https://iam.cloud.ibm.com/identity/token", data=body,
        headers={{"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json",
                 "User-Agent": "flujo-mak-research/1.0"}})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    _WX_TOK["t"] = d["access_token"]
    _WX_TOK["exp"] = time.time() + float(d.get("expires_in", 3600))
    return _WX_TOK["t"]


    def _watsonx(self, system, user, max_tok):
        base = os.environ.get("WATSONX_URL", "{base}")
        url = base.rstrip("/") + "/ml/v1/text/chat?version={version}"
        payload = {{
            "model_id": os.environ.get("WATSONX_MODEL", "{modelo}"),
            "project_id": os.environ.get("WATSONX_PROJECT_ID", ""),
            "messages": [{{"role": "system", "content": system}},
                         {{"role": "user", "content": user}}],
            "max_tokens": max_tok,
            "temperature": 0.3,
        }}
        hdr = {{"Authorization": "Bearer " + _wx_token(),
               "Content-Type": "application/json"}}
        r = _http_json(url, payload, timeout=90, headers=hdr)
        return (r["choices"][0]["message"]["content"] or "").strip()

# y en _has_key():   need = {{..., "watsonx": "WATSONX_API_KEY"}}
# NO tocar _SLOTS todavia: probar con LLM(order="watsonx") explicito.
'''


def main(argv: list[str]) -> int:
    ruta = None
    if "--env" in argv:
        ruta = Path(argv[argv.index("--env") + 1])
    listar_todo = "--modelos" in argv

    print("verificacion de watsonx  ·  no toca el repo, no escribe nada")
    cargar_env(ruta)

    key = os.environ.get("WATSONX_API_KEY", "").strip()
    proyecto = os.environ.get("WATSONX_PROJECT_ID", "").strip()
    base = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")
    modelo = os.environ.get("WATSONX_MODEL", "meta-llama/llama-3-3-70b-instruct")

    faltan = [n for n, v in (("WATSONX_API_KEY", key), ("WATSONX_PROJECT_ID", proyecto)) if not v]
    if faltan:
        print(f"\n{MAL} falta(n): {', '.join(faltan)}")
        print("\n  En ~/n8n-local/research.env (chmod 600), NUNCA en el repo:")
        print("    WATSONX_API_KEY=...")
        print("    WATSONX_PROJECT_ID=...")
        print("    WATSONX_URL=https://us-south.ml.cloud.ibm.com")
        print(f"    WATSONX_MODEL={modelo}")
        print("\n  El project_id sale de watsonx.ai Studio: proyecto -> Manage -> General.")
        print("  Y el proyecto necesita watsonx.ai Runtime ASOCIADO, o el chat da 403.")
        return 2

    print(f"       url: {base}\n       modelo: {modelo}\n       proyecto: {proyecto[:8]}...")

    tok = paso_token(key)
    if not tok:
        return 1
    paso_modelos(base, tok, listar_todo)
    res = paso_chat(base, tok, proyecto, modelo)
    if not res:
        return 1
    paso_costo(res["uso"], modelo)

    from datetime import date

    print("\n" + "=" * 72)
    print("TODO OK. Este es el codigo verificado para research_lib.py:")
    print("=" * 72)
    print(SNIPPET.format(
        fecha=date.today().isoformat(), base=base, version=VERSION_API, modelo=modelo
    ))
    print("Ajusta la llamada a _http_json a la firma real de _cerebras.")
    print("Si _http_json no acepta headers, agregale el parametro (el UA debe seguir yendo).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
