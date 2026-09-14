"""Normalizacion de eventos de productoras: fecha a ISO y lineup a campo propio.

Por que existe: la triangulacion que la DB necesita es "fecha + headliner ->
productora". Pero en `data/productoras/*.json` la fecha es prosa
("12 septiembre 2026", "MAR 28 (año no confirmado)") y el headliner viene
enterrado en el titulo del evento:

    "Piknic Electronik Santiago -- lineup PARTIBOI69 (co-org GLOVOX)"

Con los datos asi, la triangulacion no se puede correr por mas agentes que se
le pongan encima: no hay dos campos que cruzar. Este modulo saca esos dos
campos del texto.

Principio: NUNCA inventar. Si el año no esta, la fecha queda incompleta y se
dice; no se rellena con el año actual. Cada dato normalizado lleva su nivel de
confianza para que quien lo lea sepa si puede confiar o tiene que revisar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

MESES = {
    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "setiembre": 9, "sep": 9, "sept": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
}

# Confianza de un dato derivado del texto.
ALTA = "alta"          # dia, mes y año explicitos
PARCIAL = "parcial"    # falta el año, o es un rango
NULA = "nula"          # no se pudo interpretar


def _plano(texto: str) -> str:
    """Minusculas sin acentos, para comparar sin sorpresas."""
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


@dataclass
class FechaNormalizada:
    iso: str | None          # "2026-09-12", o "2026-09" si falta el dia
    confianza: str
    nota: str = ""
    crudo: str = ""

    @property
    def anio(self) -> int | None:
        return int(self.iso[:4]) if self.iso else None


def parsear_fecha(crudo: str) -> FechaNormalizada:
    """Interpreta una fecha escrita a mano en español.

    Reconoce: "12 septiembre 2026", "11/12-oct-2025", "MAR 28", "2026-09-12",
    "20-nov-2026". Si falta el año NO lo inventa: devuelve confianza parcial.
    """
    crudo = (crudo or "").strip()
    if not crudo:
        return FechaNormalizada(None, NULA, "vacia", crudo)

    t = _plano(crudo)

    # ISO ya normalizada
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return FechaNormalizada(f"{m.group(1)}-{m.group(2)}-{m.group(3)}", ALTA, "", crudo)

    anio_m = re.search(r"\b(19|20)\d{2}\b", t)
    anio = anio_m.group(0) if anio_m else None
    mes = next((n for nombre, n in MESES.items() if re.search(rf"\b{nombre}\b", t)), None)

    # Se saca el año del texto ANTES de buscar el dia. Si no, en "20-nov-2026"
    # el "20" se descartaba por estar contenido en "2026" (comparacion por
    # substring): el dia se perdia y la fecha quedaba a nivel mes.
    sin_anio = (t[:anio_m.start()] + " " + t[anio_m.end():]) if anio_m else t

    # Rango de dias: "11/12-oct-2025" o "14-15 de noviembre"
    rango = re.search(r"\b(\d{1,2})\s*[/y-]\s*(\d{1,2})\b", sin_anio)
    dia_m = re.search(r"\b(\d{1,2})\b(?!\s*[:.])", sin_anio)
    dia = None
    nota = ""
    if rango and mes:
        dia = int(rango.group(1))
        nota = f"rango de dias {rango.group(1)}-{rango.group(2)}, se toma el primero"
    elif dia_m:
        posible = int(dia_m.group(1))
        if 1 <= posible <= 31:
            dia = posible

    if mes is None:
        return FechaNormalizada(None, NULA, "no se reconocio el mes", crudo)

    if anio is None:
        base = f"????-{mes:02d}" + (f"-{dia:02d}" if dia else "")
        return FechaNormalizada(
            None, PARCIAL,
            f"sin año en el origen (mes {mes:02d}" + (f", dia {dia}" if dia else "") + f"); {nota}".rstrip("; "),
            crudo,
        )

    if dia is None:
        return FechaNormalizada(f"{anio}-{mes:02d}", PARCIAL, f"sin dia; {nota}".rstrip("; "), crudo)

    return FechaNormalizada(f"{anio}-{mes:02d}-{dia:02d}", ALTA, nota, crudo)


# "lineup X, Y", "con X", "feat X", "(co-org Y)", "co-organiza Y"
_LINEUP_RE = re.compile(r"\b(?:line ?up|lineup|con|feat\.?|presenta)\s*:?\s*([^()\[\]]+)", re.I)
_COORG_RE = re.compile(r"\b(?:co[- ]?org(?:aniza)?|junto a|en alianza con)\s*:?\s*([^()\[\],]+)", re.I)
_SEPARADORES = re.compile(r"\s*(?:,|\+|&| y | b2b | vs )\s*", re.I)
_RUIDO = {"", "-", "--", "el", "la", "los", "las", "de", "del"}


def _limpiar_nombres(texto: str) -> list[str]:
    partes = [p.strip(" .-–—") for p in _SEPARADORES.split(texto)]
    vistos: list[str] = []
    for p in partes:
        if not p or _plano(p) in _RUIDO or len(p) > 60:
            continue
        if p not in vistos:
            vistos.append(p)
    return vistos


def extraer_lineup(titulo: str) -> tuple[list[str], list[str]]:
    """Saca (lineup, co_organiza) del titulo del evento.

    El titulo suele traer el dato pegado: "... -- lineup PARTIBOI69 (co-org
    GLOVOX)". Mientras siga ahi, no se puede cruzar por headliner.
    """
    titulo = titulo or ""
    co = []
    for m in _COORG_RE.finditer(titulo):
        co += _limpiar_nombres(m.group(1))
    sin_co = _COORG_RE.sub(" ", titulo)
    line: list[str] = []
    for m in _LINEUP_RE.finditer(sin_co):
        line += _limpiar_nombres(m.group(1))
    return line, co


@dataclass
class EventoNormalizado:
    nombre: str
    fecha: FechaNormalizada
    venue: str = ""
    estado: str = ""
    lineup: list[str] = field(default_factory=list)
    co_organiza: list[str] = field(default_factory=list)
    fuente: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def a_dict(self) -> dict[str, Any]:
        """Salida para el json: agrega campos SIN pisar los existentes."""
        d: dict[str, Any] = {
            "nombre": self.nombre,
            "fecha": self.fecha.crudo,
            "venue": self.venue,
            "estado": self.estado,
        }
        if self.fecha.iso:
            d["fecha_iso"] = self.fecha.iso
        d["fecha_confianza"] = self.fecha.confianza
        if self.fecha.nota:
            d["fecha_nota"] = self.fecha.nota
        if self.lineup:
            d["lineup"] = self.lineup
        if self.co_organiza:
            d["co_organiza"] = self.co_organiza
        if self.fuente:
            d["fuente"] = self.fuente
        # Preserve only operational references/parameters that the RD panel
        # is explicitly allowed to consume.  Contacts and arbitrary source
        # fields never pass through this normalizer.
        for key in (
            "flyer_ref", "rider_ref", "layout_ref", "pack", "preset",
            "duracion_horas", "asistentes_estimados", "voluntarios",
            "layout_mode",
        ):
            value = self.extras.get(key)
            if value not in (None, ""):
                d[key] = value
        return d


def normalizar_evento(ev: dict[str, Any]) -> EventoNormalizado:
    nombre = str(ev.get("nombre") or "")
    lineup = [str(x) for x in (ev.get("lineup") or [])]
    co = [str(x) for x in (ev.get("co_organiza") or [])]
    if not lineup and not co:
        lineup, co = extraer_lineup(nombre)
    return EventoNormalizado(
        nombre=nombre,
        fecha=parsear_fecha(str(ev.get("fecha") or "")),
        venue=str(ev.get("venue") or ""),
        estado=str(ev.get("estado") or ""),
        lineup=lineup,
        co_organiza=co,
        fuente=str(ev.get("fuente") or ""),
        extras={key: ev.get(key) for key in (
            "flyer_ref", "rider_ref", "layout_ref", "pack", "preset",
            "duracion_horas", "asistentes_estimados", "voluntarios",
            "layout_mode",
        ) if ev.get(key) not in (None, "")},
    )


def normalizar_productora(datos: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Devuelve (datos con eventos normalizados, lista de avisos)."""
    avisos: list[str] = []
    eventos = datos.get("eventos") or []
    if not isinstance(eventos, list):
        return datos, ["el campo 'eventos' no es una lista: se deja intacto"]
    nuevos = []
    for i, ev in enumerate(eventos):
        if not isinstance(ev, dict):
            avisos.append(f"evento #{i} no es un objeto: se deja intacto")
            nuevos.append(ev)
            continue
        n = normalizar_evento(ev)
        if n.fecha.confianza != ALTA:
            avisos.append(f"evento #{i} '{n.nombre[:40]}': fecha {n.fecha.confianza} ({n.fecha.nota or n.fecha.crudo})")
        if not n.lineup:
            avisos.append(f"evento #{i} '{n.nombre[:40]}': sin lineup -> no triangulable")
        nuevos.append(n.a_dict())
    salida = dict(datos)
    salida["eventos"] = nuevos
    return salida, avisos


def indice_triangulacion(productoras: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Indice headliner -> eventos, que es lo que la triangulacion necesita.

    Clave: nombre del artista en plano (sin acentos, minusculas), para que
    "Partiboi69" y "PARTIBOI69" caigan juntos.
    """
    indice: dict[str, list[dict[str, Any]]] = {}
    for slug, datos in productoras.items():
        for ev in (datos.get("eventos") or []):
            if not isinstance(ev, dict):
                continue
            for artista in (ev.get("lineup") or []):
                indice.setdefault(_plano(str(artista)), []).append({
                    "artista": artista,
                    "productora": slug,
                    "evento": ev.get("nombre", ""),
                    "fecha_iso": ev.get("fecha_iso"),
                    "venue": ev.get("venue", ""),
                })
    return indice
