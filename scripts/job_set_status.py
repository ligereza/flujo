#!/usr/bin/env python3
"""Cambia estado en jobs/.../brief.yaml."""
from pathlib import Path
import re, sys
VALID={'borrador','brief_extraido_pendiente_revision','pendiente_datos','listo_para_disenar','en_diseno','generado','entregado','pausado','cancelado'}
if len(sys.argv)<3:
    print('Uso: py scripts/job_set_status.py jobs/NOMBRE nuevo_estado')
    sys.exit(1)
job=Path(sys.argv[1]); st=sys.argv[2]
if st not in VALID:
    print('Estado no recomendado:', st)
    print('Válidos:', ', '.join(sorted(VALID)))
    sys.exit(1)
brief=job/'brief.yaml'
if not brief.exists():
    print('No existe', brief); sys.exit(1)
t=brief.read_text(encoding='utf-8')
if re.search(r'^estado:', t, re.M):
    t=re.sub(r'^estado:.*$', f'estado: {st}', t, count=1, flags=re.M)
else:
    t='estado: '+st+'\n'+t
brief.write_text(t, encoding='utf-8')
print(f'Estado actualizado: {brief} -> {st}')
