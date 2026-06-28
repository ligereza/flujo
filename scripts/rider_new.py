#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys
if len(sys.argv)<2:
    print('Uso: py scripts/rider_new.py "nombre rider" [brand]')
    sys.exit(1)
name=sys.argv[1]; brand=sys.argv[2] if len(sys.argv)>2 else 'Marca'
subprocess.run([sys.executable,'scripts/project_new_from_template.py',name,'rider_eventos_a4_horizontal.config.json'],check=True)
# ajustar brand
import json, re
slug=re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',name.lower())).strip('-')
p=Path('projects/piezas_vectoriales')/slug/'config.json'
cfg=json.loads(p.read_text(encoding='utf-8'))
cfg.setdefault('project',{})['brand']=brand
p.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Rider creado: {p.parent}')
