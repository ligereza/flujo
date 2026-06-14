#!/usr/bin/env python3
from pathlib import Path
import re, sys

def get(text,key):
    m=re.search(rf'^{re.escape(key)}:\s*(.*)$', text, re.M)
    return m.group(1).strip().strip('"') if m else ''

if len(sys.argv)<2:
    print('Uso: py scripts/job_report.py jobs/NOMBRE')
    sys.exit(1)
job=Path(sys.argv[1])
brief=job/'brief.yaml'
if not brief.exists():
    print('No existe', brief); sys.exit(1)
t=brief.read_text(encoding='utf-8', errors='ignore')
priv=(job/'privacy_report.md').read_text(encoding='utf-8', errors='ignore') if (job/'privacy_report.md').exists() else 'Sin reporte de privacidad.'
out=job/'reporte_job.md'
out.write_text(f'''# Reporte job — {job.name}

## Brief

- Estado: {get(t,'estado') or 'pendiente'}
- Cliente: {get(t,'cliente') or 'pendiente'}
- Proyecto: {get(t,'proyecto') or 'pendiente'}
- Tipo pieza: {get(t,'tipo_pieza') or 'pendiente'}

## Privacidad

```txt
{priv.strip()}
```

## Próxima acción sugerida

- Si falta privacidad: ejecutar `py scripts/privacy_check_job.py "{job}"`.
- Si el brief está listo: ejecutar `py scripts/brief_to_project.py "{brief}"`.
- Si ya existe proyecto: generar y validar outputs.
''', encoding='utf-8')
print(f'Reporte creado: {out}')
