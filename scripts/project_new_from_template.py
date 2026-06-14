#!/usr/bin/env python3
"""Crea proyecto piezas_vectoriales directo desde una plantilla."""
from pathlib import Path
import json, re, shutil, sys

def slugify(s):
    s=s.lower(); s=re.sub(r'[^a-z0-9áéíóúñ]+','-',s)
    return re.sub(r'-+','-',s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')).strip('-') or 'proyecto'
if len(sys.argv)<3:
    print('Uso: py scripts/project_new_from_template.py "nombre proyecto" plantilla.json')
    sys.exit(1)
name=sys.argv[1]; template=Path(sys.argv[2])
if not template.exists(): template=Path('tools/piezas_vectoriales/plantillas')/sys.argv[2]
if not template.exists(): print('No existe plantilla:', template); sys.exit(1)
slug=slugify(name); out=Path('projects/piezas_vectoriales')/slug
if out.exists(): print('ERROR: ya existe', out); sys.exit(1)
out.mkdir(parents=True)
cfg=json.loads(template.read_text(encoding='utf-8'))
cfg.setdefault('project',{})['name']=name
cfg['project']['slug']=slug
cfg['project']['note']='Proyecto creado directo desde plantilla.'
(out/'config.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Proyecto creado: {out}')
print(f'Generar: py scripts/project_render.py "{out}/config.json"')
