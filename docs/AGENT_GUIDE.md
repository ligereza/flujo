# AGENT_GUIDE — flujo

**Repo:** `flujo` — arte + automatización · v0.34.10

## Protocolo (token-efficient, Windows primero)

1. **Obligatorio:** ejecuta `flujo app` (o `flujo app --desktop`) — entrada única diaria (lanza app real + sirve hub pro). Fallback: abre `context/flujo_hub.html`.
2. Lee `context/LAST_HANDOFF.md` (estado + tareas) + `docs/AGENT_OPERATING_MANUAL.md`.
3. Usa el **hub** (dentro de `flujo app`): intake + visualizadores + sección Datadrop + "Delegar..." (parallel delegation a roles especializados).
4. `projects/README.md` (satélites + flujo).

Verificación: `py -m flujo health` (usa py en Windows). Siempre actualiza LAST_HANDOFF al final.

**Protocolo para Datadrop (inverse airdrop, feed linea v4.1):** después de trabajo terminado (post privacy), copia fotos reales a `datadrops/incoming/` o usa hub (tab Herramientas > Datadrop): "Subir" / "Escanear incoming" (o `flujo datadrop scan`). Luego `flujo datadrop list` + `prepare` (genera _review_package.txt con manifests + for_future_ai). Linea v4.1 usa estos como ground-truth real examples. Header link en hub abre tab+sección.

Trabaja en clon limpio. Entrega vía airdrop. Nota "Windows: py".

Español prioritario. No asumas Linux paths.

## Stack

- Python 3.10+
- Instalación editable: `py -m pip install -e ".[dev]"`
- CLI: `flujo` o `py -m flujo`
- CLI framework: Typer
- Tests: pytest
- Descarga Instagram: solo `instaloader`

## Verificación mínima en clon limpio

```bash
py -m pip install -e ".[dev]"
py -m compileall -q src scripts tests
py -m pytest tests/ -q --tb=short
py -m flujo health
py -m flujo version
```

En Linux/macOS puedes usar `python3` o `python` en lugar de `py`.

## Comandos esenciales

```bash
flujo version
flujo health
flujo daily
flujo app          # ENTRADA DIARIA OBLIGATORIA ÚNICA (app real + hub pro workspace + APIs)
flujo serve        # alias (usa --legacy solo para Gradio viejo)
flujo app --desktop  # ventana nativa (pywebview + tray, launchers en root)
flujo job new "x" --email inbox/correo.txt
flujo job prepare jobs/X
flujo render run projects/piezas_vectoriales/X/config.json
flujo privacy scan archivo.txt
flujo plano projects/plano/ejemplos/evento_ejemplo.json
# Datadrop (inverse airdrop — usa hub datadrop o CLI):
flujo datadrop scan     # incoming/ bulk → manifests + analysis (for_future_ai)
flujo datadrop list     # lista procesados limpios
flujo datadrop prepare  # _review_package.txt + traits para linea v4.1
```

Ayuda:

```bash
flujo --help
flujo job --help
flujo render --help
flujo airdrop --help
flujo datadrop --help
```

## Airdrops

Lee también `docs/AGENT_AIRDROP_PROTOCOL.md` y `docs/AIRDROP_REVIEW.md`.

Validación normal:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje"
```

Si tocas `src/flujo/airdrop.py`:

```bash
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "mensaje" --allow-airdrop-engine
```

Reglas del ZIP:

- Contiene carpeta `_airdrop/`.
- Cada archivo va en su ruta final dentro de `_airdrop/`.
- Incluye handoff obligatorio.
- Sin caches, zips internos, builds, `__pycache__`, bases SQLite ni archivos pesados.
- Bump de versión en `src/flujo/version.py` y `pyproject.toml`.
- Changelog actualizado en `src/flujo/version.py`.

## Reglas innegociables

- No automatizar Photoshop / Illustrator / Blender.
- Solo `instaloader`; no `yt-dlp`.
- Privacidad primero: `flujo privacy` antes de enviar contenido a IA externa.
- Toda lógica nueva debe vivir en `src/flujo/` y tener tests.
- No modificar histórico/generados sin justificarlo en handoff.
- No dejar placeholders ni commits vacíos.

## Documentación interna clave

- `docs/CLI.md` — referencia de CLI actual (incl. `flujo datadrop scan/list/prepare`, `flujo app`).
- `docs/REPO_MAP.md` — qué está vivo (datadrops/ inverse airdrop, hub, etc.).
- `docs/SCRIPTS_INVENTORY.md` — estado de scripts.
- `docs/JOB_PIPELINE.md` — ciclo de vida de jobs.
- `docs/ESTADOS_JOB.md` — estados y transiciones.
- `docs/AGENT_OPERATING_MANUAL.md` — modelo delegación paralela (5 roles) + hub.
- `docs/AIRDROP_REVIEW.md` — revisión segura de airdrops.

**Avances:** datadrop (inverse airdrop) listo en hub (botones en Herramientas; header abre tab+sección) + CLI. Parallel delegation reciente (2+ agents + supervisor). Prepara auto-compact + linea v4.1 con datadrops reales como examples. Siempre `flujo app` + LAST_HANDOFF + hub.
