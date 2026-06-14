#!/usr/bin/env python3
from pathlib import Path
import json
base=Path('tools/piezas_vectoriales/components')
print('Componentes disponibles:')
for p in sorted(base.glob('*.json')):
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
        print(f'- {p.name}: {len(data) if isinstance(data,list) else "?"} elementos')
    except Exception as e:
        print(f'- {p.name}: ERROR {e}')
