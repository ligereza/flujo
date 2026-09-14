"""Helpers para generar prompts estructurados de ayuda remota con IA web."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

DEFAULT_REPO = "ligereza/vibecodeine"


def build_remote_ai_prompt(text: str, *, area: str = "suplementos", repo: str = DEFAULT_REPO) -> str:
    """Construye un prompt breve, estructurado y útil para IA web.

    El objetivo es convertir un pedido o correo en información procesable para
    flujo, sin inventar datos ni perder contexto del repo.
    """
    cleaned_text = (text or "").strip() or "[PEGAR PEDIDO O CORREO AQUI]"
    area_key = (area or "general").strip().lower()

    if area_key == "eventos":
        extraction_rule = (
            "Para eventos, extrae tipo de pieza, formato, fecha, lugar, alcance, "
            "referencias visuales y datos de contacto."
        )
    elif area_key == "general":
        extraction_rule = "Extrae los datos clave del mensaje y clasifica el pedido de forma útil."
    else:
        extraction_rule = (
            "Para suplementos, extrae producto, formato, medidas, cantidad, fecha, "
            "cliente y observaciones."
        )

    return f"""Hola, necesito ayuda con este repo.

Repo: {repo}
Objetivo: convertir un pedido en una cotización o brief útil para flujo.
Contexto: este repo gestiona pedidos -> jobs -> briefs -> diseño -> entrega.

Quiero que trabajes así:
- Responde en español.
- Clasifica el mensaje como nuevo pedido, modificación, corrección o cotización.
- {extraction_rule}
- Si falta información, indícala explícitamente como \"pendiente\".
- No inventes datos.
- Devuelve una salida breve y lista para copiar en un issue, brief o JSON.

Texto a procesar:
{cleaned_text}

Salida esperada:
1. Clasificación
2. Resumen corto del pedido
3. Datos extraídos
4. Datos faltantes
5. Texto listo para enviar como cotización o pedido
"""


def write_remote_ai_prompt(path: Optional[Path], prompt: str) -> Optional[Path]:
    """Escribe el prompt a un archivo si se indica una ruta."""
    if not path:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
