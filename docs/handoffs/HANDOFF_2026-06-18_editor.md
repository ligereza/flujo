# 🤝 Handoff 2026-06-18 — flujo v0.28.0 — Editor visual Gradio

## Por qué este airdrop

El dueño quiere un editor en el navegador para ajustar datos y proporción de las
piezas y **exportar SVG** (perfecto para abrir editable en Illustrator). Este
airdrop entrega la **primera versión funcional** de ese editor, como módulo del
paquete (`src/flujo/web/`), reemplazando al script legacy `scripts/app.py`.

## Qué incluye

| Archivo | Cambio |
|---|---|
| `src/flujo/web/__init__.py` | **NUEVO** paquete web. |
| `src/flujo/web/svg_preview.py` | **NUEVO.** Renderizador SVG liviano (sin deps) para preview en vivo. Soporta rect/panel/circle/line/text/paragraph/**image**/group + guía de área segura. |
| `src/flujo/web/editor.py` | **NUEVO.** Lógica pura (catálogo, carga de formato, edición de texto, proporción/DPI vía render.rescale, export) + UI Gradio (`build_app`/`launch`). |
| `src/flujo/cli.py` | `flujo serve` ahora usa el editor nuevo; flags `--port/--host/--legacy`. Fallback al script legacy si algo falla. |
| `tests/test_web_editor.py` | **NUEVO.** 17 tests de lógica pura (svg_preview + estado del editor), sin levantar Gradio. |
| `docs/EDITOR_WEB.md` | **NUEVO.** Guía del editor + arquitectura. |
| `README.md`, `version.py`, `pyproject.toml` | Sección "app" actualizada + versión 0.28.0. |

## Cómo funciona (resumen)

```
flujo serve  →  http://127.0.0.1:7860
  elegir formato (catálogo, filtros área/medio)
  → editar título/subtítulo/cuerpo
  → ajustar proporción (cm) o DPI    (reusa render.rescale)
  → PREVIEW SVG en vivo              (web/svg_preview.py)
  → exportar SVG + config.json a projects/piezas_vectoriales/<slug>/
  → flujo render run config.json     (SVG de producción para Illustrator)
```

Decisión de diseño: **el preview es liviano y aproximado** (texto vivo, word-wrap
por glifos), separado del **generador oficial** de producción
(`tools/.../generar_desde_json.py`, con fuentes reales). Así el editor es rápido y
sin dependencias nuevas, y el SVG final sigue saliendo del pipeline probado.

La **lógica de estado es pura y testeable**; Gradio solo la orquesta (import
perezoso). Compatible con Gradio 6.x (probado con 6.19): `theme`/`css` no van en
`Blocks()` sino como `<style>` inyectado.

## Verificación hecha

```
✅ compileall src/flujo/web src/flujo/cli.py   → OK
✅ build_app() construye sin warnings (Gradio 6.19)
✅ launch real → HTTP 200, la app responde     (probado y cerrado)
✅ pytest tests/  → 116 passed, 1 skipped (eran 99; +17)
✅ flujo serve --help muestra --port/--host/--legacy
```

## Cómo aplicar

```bash
flujo airdrop apply "v0.28.0 - editor visual gradio"
# o:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.28.0 - editor visual gradio"

py -m pip install -e .
flujo version         # 0.28.0
flujo serve           # abrir http://127.0.0.1:7860
py -m pytest tests/ -q  # 116 passed, 1 skipped
```

> Nota Windows: `flujo serve` abre el navegador en http://127.0.0.1:7860. Si el
> puerto está ocupado: `flujo serve --port 7870`.

## Próximos pasos (para la siguiente IA / dueño)

1. **Generador oficial: soportar elemento `image`** (hoy solo el preview lo emite).
   Es necesario para que el SVG de producción incluya la foto enlazada.
2. **Auto-fit de texto** ("misma medida, distinto texto"): encoger/crecer cajas
   flexibles respetando campos `locked`. Es la feature grande pendiente.
3. **Pestaña de avisos de Instagram** en el editor (video/privado ya detectados
   en `intake/email_parser.py`).
4. **Botón "acusar recibo"** (mailto/Gmail prellenado) — conecta con intake.
5. **Plantillas config.json** para carteleras/posts/historias (hoy el editor les
   genera una base; convendría plantillas dedicadas).
