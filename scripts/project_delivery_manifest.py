#!/usr/bin/env python3
"""Crea manifiesto de entrega de un proyecto renderizado."""
from pathlib import Path
import sys, json
if len(sys.argv)<2:
    print('Uso: py scripts/project_delivery_manifest.py projects/piezas_vectoriales/NOMBRE')
    sys.exit(1)
project=Path(sys.argv[1])
config=project/'config.json'
if not config.exists(): print('No existe config.json en', project); sys.exit(1)
cfg=json.loads(config.read_text(encoding='utf-8'))
exports=project/'salida_generada'/'04_exports'
preview=project/'salida_generada'/'03_preview'/'preview.html'
zips=sorted(exports.glob('*.zip')) if exports.exists() else []
manifest=project/'DELIVERY.md'
manifest.write_text(f'''# Delivery — {cfg.get('project',{}).get('name', project.name)}

## Proyecto

- Carpeta: `{project}`
- Config: `{config}`
- Preview: `{preview}`

## Entregables ZIP

{''.join(f'- `{z}`\n' for z in zips) if zips else '- Pendiente generar outputs.\n'}

## Validación sugerida

```bash
py scripts/project_render.py "{config}"
py scripts/piezas_check_outputs.py
```
''', encoding='utf-8')
print(f'Manifiesto creado: {manifest}')
