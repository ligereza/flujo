# Editor visual web (Gradio)

Editor local para componer piezas sin tocar JSON a mano. Vive en el paquete
(`src/flujo/web/`), no en `scripts/` legacy.

```bash
flujo serve                       # http://127.0.0.1:7860
flujo serve --port 8080           # otro puerto
flujo serve --host 0.0.0.0        # accesible en la red local
flujo serve --legacy              # usar el antiguo scripts/app.py
```

## Flujo de trabajo

```
1. Elegir formato        2. Editar datos        3. Proporción/DPI
   (catálogo, filtros)      título/sub/cuerpo       cm o dpi
        │                        │                      │
        └──────────────┬────────┴──────────────────────┘
                       ▼
              PREVIEW SVG en vivo
                       │
                       ▼
       Exportar SVG + config.json  →  projects/piezas_vectoriales/<slug>/
                       │
                       ▼
          flujo render run config.json   (SVG editable + vectorizado para Illustrator)
```

## Qué hace cada parte

- **Catálogo:** lee `INDEX_FORMATOS.json` (los 12 formatos de la ONG). Filtros por
  **área** (eventos/suplementos) y **medio** (impresión/digital).
- **Carga:** si el formato tiene plantilla `config.json`, la usa; si no (carteleras,
  posts), genera una base con **imagen + textos** lista para editar.
- **Datos:** edita los primeros `text`/`paragraph` como título/subtítulo/cuerpo.
- **Proporción/DPI:** reutiliza `flujo render rescale` por debajo
  (`set_real_size` / `set_dpi`). Cambiar cm = proporción; cambiar DPI = resolución
  (anti-pixelado).
- **Preview:** `web/svg_preview.py` genera un SVG rápido (texto vivo, word-wrap
  aproximado, soporte de elemento `image`, guía de área segura). **No** es el SVG
  de producción.
- **Exportar:** guarda `config.json` + `preview.svg` en el proyecto. El SVG final
  de calidad se obtiene con `flujo render run` (usa el generador oficial con
  fuentes del sistema).

## Arquitectura (para la siguiente IA)

```
src/flujo/web/
├── __init__.py
├── svg_preview.py   # render_svg(config) -> str  (sin dependencias externas)
└── editor.py        # lógica pura (catalog_choices, load_format_state,
                     #  update_state, export_files) + build_app()/launch() Gradio
```

- La **lógica de estado es pura y testeable** (no importa Gradio); la UI solo la
  orquesta. `import gradio` es perezoso dentro de `build_app()`.
- Tests en `tests/test_web_editor.py` (svg_preview + funciones de estado).

## Limitaciones actuales / próximos pasos

1. **Elemento `image`:** el preview ya lo soporta (placeholder si no hay `src`,
   `<image href>` si lo hay). Falta que el **generador oficial**
   (`tools/.../generar_desde_json.py`) también lo emita para el SVG de producción.
2. **Auto-fit de texto** ("misma medida, distinto texto"): aún no; el preview hace
   word-wrap aproximado pero no encoge/crece cajas. Es la siguiente feature grande.
3. **Avisos de Instagram** (video en 1ª del carrusel / perfil privado): existen en
   `intake/email_parser.py`; falta exponerlos como una pestaña del editor.
4. **Edición de elemento por elemento** (arrastrar/posicionar): hoy se editan
   título/sub/cuerpo; el resto se ajusta en Illustrator tras exportar.
5. **Botón "acusar recibo"** (mailto/Gmail prellenado) para el flujo de intake.
