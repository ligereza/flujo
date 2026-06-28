# HANDOFF 2026-06-28 - README logo clean summary

## Objetivo

Actualizar documentacion sin tocar el motor de airdrop.

Este airdrop:

- vuelve a dejar como recomendacion principal los dos comandos normales de airdrop;
- documenta que el bloqueo anterior probablemente fue por una carpeta local pesada `logo3d/` colada en el repo;
- agrega summary y goal de `logo_clean_lab`;
- actualiza README general;
- agrega ignore para carpetas 3D locales accidentales.

## Archivos

```txt
README.md
README_AIRDROP.md
.gitignore
context/LAST_HANDOFF.md
projects/logo_clean_lab/README.md
projects/logo_clean_lab/docs/SUMMARY_AND_GOAL.md
```

## Comandos

Desde root del repo:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "actualiza readme y logo clean lab summary"
```

No requiere `--allow-airdrop-engine` porque no modifica `src/flujo/airdrop.py`.

## Nota operativa

Antes de correr auto-checkpoint:

```bash
git status --short
```

Si aparece una carpeta local pesada o de otro proyecto, sacarla o ignorarla antes de correr el runner.

## Tareas simples (low token)

1. Aplicar airdrop con los dos comandos normales.
2. Confirmar `git status --short` limpio o solo cambios esperados.
3. Probar `tools/illustrator/scripts/logo_clean_master.jsx` en Illustrator.
4. Registrar resultados en `projects/logo_clean_lab/learning/`.
