#!/usr/bin/env python3
"""Wrapper para generar proyectos de piezas vectoriales desde config.json."""
from pathlib import Path
import subprocess
import sys

if len(sys.argv) < 2:
    print('Uso: py scripts/piezas_generar.py projects/piezas_vectoriales/mi_proyecto/config.json')
    sys.exit(1)

config = Path(sys.argv[1])
script = Path('tools/piezas_vectoriales/scripts/generar_desde_json.py')
if not config.exists():
    print(f'No existe config: {config}')
    sys.exit(1)
if not script.exists():
    print(f'No existe script: {script}')
    sys.exit(1)
subprocess.run([sys.executable, str(script), str(config)], check=True)
