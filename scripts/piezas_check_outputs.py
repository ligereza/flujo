#!/usr/bin/env python3
"""Chequeo rápido de proyectos de piezas vectoriales."""
from pathlib import Path
import json
import sys

root = Path.cwd()
errors = []
jsons = list(root.glob('projects/piezas_vectoriales/*/config.json'))
jsons += list(root.glob('projects/piezas_vectoriales/*/01_contenido/*.json'))

for p in jsons:
    try:
        json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'JSON inválido: {p} -> {e}')

vector_dirs = list(root.glob('projects/piezas_vectoriales/*/salida_generada/02_vectorizados_svg'))
vector_dirs += list(root.glob('projects/piezas_vectoriales/*/03_final_vectorizado_svg'))
for d in vector_dirs:
    for svg in d.glob('*.svg'):
        txt = svg.read_text(encoding='utf-8', errors='ignore')
        if '<text' in txt:
            errors.append(f'Vectorizado contiene <text>: {svg}')

zips = list(root.glob('projects/piezas_vectoriales/*/salida_generada/04_exports/*.zip'))
zips += list(root.glob('projects/piezas_vectoriales/*/05_exports/*.zip'))

print('Chequeo piezas vectoriales')
print('JSONs revisados:', len(jsons))
print('Directorios vectorizados revisados:', len(vector_dirs))
print('ZIPs encontrados:', len(zips))
for z in zips:
    print('-', z)

if errors:
    print('\nERRORES:')
    for e in errors:
        print('-', e)
    sys.exit(1)
print('\nOK: sin errores críticos detectados')
