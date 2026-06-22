# Propuesta de Mejoras de Código - Herramientas flujo

**Fecha:** 2026-06-22
**Enfoque:** Optimizar herramientas para flujo real del diseñador (Windows, intake manual de WhatsApp/Gmail, texto → estructura → imagen).
**Objetivo principal:** Hacer que el hub sea la herramienta #1 de jornada. Reducir fricción en intake manual. Integrar aistetic como fuente única de estilo. Facilitar ayuda de agentes con bajo consumo de tokens.

## Problemas actuales identificados
- Intake manual depende de mocks débiles en JS (hub).
- Cotizaciones y plano usan aistetic de forma básica (strings, no datos reales + render).
- No hay loader central de estilos en Python (duplicación).
- Hub es estático (no carga datos reales de aistetic.json ni ejemplos).
- Herramientas CLI están sueltas; falta orquestación ligera.
- Poca visibilidad de "cómo se ve el estilo aistetic aplicado" en previews.
- Código mixto (mucho inline en HTML, poco reusable).

## Mejoras propuestas (priorizadas por impacto / esfuerzo bajo)

### 1. Crear loader central de aistetic (Python) - Alta prioridad
**Archivo nuevo:** `src/flujo/aistetic.py`

Razones:
- Fuente única de verdad.
- Fácil de usar desde cotizaciones, plano, futuros renders y scripts.
- Agentes pueden inspeccionar estilos sin leer JSON manualmente.
- Windows-friendly.

```python
# src/flujo/aistetic.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

def load_styles() -> Dict[str, Any]:
    """Carga la línea editorial aistetic."""
    path = Path("projects/aistetic/aistetic.json")
    if not path.exists():
        return _default_styles()
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("colors", {}) | data.get("typography", {}) | {"tone": data.get("tone", {})}

def get_color(name: str, default: str = "#000000") -> str:
    return load_styles().get(name, default)

def _default_styles() -> Dict[str, Any]:
    return {
        "ink": "#1f2a24", "accent": "#2d5a4a", "paper": "#f8f1e3",
        "support": "#675f55", "alert": "#c2410f"
    }
```

**Impacto:** Todas las herramientas heredan estilos automáticamente.

### 2. Mejorar cotizaciones para generar archivos reales con aistetic
**Archivo:** `projects/cotizaciones/engine.py`

Mejoras:
- Aceptar parámetro `--output` o generar dos archivos.
- Usar estilos reales (colores + tipografía) para generar HTML simple + texto.
- Soporte para audiencia "productora" (infográfico bonito) vs "interno".

Ejemplo de salida productora:
```html
<div style="background:{{paper}}; color:{{ink}}; border-color:{{accent}}">
  <h1 style="color:{{accent}}">COTIZACIÓN - Reduciendo Daño</h1>
  ...
</div>
```

Añadir:
```python
def generar_archivos(evento_path: Path, audiencia: str, output_dir: Path | None = None):
    ...
    # genera cotizacion_productora.html + cotizacion_interno.txt
```

### 3. Fortalecer el intake manual en el hub (la herramienta más usada)
**Archivo:** `context/flujo_hub.html`

Mejoras concretas de código:
- Mejor parser (regex + reglas simples) que genera YAML válido de brief.
- Botón "Copiar como brief.yaml" (usa Clipboard API).
- Aplicar aistetic en tiempo real al preview generado (colores dinámicos).
- Opción "Enviar a agente" que genera texto listo para copiar:
  "Revisa mi repo. Este correo me llegó:\n\n[paste]\n\nPor favor genera el brief y la cotización usando aistetic."

Añadir sección pequeña:
```html
<button onclick="exportToClipboard()">Copiar brief listo para job</button>
```

Esto reduce pasos manuales y hace el flujo texto → estructura más fluido.

### 4. Loader + aplicación de aistetic en previews del hub
Hacer que el visualizador de texto/JSON use los colores reales de `aistetic.json` (cargarlo vía fetch si es posible en file:// o hardcodear por ahora + botón "Recargar aistetic").

Añadir:
```js
async function loadAistetic() {
  // para uso local: mostrar los valores actuales
  // futuro: integrar con un pequeño servidor o leer del JSON
}
```

### 5. Pequeña mejora en CLI para herramientas
En `src/flujo/cli.py`:

Añadir comando ligero:
```python
@aistetic_app.command("styles")
def aistetic_styles():
    """Muestra la paleta y reglas actuales de aistetic (útil para agentes)."""
    from projects.aistetic import load  # o desde el nuevo loader
    ...
```

También:
- `flujo cotizaciones <evento> --output-dir . --tipo productora`
- Mejorar mensajes de error con notas Windows.

### 6. Estructura para agentes (ahorro de tokens)
- En `context/flujo_hub.html` dejar una sección fija "Cómo ayudar" con instrucciones cortas + link directo a LAST_HANDOFF + ejemplos.
- Actualizar `LAST_HANDOFF.md` automáticamente con sección de "herramientas mejoradas" (o dejar tarea simple para agente).

### Beneficios esperados
- Menos pasos manuales al pegar un correo de WhatsApp/Gmail.
- Estilo consistente (aistetic) en **todas** las salidas sin esfuerzo extra.
- El hub se vuelve realmente la herramienta de entrada (un solo archivo que lo controla todo).
- Agentes pueden contribuir con tareas pequeñas (mejorar el parser JS, agregar más tipos al intake, etc.) sin leer todo el repo.
- Mejor soporte Windows explícito.

### Orden de implementación sugerido (bajo riesgo)
1. Crear `src/flujo/aistetic.py` (loader).
2. Refactor cotizaciones para usar el loader + generar HTML.
3. Mejorar parser + botones en el hub.
4. Actualizar CLI con `aistetic styles` y flags en cotizaciones.
5. Pequeños toques de documentación en el hub.

Esto mantiene el espíritu "dimensiones del orden" y facilita el uso diario + colaboración con agentes.

¿Quieres que implemente alguna de estas mejoras ahora (empezando por la 1 y 3)?
```

This file can be used as a clean proposal document.
