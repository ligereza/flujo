#!/usr/bin/env python3
"""Lista jobs y estados."""
from pathlib import Path
import re, sys


def val(text, key):
    m=re.search(rf'^{re.escape(key)}:\s*(.*)$', text, re.M)
    return m.group(1).strip().strip('"') if m else ''

def pending_count(text):
    m=re.search(r'^pendientes:\s*$(.*?)(?:\n\S|\Z)', text, re.M|re.S)
    if not m: return 0
    return len(re.findall(r'^\s*-\s+', m.group(1), re.M))

def main():
    base=Path('jobs')
    show_examples='--examples' in sys.argv
    rows=[]
    for b in sorted(base.glob('*')):
        if b.name.startswith('_') and not show_examples: continue
        brief=b/'brief.yaml'
        if not brief.exists(): continue
        t=brief.read_text(encoding='utf-8', errors='ignore')
        rows.append((b.as_posix(), val(t,'estado') or 'sin_estado', val(t,'tipo_pieza'), val(t,'proyecto'), pending_count(t)))
    if not rows:
        print('No hay jobs. Crear: bash scripts/job_new.sh "nombre"')
        return
    print(f'Jobs encontrados: {len(rows)}')
    for path,estado,tipo,proyecto,pend in rows:
        print(f'- {path} | {estado} | pendientes:{pend} | {tipo or "tipo?"} | {proyecto or "proyecto?"}')

if __name__=='__main__': main()
