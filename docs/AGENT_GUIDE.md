# AGENT_GUIDE — flujo

**Repo:** `flujo` — arte + automatización · v0.34.10

## Protocolo (token-efficient, Windows primero)

1. Abre `context/flujo_hub.html` (entrada principal)
2. `PARA_IA_CONTEXT.md` + `context/LAST_HANDOFF.md` (tareas simples + estado)
3. `projects/README.md` (satélites + aistetic)

Verificación: `py -m flujo health` (usa py en Windows)

Trabaja en clon limpio. Entrega vía airdrop. Siempre actualiza LAST_HANDOFF con tareas claras + nota "Windows: py".

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
flujo job new "x" --email inbox/correo.txt
flujo job prepare jobs/X
flujo job activate jobs/X
flujo render run projects/piezas_vectoriales/X/config.json
flujo render formats
flujo privacy scan archivo.txt
flujo daily
flujo serve
flujo app
flujo plano projects/plano/ejemplos/evento_ejemplo.json
```

Ayuda:

```bash
flujo --help
flujo job --help
flujo render --help
flujo airdrop --help
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

- `docs/CLI.md` — referencia de CLI actual.
- `docs/REPO_MAP.md` — qué está vivo, histórico o generado.
- `docs/SCRIPTS_INVENTORY.md` — estado de scripts.
- `docs/JOB_PIPELINE.md` — ciclo de vida de jobs.
- `docs/ESTADOS_JOB.md` — estados y transiciones.
- `docs/INTAKE_JSON.md` — contrato JSON pendiente de implementación end-to-end.
- `docs/AIRDROP_REVIEW.md` — revisión segura de airdrops.
