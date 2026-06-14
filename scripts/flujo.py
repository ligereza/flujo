#!/usr/bin/env python3
"""Comando unificado para operaciones frecuentes del repo flujo."""
from pathlib import Path
import subprocess, sys

PY = sys.executable

def run(args):
    print('$', ' '.join(args))
    subprocess.run(args, check=True)

def usage():
    print('''Uso:
  py scripts/flujo.py health
  py scripts/flujo.py clean
  py scripts/flujo.py job-from-text "nombre" inbox/correo.txt
  py scripts/flujo.py job-prepare jobs/NOMBRE
  py scripts/flujo.py job-next
  py scripts/flujo.py brief-to-project jobs/NOMBRE/brief.yaml [nombre]
  py scripts/flujo.py job-activate jobs/NOMBRE [nombre_proyecto]
  py scripts/flujo.py render projects/piezas_vectoriales/NOMBRE/config.json
  py scripts/flujo.py privacy jobs/NOMBRE
  py scripts/flujo.py formatos [ancho alto tipo]
  py scripts/flujo.py validate
  py scripts/flujo.py summary
  py scripts/flujo.py components
  py scripts/flujo.py inspect projects/piezas_vectoriales/NOMBRE
  py scripts/flujo.py backlog
''')
    sys.exit(1)

if len(sys.argv) < 2:
    usage()
cmd = sys.argv[1]
args = sys.argv[2:]

if cmd == 'health':
    run([PY, 'scripts/flujo_health.py'])
elif cmd == 'clean':
    run([PY, 'scripts/flujo_clean_generated.py'])
elif cmd == 'job-from-text' and len(args) >= 2:
    run([PY, 'scripts/job_from_text.py', args[0], args[1]])
elif cmd == 'job-prepare' and len(args) >= 1:
    run([PY, 'scripts/job_prepare.py', args[0]])
elif cmd == 'job-next':
    run([PY, 'scripts/job_next_actions.py'])
elif cmd == 'brief-to-project' and len(args) >= 1:
    run([PY, 'scripts/brief_to_project.py'] + args)
elif cmd == 'render' and len(args) >= 1:
    run([PY, 'scripts/project_render.py', args[0]])
elif cmd == 'job-activate' and len(args) >= 1:
    run([PY, 'scripts/job_activate.py'] + args)
elif cmd == 'privacy' and len(args) >= 1:
    run([PY, 'scripts/privacy_check_job.py', args[0]])
elif cmd == 'formatos':
    run([PY, 'scripts/piezas_formatos.py'] + args)
elif cmd == 'validate':
    run([PY, 'scripts/piezas_validate_config.py'])
elif cmd == 'summary':
    run([PY, 'scripts/piezas_project_summary.py'])
elif cmd == 'components':
    run([PY, 'scripts/piezas_components.py'])
elif cmd == 'inspect' and len(args) >= 1:
    run([PY, 'scripts/project_inspect.py', args[0]])
elif cmd == 'backlog':
    run([PY, 'scripts/backlog_list.py'])
else:
    usage()
