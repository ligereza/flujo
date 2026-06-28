# flujo — Identidad visual central

**Propósito**: Definir y centralizar la identidad visual, tono, reglas de marca y lenguaje estético que debe guiar **todos** los entregables generados con flujo (piezas vectoriales, flyers de eventos, riders, planos, visualizaciones, etc.).

Este es el proyecto "satélite" que actúa como **fuente de verdad** de la identidad "flujo". Los otros proyectos deben poder referenciarlo.

## Estructura recomendada

```
projects/flujo/
├── README.md
├── linea_editorial.md         # Documento principal de la identidad visual
├── flujo.json                 # Versión machine-readable (tokens)
├── ejemplos/                  # Trabajos reales de referencia
├── json/                      # JSONs descriptivos
├── palettes/
├── typography/
├── motifs/
├── references/
└── ...
```

**Importante:**
- Tú cargas trabajos terminados en `ejemplos/`
- El agente que entre analiza y genera (o usa) los JSON descriptivos en `json/`
- Si ya existen JSONs dentro de esta estructura, la carpeta `json/` ya existirá.
- Ver `ejemplos/README.md` y `json/README.md` para instrucciones detalladas + schema.

## Cómo se usa (visión)

1. Una IA externa recibe el repo completo (o esta carpeta + algunos ejemplos) y genera/actualiza `linea_editorial.md` + `flujo.json`.
2. Los motores de flujo (`render/`, `plano/`, etc.) leen `flujo.json` o referencias para aplicar consistencia.
3. Cuando se crea un nuevo proyecto o pieza, se puede pasar `--flujo flujo/` o referenciarlo en el `config.json`.

## Estado actual (2026-06)

- Integrado en hub: `flujo app` → sección Brand / datadrop (manifests ground-truth) + Brand Validator.
- `projects/flujo/flujo.json` + `linea_editorial.md` son fuente de verdad para brand (usados por hub, visualizers, tapiz, etc.).
- Datadrop system produce ground truth manifests (en datadrops/) usables en `projects/flujo/linea_editorial.md` para refinar con ejemplos reales de entregas.
- Dirección a v4.1: datadrops + root `linea_editorial/v4.1.md` (RD rave) integran con identidad base de `flujo/` vía Brand Guardian + parallel delegation.
- El objetivo de esta carpeta es servir como **paquete limpio** para alimentar a otra IA y que extraiga/refine la identidad a partir del trabajo existente en el resto del repo (principalmente `piezas_vectoriales/`, `flyer_eventos/` y `plano/`) + datadrops.

## Instrucciones para la IA que recibirá este repo

Si te están mandando el repositorio `flujo` para que generes la línea editorial:

1. Lee primero `projects/README.md` para entender el ecosistema.
2. Lee `docs/FOR_EXTERNAL_AI.md` (guía específica para este caso de uso).
3. Enfócate en `projects/flujo/` (aquí es donde debe vivir el resultado).
4. Explora patrones estéticos en:
   - `projects/piezas_vectoriales/` (config.json → colores, tipografía, jerarquía, marcos)
   - `projects/flyer_eventos/` (manifiestos + imágenes de referencia)
   - `projects/plano/` (estilo de diagramas, tipografía técnica, uso de color)
   - `projects/tapiz/` (estética visual de "vida del código")
5. Extrae y produce:
   - `linea_editorial.md`
   - `flujo.json`
   - Contenido en `palettes/`, `typography/`, `references/`

No inventes. Basa todo en lo que realmente aparece en el trabajo existente del repo.

## Próximos pasos (integración con cotizaciones/planos)

- Usar flujo en cotizaciones (ya iniciado en projects/cotizaciones/engine.py)
- Mejorar planos para heredar paleta de flujo (hecho en render_svg)
- Agregar ejemplos de cotizaciones a flujo/ejemplos/ para que agentes extraigan
- Integrar formatos infográficos entre flujo y cotizaciones/planos

---

Este proyecto convierte al repo en algo **ocupable** y no solo mejorado internamente. Es el punto de entrada para definir identidad antes de generar más piezas.
