"""Configuración de suplementos RD para CLI y generación de contraportadas.

Define los 7 suplementos principales con sus beneficios, perfiles nutricionales
y colores de acento. Usado por:
- CLI: `py -m flujo suplementos contraportada`
- Generador SVG
- Hub (futuro: integración datadrop)
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Suplemento:
    """Definición de un suplemento RD."""

    nombre: str  # Ej: "Impulso"
    descripcion: str  # Ej: "Energía sostenible"
    beneficio_1: str  # Línea 1 de beneficio
    beneficio_2: str  # Línea 2 de beneficio (opcional)
    info_nutricional: list[str]  # Bullets de info nutricional (máx 3-4)
    whatsapp_label: str  # Ej: "Consulta disponibilidad"
    contacto_label: str  # Ej: "+1 (XXX) XXX-XXXX"
    qr_text: str  # QR texto o URL para generar QR
    color_acento: str  # HEX color secundario (opcional, default: #F5C54D)
    tags: list[str]  # Categorías: "energía", "recuperación", "performance", etc.


SUPLEMENTOS: Dict[str, Suplemento] = {
    "Impulso": Suplemento(
        nombre="Impulso",
        descripcion="Energía sostenible y enfoque mental",
        beneficio_1="Potencia tu rendimiento físico",
        beneficio_2="Concentración mental sin colapso",
        info_nutricional=[
            "• Cafeína natural + L-Teanina (enfoque sin ansiedad)",
            "• Vitaminas B para metabolismo óptimo",
            "• Tomar 1 scoop con agua 30 min antes del entrenamiento",
        ],
        whatsapp_label="Consulta sabores",
        contacto_label="+1 (809) 555-0100",
        qr_text="https://wa.me/+18095550100",
        color_acento="#F5C54D",
        tags=["energía", "performance", "pre-entrenamiento"],
    ),
    "Creatina": Suplemento(
        nombre="Creatina",
        descripcion="Fuerza y resistencia muscular",
        beneficio_1="Recuperación acelerada post-entreno",
        beneficio_2="Ganancia de masa muscular",
        info_nutricional=[
            "• Monohidrato 5g por servicio (máxima eficacia)",
            "• Mejora rendimiento en ejercicios de alta intensidad",
            "• Mezclar con agua, tomar todos los días",
        ],
        whatsapp_label="Dudas sobre ciclos",
        contacto_label="+1 (809) 555-0101",
        qr_text="https://wa.me/+18095550101",
        color_acento="#E74C3C",
        tags=["fuerza", "recuperación", "masa"],
    ),
    "Pre Fiesta": Suplemento(
        nombre="Pre Fiesta",
        descripcion="Energía prolongada para la noche",
        beneficio_1="Energía que dura 8+ horas",
        beneficio_2="Sin crash: caída gradual y controlada",
        info_nutricional=[
            "• Fórmula balanceada: cafeína + aminoácidos + vitaminas",
            "• Sin azúcar refinada (sweetener natural)",
            "• Tomar 1-2 scoops según tolerancia, 20 min antes",
        ],
        whatsapp_label="Pedir sabor",
        contacto_label="+1 (809) 555-0102",
        qr_text="https://wa.me/+18095550102",
        color_acento="#9B59B6",
        tags=["energía", "social", "noche"],
    ),
    "Recovery": Suplemento(
        nombre="Recovery",
        descripcion="Recuperación muscular post-entreno",
        beneficio_1="Reduce dolor muscular (DOMS)",
        beneficio_2="Repara fibras y regenera",
        info_nutricional=[
            "• Whey protein aislada 25g proteína por scoop",
            "• Aminoácidos esenciales (EAA) balanceados",
            "• Dentro de 30 min post-entreno, con agua o leche",
        ],
        whatsapp_label="Sabores disponibles",
        contacto_label="+1 (809) 555-0103",
        qr_text="https://wa.me/+18095550103",
        color_acento="#27AE60",
        tags=["recuperación", "proteína", "post-entreno"],
    ),
    "Colágeno Fit": Suplemento(
        nombre="Colágeno Fit",
        descripcion="Salud articular y piel firme",
        beneficio_1="Fortalece articulaciones y ligamentos",
        beneficio_2="Piel, cabello y uñas radiantes",
        info_nutricional=[
            "• Colágeno hidrolizado 10g: absorción máxima",
            "• Vitamina C + ácido hialurónico",
            "• Disolver en agua tibia, 1-2 veces por día",
        ],
        whatsapp_label="Consulta presentaciones",
        contacto_label="+1 (809) 555-0104",
        qr_text="https://wa.me/+18095550104",
        color_acento="#E8DAEF",
        tags=["salud", "belleza", "articulaciones"],
    ),
    "Omega+ Immune": Suplemento(
        nombre="Omega+ Immune",
        descripcion="Inmunidad y salud cardiovascular",
        beneficio_1="Defensa natural reforzada",
        beneficio_2="Corazón y sistema nervioso protegido",
        info_nutricional=[
            "• Omega-3 3g (EPA + DHA): salud cardiovascular",
            "• Vitamina D3 + Zinc: inmunidad óptima",
            "• 2 cápsulas con comida (desayuno o almuerzo)",
        ],
        whatsapp_label="Preguntas sobre vegano",
        contacto_label="+1 (809) 555-0105",
        qr_text="https://wa.me/+18095550105",
        color_acento="#3498DB",
        tags=["salud", "inmunidad", "corazón"],
    ),
    "Sleep Relax": Suplemento(
        nombre="Sleep Relax",
        descripcion="Sueño profundo y reparador",
        beneficio_1="Duerme más profundo, descansa mejor",
        beneficio_2="Despertar sin grogginess",
        info_nutricional=[
            "• Magnesio glicinatо 400mg: relajación natural",
            "• L-Teanina + Melatonina: ciclo sueño-vigilia",
            "• 1 dosis 30-60 min antes de dormir",
        ],
        whatsapp_label="Disponible ahora",
        contacto_label="+1 (809) 555-0106",
        qr_text="https://wa.me/+18095550106",
        color_acento="#34495E",
        tags=["sueño", "relax", "recuperación"],
    ),
}


def get_suplemento(nombre: str) -> Suplemento:
    """Obtener configuración de suplemento por nombre.

    Args:
        nombre: Nombre del suplemento (case-insensitive).

    Returns:
        Suplemento configurado.

    Raises:
        KeyError: Si no existe el suplemento.
    """
    for key, supl in SUPLEMENTOS.items():
        if key.lower() == nombre.lower():
            return supl
    raise KeyError(f"Suplemento '{nombre}' no encontrado. Disponibles: {list(SUPLEMENTOS.keys())}")


def list_suplementos() -> list[str]:
    """Listar nombres de suplementos disponibles."""
    return list(SUPLEMENTOS.keys())


if __name__ == "__main__":
    # Debug: mostrar config
    import json

    print("Suplementos disponibles:")
    for nombre in list_suplementos():
        print(f"  - {nombre}")

    print("\nEjemplo (Impulso):")
    s = get_suplemento("Impulso")
    print(f"  Nombre: {s.nombre}")
    print(f"  Descripción: {s.descripcion}")
    print(f"  Beneficio 1: {s.beneficio_1}")
    print(f"  Info: {s.info_nutricional}")
