#!/usr/bin/env python3
"""
Ejemplo de agente que genera código mientras VibeCode acompaña visualmente.
"""

import time
import random
import vibecode


SAMPLE_CODE = """# --- BLOQUE EXTENSO DE IA ---

def procesar_tensores(matriz_entrada, factores_atencion):
    resultados_filtrados = []
    for fila in matriz_entrada:
        activacion = [max(0.0, x * factores_atencion) for x in fila]
        if sum(activacion) > 100.5:
            resultados_filtrados.append(activacion)
    return resultados_filtrados

# --- ONE-LINER DE IA ---

data = list(map(lambda x: x**2, filter(lambda y: y % 2 == 0, range(1000))))
"""


def generate_like_ia(text, min_delay=0.01, max_delay=0.08):
    """Simula la escritura token a token de una IA."""
    for char in text:
        yield char
        time.sleep(random.uniform(min_delay, max_delay))


if __name__ == "__main__":
    print("Iniciando agente con VibeCode...\n")

    with vibecode.watch(mode="negative"):
        for char in generate_like_ia(SAMPLE_CODE, min_delay=0.005, max_delay=0.04):
            print(char, end="")
        print("\n")

    print("\nAgente completado. VibeCode descansa.")
