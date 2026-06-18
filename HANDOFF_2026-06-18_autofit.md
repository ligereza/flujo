# 🤝 Handoff 2026-06-18 — flujo v0.30.0 — Auto-fit de texto + avisos IG + acuse de recibo

## Contexto

Seguimos el plan del editor. El dueño decidió **mantener SVG puro** (sin elemento
`image` por ahora), así que este airdrop trae **todo menos image**:

1. **Auto-fit de texto** (la feature grande: "misma medida, distinto texto").
2. **Pestaña INSTAGRAM** en el editor (avisos privado/video/sin links).
3. **Pestaña ACUSE DE RECIBO** (mailto/Gmail prellenado, semiautomático).

## Qué incluye

| Archivo | Cambio |
|---|---|
| `src/flujo/render/autofit.py` | **NUEVO.** Motor de auto-fit puro y testeable. `fit_font_size`, `autofit_element`, `autofit_config`. Independiente del medidor (recibe `measure`). Respeta `locked` y `min_size`. |
| `tools/piezas_vectoriales/scripts/generar_desde_json.py` | `_autofit_size()` nuevo + llamada al inicio de `add_text`. Usa medición **real** (TextPath). |
| `src/flujo/web/svg_preview.py` | `_render_text` aplica autofit (medición aproximada) antes de envolver. |
| `src/flujo/web/editor.py` | Pestañas EDITOR / INSTAGRAM / ACUSE; `analizar_instagram()`, `construir_acuse()`, `_mark_autofit()`; checkbox de autofit; `update_state(..., autofit=)`. |
| `tests/test_autofit.py` | **NUEVO.** 11 tests del motor. |
| `tests/test_web_features.py` | **NUEVO.** 13 tests (IG, acuse, autofit en editor/preview). |
| `docs/AUTOFIT.md` | **NUEVO.** Guía de autofit + locked/min_size. |
| `version.py`, `pyproject.toml`, `README` (changelog) | v0.30.0. |

## Decisiones de diseño

- **Motor de autofit separado del medidor.** `render/autofit.py` recibe una función
  `measure(text, size, weight)`. El generador oficial le pasa la medición exacta
  (matplotlib); el preview, una aproximación. Misma lógica, sin duplicar.
  → preview coherente con el resultado final.
- **`locked` = datos exactos intocables** (gramaje, lote, registro sanitario).
  Aunque tengan `autofit`, nunca se reescalan. `min_size` evita texto ilegible.
- **Acuse de recibo semiautomático:** no se incrusta Gmail (Google lo bloquea en
  iframes); se generan enlaces `mailto:` y de Gmail web prellenados. Un clic abre
  el correo con folio + resumen.
- **Avisos de IG reutilizan** `intake/email_parser.py` (ya detectaba privado/video),
  solo se expusieron en una pestaña.
- **Sin elemento `image`** (decisión del dueño: mantener SVG puro).

## Verificación hecha

```
✅ compileall src/ + generador        → OK
✅ generador real: texto largo 100→50; locked se mantiene en 100
✅ preview aplica autofit (varias líneas)
✅ build_app() con 3 pestañas sin warnings (Gradio 6.x)
✅ launch real → HTTP 200
✅ pytest tests/  → 144 passed, 1 skipped (eran 120; +24)
```

## Cómo aplicar

```bash
flujo airdrop apply "v0.30.0 - autofit + avisos IG + acuse de recibo"
py -m pip install -e .
flujo version            # 0.30.0
flujo serve              # http://127.0.0.1:7860  (3 pestañas)
py -m pytest tests/ -q   # 144 passed, 1 skipped
```

> Este apply ya corre con el 0.29.0 instalado, así que el auto-checkpoint+push
> debería funcionar solo (sin el error de bash). Si ves
> "✓ Checkpoint creado y cambios subidos al servidor", quedó pusheado.

## Cómo usar el auto-fit (dueño)

En el editor, marcá el checkbox "Auto-ajustar texto a la caja". Para datos que
NO deben reescalarse (gramaje, lote), en el `config.json` poné `"locked": true`
en ese elemento. Detalle en `docs/AUTOFIT.md`.

## Próximos pasos

- Elemento `image` en el generador (cuando el dueño quiera; hoy se omite a propósito).
- Edición visual elemento-por-elemento (posicionar) en el editor.
- Inferencia IG (productora/fecha/venue/logo) para carteleras.
- Conectar el acuse de recibo con el intake JSON (folio automático).
