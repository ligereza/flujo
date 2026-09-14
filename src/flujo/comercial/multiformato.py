"""Generador de brief comercial multiformato + cotización base.

Caso objetivo:
    "Necesito enviar un brief que explique la estructura imagen / texto de
    flyers, etiquetas, pendones, post de instagram junto con una cotización"

El módulo no inventa precios: genera una estructura profesional con campos
"A definir" salvo que el operador entregue valores por CLI.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class FormatDefinition:
    id: str
    nombre: str
    aliases: tuple[str, ...]
    objetivo: str
    estructura_imagen: tuple[str, ...]
    estructura_texto: tuple[str, ...]
    entregables: tuple[str, ...]
    preguntas: tuple[str, ...]


FORMAT_DEFINITIONS: dict[str, FormatDefinition] = {
    "flyer": FormatDefinition(
        id="flyer",
        nombre="Flyer",
        aliases=("flyer", "flyers", "afiche", "afiches", "volante"),
        objetivo="Pieza de comunicación principal para evento/campaña; debe entenderse rápido y motivar acción.",
        estructura_imagen=(
            "Imagen protagonista o key visual con foco claro.",
            "Logo/marca en zona visible sin competir con el llamado principal.",
            "Jerarquía visual: título primero, datos clave después, CTA al final.",
            "Contraste suficiente para lectura a distancia o en pantalla móvil.",
        ),
        estructura_texto=(
            "Título del evento/campaña.",
            "Bajada corta: qué es y para quién.",
            "Fecha, hora y lugar si aplica.",
            "Llamado a la acción: comprar, inscribirse, asistir, contactar.",
            "Créditos, redes o información legal mínima si corresponde.",
        ),
        entregables=("SVG/AI editable", "PDF impresión si aplica", "PNG/JPG preview", "ZIP de entrega"),
        preguntas=(
            "¿Medida final: 10x14, A5, A4 u otra?",
            "¿Es impresión, digital o ambos?",
            "¿Existe imagen protagonista aprobada?",
        ),
    ),
    "etiqueta": FormatDefinition(
        id="etiqueta",
        nombre="Etiqueta",
        aliases=("etiqueta", "etiquetas", "label", "labels"),
        objetivo="Pieza informativa de producto: debe equilibrar identidad, legibilidad y datos obligatorios.",
        estructura_imagen=(
            "Marca/nombre de producto como elemento principal.",
            "Sistema visual consistente entre variantes/sabores/productos.",
            "Espacio reservado para lote, vencimiento, QR o datos regulatorios si aplica.",
            "Margen seguro y sangrado claros para imprenta.",
        ),
        estructura_texto=(
            "Nombre de producto y variante.",
            "Beneficio o descriptor corto sin claims no aprobados.",
            "Contenido neto, modo de uso, advertencias o ingredientes si aplica.",
            "Datos de contacto, web, QR, lote y vencimiento cuando corresponda.",
        ),
        entregables=("SVG/AI editable", "PDF impresión", "Preview PNG/JPG", "Archivo por variante"),
        preguntas=(
            "¿Medidas exactas y forma de troquel?",
            "¿Cuántas variantes/productos?",
            "¿Textos regulatorios están aprobados?",
        ),
    ),
    "pendon": FormatDefinition(
        id="pendon",
        nombre="Pendón",
        aliases=("pendon", "pendón", "pendones", "banner", "roller"),
        objetivo="Pieza de presencia a distancia; debe comunicar marca/tema con muy poco texto.",
        estructura_imagen=(
            "Logo o marca en tercio superior.",
            "Imagen o patrón visual de alto impacto, legible desde lejos.",
            "Zona inferior para web/redes/QR sin saturación.",
            "Composición vertical con aire y márgenes de seguridad amplios.",
        ),
        estructura_texto=(
            "Frase principal corta (máximo una idea).",
            "Subtítulo o descriptor opcional.",
            "Web, redes, QR o contacto.",
            "Evitar párrafos largos: lectura debe funcionar a distancia.",
        ),
        entregables=("PDF impresión gran formato", "SVG/AI editable", "Preview JPG", "Especificación de medida"),
        preguntas=(
            "¿Medida exacta del pendón/roller?",
            "¿Proveedor de impresión y requisitos de archivo?",
            "¿Distancia de lectura esperada?",
        ),
    ),
    "post_instagram": FormatDefinition(
        id="post_instagram",
        nombre="Post de Instagram",
        aliases=("post instagram", "post de instagram", "instagram", "ig", "post ig", "feed"),
        objetivo="Pieza digital para feed/redes; debe funcionar en móvil y sostener identidad visual.",
        estructura_imagen=(
            "Key visual o composición optimizada para lectura en pantalla pequeña.",
            "Formato sugerido: 1080x1350 para feed o 1080x1080 si se requiere cuadrado.",
            "Área segura para evitar cortes en preview y grilla.",
            "Versión adaptable a historia si se solicita.",
        ),
        estructura_texto=(
            "Hook/título breve visible en móvil.",
            "Dato principal o beneficio.",
            "CTA corto: link en bio, desliza, comenta, inscríbete, etc.",
            "Caption separado si se requiere texto largo.",
        ),
        entregables=("PNG/JPG 1080px", "Editable si se acuerda", "Caption sugerido opcional"),
        preguntas=(
            "¿Feed 4:5, cuadrado o historia 9:16?",
            "¿Se requiere caption?",
            "¿Hay guideline de Instagram/marca?",
        ),
    ),
}

DEFAULT_FORMAT_ORDER = ["flyer", "etiqueta", "pendon", "post_instagram"]
SIZE_PATTERN = r"\d+(?:[.,]\d+)?\s*(?:x|×)\s*\d+(?:[.,]\d+)?(?:\s*(?:cm|mm|m|in|px|pt))?"
RATIO_PATTERN = r"\d+(?:[.,]\d+)?\s*:\s*\d+(?:[.,]\d+)?"


def _norm(text: str) -> str:
    text = (text or "").lower()
    replacements = str.maketrans("áéíóúüñ", "aeiouun")
    return text.translate(replacements)


def detect_requested_formats(text: str) -> list[str]:
    """Detecta formatos mencionados preservando un orden comercial estable."""
    low = _norm(text)
    found: list[str] = []
    for fmt_id in DEFAULT_FORMAT_ORDER:
        spec = FORMAT_DEFINITIONS[fmt_id]
        aliases = {_norm(a) for a in spec.aliases}
        if any(re.search(rf"\b{re.escape(alias)}\b", low) for alias in aliases):
            found.append(fmt_id)
    return found


def is_multiformat_quote_request(text: str) -> bool:
    """True si parece paquete de brief/cotización para varios formatos."""
    low = _norm(text)
    formats = detect_requested_formats(text)
    has_quote = any(k in low for k in ("cotizacion", "presupuesto", "quote"))
    has_brief = any(k in low for k in ("brief", "estructura", "imagen", "texto"))
    return len(formats) >= 2 and (has_quote or has_brief)


def _extract_flexible_specs(text: str) -> list[dict[str, str]]:
    """Extrae tamaños y proporciones flexibles desde texto libre.

    Mantiene la flexibilidad del pedido: no fuerza un formato fijo, solo registra
    medidas/proporciones si el usuario las menciona.
    """
    specs: list[dict[str, str]] = []
    normalized = _norm(text)

    for fmt_id in DEFAULT_FORMAT_ORDER:
        spec = FORMAT_DEFINITIONS[fmt_id]
        aliases = {_norm(alias) for alias in spec.aliases}
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            size_match = re.search(
                rf"\b{re.escape(_norm(spec.nombre))}\b(?:\s+de)?\s*(?P<size>{SIZE_PATTERN})",
                normalized,
                re.IGNORECASE,
            )
            if size_match:
                specs.append({"label": fmt_id, "size": size_match.group("size"), "proportion": "", "source": spec.nombre})

    # Fallback simple para etiquetas no catalogadas o nombres cortos.
    for match in re.finditer(
        rf"(?P<label>[a-zA-Záéíóúñ]+(?:\s+[a-zA-Záéíóúñ]+)*)\s*(?P<size>{SIZE_PATTERN})",
        text,
        re.IGNORECASE,
    ):
        label = match.group("label").strip().lower()
        if not label or label in {"quiero", "necesito", "un", "una", "y", "con"}:
            continue
        size_value = match.group("size")
        if any(existing.get("size") == size_value and existing.get("label") == label for existing in specs):
            continue
        if label in {fmt_id for fmt_id in FORMAT_DEFINITIONS}:
            continue
        specs.append({"label": label, "size": size_value, "proportion": "", "source": label})

    ratio_match = re.search(rf"proporci(?:on|ón)\s*(?:de)?\s*(?P<ratio>{RATIO_PATTERN})", text, re.IGNORECASE)
    if ratio_match:
        ratio_value = ratio_match.group("ratio")
        if specs:
            specs[0]["proportion"] = ratio_value
        else:
            specs.append({"label": "pieza", "size": "", "proportion": ratio_value, "source": "proporción"})

    return specs


def _money(value: str | None) -> str:
    value = (value or "").strip()
    return value if value else "A definir"


def _bullet(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _format_section(spec: FormatDefinition) -> str:
    return f"""## {spec.nombre}

**Objetivo:** {spec.objetivo}

### Estructura de imagen
{_bullet(spec.estructura_imagen)}

### Estructura de texto
{_bullet(spec.estructura_texto)}

### Entregables sugeridos
{_bullet(spec.entregables)}

### Datos a confirmar
{_bullet(spec.preguntas)}
"""


def build_package_documents(
    source_text: str,
    *,
    titulo: str = "Brief estructura imagen/texto + cotización",
    cliente: str = "",
    moneda: str = "CLP",
    precios: Optional[Dict[str, str]] = None,
) -> dict[str, str]:
    """Construye los documentos markdown sin escribir a disco."""
    precios = precios or {}
    formats = detect_requested_formats(source_text) or DEFAULT_FORMAT_ORDER
    specs = [FORMAT_DEFINITIONS[f] for f in formats]
    now = datetime.now().isoformat(timespec="seconds")
    cliente_line = cliente or "A definir"

    # Python 3.11 no permite backslashes dentro de expresiones f-string
    # (PEP 701 llega en 3.12). Precalcular secciones mantiene compatibilidad Windows.
    formats_bullets = _bullet(spec.nombre for spec in specs)
    sections_md = "".join(_format_section(spec) + "\n" for spec in specs)
    source_clean = source_text.strip() or "A definir"
    flexible_specs = _extract_flexible_specs(source_text)
    flexible_lines = []
    for item in flexible_specs:
        if item.get("size") and item.get("proportion"):
            flexible_lines.append(f"- {item['label']}: {item['size']} | proporción {item['proportion']}")
        elif item.get("size"):
            flexible_lines.append(f"- {item['label']}: {item['size']}")
        elif item.get("proportion"):
            flexible_lines.append(f"- Proporción general: {item['proportion']}")
    if flexible_lines:
        flexible_block = "\n".join(flexible_lines)
    else:
        flexible_block = "- Medidas y proporciones por confirmar."

    brief = f"""# {titulo}

Generado: {now}
Cliente/productora: {cliente_line}
Moneda cotización: {moneda}

## Pedido original

> {source_clean}

## Objetivo del documento

Explicar de forma clara cómo se estructura la relación **imagen / texto** para cada formato solicitado y dejar una cotización base revisable antes de enviar a cliente/productora.

## Formatos incluidos

{formats_bullets}

## Principios comunes

- No inventar claims, fechas, precios ni datos legales: todo debe venir aprobado por cliente/productora.
- Mantener flexibilidad de formatos, tamaños y proporciones: si el pedido viene con medidas o proporciones, registrarlas sin forzar una única opción.
- Separar contenido visual (imagen, logos, patrones, fotos) de contenido textual (títulos, bajadas, CTA, datos obligatorios).
- Mantener jerarquía: mensaje principal → soporte → acción.
- Definir entregables antes de cerrar precio: editable, PDF impresión, PNG/JPG, cantidad de variantes y revisiones.
- Confirmar si la pieza es digital, impresión o mixta.

{sections_md}

## Medidas y proporciones flexibles

{flexible_block}

## Pendientes para cerrar

- Confirmar cliente/productora y marca base.
- Confirmar si se cotiza por pieza, por paquete o por cantidad de variantes.
- Confirmar número de rondas de ajustes incluidas.
- Confirmar si incluye impresión o solo archivos finales.
- Confirmar fechas de entrega y prioridad/urgencia.
"""

    rows = ["| Formato | Imagen | Texto | Entregables |", "|---|---|---|---|"]
    for spec in specs:
        rows.append(
            "| {name} | {img} | {txt} | {ent} |".format(
                name=spec.nombre,
                img="<br>".join(spec.estructura_imagen[:2]),
                txt="<br>".join(spec.estructura_texto[:3]),
                ent="<br>".join(spec.entregables[:3]),
            )
        )
    tabla = "# Tabla resumen imagen / texto\n\n" + "\n".join(rows) + "\n"

    quote_rows = ["| Ítem | Precio | Notas |", "|---|---:|---|"]
    for spec in specs:
        quote_rows.append(
            f"| {spec.nombre} | {_money(precios.get(spec.id))} | Precio depende de medida, variantes, editable e impresión. |"
        )
    quote_rows.append(f"| Paquete completo | {_money(precios.get('paquete'))} | Puede agrupar estrategia + diseño + export por formatos. |")
    cotizacion = f"""# Cotización base — {titulo}

Cliente/productora: {cliente_line}
Moneda: {moneda}

> **Importante:** los valores marcados como "A definir" no deben enviarse como precio final. Completar antes de enviar.

{chr(10).join(quote_rows)}

## Condiciones sugeridas

- Incluye hasta **2 rondas de ajustes** por formato, salvo acuerdo distinto.
- No incluye impresión física salvo que se indique explícitamente.
- Entrega editable incluida solo si se acuerda dentro del alcance.
- Textos, claims, fechas, logos y datos regulatorios deben venir aprobados por cliente/productora.
- Cambios de alcance (nuevas variantes, medidas extra, urgencia) se cotizan aparte.

## Próximo paso

Completar precios y datos pendientes; luego enviar al cliente/productora para aprobación.
"""

    preguntas = "# Preguntas para cerrar antes de enviar\n\n" + _bullet(
        [
            "¿Quién es el cliente/productora y cuál es la marca base?",
            "¿La cotización será por pieza, por paquete o por número de variantes?",
            "¿Se requiere editable (AI/SVG/PSD/Canva) o solo archivos finales?",
            "¿Incluye impresión física o solo diseño/export digital?",
            "¿Cuáles son las medidas exactas de flyer, etiqueta y pendón?",
            "¿Post de Instagram será feed 4:5, cuadrado o historia?",
            "¿Cuántas rondas de revisión se quieren incluir?",
            "¿Hay fecha límite o urgencia?",
            "¿Los textos y claims están aprobados?",
            "¿Hay fotos/logos/paleta obligatoria?",
        ]
    ) + "\n"

    manifest = json.dumps(
        {
            "tool": "flujo.comercial.multiformato",
            "generated_at": now,
            "titulo": titulo,
            "cliente": cliente,
            "moneda": moneda,
            "formats": [asdict(spec) for spec in specs],
            "flexible_specs": flexible_specs,
            "prices_provided": precios,
        },
        ensure_ascii=False,
        indent=2,
    )

    return {
        "brief_estructura_multiformato.md": brief,
        "tabla_formatos.md": tabla,
        "cotizacion_base.md": cotizacion,
        "preguntas_para_cerrar.md": preguntas,
        "manifest.json": manifest + "\n",
    }


def write_multiformat_package(
    output_dir: Path,
    source_text: str,
    *,
    titulo: str = "Brief estructura imagen/texto + cotización",
    cliente: str = "",
    moneda: str = "CLP",
    precios: Optional[Dict[str, str]] = None,
) -> dict[str, Path]:
    """Escribe el paquete comercial en output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    docs = build_package_documents(
        source_text,
        titulo=titulo,
        cliente=cliente,
        moneda=moneda,
        precios=precios,
    )
    written: dict[str, Path] = {}
    for name, content in docs.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        written[name] = path
    return written


def _read_source_from_path(path: Path) -> tuple[str, Path]:
    path = Path(path)
    if path.is_dir():
        for candidate in (path / "pedido_sanitizado.txt", path / "pedido_original.txt"):
            if candidate.exists():
                return candidate.read_text(encoding="utf-8", errors="ignore"), path
        raise FileNotFoundError(f"No hay pedido_original.txt ni pedido_sanitizado.txt en {path}")
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="ignore"), path.parent
    raise FileNotFoundError(f"No existe: {path}")


def generate_from_path(
    source: Path,
    *,
    output: Optional[Path] = None,
    titulo: str = "Brief estructura imagen/texto + cotización",
    cliente: str = "",
    moneda: str = "CLP",
    precios: Optional[Dict[str, str]] = None,
) -> dict[str, Path]:
    """Genera paquete desde un job dir o archivo de texto."""
    text, base = _read_source_from_path(Path(source))
    out = Path(output) if output else base / "salida_comercial"
    return write_multiformat_package(
        out,
        text,
        titulo=titulo,
        cliente=cliente,
        moneda=moneda,
        precios=precios,
    )
