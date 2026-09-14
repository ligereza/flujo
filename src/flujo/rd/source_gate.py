# -*- coding: utf-8 -*-
"""Compuerta de calidad de fuente: una pregunta sobre derecho chileno no se
responde con un PDF de pedagogia peruano.

El defecto que este modulo cierra (medido, no supuesto): el informe
`docs/rd/informes/ley_20000_marco_legal.md` (2026-07-22) afirma que el ISP
autoriza a ONG a realizar pruebas de composicion quimica, citando tres fuentes
que son -- segun su propio bloque `meta:` -- una escuela de pedagogia peruana,
una universidad venezolana y un agregador de libros pirateados. Ninguna es
fuente sobre derecho chileno. El sistema medio las tildes de ese informe
(93/100) y no midio si las fuentes eran del tema.

El contraste esta en el mismo repo y es el diagnostico: el informe de
fundaciones internacionales (`docs/becas/informes/2026...fundaciones...`) se
porto BIEN -- dijo "no se localizan anuncios explicitos" y listo las lagunas.
Fallo ruidosamente. El legal fallo en silencio. Misma maquina, dos
comportamientos: el problema no es el modelo, es que no hay compuerta.

Regla: sin fuente primaria del dominio, el informe NO AFIRMA. Registra que
busco, que encontro, y se marca. Un informe marcado es util; un informe que
inventa jurisprudencia es un pasivo.

Sin dependencias: solo stdlib. Los helpers de fallback compartidos viven en
`cultura/mak_codex/fallback_util.py`; este modulo no mantiene una copia.
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit

__all__ = [
    "DOMINIOS",
    "clasificar",
    "hay_primaria",
    "dominio_de_tema",
    "sugerir_queries",
    "encabezado",
    "instruccion_sintesis",
    "evaluar",
]

# Un dominio de conocimiento = que hosts cuentan como fuente PRIMARIA.
# Primaria significa: la publica quien tiene autoridad sobre el hecho.
# No es una lista de sitios "buenos": es una lista de sitios COMPETENTES.
DOMINIOS: dict[str, dict] = {
    "cl_legal": {
        "descripcion": "derecho chileno: leyes, reglamentos, organismos del Estado",
        "primarias": (
            "bcn.cl",
            "leychile.cl",
            "diariooficial.interior.gob.cl",
            "ispch.gob.cl",
            "minsal.gob.cl",
            "minsal.cl",
            "senda.gob.cl",
            "contraloria.cl",
            "tribunalconstitucional.cl",
            "pjud.cl",
            "camara.cl",
            "senado.cl",
        ),
        "pistas": (
            "ley 20.000", "ley 21.817", "ley 21.719", "ley chile", "codigo penal",
            "reglamento", "decreto", "isp", "minsal", "senda", "normativa chilena",
            "marco legal", "que puede y no puede", "jurisprudencia",
        ),
        "sitios_sugeridos": ("bcn.cl", "leychile.cl", "diariooficial.interior.gob.cl"),
    },
    "cl_fondos": {
        "descripcion": "fondos y convocatorias publicas chilenas",
        "primarias": (
            "fondosdecultura.cl",
            "fondos.gob.cl",
            "cultura.gob.cl",
            "corfo.cl",
            "fosis.gob.cl",
            "senda.gob.cl",
            "anid.cl",
            "chileatiende.gob.cl",
        ),
        "pistas": ("fondart", "convocatoria", "fondos de cultura", "corfo", "fosis", "postulacion"),
        "sitios_sugeridos": ("fondosdecultura.cl", "fondos.gob.cl", "chileatiende.gob.cl"),
    },
    "norma_tecnica": {
        "descripcion": "estandares tecnicos publicados",
        "primarias": (
            "gdtf-share.com",
            "gdtf.eu",
            "github.com/mvrdevelopment",
            "din.de",
            "iso.org",
            "esta.org",
            "tc.esta.org",
        ),
        "pistas": ("gdtf", "mvr", "din spec", "iso ", "estandar abierto", "esta standard"),
        "sitios_sugeridos": ("gdtf-share.com", "github.com/mvrdevelopment/spec"),
    },
    # Added 2026-07-31. Cause, measured: the 8-report watsonx batch
    # (2026-07-30) ran scientific harm-reduction topics and six of eight got
    # `dominio: None` -- no primary-source requirement at all. The reports cite
    # scielo/journals, but nothing CHECKS it. Same defect class the module was
    # built for, one domain short. Goes LAST on purpose: dict order decides
    # detection precedence, and a legal question that mentions harm reduction
    # ("ley 20.000 y reduccion de danos") must keep hitting `cl_legal` first.
    "biomedico": {
        "descripcion": "evidencia biomédica: farmacología, toxicología, "
                       "epidemiología y reducción de daños",
        "primarias": (
            "pubmed.ncbi.nlm.nih.gov",
            "ncbi.nlm.nih.gov",
            "scielo.org",
            "scielo.cl",
            "scielo.br",
            "scielo.org.mx",
            "scielo.org.ar",
            "scielo.org.co",
            "scielo.org.pe",
            "who.int",
            "euda.europa.eu",
            "emcdda.europa.eu",
            "ispch.gob.cl",
            "cochrane.org",
            "cochranelibrary.com",
        ),
        # Stems, not full words: `dominio_de_tema` matches by substring, so
        # "farmacolog" covers farmacologia/farmacologico. ASCII only -- the
        # topic is diacritic-folded before matching (see `_plegar`).
        "pistas": (
            "farmacolog", "farmacocinetic", "toxicolog", "toxicidad",
            "epidemiolog", "sobredosis", "reduccion de dano", "harm reduction",
            "drug checking", "analisis de sustancias", "neurotox",
            "ensayo clinico", "evidencia clinica", "efectos adversos",
            "via de administracion", "interaccion entre sustancias",
        ),
        "sitios_sugeridos": ("pubmed.ncbi.nlm.nih.gov", "scielo.org", "who.int"),
    },
    # El dominio de lo que el organismo investiga de VERDAD. Medido el
    # 2026-08-01 sobre los ultimos 55 informes: 54 salieron con
    # `dominio: None`, o sea la compuerta de fuentes primarias NUNCA corrio, y
    # el estado anterior lo leia como "produce cero fuentes primarias" -- como si
    # fallara buscandolas. No fallaba: nadie le habia dicho cuales son. Los
    # tres dominios que existian son institucionales chilenos y el 98% de los
    # temas de MAK son eventos y productoras.
    #
    # Va ULTIMO y sus pistas son del OFICIO, no del ambiente. `dominio_de_tema`
    # devuelve el primero que matchea, asi que un dominio ancho puesto arriba
    # se come a los especificos: con la pista `fiesta` y en primer lugar, este
    # se llevaba "reduccion de danos en fiestas electronicas", que es
    # biomedico. Lo atrapo `test_detecta_dominio_con_tildes`.
    #
    # Que es primaria aca: quien ORGANIZO dice quien organizo. El Instagram de
    # la productora, el sitio del venue y la ticketera son el registro; una
    # nota de prensa o un agregador son secundarias, porque repiten. Ese corte
    # es el mismo que el usuario usa a mano ("headliner + fecha = productora
    # encontrable").
    "cl_eventos": {
        "descripcion": "eventos y productoras en Chile: quien organizo, donde y cuando",
        "primarias": (
            "instagram.com",
            "facebook.com/events",
            "passline.com",
            "puntoticket.com",
            "ticketplus.cl",
            "portaldisc.com",
            "clubhipico.cl",
            "movistararena.cl",
            "teatrocaupolican.cl",
            "espacioriesco.cl",
            "blondie.cl",
            "clubchocolate.cl",
            "bar-loreto.cl",
            "sala-metronomo.cl",
        ),
        "pistas": (
            "productora", "que productora", "quien organizo", "organizo el evento",
            "evento del", "festival", "line up", "lineup", "headliner",
            "venue", "recinto", "club hipico", "caupolican", "movistar arena",
            "espacio riesco", "blondie", "tocata",
            "ticketera", "entradas para",
        ),
        "sitios_sugeridos": ("instagram.com", "passline.com", "puntoticket.com"),
    },
}

# Hosts que NUNCA cuentan como primaria en ningun dominio: son buscadores,
# agregadores o repositorios de terceros. Aparecen en `sources` porque el
# fetch devolvio ALGO, no porque contengan la respuesta.
NUNCA_PRIMARIA = (
    "google.com", "scholar.google", "bing.com", "duckduckgo.com",
    "dokumen.pub", "scribd.com", "coursehero.com", "studocu.com",
    "es.wikipedia.org", "en.wikipedia.org",
)


def _host(url: str) -> str:
    try:
        h = (urlsplit(url).netloc or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _coincide(url: str, patron: str) -> bool:
    """`patron` puede ser un host (`bcn.cl`) o host+ruta (`github.com/mvrdevelopment`)."""
    u = url.lower()
    if "/" in patron:
        return patron in u
    h = _host(url)
    return h == patron or h.endswith("." + patron)


def clasificar(urls, dominio: str) -> tuple[list[str], list[str]]:
    """Devuelve (primarias, secundarias). Dominio desconocido -> todo secundario."""
    urls = [u for u in (urls or []) if isinstance(u, str) and u.strip()]
    cfg = DOMINIOS.get(dominio)
    if not cfg:
        return [], list(urls)
    prim = []
    for u in urls:
        if any(_coincide(u, n) for n in NUNCA_PRIMARIA):
            continue
        if any(_coincide(u, p) for p in cfg["primarias"]):
            prim.append(u)
    sec = [u for u in urls if u not in prim]
    return prim, sec


def hay_primaria(urls, dominio: str) -> bool:
    return bool(clasificar(urls, dominio)[0])


def _plegar(texto: str) -> str:
    """Diacritic fold for KEYWORD MATCHING only (a machine key operation --
    lossy folding never touches a human-read value). Reports and their
    harvested questions carry correct Spanish diacritics, while `pistas` are
    ASCII stems: without folding, "farmacología" misses "farmacolog"."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def dominio_de_tema(tema: str) -> str | None:
    """Detecta el dominio por pistas en el texto del tema. None si no aplica
    ninguno: la mayoria de las preguntas culturales NO tienen fuente primaria y
    esta compuerta no debe estorbarlas."""
    t = _plegar((tema or "").lower())
    for nombre, cfg in DOMINIOS.items():
        if any(p in t for p in cfg["pistas"]):
            return nombre
    return None


def sugerir_queries(tema: str, dominio: str) -> list[str]:
    """Queries con `site:` para que la busqueda tenga la chance de traer
    primaria. Media linea de codigo, y cambia que se encuentra."""
    cfg = DOMINIOS.get(dominio)
    if not cfg:
        return [tema]
    base = re.sub(r"\s+", " ", (tema or "").strip())
    return [base] + [f"{base} site:{s}" for s in cfg["sitios_sugeridos"]]


_MARCA = "SIN FUENTE PRIMARIA"


def encabezado(urls, dominio: str) -> str:
    """Bloque que va ARRIBA del informe. Cadena vacia si hay primaria."""
    prim, sec = clasificar(urls, dominio)
    if prim:
        return ""
    cfg = DOMINIOS.get(dominio, {})
    desc = cfg.get("descripcion", dominio)
    consultadas = "\n".join(f">   - {u}" for u in sec[:10]) or ">   (ninguna)"
    return (
        f"> **{_MARCA}.** La pregunta es de dominio `{dominio}` ({desc}) y ninguna\n"
        "> de las fuentes consultadas es normativa u oficial de ese dominio.\n"
        ">\n"
        "> **Este documento NO afirma nada sobre el estado del derecho, de las\n"
        "> bases de una convocatoria ni del contenido de una norma.** Registra que\n"
        "> se busco y que no se encontro fuente primaria. No citar como respaldo.\n"
        ">\n"
        "> Fuentes consultadas (secundarias):\n"
        f"{consultadas}\n"
    )


def instruccion_sintesis(urls, dominio: str) -> str:
    """Se ANEXA al `system` de la etapa de sintesis. Cuando no hay primaria,
    cambia la tarea: de 'sintetiza' a 'reporta la ausencia'."""
    if hay_primaria(urls, dominio):
        cfg = DOMINIOS.get(dominio, {})
        return (
            " Hay fuente primaria disponible. Toda afirmacion sobre "
            f"{cfg.get('descripcion', dominio)} debe apoyarse en una fuente primaria "
            "y citarla con su URL. Lo que solo aparezca en fuentes secundarias se "
            "presenta como 'segun fuentes secundarias', nunca como el estado de la norma."
        )
    return (
        " ATENCION: NINGUNA fuente consultada es primaria de este dominio. "
        "PROHIBIDO afirmar el contenido de una norma, un procedimiento, una "
        "autorizacion, un plazo, un monto o un requisito. PROHIBIDO nombrar "
        "organismos como si se hubiera verificado su competencia. Tu tarea NO es "
        "sintetizar: es reportar la ausencia. Escribe unicamente (1) que se "
        "pregunto, (2) que fuentes se obtuvieron y por que no sirven, (3) que "
        "fuentes primarias habria que consultar. Si no puedes hacerlo sin afirmar, "
        "escribe solo la lista de fuentes primarias pendientes."
    )


def evaluar(tema: str, urls, dominio: str | None = None) -> dict:
    """Todo junto, para meter en `meta` y decidir el encabezado.

    Devuelve dict con: dominio, fuentes_primarias, fuentes_secundarias,
    sin_fuente_primaria (bool), marca (str|None).
    """
    dom = dominio or dominio_de_tema(tema)
    if not dom:
        return {
            "dominio": None,
            "fuentes_primarias": [],
            "fuentes_secundarias": list(urls or []),
            "sin_fuente_primaria": False,
            "marca": None,
        }
    prim, sec = clasificar(urls, dom)
    return {
        "dominio": dom,
        "fuentes_primarias": prim,
        "fuentes_secundarias": sec,
        "sin_fuente_primaria": not prim,
        "marca": None if prim else _MARCA,
    }
