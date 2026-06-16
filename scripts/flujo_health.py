#!/usr/bin/env python3
"""Chequeo general rápido del repo flujo."""
from pathlib import Path
import json, subprocess, sys

errors=[]
warnings=[]

def check_jsons():
    for p in Path('.').glob('**/*.json'):
        if any(part in p.parts for part in ['.git','salida_generada','02_editables_svg','03_final_vectorizado_svg','04_preview','05_exports']):
            continue
        try:
            json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            errors.append(f'JSON inválido {p}: {e}')

def check_pycache():
    for p in Path('.').glob('**/__pycache__'):
        if '.git' not in p.parts:
            warnings.append(f'Cache Python presente: {p}')
    for p in Path('.').glob('**/*.pyc'):
        if '.git' not in p.parts:
            warnings.append(f'PYC presente: {p}')

def run_optional(cmd):
    try:
        r=subprocess.run(cmd, text=True, capture_output=True, timeout=60)
        if r.returncode != 0:
            errors.append(f'Falla comando {cmd}: {r.stderr or r.stdout}')
        else:
            print(r.stdout.strip())
    except Exception as e:
        errors.append(f'No se pudo ejecutar {cmd}: {e}')

print('# Flujo health check')
check_jsons()
check_pycache()
if Path('scripts/piezas_validate_config.py').exists():
    run_optional([sys.executable, 'scripts/piezas_validate_config.py'])

if warnings:
    print('\nAVISOS:')
    for w in warnings:
        print('-', w)

if errors:
    print('\nERRORES:')
    for e in errors:
        print('-', e)
    sys.exit(1)
print('\nOK: health check sin problemas críticos')
