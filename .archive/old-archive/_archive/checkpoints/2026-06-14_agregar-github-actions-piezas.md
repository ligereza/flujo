# Checkpoint — GitHub Actions piezas vectoriales

Fecha: 2026-06-14

## Cambio

Se agregó workflow para generar outputs de piezas vectoriales desde GitHub Actions.

## Archivos

- `.github/workflows/render_piezas_vectoriales.yml`
- `docs/GITHUB_ACTIONS_PIEZAS.md`

## Objetivo

Permitir flujo web/chat sin ejecución local:

```txt
IA modifica JSON/config → push/PR → GitHub Actions genera artifacts descargables
```
