# Higiene del repo

Versión: v0.51.0

## Política

El repo debe mantenerse útil para trabajo real y legible para agentes. No debe convertirse en un basurero de outputs, caches o pruebas locales.

Ejecuta `py scripts/suggest_repo_hygiene.py` (100% no destructivo) + terminal safe rm SOLO generados (pycache/.pytest_cache) para ver sugerencias actualizadas del estado actual. Siempre empieza por `flujo app` + hub + LAST_HANDOFF (reinforces resumption and speeds daily designer flow: pedido → `flujo app`/hub → real actions/visualizers → export). **Punto de entrada: `flujo app` (lanza app real + hub) → usa hub + lee context/LAST_HANDOFF.md.**

## Nunca commitear

- `_airdrop/`, `_airdrop_backups/`, `_logs/`
- `__pycache__/`, `*.pyc`
- `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`
- `*.egg-info/` nuevos
- `data/*.db`, `*.sqlite*`
- `context/DAILY.md`, `context/dashboard.html`
- `projects/**/salida_generada/`
- medios pesados descargados: `*.mp4`, `*.mov`, `*.mkv`, `*.psd`, `*.ai`, `*.zip`
- `jobs/20*` y `projects/piezas_vectoriales/20*` de pruebas/demo (jobs reales fechados no deberían commitearse; `jobs/_template/` sí se versiona)

Ejemplos intencionales que SÍ se mantienen versionados: `etiquetas_ejemplo`, `flyer_horizontal_minimo`, `plantillas_rd`, `prueba-rd-intervencion-terreno`, `rider_rd_intervencion_terreno`, `suplementos_rd`.

## Antes de checkpoint

```bash
git status --short
py -m compileall -q src scripts tests
py -m pytest tests/ -q
py -m flujo health
```

Limpieza de generados/caches:

```bash
flujo clean --generated       # via CLI Typer (pycache + outputs regenerables de piezas_vectoriales)
py scripts/flujo_health.py    # chequeo directo (usado tambien por .github/workflows/render_piezas_vectoriales.yml)
bash scripts/limpiar_basura.sh   # usado por make clean
```

## Antes de aceptar un airdrop externo

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje"
```

La validación vigente está en `scripts/validate_airdrop.py`; el runner histórico
ya no forma parte del checkout actual.

## Deuda conocida

- `projects/tapiz/vibecode.egg-info/` está trackeado históricamente.
- Historial de commits de v0.34 con tareas parciales/fallidas fue consolidado; el viejo REPO_MAP.md fue archivado.
- checkpoints/ y docs/handoffs/ se mantienen como bitácora (no agregar commits ruidosos de micro-tareas).
- Se recomienda correr git filter-repo para reducir tamaño del .git (ver docs/LIMPIEZA_HISTORIAL.md).

**Actual (2026-06):** `context/flujo_hub.html` + `svg_visualizer.html` + `plano_demo.html` + `LAST_HANDOFF.md` son la fuente de verdad diaria.

Histórico (checkpoints, _archive, reference_old) se movió a `_archive/legacy_historico_previo/` y se RETIRÓ el 2026-07-30: era un archivo dentro de un archivo dentro de un archivo, 283 archivos que nadie volvió a abrir. Vive en el historial de git, que es para lo que existe. Mantener el root limpio; la orientación contractual está en `AGENTS.md`.

**Herramientas de limpieza, estado 2026-07-30.** Vivas: `limpiar_basura.sh`
(usado por `make clean`), `find_duplicates.py` y `suggest_repo_hygiene.py` --
esta última **se invoca a mano**, no la llama ningún cron ni workflow, sirve
como señal de cobertura cuando alguien quiere revisar el estado del repo.
Retirados el 2026-07-30 por no tener invocador real (ni Makefile, ni
`.github/workflows/*.yml`, ni cron, solo mención en docs): `flujo_clean_generated.py`,
`soft_cleanup.py`, `cleanup_demo_artifacts.sh`, `cleanup_ig_temp_folders.sh`.
Los checkpoints de versión en `docs/handoffs/archive/` (los `HANDOFF_v0.4x.md`,
`HOTFIX_*.md` y similares, ~93 archivos) también se retiraron ese día: git ya
es el registro de esa historia, y ninguno de esos archivos tenía un consumidor
real (ni el handoff ni el contrato actual los citaban por nombre). Lo que sí se
cita por nombre se queda: las ocho notas de decisiones de julio 2026 en esa
misma carpeta.
