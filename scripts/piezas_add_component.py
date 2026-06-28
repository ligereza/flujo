#!/usr/bin/env python3
"""Inserta un componente JSON en un config.json de piezas_vectoriales."""
from pathlib import Path
import json, sys

if len(sys.argv) < 3:
    print('Uso: py scripts/piezas_add_component.py config.json componente.json [global|doc] [doc_index]')
    sys.exit(1)
config = Path(sys.argv[1])
component = Path(sys.argv[2])
target = sys.argv[3] if len(sys.argv) >= 4 else 'doc'
doc_index = int(sys.argv[4]) if len(sys.argv) >= 5 else 0

if not config.exists():
    print('No existe config:', config); sys.exit(1)
if not component.exists():
    alt = Path('tools/piezas_vectoriales/components') / component
    component = alt
if not component.exists():
    print('No existe componente:', component); sys.exit(1)

cfg = json.loads(config.read_text(encoding='utf-8'))
comp = json.loads(component.read_text(encoding='utf-8'))
if not isinstance(comp, list):
    print('El componente debe ser un array JSON')
    sys.exit(1)

if target == 'global':
    cfg.setdefault('global_elements', [])
    cfg['global_elements'].extend(comp)
elif target == 'doc':
    docs = cfg.setdefault('documents', [])
    if not docs:
        docs.append({'id': '01_base', 'title': 'Base', 'elements': []})
    while len(docs) <= doc_index:
        docs.append({'id': f'{len(docs)+1:02d}_base', 'title': 'Base', 'elements': []})
    docs[doc_index].setdefault('elements', [])
    docs[doc_index]['elements'].extend(comp)
else:
    print('target debe ser global o doc')
    sys.exit(1)

config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Componente agregado: {component} -> {config} ({target})')
