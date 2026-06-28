#!/usr/bin/env python3
from pathlib import Path
import shutil, re, sys, json

def slug(s):
    s=s.lower(); s=re.sub(r'[^a-z0-9áéíóúñ]+','-',s)
    return re.sub(r'-+','-',s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')).strip('-')
if len(sys.argv)<3:
    print('Uso: py scripts/project_clone_variant.py projects/piezas_vectoriales/origen "nuevo nombre"')
    sys.exit(1)
src=Path(sys.argv[1]); name=sys.argv[2]; dst=Path('projects/piezas_vectoriales')/slug(name)
if not (src/'config.json').exists(): print('No existe config en origen'); sys.exit(1)
if dst.exists(): print('ERROR: ya existe', dst); sys.exit(1)
dst.mkdir(parents=True)
shutil.copy2(src/'config.json', dst/'config.json')
cfg=json.loads((dst/'config.json').read_text(encoding='utf-8'))
cfg.setdefault('project',{})['name']=name
cfg['project']['slug']=dst.name
cfg['project']['note']='Variante clonada desde '+src.as_posix()
(dst/'config.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Variante creada: {dst}')
