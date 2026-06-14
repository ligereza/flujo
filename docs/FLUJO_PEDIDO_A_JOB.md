# Flujo pedido/correo → job preparado

## Desde archivo de correo

```bash
py scripts/job_from_text.py "nombre pedido" inbox/correo.txt
py scripts/job_prepare.py "jobs/YYYY-MM-DD_nombre-pedido"
```

`job_prepare.py` ejecuta:

1. `privacy_check_job.py`
2. `job_extract_brief.py`
3. `job_report.py`
4. asigna estado sugerido:
   - `pendiente_datos` si hay pendientes o riesgo privacidad alto,
   - `listo_para_disenar` si no detecta pendientes críticos.

## Ver próximas acciones

```bash
py scripts/job_next_actions.py
```

## Después

Si el job queda `listo_para_disenar`:

```bash
py scripts/brief_to_project.py "jobs/YYYY-MM-DD_nombre/brief.yaml"
```
