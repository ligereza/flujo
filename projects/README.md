# Proyectos satélite de flujo

Este directorio contiene **proyectos experimentales y productivos** que extienden el sistema flujo más allá del núcleo (jobs → piezas vectoriales).

Cada subdirectorio es un "satélite" con su propia lógica, pero que idealmente debería alinearse con la **línea editorial central** (ver `flujo/`).

Workflow actual: usa `flujo app` → hub (jobs + render + datadrop) + parallel delegation. Datadrops generan manifests ground-truth para alimentar `projects/flujo/linea_editorial.md` y v4.1.

## Lista de proyectos

| Proyecto              | Propósito principal                          | Estado          | Tipo          | Referencia principal |
|-----------------------|----------------------------------------------|-----------------|---------------|----------------------|
| `piezas_vectoriales/` | Generación de flyers, etiquetas, riders vectoriales listos para Illustrator/PS | Activo / producción | Vectorial    | `config.json` + `INDEX_FORMATOS.json` |
| `flyer_eventos/`      | Flujos reales de eventos (ingesta IG/correo → análisis → export) | Operativo (con datos reales) | Operación    | Carpetas fechadas con manifest |
| `plano/`              | Generador paramétrico de planos de stands + riders + costos (integrado jobs/render) | Prototipo maduro | Operativo    | `plano_stands.py` + `engine.py` |
| `tapiz/`              | VibeCode: visualización en tiempo real de la generación de código por IA (usa flujo brand) | Integrado (flujo) | Herramienta IA | `vibecode/` package + HTML visualizers |
| `flujo/`           | **Línea editorial / identidad visual central** (paleta, tipografía, motivos, reglas de marca) | Activo (datadrops feed) | Identidad    | `linea_editorial.md` + `flujo.json` + ejemplos/json |
| `cotizaciones/`       | Cotizaciones duales (productora vs ONG/empresa) integradas con flujo + infografías | Integrado | Operativo | Reusa plano + catálogo de formatos |

## Reglas de convivencia

- Todos los proyectos deben poder **consumir** definiciones de `flujo/` (colores, tipografías, estilos de texto, framing, etc.).
- Los proyectos de "producción" (`piezas_vectoriales`, `flyer_eventos`) generan entregables reales.
- Los proyectos "satélite" (`plano`, `tapiz`, `flujo`) exploran nuevas capacidades o centralizan conocimiento.
- **Punto de entrada OBLIGATORIO para todos (dueño + agentes):** ejecuta `flujo app` (o `flujo app --desktop`). Lanza la app real + sirve el hub pro (`context/flujo_hub.html`) como workspace central (intake de pedidos, jobs + render workflow, visualizadores SVG/planos embebidos, delegación paralela a agentes, datadrop, export).

El hub (dentro de `flujo app`) es el workspace central: intake → jobs → visualizadores SVG embebidos por grupos + plano demo interactivo, comandos, sección "Delegar..." para parallel delegation (5 roles especializados: Visual Polish, Pipeline, Brand Guardian, etc.), sección datadrop.

Desde el hub se accede a:
- Visualizador SVG completo (`context/svg_visualizer.html`) — piezas agrupadas Eventos vs Suplementos, embebidas, con "Usar como base".
- Plano Demo (`context/plano_demo.html`) — interactivo, flujo, export.
- Intake, comandos, RAW para agentes, datadrop tools.

Todos los proyectos satélite deben alinearse a `flujo/`.

Cuando una IA reciba el repo, debe empezar por `flujo app` + hub + este archivo + `projects/flujo/`. No leas todo. Usa el hub para ver el estado real de trabajos SVG, planos, jobs y renders. Hub workflow unifica jobs + render.

## Cómo agregar un nuevo proyecto satélite

1. Crear `projects/<nombre>/`
2. Incluir al menos:
   - `README.md` (idea + arquitectura + estado)
   - Estructura clara (ejemplos/, src/ o engine/, assets/)
3. Actualizar este `README.md`
4. Actualizar `docs/REPO_MAP.md`
5. (Ideal) Crear referencia en `flujo/` si afecta identidad visual.

**Export a tus herramientas:**
Usa `flujo render ... --for illustrator|photoshop|blender` o `flujo export ... --for ...` (desde hub o CLI).
Los archivos salen listos para abrir en AI, PS o Blender (con flujo aplicado).

Workflow en hub (`flujo app`): jobs lifecycle (draft → ... → entregado), render integrado, visualizadores embebidos. Teasers de piezas SVG + botones directos al **Visualizador SVG** (`context/svg_visualizer.html`) con previews embebidos por grupo (Eventos / Suplementos) y acciones "Usar como base". Plano demo + datadrop tools también desde hub.

El hub es el centro (workflow jobs+render + parallel delegation). Ver `context/flujo_hub.html` (vía `flujo app`), `context/svg_visualizer.html`, `context/plano_demo.html`, `docs/AGENT_OPERATING_MANUAL.md`.

## Para IAs externas que reciban el repo completo

Si te mandaron este repositorio para extraer información (ej. para crear la línea editorial "flujo"):

- **No leas todo**. Empieza por los archivos de este `projects/README.md` y `projects/flujo/`. Siempre: ejecuta `flujo app` primero → usa hub.
- Busca patrones visuales en:
  - `projects/piezas_vectoriales/*/config.json` (paletas, tipografía, composición)
  - `projects/flyer_eventos/` (manifests + refs/)
  - `projects/plano/` (reglas operativas + SVG output)
  - `projects/tapiz/vibecode/` (estética de visualización de código)
- **Datadrop system (nuevo)**: produce ground truth manifests en `datadrops/<id>/manifest.json` (con `palette`, `ocr_hints`, `visual_traits`, `for_future_ai`). Estos son ejemplos reales de entregas terminadas (fotos subidas → análisis local). Usables directamente en `projects/flujo/linea_editorial.md` (y root `linea_editorial/v4.1.md`) para refinar reglas con datos reales en lugar de specs teóricas. Ver sección datadrop en hub (Herramientas) o `flujo datadrop prepare` (genera _review_package.txt con ground-truth).
- Dirección a integración v4.1: los datadrops alimentan validación de linea_editorial (v4.1 para materiales RD rave/testeo) vs identidad base `projects/flujo/flujo.json`. Brand Guardian valida; usa manifests para cross-check paletas/contrastes reales de entregas vs editorial.
- El núcleo de flujo (`src/flujo/`) define el pipeline, pero la **estética real** vive en estos proyectos + datadrops + hub workflow (jobs + render).

---

## Backlog de refinamiento pendiente

Estas son las ideas y herramientas que aún están en estado incompleto o necesitan pulido para volverse más operativas:

1. **Plano / rider / costos**
   - Refinar constantes reales de montaje y medidas.
   - Añadir reglas operativas más completas al JSON.
   - Preparar un editor visual simple para ajustar plano y rider en vivo.

2. **Cotizaciones duales**
   - Integrar mejor con el mismo fuente de datos del plano.
   - Mejorar la salida para productora vs interno con más claridad visual.
   - Añadir más plantillas y reglas de pricing por alcance.

3. **Tapiz / vibecode spaces**
   - Consolidar la versión base como librería + CLI.
   - Elegir los modos más útiles para uso real en el flujo diario.
   - Definir qué modos son brand-safe y cuáles son exploratorios.

4. **Logo clean lab**
   - Construir un dataset pequeño de pruebas con resultados buenos/malos.
   - Registrar aprendeajes y errores de forma más sistemática.
   - Usar esos ejemplos para refinar el script principal con evidencia.

5. **Herramientas de IA remota / intake**
   - Seguir mejorando prompts, parsing y generación de briefs desde pedidos sueltos.
   - Mantener la flexibilidad de medidas, proporciones y formatos sin rigidizar.

**Objetivo a largo plazo**: Que "flujo" se convierta en la fuente de verdad de identidad visual, y que los otros proyectos (incluyendo nuevos) la consuman de forma declarativa. Dirección futura: integración v4.1 + datadrops para cerrar loop de ground-truth → editorial → generación.
