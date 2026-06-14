#!/usr/bin/env python3
"""Activa un job creando proyecto base desde brief.yaml y actualizando resultado/estado."""
from pathlib import Path
import re, subprocess, sys

if len(sys.argv) < 2:
    print('Uso: py scripts/job_activate.py jobs/NOMBRE [nombre_proyecto]')
    sys.exit(1)
job = Path(sys.argv[1])
brief = job / 'brief.yaml'
if not brief.exists():
    print('No existe', brief); sys.exit(1)
cmd = [sys.executable, 'scripts/brief_to_project.py', str(brief)]
if len(sys.argv) >= 3:
    cmd.append(sys.argv[2])
r = subprocess.run(cmd, text=True, capture_output=True)
print(r.stdout, end='')
if r.returncode != 0:
    print(r.stderr, file=sys.stderr)
    sys.exit(r.returncode)
match = re.search(r'Proyecto base creado:\s*(.+)', r.stdout)
project = match.group(1).strip() if match else ''
# estado en_diseno
text = brief.read_text(encoding='utf-8')
text = re.sub(r'^estado:.*$', 'estado: en_diseno', text, count=1, flags=re.M) if re.search(r'^estado:', text, re.M) else 'estado: en_diseno\n' + text
brief.write_text(text, encoding='utf-8')
resultado = job / 'resultado.md'
resultado.write_text(f'''# Resultado

## Proyecto activado

- Proyecto: `{project}`
- Config: `{project}/config.json`

## Próxima acción

```bash
py scripts/project_render.py "{project}/config.json"
```

## Estado

Job actualizado a `en_diseno`.
''', encoding='utf-8')
print(f'Job actualizado: {job} -> en_diseno')
print(f'Resultado: {resultado}')
