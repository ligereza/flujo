#!/usr/bin/env python3
"""Sugiere próximas acciones según estados de jobs."""
from pathlib import Path
import re

def get(t,k):
    m=re.search(rf'^{re.escape(k)}:\s*(.*)$', t, re.M)
    return m.group(1).strip().strip('"') if m else ''

def action(st, path):
    if st in ('borrador',''):
        return f'pegar pedido y ejecutar: py scripts/job_prepare.py "{path}"'
    if st=='brief_extraido_pendiente_revision':
        return 'revisar brief.yaml y definir estado'
    if st=='pendiente_datos':
        return 'resolver pendientes / revisar privacidad'
    if st=='listo_para_disenar':
        return f'crear proyecto: py scripts/brief_to_project.py "{path}/brief.yaml"'
    if st=='en_diseno':
        return 'ajustar config.json, generar y validar'
    if st=='generado':
        return 'revisar outputs y entregar'
    return 'sin acción automática'

for brief in sorted(Path('jobs').glob('*/brief.yaml')):
    if brief.parent.name.startswith('_'): continue
    t=brief.read_text(encoding='utf-8', errors='ignore')
    st=get(t,'estado')
    print(f'- {brief.parent} | {st or "sin_estado"} -> {action(st, brief.parent)}')
