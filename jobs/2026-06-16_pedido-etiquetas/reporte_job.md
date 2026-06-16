# Reporte job — 2026-06-16_pedido-etiquetas

## Brief

- Estado: brief_extraido_pendiente_revision
- Cliente: proyecto:
- Proyecto: tipo_pieza:
- Tipo pieza: medidas:

## Privacidad

```txt
# Reporte privacidad: C:\IA\flujo\jobs\2026-06-16_pedido-etiquetas\pedido_original.txt

- email: 0
- rut_chile: 0
- telefono_cl: 0
- url: 2
  muestras: https://www.instagram.com/p/ABC123test/, https://www.instagram.com/reel/XYZ789test/
- palabras_sensibles/contexto: 0

riesgo_privacidad: medio
requiere_sanitizacion: true
requiere_revision_humana: false
aprobado_para_ia_externa: false
```

## Próxima acción sugerida

- Si falta privacidad: ejecutar `py scripts/privacy_check_job.py "C:\IA\flujo\jobs\2026-06-16_pedido-etiquetas"`.
- Si el brief está listo: ejecutar `py scripts/brief_to_project.py "C:\IA\flujo\jobs\2026-06-16_pedido-etiquetas\brief.yaml"`.
- Si ya existe proyecto: generar y validar outputs.
