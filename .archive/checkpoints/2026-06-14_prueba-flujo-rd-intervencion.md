# Checkpoint — prueba flujo RD intervención terreno

Fecha: 2026-06-14

## Prueba realizada

Se creó una prueba controlada usando el brief largo de Reduciendo Daño:

```txt
jobs/2026-06-14_prueba-rd-intervencion-terreno/
projects/piezas_vectoriales/prueba-rd-intervencion-terreno/
```

## Flujo probado

```txt
job → privacy_check → job_report → job_activate → project_inspect → project_render → delivery_manifest → piezas_check_outputs → clean → health
```

## Resultado

- El proyecto base se creó correctamente.
- `brief_to_project` eligió plantilla one-page A4 por intención (`propuesta`, `dossier`, `one_page`).
- El render funcionó.
- Los outputs generados fueron limpiados para no versionarlos.
- `flujo_health` terminó OK.

## Nota

No se diseñó pieza final. Es solo prueba de flujo.
