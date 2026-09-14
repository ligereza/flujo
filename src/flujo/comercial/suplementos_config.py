"""RD supplements, read from the approved content file.

WHY THIS FILE LOOKS LIKE THIS (2026-07-26)
------------------------------------------
It used to hold a hardcoded dict of seven supplements. Four of them did not
exist -- "Recovery", "Colágeno Fit", "Omega+ Immune", "Sleep Relax" -- and the
copy was gym marketing ("ganancia de masa muscular", "antes del entrenamiento")
for a harm-reduction NGO, with placeholder Dominican phone numbers
(`+1 (809) 555-01xx`) for an organisation that operates in Chile. Running
`flujo suplementos list` printed those invented products as if they were the
real line.

The user's rule, in his words: for supplements, the text that goes on flyers and
labels **always comes from a file an RD manager sends, and that file wins**.
Never invent names, never look up properties, never invent descriptions.

So this module no longer holds content. It reads the approved file:

    projects/piezas_vectoriales/suplementos_rd/01_contenido/contenido_suplementos_rd.json

which is the same source `rd-db` projects and the same one the real generator
(`.claude/skills/entregas-rd/generadores/gen_contraportadas.py`) overlays onto
the approved template. One source of truth per axis:

    style -> svg/suplementos_rd/_plantilla/contraportada_cambios.svg (never edited)
    text  -> the JSON above (comes from the manager)

Contact fields are gone on purpose: the QR and the website are baked into the
approved template and are the same on every flyer, so nothing injects them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict

from ..paths import repo_root

CONTENIDO_REL = (
    "projects/piezas_vectoriales/suplementos_rd/01_contenido/"
    "contenido_suplementos_rd.json"
)


@dataclass
class Suplemento:
    """One supplement, exactly as the approved content file describes it."""

    id: str  # "02_impulso"
    nombre: str  # "IMPULSO"
    tipo: str  # "general" | "producto"
    tag: str  # "Foco sostenido"
    accent: str  # palette key: "yellow", "purple", ...
    color_acento: str  # resolved hex from the palette
    descripcion: list[str]  # paragraphs, verbatim
    section_title: str  # "Nutrientes" | "Productos" | ...
    items: list[str] = field(default_factory=list)  # bullets, verbatim


def _contenido_path():
    return repo_root() / CONTENIDO_REL


@lru_cache(maxsize=1)
def _cargar() -> tuple[Dict[str, Suplemento], dict]:
    """Read the approved file. Raises if it is missing: better a loud failure
    than silently falling back to invented data, which is what used to happen."""
    ruta = _contenido_path()
    if not ruta.is_file():
        raise FileNotFoundError(
            "No existe el archivo de contenido aprobado: %s. "
            "El texto de los suplementos viene de ese archivo, no del codigo." % ruta
        )
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    paleta = datos.get("palette", {})
    salida: Dict[str, Suplemento] = {}
    for f in datos.get("flyers", []):
        acc = f.get("accent", "")
        salida[f["title"]] = Suplemento(
            id=f.get("id", ""),
            nombre=f.get("title", ""),
            tipo=f.get("type", ""),
            tag=f.get("tag", ""),
            accent=acc,
            color_acento=paleta.get(acc, "#F5C54D"),
            descripcion=list(f.get("description", []) or []),
            section_title=f.get("section_title", ""),
            items=list(f.get("items", []) or []),
        )
    return salida, datos.get("project", {})


def suplementos() -> Dict[str, Suplemento]:
    """All supplements, keyed by their real title."""
    return _cargar()[0]


def proyecto() -> dict:
    """Project-level constants (brand, website, canvas, real size)."""
    return _cargar()[1]


def get_suplemento(nombre: str) -> Suplemento:
    """Look a supplement up by title or id, case-insensitively.

    Raises KeyError listing the real names. There is no fallback that fabricates
    a supplement: if it is not in the approved file, it does not exist.
    """
    todos = suplementos()
    objetivo = nombre.strip().lower()
    for titulo, supl in todos.items():
        if titulo.lower() == objetivo or supl.id.lower() == objetivo:
            return supl
    raise KeyError(
        "Suplemento '%s' no existe en el archivo aprobado. Disponibles: %s"
        % (nombre, list(todos.keys()))
    )


def list_suplementos() -> list[str]:
    """Real supplement names, in the order the approved file declares them."""
    return list(suplementos().keys())


if __name__ == "__main__":
    proy = proyecto()
    print("%s -- %s" % (proy.get("name", "Suplementos"), proy.get("brand", "")))
    for supl in suplementos().values():
        print("  %-28s %s" % (supl.nombre, supl.tag))
