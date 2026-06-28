# Mapa del repo — flujo

Versión: v0.34.10 (historia consolidada)

Este mapa existe para que humanos y agentes de IA entiendan rápido qué carpetas están vivas, cuáles son históricas y qué NO deben tocar sin permiso.

## Núcleo vivo

| Ruta | Rol | Estado |
|---|---|---|
| `src/flujo/` | Paquete Python principal y CLI `flujo` | Vivo |
| `tests/` | Tests automatizados | Vivo |
| `scripts/validate_airdrop.py` | Validador de entregas `_airdrop/` | Vivo |
| `scripts/run_airdrop_checks.py` | Runner seguro con logs y checkpoint solo si pasa | Vivo |
| `.github/workflows/ci.yml` | CI real: install, compileall, health, pytest | Vivo |
| `pyproject.toml` | Metadata, dependencias y versión del paquete | Vivo |
| `requirements.txt` | Dependencias equivalentes para instalación simple | Vivo |

## Operación diaria

| Ruta | Rol | Estado |
|---|---|---|
| `jobs/_template/` | Plantilla versionada de jobs | Vivo |
| `inbox/` | Ejemplos/entradas de prueba | Vivo con cuidado |
| `datadrops/` (incl. incoming/) | Datadrop (inverse airdrop): bulk fotos terminadas → manifests + palette/ocr + for_future_ai (feed linea v4.1) | Vivo — usa hub (`flujo app` → Datadrop) o `flujo datadrop scan/list/prepare` |
| `projects/flyer_eventos/` | Proyectos flyer de ejemplo/estructura | Mixto |
| `projects/piezas_vectoriales/` | Proyectos y plantillas vectoriales | Vivo/ejemplos |
| `tools/` | Especificaciones, componentes y plantillas base | Vivo |
| `schemas/` | Schema intake JSON y ejemplos | Vivo |

## Proyectos satélite

| Ruta | Rol | Estado |
|---|---|---|
| `projects/piezas_vectoriales/` | Proyectos y plantillas vectoriales | Vivo |
| `projects/flyer_eventos/` | Flujos reales de eventos | Operativo |
| `projects/plano/` | Generador de planos/riders/costos | Vivo |
| `projects/tapiz/` | Experimento visual (VibeCode) | Referencia |
| `projects/flujo/` | Línea editorial central + ejemplos/json para agentes | Nuevo |
| `projects/cotizaciones/` | Cotizaciones duales integradas con flujo (productora vs ONG/empresa) | Nuevo — mejora de planos |

Ver también `docs/FOR_EXTERNAL_AI.md` cuando se alimente el repo completo a una IA.

Nota: `projects/tapiz/vibecode.egg-info/` está trackeado históricamente. No agregar nuevos `.egg-info`.

## Documentación viva + entrada principal

**Abre primero (siempre):** ejecuta `flujo app` (o `flujo app --desktop`; o abre `context/flujo_hub.html` como fallback).

El hub es el **workspace principal pro** (HTMLs servidos por backend cuando usas la app):
- Intake + match real
- Visualizadores SVG/plano embebidos
- Datadrop section (working buttons; header abre tab+sección) + comandos
- Comandos + tokens live + Brand Validator
- Sección "Delegar a Agentes Especializados" (guía práctica + prompts copiables para 5 roles; parallel delegation reciente) + RAW para agentes
- APIs + SSE + PWA cuando `flujo app` corre

| Ruta | Rol |
|---|---|
| `flujo app` (o context/flujo_hub.html) | Entrada diaria obligatoria + hub pro workspace (UI + delegación + datadrop) |
| `context/svg_visualizer.html` | Visualizador real de piezas SVG (embebido, grupos exactos) |
| `context/plano_demo.html` | Demo de planos + riders + costos |
| `context/LAST_HANDOFF.md` | Estado + tareas (bajo tokens) |
| `docs/AGENT_OPERATING_MANUAL.md` | Dos flujos + modelo delegación multi-agente (5 roles) |
| `projects/README.md` | Satélites alineados a flujo |

El resto de docs son de soporte o histórico. No los leas primero.

**Contexto para agentes:** Hub + LAST_HANDOFF + AGENT_OPERATING_MANUAL = única fuente necesaria. Dirección: prep auto-compact parallel work; linea v4.1 con datadrops reales.

## Histórico / referencia

Todo histórico movido a `.archive/` (checkpoints, old _archive, reference_old, etc.).

| Ruta | Rol | Regla |
|---|---|---|
| `.archive/` | Material archivado (checkpoints, _archive, reference_old, _airdrop_backups) | No usar como fuente primaria salvo investigación. Ver .archive/README.md |
| `docs/handoffs/` | Notas de agentes (HANDOFF, HOTFIX, AUDITORIA, REVISION) | Ubicación consolidada para higiene de raíz. No agregar ruido de tareas a medias |

**Nota de limpieza (2026-06):** Commits de v0.34.x con tareas parciales/fallidas fueron consolidados en un solo commit ("v0.34 consolidated"). El detalle queda en los archivos de handoffs/ y checkpoints/.

## Archivos generados/locales que NO deben entrar en airdrops

- `_airdrop/`
- `_airdrop_backups/`
- `_logs/`
- `__pycache__/`, `*.pyc`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `*.egg-info/` nuevos
- `data/*.db`, `*.sqlite*`
- `context/DAILY.md`, `context/dashboard.html` (LAST_HANDOFF.md **sí** se versiona: es el estado para continuidad de IAs)
- `projects/**/salida_generada/`
- media pesada: `*.mp4`, `*.mov`, `*.psd`, `*.ai`, `*.zip`, etc.

## Regla para agentes

Antes de proponer cambios, identifica si el archivo pertenece a:

1. Núcleo vivo.
2. Operación diaria.
3. Documentación viva.
4. Histórico/referencia.
5. Generado/local.

Si es histórico o generado, no lo uses como base de cambios sin avisar.
