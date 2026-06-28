#!/usr/bin/env python3
from pathlib import Path
import json
base=Path('tools/piezas_vectoriales/presets/rider')
print('Presets rider:')
for p in sorted(base.glob('*.json')):
    d=json.loads(p.read_text(encoding='utf-8'))
    print(f"- {d.get('id')}: {d.get('nombre')} | {d.get('ancho_m')}×{d.get('alto_m')} m | incluye: {', '.join(d.get('incluye', []))}")
