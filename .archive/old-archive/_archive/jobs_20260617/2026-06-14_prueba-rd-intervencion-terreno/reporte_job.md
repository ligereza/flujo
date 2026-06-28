# Reporte job — 2026-06-14_prueba-rd-intervencion-terreno

## Brief

- Estado: listo_para_disenar
- Cliente: Reduciendo Daño Chile
- Proyecto: Propuesta de Servicio – Intervención en Terreno
- Tipo pieza: pendiente_definir

## Privacidad

```txt
# Reporte privacidad: jobs/2026-06-14_prueba-rd-intervencion-terreno/pedido_original.txt

- email: 0
- rut_chile: 0
- telefono_cl: 0
- url: 0
- palabras_sensibles/contexto: 6
  detectadas: asistente, consumo, médico, psicológica, salud, sustancias

riesgo_privacidad: alto
requiere_sanitizacion: false
requiere_revision_humana: true
aprobado_para_ia_externa: false
```

## Próxima acción sugerida

- Si falta privacidad: ejecutar `py scripts/privacy_check_job.py "jobs/2026-06-14_prueba-rd-intervencion-terreno"`.
- Si el brief está listo: ejecutar `py scripts/brief_to_project.py "jobs/2026-06-14_prueba-rd-intervencion-terreno/brief.yaml"`.
- Si ya existe proyecto: generar y validar outputs.
