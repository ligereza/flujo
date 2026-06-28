# Revisión rápida — limpieza repo flujo

Fecha: 2026-06-21
Repo revisado: https://github.com/ligereza/flujo
Commit base: dfa8c69 (`v0.33.3`)

## Estado general

- Versión actual: `0.33.3`.
- `compileall`: OK.
- `flujo health`: OK, con aviso esperado de índice faltante (`flujo index --rebuild`).
- Suite completa: `132 passed, 1 skipped`.
- Working tree original del remoto: limpio.

## Limpieza

- Las carpetas temporales tipo `C：/Users/.../Temp/ig_*` ya no están trackeadas en el working tree.
- El historial remoto actual ya está liviano: `.git` aprox. `1.5 MB`, pack aprox. `1.20 MiB`.
- Aún queda un blob histórico pequeño de una descarga IG (~0.19 MB), pero no es crítico.
- Hay muchos `HANDOFF_*`, `checkpoints/`, `jobs/` y `_archive/`; no los borré porque parecen ser parte del sistema/documentación. Si quieres limpieza agresiva, conviene decidir una política antes.

## Problema encontrado

Al correr la suite completa, algunos tests podían crear proyectos reales en `projects/piezas_vectoriales/20*/` dentro del repo. Eso deja basura/noise después de testear y confirma tu sospecha de que faltaba limpieza.

Causa: algunos tests monkeypatcheaban `flujo.paths.repo_root`, pero módulos como `flujo.jobs.job` y `flujo.render.piezas` importan `repo_root` directamente, así que el patch no llegaba a todas partes.

## Fix aplicado en este clon

Archivos modificados:

- `.gitignore`
  - Ignora futuros proyectos generados por jobs con prefijo de fecha: `projects/piezas_vectoriales/20*/`.
- `tests/test_jobs_lifecycle.py`
  - Parchea también `flujo.jobs.job.repo_root`.
  - Parchea `flujo.render.piezas.repo_root` en el test de activación.
- `tests/test_render_formats.py`
  - Parchea `flujo.render.piezas.repo_root` donde se crean proyectos desde brief.

## Verificación post-fix

```text
python -m pytest tests/ -q
→ 132 passed, 1 skipped

python -m compileall -q src scripts tests projects/plano
→ OK

flujo health
→ OK, con aviso: Index no existe. Ejecutar: flujo index --rebuild

git status --short
→ solo los 3 cambios intencionales + este reporte
```

## Recomendación siguiente

Commit sugerido:

```bash
git add .gitignore tests/test_jobs_lifecycle.py tests/test_render_formats.py REVISION_LIMPIEZA_2026-06-21.md
git commit -m "test: aislar repo_root y evitar proyectos generados en tests"
```

Si prefieres no meter este reporte al repo, no lo agregues al commit.
