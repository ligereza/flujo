#!/usr/bin/env python3
"""Crea un job desde un archivo de texto/correo."""
from pathlib import Path
from datetime import date
import re, shutil, sys

from _common import repo_root


def slugify(s):
    s=s.lower()
    s=re.sub(r'[^a-z0-9áéíóúñ]+','-',s)
    s=s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
    return re.sub(r'-+','-',s).strip('-') or 'pedido'

ROOT = repo_root()

if len(sys.argv)<3:
    print('Uso: py scripts/job_from_text.py "nombre pedido" ruta/correo.txt')
    sys.exit(1)
name=sys.argv[1]
src=Path(sys.argv[2])
if not src.exists():
    print('No existe archivo:', src); sys.exit(1)
job=ROOT / 'jobs' / f'{date.today().isoformat()}_{slugify(name)}'
if job.exists():
    print('ERROR: ya existe', job); sys.exit(1)
shutil.copytree(ROOT / 'jobs/_template', job)
(job/'pedido_original.txt').write_text(src.read_text(encoding='utf-8', errors='ignore'), encoding='utf-8')
brief=job/'brief.yaml'
s=brief.read_text(encoding='utf-8').replace('YYYY-MM-DD_nombre_pedido', job.name)
brief.write_text(s, encoding='utf-8')
print(f'Job creado: {job}')
print(f'Siguiente: py scripts/job_prepare.py "{job}"')
