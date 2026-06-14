#!/usr/bin/env python3
"""Genera un proyecto piezas_vectoriales y crea reporte de render."""
from pathlib import Path
import subprocess, sys

if len(sys.argv) < 2:
    print('Uso: py scripts/project_render.py projects/piezas_vectoriales/NOMBRE/config.json')
    sys.exit(1)
config = Path(sys.argv[1])
if not config.exists():
    print('No existe', config); sys.exit(1)
project = config.parent
subprocess.run([sys.executable, 'scripts/piezas_validate_config.py', str(config)], check=True)
subprocess.run([sys.executable, 'scripts/piezas_generar.py', str(config)], check=True)
# Reporte local del proyecto
out = project / 'render_report.md'
exports = project / 'salida_generada' / '04_exports'
preview = project / 'salida_generada' / '03_preview' / 'preview.html'
zips = sorted(exports.glob('*.zip')) if exports.exists() else []
out.write_text('# Render report\n\n' +
               f'- Proyecto: `{project}`\n' +
               f'- Config: `{config}`\n' +
               f'- Preview: `{preview}`\n' +
               '\n## ZIPs\n\n' +
               ''.join(f'- `{z}`\n' for z in zips), encoding='utf-8')
print(f'Render OK: {project}')
print(f'Reporte: {out}')
