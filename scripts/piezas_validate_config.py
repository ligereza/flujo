#!/usr/bin/env python3
"""Validación liviana de config.json de piezas_vectoriales."""
from pathlib import Path
import json, sys

def validate(p):
    errors=[]
    try:
        cfg=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        return [f'JSON inválido: {e}']
    for key in ['project','canvas','palette','documents']:
        if key not in cfg: errors.append(f'falta {key}')
    c=cfg.get('canvas',{})
    for key in ['width','height']:
        if not isinstance(c.get(key), (int,float)) or c.get(key)<=0: errors.append(f'canvas.{key} inválido')
    docs=cfg.get('documents',[])
    if not isinstance(docs,list) or not docs: errors.append('documents vacío')
    for i,d in enumerate(docs):
        if 'id' not in d: errors.append(f'doc {i} sin id')
        if 'elements' not in d: errors.append(f'doc {i} sin elements')
    return errors

paths=[Path(x) for x in sys.argv[1:]] or list(Path('projects/piezas_vectoriales').glob('*/config.json'))
failed=False
for p in paths:
    errs=validate(p)
    if errs:
        failed=True; print(f'ERROR {p}:'); [print(' -',e) for e in errs]
    else:
        print('OK', p)
sys.exit(1 if failed else 0)
