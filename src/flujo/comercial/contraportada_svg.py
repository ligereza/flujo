"""Generador SVG para contraportadas de suplementos RD.

Lee la plantilla base (01_contraportada_base_10x14cm.svg) y reemplaza
placeholders de texto con los datos del suplemento.

Uso:
    from flujo.comercial.contraportada_svg import generar_contraportada
    svg = generar_contraportada(suplemento_obj, output_path)
"""

from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from .suplementos_config import Suplemento


def _get_base_svg_path() -> Path:
    """Obtener ruta a la plantilla base SVG."""
    from ..paths import repo_root

    base = repo_root() / "svg" / "suplementos_rd" / "04_contraportadas" / "01_contraportada_base_10x14cm.svg"
    if not base.exists():
        raise FileNotFoundError(f"Plantilla base no encontrada: {base}")
    return base


def _replace_text_in_svg(root: ET.Element, old_text: str, new_text: str) -> int:
    """Reemplazar texto dentro de elementos <text> en un árbol SVG.

    Args:
        root: Elemento raíz del SVG
        old_text: Texto a buscar
        new_text: Texto de reemplazo

    Returns:
        Número de reemplazos realizados
    """
    count = 0
    ns = {"svg": "http://www.w3.org/2000/svg"}

    for text_elem in root.findall(".//svg:text", ns):
        if text_elem.text and old_text in text_elem.text:
            text_elem.text = text_elem.text.replace(old_text, new_text)
            count += 1

    return count


def generar_contraportada(
    suplemento: Suplemento,
    output_path: Optional[Path] = None,
) -> Path:
    """Generar SVG de contraportada para un suplemento.

    Reemplaza placeholders en la plantilla base con datos del suplemento:
    - NOMBRE DEL SUPLEMENTO → Suplemento.nombre
    - DESCRIPCIÓN → Suplemento.descripcion
    - Texto de beneficios y info nutricional

    Args:
        suplemento: Objeto Suplemento con datos
        output_path: Ruta de salida (default: svg/suplementos_rd/04_contraportadas/[nombre]_final.svg)

    Returns:
        Path del archivo generado

    Raises:
        FileNotFoundError: Si no existe la plantilla base
        ET.ParseError: Si la plantilla SVG está corrupta
    """
    base_path = _get_base_svg_path()

    # Parsear SVG base
    tree = ET.parse(str(base_path))
    root = tree.getroot()

    # Reemplazar placeholders
    _replace_text_in_svg(root, "NOMBRE DEL SUPLEMENTO", suplemento.nombre)
    _replace_text_in_svg(root, "DESCRIPCIÓN", suplemento.descripcion)

    # Reemplazar beneficios (líneas 1-2)
    _replace_text_in_svg(root, "Beneficio principal o idea de campaña para la pieza.", suplemento.beneficio_1)
    if suplemento.beneficio_2:
        _replace_text_in_svg(root, "Texto breve y claro para acompañar el producto.", suplemento.beneficio_2)

    # Reemplazar info nutricional
    info_text = "\n".join(suplemento.info_nutricional[:3])
    _replace_text_in_svg(root, "• Ingredientes o perfil principal del suplemento.", suplemento.info_nutricional[0] if suplemento.info_nutricional else "")
    if len(suplemento.info_nutricional) > 1:
        _replace_text_in_svg(root, "• Indicaciones de uso y contexto de consumo.", suplemento.info_nutricional[1])
    if len(suplemento.info_nutricional) > 2:
        _replace_text_in_svg(root, "• Recomendación de seguimiento y responsabilidad.", suplemento.info_nutricional[2])

    # Reemplazar contactos
    _replace_text_in_svg(root, "texto o QR", suplemento.qr_text[:20] if suplemento.qr_text else "")
    _replace_text_in_svg(root, "espacio editable", suplemento.contacto_label)

    # Determinar ruta de salida
    if output_path is None:
        from ..paths import repo_root

        output_dir = repo_root() / "svg" / "suplementos_rd" / "04_contraportadas" / "generadas"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{suplemento.nombre.lower().replace(' ', '_')}_final.svg"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Escribir SVG generado
    tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
    )

    return output_path
