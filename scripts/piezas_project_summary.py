#!/usr/bin/env python3
"""Resumen de proyectos piezas_vectoriales."""
from pathlib import Path
import json
base=Path('projects/piezas_vectoriales')
rows=[]
for cfgp in sorted(base.glob('*/config.json')):
    try: cfg=json.loads(cfgp.read_text(encoding='utf-8'))
    except Exception: continue
    c=cfg.get('canvas',{}); rs=c.get('real_size_cm',{})
    out=cfgp.parent/'salida_generada'
    zips=list((out/'04_exports').glob('*.zip')) if (out/'04_exports').exists() else []
    rows.append((cfgp.parent.name, cfg.get('project',{}).get('name',''), c.get('width'), c.get('height'), rs.get('width'), rs.get('height'), len(cfg.get('documents',[])), len(zips)))
print(f'Proyectos piezas_vectoriales: {len(rows)}')
for r in rows:
    print(f'- {r[0]} | {r[1]} | {r[2]}x{r[3]} px | {r[4]}x{r[5]} cm | docs:{r[6]} | zips:{r[7]}')
