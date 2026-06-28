# Auto-fit de texto ("misma medida, distinto texto")

Resuelve el problema de dos piezas del mismo formato donde una tiene más texto
que otra (p.ej. dos etiquetas 16.5×6.5 cm, una con 5 ingredientes y otra con 20).
En vez de desbordarse, el texto **reduce su tamaño de fuente** hasta entrar.

## Cómo se activa

En un elemento de texto del `config.json`:

```json
{
  "type": "paragraph",
  "content": "INGREDIENTES: ...",
  "x": 120, "y": 600,
  "size": 80,            // tamaño deseado (máximo)
  "max_width": 1800,     // ancho de la caja (obligatorio para autofit)
  "max_height": 400,     // alto disponible (si falta, solo ajusta por ancho)
  "autofit": true,       // activar el ajuste
  "min_size": 36,        // (opcional) no baja de aquí; default 50% del size
  "locked": false        // si true, NUNCA se reescala (ver abajo)
}
```

## Campos `locked` vs `autofit` (clave)

- **`autofit: true`** → texto flexible: encoge para caber (títulos, descripciones).
- **`locked: true`** → texto **exacto que nunca se toca**: gramaje, lote, registro
  sanitario, precio. Aunque tenga `autofit`, si está `locked` se respeta el tamaño.

Así una etiqueta puede encoger la lista de ingredientes pero **jamás** alterar el
"500 g" o el código de lote.

## Dónde actúa

| Lugar | Medición | Uso |
|---|---|---|
| Generador oficial (`generar_desde_json.py::_autofit_size`) | **exacta** (matplotlib TextPath) | SVG de producción |
| Preview del editor (`web/svg_preview.py`) | aproximada (~0.52·size/glifo) | vista rápida en Gradio |
| Motor común (`render/autofit.py`) | recibe la función de medición | lógica compartida y testeable |

La lógica de ajuste es la misma; solo cambia la función `measure`. Por eso el
preview se ve coherente con el resultado final.

## En el editor

La pestaña **EDITOR** tiene un checkbox "Auto-ajustar texto a la caja (autofit)".
Al actualizar, marca `autofit` en los textos con `max_width` (respetando `locked`)
y el preview muestra el tamaño ajustado.

## API (para la siguiente IA)

```python
from flujo.render.autofit import fit_font_size, autofit_element, autofit_config

# tamaño que hace caber un texto:
size, lines = fit_font_size(texto, size=80, max_width=1800, max_height=400)

# ajustar un elemento (devuelve copia):
el2 = autofit_element(el)            # usa medición aproximada por defecto
el2 = autofit_element(el, measure)   # con tu propia función de medición
```
