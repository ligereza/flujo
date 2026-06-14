#!/usr/bin/env python3
"""Prepara un job: privacidad -> brief -> reporte -> estado sugerido."""
from pathlib import Path
import re, subprocess, sys

if len(sys.argv)<2:
    print('Uso: py scripts/job_prepare.py jobs/NOMBRE')
    sys.exit(1)
job=Path(sys.argv[1])
if not (job/'pedido_original.txt').exists():
    print('No existe pedido_original.txt en', job); sys.exit(1)

def run(cmd):
    print('$', ' '.join(map(str,cmd)))
    subprocess.run([sys.executable if c=='PY' else c for c in cmd], check=True)

run(['PY','scripts/privacy_check_job.py', str(job)])
run(['PY','scripts/job_extract_brief.py', str(job)])
run(['PY','scripts/job_report.py', str(job)])

brief=job/'brief.yaml'
t=brief.read_text(encoding='utf-8')
pend=len(re.findall(r'^\s*-\s+', re.search(r'^pendientes:\s*$(.*?)(?:\n\S|\Z)', t, re.M|re.S).group(1), re.M)) if re.search(r'^pendientes:\s*$', t, re.M) else 0
privacy=(job/'privacy_report.md').read_text(encoding='utf-8', errors='ignore')
high='riesgo_privacidad: alto' in privacy
new_status='pendiente_datos' if pend or high else 'listo_para_disenar'
t=re.sub(r'^estado:.*$', f'estado: {new_status}', t, count=1, flags=re.M)
brief.write_text(t, encoding='utf-8')
print(f'Estado sugerido aplicado: {new_status}')
print(f'Reporte: {job/"reporte_job.md"}')
