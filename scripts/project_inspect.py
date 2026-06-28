#!/usr/bin/env python3
from pathlib import Path
import json, sys
if len(sys.argv)<2:
    print('Uso: py scripts/project_inspect.py projects/piezas_vectoriales/NOMBRE')
    sys.exit(1)
p=Path(sys.argv[1]); cfgp=p/'config.json'
if not cfgp.exists(): print('No existe config.json'); sys.exit(1)
cfg=json.loads(cfgp.read_text(encoding='utf-8'))
print('# Project inspect')
print('Nombre:', cfg.get('project',{}).get('name'))
print('Slug:', cfg.get('project',{}).get('slug'))
c=cfg.get('canvas',{}); print('Canvas:', c.get('width'), 'x', c.get('height'), 'px')
print('Real cm:', c.get('real_size_cm'))
print('Docs:', len(cfg.get('documents',[])))
for d in cfg.get('documents',[]):
    print('-', d.get('id'), '|', d.get('title'), '| elements:', len(d.get('elements',[])))
