#!/usr/bin/env python3
from pathlib import Path
import re, sys
if len(sys.argv)<2:
    print('Uso: py scripts/job_complete.py jobs/NOMBRE')
    sys.exit(1)
job=Path(sys.argv[1]); brief=job/'brief.yaml'
if not brief.exists(): print('No existe brief'); sys.exit(1)
t=brief.read_text(encoding='utf-8')
t=re.sub(r'^estado:.*$', 'estado: entregado', t, count=1, flags=re.M) if re.search(r'^estado:', t, re.M) else 'estado: entregado\n'+t
brief.write_text(t, encoding='utf-8')
with (job/'resultado.md').open('a', encoding='utf-8') as f:
    f.write('\n\n## Cierre\n\nEstado actualizado a `entregado`.\n')
print('Job marcado como entregado:', job)
