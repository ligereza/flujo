# Limpieza — flujo

## Política actual

**Usa primero el workspace moderno:** `context/flujo_hub.html` + visualizadores. Muchos artefactos antiguos ya se manejan ignorando en .gitignore.

El repo debe mantenerse chico y útil:

- `jobs/_template/` sí se versiona.
- Jobs reales o pruebas generadas (`jobs/20*`) no deberían commitearse.
- Proyectos generados desde jobs con prefijo fecha (`projects/piezas_vectoriales/20*`) no deberían commitearse.
- Ejemplos intencionales sí se mantienen: `etiquetas_ejemplo`, `flyer_horizontal_minimo`, `plantillas_rd`, `prueba-rd-intervencion-terreno`, `rider_rd_intervencion_terreno`, `suplementos_rd`.
- Caches (`__pycache__`, `.pytest_cache`) y backups de airdrop no se versionan.

## Script recomendado

```bash
bash scripts/cleanup_demo_artifacts.sh --dry-run
bash scripts/cleanup_demo_artifacts.sh --apply
```

El script elimina artefactos históricos de demo/test:

- `jobs/20*_etiquetas-acme*`
- `jobs/20*_uno`
- `jobs/20*_dos`
- `jobs/20*_test-pipeline`
- `projects/piezas_vectoriales/20*-etiquetas-acme*`
- `projects/piezas_vectoriales/pieza-x`
- `projects/piezas_vectoriales/etiqueta-acme`

También limpia `__pycache__`, `.pytest_cache` y backups locales de airdrop.

## Otros scripts

- `scripts/cleanup_legacy_aggressive.sh` — archiva scripts legacy.
- `scripts/cleanup_moderate.sh` — limpieza general.
- `scripts/find_duplicates.py` — detecta duplicados.
- `scripts/sanitize_sensitive.py` — sanitiza datos sensibles.
- `scripts/cleanup_ig_temp_folders.sh` — elimina carpetas temporales IG tipo Windows.

## Después de limpiar

```bash
git status --short
py -m pytest tests/ -q
flujo health
```

---

**Versión:** Junio 2026 · v0.34.0
