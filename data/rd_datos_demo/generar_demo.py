"""Generador de datos de demo 100% FICTICIOS para `flujo rd-datos ingest`.

Uso: `py data/rd_datos_demo/generar_demo.py` (reescribe los 3 CSV de esta
carpeta). Seed fija (2026) -> salida deterministica, reproducible.

CERO datos reales: nombres de eventos, sustancias, reactivos y respuestas
son sinteticos. Vocabulario de reactivo/familia coherente con
`projects/cultura/identidad/reactivos.json` (colorimetria presuntiva real
del dominio), pero las FILAS (quien, cuando exacto, que dijo) son inventadas.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)

_DIR = Path(__file__).resolve().parent

# 2026-Q2 (abr-jun) + 2026-Q3 (jul-sep)
_FECHA_INICIO = date(2026, 4, 1)
_FECHA_FIN = date(2026, 9, 30)
_RANGO_DIAS = (_FECHA_FIN - _FECHA_INICIO).days


def _fecha_random() -> str:
    return (_FECHA_INICIO + timedelta(days=random.randint(0, _RANGO_DIAS))).isoformat()


EVENTOS = [
    "Festival Rio Verde", "Under Bosque", "Fiesta Solsticio", "After Mecanica",
    "Club Nortico", "Rave Cordillera", "Open Air Dunas", "Warehouse 12",
]

# (sustancia_declarada, reactivo, familia_detectada, resultado_color, coincide)
_PERFILES_TESTEO = [
    ("MDMA", "Marquis", "MDMA", "negro-violeta", 1),
    ("MDMA", "Mecke", "MDMA", "azul-verde oscuro", 1),
    ("cristal (supuesta cocaina)", "Simon", "cocaina", "sin reaccion (blanco)", 0),
    ("2C-B", "Mandelin", "2C-x", "verde oliva", 1),
    ("LSD (secante)", "Ehrlich", "LSD / indoles", "violeta", 1),
    ("ketamina", "Froehde", "ketamina", "amarillo palido", 1),
    ("anfetamina (speed)", "Liebermann", "anfetamina", "naranja-rojizo", 1),
    ("MDA", "Marquis", "MDMA / MDA", "negro-azulado", 1),
    ("desconocida (pastilla sin marca)", "Marquis", "sin reaccion (blanco)", "sin cambio", 0),
    ("cocaina", "Simon", "cocaina cortada (levamisol / lidocaina)", "azul palido", 0),
]

_ADULTERANTES = [None, None, None, "levamisol", "cafeina", "lidocaina", "manitol"]

_TIPOS_ATENCION = ["hidratacion", "escucha", "derivacion", "informacion"]
_DERIVADO_A = [None, None, "salud mental", "urgencias medicas", "punto de hidratacion"]
_RANGOS_ETARIOS = ["18-24", "25-34", "35-44", "45+"]

_PREGUNTAS = [
    ("Q1_conocias_el_stand", ["si", "no", "me entere por un amigo"]),
    ("Q2_usarias_de_nuevo_el_servicio", ["si", "no", "tal vez"]),
    ("Q3_como_calificas_la_atencion", ["excelente", "buena", "regular"]),
    ("Q4_te_sentiste_juzgado", ["no", "un poco", "para nada"]),
    ("Q5_recomendarias_el_stand", ["si", "si, totalmente", "no se"]),
]


def generar_testeos(n: int = 30) -> None:
    path = _DIR / "testeos_demo.csv"
    campos = [
        "fecha", "evento", "sustancia_declarada", "reactivo", "resultado_color",
        "familia_detectada", "coincide", "adulterante_sospechado", "descartada", "notas",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for _ in range(n):
            sust, react, fam, color, coincide = random.choice(_PERFILES_TESTEO)
            w.writerow({
                "fecha": _fecha_random(),
                "evento": random.choice(EVENTOS),
                "sustancia_declarada": sust,
                "reactivo": react,
                "resultado_color": color,
                "familia_detectada": fam,
                "coincide": coincide,
                "adulterante_sospechado": random.choice(_ADULTERANTES) or "",
                "descartada": 0,
                "notas": random.choice([
                    "", "persona reporta primera vez con esta sustancia",
                    "reactivo aplicado en punto fijo", "muestra pequena, resultado tentativo",
                ]),
            })


def generar_atenciones(n: int = 15) -> None:
    path = _DIR / "atenciones_demo.csv"
    campos = ["fecha", "evento", "tipo", "derivado_a", "rango_etario", "notas"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for _ in range(n):
            w.writerow({
                "fecha": _fecha_random(),
                "evento": random.choice(EVENTOS),
                "tipo": random.choice(_TIPOS_ATENCION),
                "derivado_a": random.choice(_DERIVADO_A) or "",
                "rango_etario": random.choice(_RANGOS_ETARIOS),
                "notas": random.choice([
                    "", "acompanamiento breve en punto fijo",
                    "entrega de agua y sales", "conversacion de contencion, sin derivacion",
                ]),
            })


def generar_encuestas(n: int = 15) -> None:
    path = _DIR / "encuestas_demo.csv"
    campos = ["fecha", "evento", "pregunta_id", "respuesta"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for _ in range(n):
            pid, respuestas = random.choice(_PREGUNTAS)
            w.writerow({
                "fecha": _fecha_random(),
                "evento": random.choice(EVENTOS),
                "pregunta_id": pid,
                "respuesta": random.choice(respuestas),
            })


if __name__ == "__main__":
    generar_testeos()
    generar_atenciones()
    generar_encuestas()
    print("OK: testeos_demo.csv, atenciones_demo.csv, encuestas_demo.csv regenerados (seed=2026)")
