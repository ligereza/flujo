#!/usr/bin/env python3
"""Valida estructura mínima de un job."""
from pathlib import Path
import re, sys
VALID={'borrador','brief_extraido_pendiente_revision','pendiente_datos','listo_para_disenar','en_diseno','generado','entregado','pausado','cancelado','pendiente_diseno'}
if len(sys.argv)<2:
    print('Uso: py scripts/job_validate.py jobs/NOMBRE')
    sys.exit(1)
job=Path(sys.argv[1]); errors=[]; warnings=[]
for f in ['brief.yaml','pedido_original.txt','estado.md','resultado.md']:
    if not (job/f).exists(): errors.append(f'falta {f}')
brief=job/'brief.yaml'
if brief.exists():
    t=brief.read_text(encoding='utf-8', errors='ignore')
    m=re.search(r'^estado:\s*(.*)$', t, re.M)
    st=m.group(1).strip() if m else ''
    if not st: errors.append('brief sin estado')
    elif st not in VALID: warnings.append(f'estado no estándar: {st}')
    for key in ['id','origen','tipo_pieza']:
        if not re.search(rf'^{key}:', t, re.M): warnings.append(f'brief sin {key}')
if (job/'privacy_report.md').exists():
    pr=(job/'privacy_report.md').read_text(encoding='utf-8', errors='ignore')
    if 'riesgo_privacidad: alto' in pr: warnings.append('privacidad alto: requiere revisión humana')
else:
    warnings.append('sin privacy_report.md')
print(f'Job: {job}')
for w in warnings: print('WARN:', w)
for e in errors: print('ERROR:', e)
if errors: sys.exit(1)
print('OK: job válido')
