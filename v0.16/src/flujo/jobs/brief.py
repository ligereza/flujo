"""Modelo de Brief y serialización YAML simple.

El brief.yaml es el documento canónico que describe un pedido creativo.
Usamos un parser YAML mínimo para no depender de pyyaml en runtime,
aunque también soportamos yaml.safe_load si está disponible.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class EstadoJob(str, Enum):
    """Estados posibles de un job en su ciclo de vida."""

    BORRADOR = "borrador"
    BRIEF_EXTRAIDO = "brief_extraido_pendiente_revision"
    PENDIENTE_DATOS = "pendiente_datos"
    LISTO_PARA_DISENAR = "listo_para_disenar"
    EN_DISENO = "en_diseno"
    GENERADO = "generado"
    ENTREGADO = "entregado"
    PAUSADO = "pausado"
    CANCELADO = "cancelado"


# Estados terminales / no automáticos
ESTADOS_TERMINALES = {EstadoJob.ENTREGADO, EstadoJob.CANCELADO, EstadoJob.PAUSADO}

# Transiciones válidas
TRANSICIONES_VALIDAS: Dict[EstadoJob, set] = {
    EstadoJob.BORRADOR: {
        EstadoJob.BRIEF_EXTRAIDO,
        EstadoJob.PENDIENTE_DATOS,
        EstadoJob.LISTO_PARA_DISENAR,
        EstadoJob.CANCELADO,
    },
    EstadoJob.BRIEF_EXTRAIDO: {
        EstadoJob.PENDIENTE_DATOS,
        EstadoJob.LISTO_PARA_DISENAR,
        EstadoJob.PAUSADO,
    },
    EstadoJob.PENDIENTE_DATOS: {
        EstadoJob.LISTO_PARA_DISENAR,
        EstadoJob.PAUSADO,
        EstadoJob.CANCELADO,
    },
    EstadoJob.LISTO_PARA_DISENAR: {
        EstadoJob.EN_DISENO,
        EstadoJob.PAUSADO,
    },
    EstadoJob.EN_DISENO: {
        EstadoJob.GENERADO,
        EstadoJob.PAUSADO,
    },
    EstadoJob.GENERADO: {
        EstadoJob.ENTREGADO,
        EstadoJob.EN_DISENO,  # volver si hay ajustes
    },
    EstadoJob.PAUSADO: {
        EstadoJob.PENDIENTE_DATOS,
        EstadoJob.LISTO_PARA_DISENAR,
        EstadoJob.EN_DISENO,
        EstadoJob.CANCELADO,
    },
    EstadoJob.ENTREGADO: set(),
    EstadoJob.CANCELADO: set(),
}


@dataclass
class Medidas:
    ancho_cm: Optional[float] = None
    alto_cm: Optional[float] = None
    orientacion: str = ""
    sangrado_mm: Optional[float] = None
    area_segura_mm: Optional[float] = None


@dataclass
class Entrega:
    editable_svg: bool = True
    vectorizado_svg: bool = True
    pdf_impresion: bool = False
    zip: bool = True
    otro: str = ""


@dataclass
class Contenido:
    fuente: str = "correo_original"
    texto_aprobado: bool = False
    notas: str = ""


@dataclass
class Restricciones:
    no_inventar_claims: bool = True
    texto_vectorizado: bool = True
    editable_para_illustrator: bool = True


@dataclass
class Brief:
    """Modelo de brief.yaml."""

    id: str = ""
    estado: EstadoJob = EstadoJob.BORRADOR
    origen: str = ""
    cliente: str = ""
    proyecto: str = ""
    tipo_pieza: str = ""
    posibles_formatos: List[str] = field(default_factory=list)
    medidas: Medidas = field(default_factory=Medidas)
    entrega: Entrega = field(default_factory=Entrega)
    productos: List[str] = field(default_factory=list)
    contenido: Contenido = field(default_factory=Contenido)
    restricciones: Restricciones = field(default_factory=Restricciones)
    pendientes: List[str] = field(default_factory=list)

    def tiene_datos_criticos(self) -> bool:
        """Retorna True si el brief tiene tipo + medidas + al menos un producto o descripción."""
        return bool(
            self.tipo_pieza
            and self.medidas.ancho_cm
            and self.medidas.alto_cm
        )

    def resumen_pendientes(self) -> str:
        if not self.pendientes:
            return "sin pendientes"
        return f"{len(self.pendientes)} pendientes"

    def puede_transicionar(self, nuevo: EstadoJob) -> bool:
        return nuevo in TRANSICIONES_VALIDAS.get(self.estado, set())


# ============================================================
# YAML simple: parser y dumper sin dependencias
# ============================================================

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _coerce_scalar(v: str) -> Any:
    """Convierte string a bool/int/float si corresponde."""
    v = v.strip()
    if v == "":
        return ""
    if v.lower() in ("true", "yes", "si", "sí"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if v in ("[]", "~", "null", "None"):
        return []
    # número
    try:
        if "." in v or "," in v:
            return float(v.replace(",", "."))
        return int(v)
    except ValueError:
        pass
    return _strip_quotes(v)


def parse_yaml_simple(text: str) -> Dict[str, Any]:
    """Parser YAML mínimo: soporta mappings, listas anidadas, escalares.

    No soporta anchors, multi-doc, flow style. Suficiente para brief.yaml.
    """
    lines = text.splitlines()
    root: Dict[str, Any] = {}
    # Pila de (indent, container, is_list)
    stack: List[tuple] = [(-1, root, False)]

    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        # pop stack hasta encontrar un padre con menor indent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(-1, root, False)]
        parent_indent, parent, _ = stack[-1]

        # entrada de lista: '- algo' bajo cualquier nivel
        if content.startswith("- "):
            item = content[2:].strip()
            if not isinstance(parent, list):
                # convertir
                pass
            if isinstance(parent, list):
                # ¿el item tiene sub-claves?
                if ":" in item and not item.startswith('"'):
                    key, _, val = item.partition(":")
                    key = key.strip()
                    val = val.strip()
                    sub: Dict[str, Any] = {key: _coerce_scalar(val)}
                    parent.append(sub)
                    stack.append((indent, sub, False))
                else:
                    parent.append(_coerce_scalar(item))
            continue

        # mapping key: value
        if ":" in content:
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            if isinstance(parent, dict):
                if val == "":
                    # crear contenedor; deducir tipo mirando siguientes líneas
                    container: Any = {}
                    parent[key] = container
                    stack.append((indent, container, False))
                else:
                    parent[key] = _coerce_scalar(val)
        else:
            # línea suelta: ignorar
            continue

    return root


def dump_yaml_simple(data: Dict[str, Any], indent: int = 0) -> str:
    """Dumper YAML simple que produce el mismo formato que el parser entiende."""
    out: List[str] = []
    _dump_yaml(data, out, indent)
    return "\n".join(out) + "\n"


def _dump_yaml(data: Any, out: List[str], indent: int) -> None:
    pad = " " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                out.append(f"{pad}{k}:")
                _dump_yaml(v, out, indent + 2)
            elif isinstance(v, list):
                out.append(f"{pad}{k}:")
                _dump_yaml(v, out, indent + 2)
            else:
                out.append(f"{pad}{k}: {_format_scalar(v)}")
    elif isinstance(data, list):
        if not data:
            out.append(f"{pad}[]")
        else:
            for item in data:
                if isinstance(item, dict):
                    # primer key en línea con '- ', resto indentado
                    items = list(item.items())
                    if items:
                        first_k, first_v = items[0]
                        if isinstance(first_v, (dict, list)):
                            out.append(f"{pad}- {first_k}:")
                            _dump_yaml(first_v, out, indent + 4)
                        else:
                            out.append(f"{pad}- {first_k}: {_format_scalar(first_v)}")
                        for k, v in items[1:]:
                            if isinstance(v, (dict, list)):
                                out.append(f"{pad}  {k}:")
                                _dump_yaml(v, out, indent + 4)
                            else:
                                out.append(f"{pad}  {k}: {_format_scalar(v)}")
                    else:
                        out.append(f"{pad}- {{}}")
                else:
                    out.append(f"{pad}- {_format_scalar(item)}")


def _format_scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in ":#") or s == "":
        return f'"{s}"'
    return s


# ============================================================
# Carga / guardado de brief desde archivo
# ============================================================

def _build_brief(data: Dict[str, Any]) -> Brief:
    medidas_raw = data.get("medidas", {}) or {}
    entrega_raw = data.get("entrega", {}) or {}
    contenido_raw = data.get("contenido", {}) or {}
    restr_raw = data.get("restricciones", {}) or {}

    medidas = Medidas(
        ancho_cm=_num(medidas_raw.get("ancho_cm")),
        alto_cm=_num(medidas_raw.get("alto_cm")),
        orientacion=str(medidas_raw.get("orientacion", "") or ""),
        sangrado_mm=_num(medidas_raw.get("sangrado_mm")),
        area_segura_mm=_num(medidas_raw.get("area_segura_mm")),
    )
    entrega = Entrega(
        editable_svg=bool(entrega_raw.get("editable_svg", True)),
        vectorizado_svg=bool(entrega_raw.get("vectorizado_svg", True)),
        pdf_impresion=bool(entrega_raw.get("pdf_impresion", False)),
        zip=bool(entrega_raw.get("zip", True)),
        otro=str(entrega_raw.get("otro", "") or ""),
    )
    contenido = Contenido(
        fuente=str(contenido_raw.get("fuente", "correo_original") or ""),
        texto_aprobado=bool(contenido_raw.get("texto_aprobado", False)),
        notas=str(contenido_raw.get("notas", "") or ""),
    )
    restr = Restricciones(
        no_inventar_claims=bool(restr_raw.get("no_inventar_claims", True)),
        texto_vectorizado=bool(restr_raw.get("texto_vectorizado", True)),
        editable_para_illustrator=bool(restr_raw.get("editable_para_illustrator", True)),
    )

    estado_str = str(data.get("estado", "borrador") or "borrador")
    try:
        estado = EstadoJob(estado_str)
    except ValueError:
        estado = EstadoJob.BORRADOR

    productos = data.get("productos", []) or []
    if isinstance(productos, str):
        productos = [productos]
    pendientes = data.get("pendientes", []) or []
    if isinstance(pendientes, str):
        pendientes = [pendientes]
    posibles = data.get("posibles_formatos", []) or []
    if isinstance(posibles, str):
        posibles = [posibles]

    return Brief(
        id=str(data.get("id", "") or ""),
        estado=estado,
        origen=str(data.get("origen", "") or ""),
        cliente=str(data.get("cliente", "") or ""),
        proyecto=str(data.get("proyecto", "") or ""),
        tipo_pieza=str(data.get("tipo_pieza", "") or ""),
        posibles_formatos=list(posibles),
        medidas=medidas,
        entrega=entrega,
        productos=list(productos),
        contenido=contenido,
        restricciones=restr,
        pendientes=list(pendientes),
    )


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None


def load_brief(path: Path) -> Brief:
    """Carga un brief desde archivo YAML."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    # Intentar primero con yaml si está disponible
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            data = {}
    except ImportError:
        data = parse_yaml_simple(text)
    return _build_brief(data)


def save_brief(path: Path, brief: Brief) -> None:
    """Guarda un brief en formato YAML."""
    data: Dict[str, Any] = {
        "id": brief.id,
        "estado": brief.estado.value,
        "origen": brief.origen,
        "cliente": brief.cliente,
        "proyecto": brief.proyecto,
        "tipo_pieza": brief.tipo_pieza,
        "medidas": {
            "ancho_cm": brief.medidas.ancho_cm if brief.medidas.ancho_cm is not None else "",
            "alto_cm": brief.medidas.alto_cm if brief.medidas.alto_cm is not None else "",
            "orientacion": brief.medidas.orientacion,
            "sangrado_mm": brief.medidas.sangrado_mm if brief.medidas.sangrado_mm is not None else "",
            "area_segura_mm": brief.medidas.area_segura_mm if brief.medidas.area_segura_mm is not None else "",
        },
        "entrega": {
            "editable_svg": brief.entrega.editable_svg,
            "vectorizado_svg": brief.entrega.vectorizado_svg,
            "pdf_impresion": brief.entrega.pdf_impresion,
            "zip": brief.entrega.zip,
            "otro": brief.entrega.otro,
        },
        "productos": brief.productos,
        "contenido": {
            "fuente": brief.contenido.fuente,
            "texto_aprobado": brief.contenido.texto_aprobado,
            "notas": brief.contenido.notas,
        },
        "restricciones": {
            "no_inventar_claims": brief.restricciones.no_inventar_claims,
            "texto_vectorizado": brief.restricciones.texto_vectorizado,
            "editable_para_illustrator": brief.restricciones.editable_para_illustrator,
        },
        "pendientes": brief.pendientes,
    }
    if brief.posibles_formatos:
        data["posibles_formatos"] = brief.posibles_formatos
    # limpiar vacíos
    data = _strip_empty(data)
    out = dump_yaml_simple(data)
    Path(path).write_text(out, encoding="utf-8")


def _strip_empty(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v2 = _strip_empty(v)
            if v2:
                out[k] = v2
        elif isinstance(v, list):
            if v:
                out[k] = v
        elif v is None or v == "":
            continue
        else:
            out[k] = v
    return out


# ============================================================
# Extracción de brief desde texto/correo
# ============================================================

import re

PRODUCT_HINTS = [
    "impulso", "magnesio", "creatina", "proteína", "proteina", "pre fiesta",
    "post fiesta", "hongos adaptógenos", "hongos adaptogenos", "whey", "iso protein",
    "vitamina", "omega", "colágeno", "colageno",
]

TIPO_HINTS = ["etiqueta", "flyer", "sticker", "tarjeta", "afiche", "catalogo", "catálogo", "rider", "dossier", "one_page"]


def _find_measure(text: str):
    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*[x×]\s*(\d+(?:[\.,]\d+)?)\s*(cm|mm)?", text, re.I)
    if not m:
        return None, None, None
    a = float(m.group(1).replace(",", "."))
    b = float(m.group(2).replace(",", "."))
    unit = (m.group(3) or "cm").lower()
    if unit == "mm":
        a, b = a / 10, b / 10
    return a, b, "horizontal" if a >= b else "vertical"


def _detect_delivery(text: str) -> Dict[str, Any]:
    low = text.lower()
    return {
        "editable_svg": any(x in low for x in ["editable", "svg editable", "illustrator", ".ai", "ai "]),
        "vectorizado_svg": any(x in low for x in ["vector", "vectorizado", "curvas", "contornos", "trazados"]),
        "pdf_impresion": "pdf" in low,
        "zip": "zip" in low or "comprimido" in low,
        "otro": "",
    }


def _detect_type(text: str) -> str:
    low = text.lower()
    for key in TIPO_HINTS:
        if key in low:
            return key
    return ""


def _detect_products(text: str) -> List[str]:
    low = text.lower()
    found: List[str] = []
    for p in PRODUCT_HINTS:
        if p in low:
            label = p.title().replace("Proteina", "Proteína")
            if label not in found:
                found.append(label)
    return found


def _detect_bleed(text: str) -> Optional[float]:
    low = text.lower()
    m = re.search(r"sangrado\D{0,10}(\d+(?:[\.,]\d+)?)\s*mm", low)
    if m:
        return float(m.group(1).replace(",", "."))
    return None if "sangrado" not in low else None


def brief_from_text(text: str, job_id: str = "") -> Brief:
    """Genera un Brief inicial a partir de texto/correo.

    No pretende ser perfecto: solo acelera el primer ordenamiento
    para que un humano o IA revise y complete.
    """
    ancho, alto, orient = _find_measure(text)
    entrega_dict = _detect_delivery(text)
    tipo = _detect_type(text)
    productos = _detect_products(text)
    sangrado = _detect_bleed(text)

    pendientes: List[str] = []
    if not ancho or not alto:
        pendientes.append("Confirmar medida final.")
    if not tipo:
        pendientes.append("Confirmar tipo de pieza.")
    if not productos:
        pendientes.append("Confirmar producto(s).")
    if not any(entrega_dict.values()):
        pendientes.append("Confirmar formato de entrega.")
    if "sangrado" in text.lower() and sangrado is None:
        pendientes.append("Confirmar sangrado (mm).")

    return Brief(
        id=job_id,
        estado=EstadoJob.BRIEF_EXTRAIDO,
        origen="correo_jefe",
        tipo_pieza=tipo,
        medidas=Medidas(
            ancho_cm=ancho,
            alto_cm=alto,
            orientacion=orient or "",
            sangrado_mm=sangrado,
        ),
        entrega=Entrega(
            editable_svg=entrega_dict["editable_svg"],
            vectorizado_svg=entrega_dict["vectorizado_svg"],
            pdf_impresion=entrega_dict["pdf_impresion"],
            zip=entrega_dict["zip"],
            otro=entrega_dict["otro"],
        ),
        productos=productos,
        contenido=Contenido(
            fuente="correo_original",
            texto_aprobado=False,
            notas="Extraído automáticamente; revisar antes de generar.",
        ),
        restricciones=Restricciones(),
        pendientes=pendientes,
    )
