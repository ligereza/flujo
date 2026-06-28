#!/usr/bin/env python3
"""Limpia archivos generados que no deberían quedar versionados."""
from pathlib import Path
import shutil

PATTERNS = [
    '**/__pycache__',
    '**/*.pyc',
]
DIRS = [
    'projects/piezas_vectoriales/*/salida_generada',
    'projects/piezas_vectoriales/*/02_editables_svg',
    'projects/piezas_vectoriales/*/03_final_vectorizado_svg',
    'projects/piezas_vectoriales/*/04_preview',
    'projects/piezas_vectoriales/*/05_exports',
]

removed=[]
for pat in PATTERNS:
    for p in Path('.').glob(pat):
        if '.git' in p.parts:
            continue
        if p.is_dir():
            shutil.rmtree(p)
            removed.append(str(p))
        elif p.is_file():
            p.unlink()
            removed.append(str(p))

for pat in DIRS:
    for p in Path('.').glob(pat):
        if p.exists() and p.is_dir():
            shutil.rmtree(p)
            removed.append(str(p))

print(f'Elementos limpiados: {len(removed)}')
for r in removed[:80]:
    print('-', r)
if len(removed)>80:
    print(f'... y {len(removed)-80} más')
