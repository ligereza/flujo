# 🤝 Handoff 2026-06-18 — flujo v0.30.1 — Fixes del editor

## Bugs reportados por el dueño (al probar el editor 0.30.0)

1. "el gradio no, los formatos no corresponden, las medidas están horizontales"
2. "no funciona el escalado, se bugea"
3. "el link de Instagram tampoco, no detecta ni entregándole el URL directo ni
   colocando 'hola .... links'"

> Nota positiva: el **auto-checkpoint+push automático funcionó** (`✓ Checkpoint
> creado y cambios subidos al servidor`) — el fix de bash (0.29.0) quedó OK.

## Diagnóstico (reproducido) y solución

### BUG 1 — Instagram no detecta URLs sin esquema  (`src/flujo/intake/email_parser.py`)
El regex exigía `https?://`. Si pegabas `instagram.com/p/ABC/` (sin `https://`,
como queda al copiar a veces) → 0 links → "SIN LINKS".
**Fix:** regex acepta URLs con o sin esquema y con/sin www; normaliza a `https://`,
deduplica e ignora query string. Soporta `p/reel/reels/tv`.

### BUG 2 — Preview se sale de pantalla / "se ve horizontal raro"  (`src/flujo/web/svg_preview.py` + `editor.py`)
El SVG salía con `width="3300px"` fijo → un lienzo de 3300px se desbordaba del
panel y se veía gigante/cortado. El "escalado bugeado" era esto.
**Fix:** `render_svg(..., responsive=True)` para el preview → `width="100%"`,
`height="auto"`, `preserveAspectRatio`, `max-height:80vh` y el `viewBox` hace el
escalado. El export a archivo mantiene los px reales.

### BUG 3 — Formato vertical cargaba horizontal  (`src/flujo/web/editor.py`)
El flyer físico 10×14 (vertical) reusa la plantilla `flyer_horizontal_minimo`
(canvas 2800×2000 horizontal) → cargaba horizontal. Por eso "los formatos no
corresponden / medidas horizontales".
**Fix:** `_load_template_config` reconcilia la orientación: si la plantilla no
coincide con la medida real del catálogo, ajusta el canvas a la medida del
formato y deja un `_aviso_orientacion`. (La etiqueta 16.5×6.5 sigue horizontal,
que es lo correcto.)

## Archivos

| Archivo | Cambio |
|---|---|
| `src/flujo/intake/email_parser.py` | regex IG robusto (sin esquema/www, normaliza, dedup). |
| `src/flujo/web/svg_preview.py` | `render_svg(responsive=...)` para preview escalable. |
| `src/flujo/web/editor.py` | preview en modo responsive; `_load_template_config` reconcilia orientación; `_svg_html` con contenedor responsivo. |
| `tests/test_web_fixes.py` | **NUEVO.** 11 tests de regresión de los 3 bugs. |
| `version.py`, `pyproject.toml` | v0.30.1. |

## Verificación hecha

```
✅ IG: 'instagram.com/p/ABC/' → ['https://instagram.com/p/ABC/'] (+ reel, http, querystring, múltiples)
✅ preview responsive (width=100%, sin px fijo) ; export mantiene px reales
✅ flyer_fisico_10x14 carga VERTICAL (2000x2800) ; etiqueta sigue HORIZONTAL
✅ build_app + launch real → HTTP 200 ; Gradio carga como API
✅ pytest tests/ → 144 passed, 1 skipped (se mantienen) + 11 nuevos
✅ compileall OK
```

## Cómo aplicar

```bash
flujo airdrop apply "v0.30.1 - fixes editor (IG, preview, orientacion)"
py -m pip install -e .
flujo version            # 0.30.1
flujo serve              # probar: pegar 'instagram.com/p/XXX/' en pestaña INSTAGRAM
py -m pytest tests/ -q   # 155 passed, 1 skipped
```

### Para probar los fixes en el editor
- **IG:** pestaña INSTAGRAM → pegá `instagram.com/p/loquesea/` (sin https) → debe
  detectarlo.
- **Preview/escalado:** pestaña EDITOR → elegí cualquier formato → el preview
  ahora encaja en el panel sin salirse.
- **Orientación:** elegí `evt_flyer_fisico_10x14` → debe verse **vertical**.

## Pendiente / próximos pasos

- Edición visual de posición de elementos (hoy solo título/sub/cuerpo).
- Inferencia IG (productora/fecha/venue/logo) para carteleras.
- Elemento `image` en el generador (pospuesto por decisión del dueño: SVG puro).
- Las plantillas de los formatos verticales que reusan una horizontal podrían
  tener su propio `config.json` dedicado para mejor layout inicial.
