# Guía para IAs externas que reciben este repositorio

**Lee primero (en orden):**
1. Ejecuta `flujo app` (o abre `context/flujo_hub.html` — workspace principal con visualizadores, intake, UI de delegación a agentes y datos crudos)
2. `context/LAST_HANDOFF.md`
3. `docs/AGENT_OPERATING_MANUAL.md` (incluye modelo de delegación a sub-agentes especializados)

El resto solo si es necesario.

## Orden de lectura recomendado (ahorra tokens)

1. Ejecuta `flujo app` (o abre `context/flujo_hub.html` — hub con visualizadores SVG/Plano, intake de pedidos, sección delegación a agentes especializados + comandos/raw).
2. `context/LAST_HANDOFF.md` (estado actual y tareas).
3. `projects/flujo/` (con sus ejemplos/ y json/ para extraer estética real).
4. Revisa ejemplos reales en los proyectos para entender el flujo texto ↔ imagen.

**No leas todo el código fuente ni todos los handoffs antiguos** al principio. Solo si te piden algo técnico específico.

## Qué extraer típicamente

Cuando te pidan una "línea editorial" o "flujo":

- **Paleta de colores** (nombres internos usados + usos)
- **Tipografía y jerarquía**
- **Principios de composición** (márgenes, ritmos, densidad)
- **Motivos visuales** recurrentes
- **Tono de voz** y lenguaje
- **Reglas por formato** (qué cambia entre flyer impreso, IG, rider, plano)

## Dónde vive la identidad real hoy

La estética actual **no** está centralizada. Está dispersa en:

- Configuraciones de piezas vectoriales (`config.json`)
- Manifiestos y archivos de entrada de eventos reales
- Reglas del generador de planos
- Estilo visual de las herramientas experimentales (tapiz)

Tu trabajo es **sintetizarla** en `projects/flujo/`.

## Estructura que se espera que produzcas

Idealmente genera/actualiza:

- `projects/flujo/linea_editorial.md` (documento humano)
- `projects/flujo/flujo.json` (versión estructurada para código futuro)
- Carpetas `palettes/`, `typography/`, `references/` con contenido real extraído

## Reglas importantes del repo

- No automatizar Photoshop/Illustrator/Blender (solo preparar archivos).
- Solo usar instaloader para Instagram.
- Todo cambio se entrega como airdrop (pero como IA externa probablemente solo generas el contenido de flujo).
- Mantén los archivos generados **útiles y accionables**.

## Mecanismo de ejemplos + JSON descriptivos (para línea editorial)

Si tu tarea es generar/refinar la línea editorial de **flujo**:

1. Ve a `projects/flujo/ejemplos/`
2. Analiza los trabajos reales que el dueño haya cargado allí (carpetas con archivos terminados).
3. Genera JSONs descriptivos en `projects/flujo/json/`.
4. Usa el schema `schemas/example_description.schema.json` como guía de estructura.
5. Con la información de los JSONs + lo que veas en piezas y planos, actualiza:
   - `projects/flujo/linea_editorial.md`
   - `projects/flujo/flujo.json`

Este es el flujo principal para "ocupar" el repo con información real de estética.

## Flujo 1: Pedido Reciente (Operativo)

Te mandaron el repo + un correo o mensaje de WhatsApp/Gmail.

**Pasos obligatorios:**

1. Abre `context/flujo_hub.html` y pega el texto del pedido en la sección "Pedidos".
2. Analiza contra las secciones de formato existentes:
   - Revisa `projects/flujo/` (línea editorial) + `tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json`.
   - Revisa proyectos activos: `piezas_vectoriales/`, `plano/`, `cotizaciones/`, `flyer_eventos/`.
3. **Si hay coincidencia**:
   - Genera estructura ordenada (brief).
   - Propón el comando correcto (ej: `flujo render ... --for illustrator`, `flujo cotizaciones ... --para productora`).
   - Genera archivos listos para Adobe Illustrator, Photoshop o Blender.
   - Usa siempre estilos de flujo.
4. **Si NO hay coincidencia**:
   - Ofrece crear una nueva sección en flujo (o nuevo proyecto satélite).
   - O bien: déjalo como tarea clara de mejora en `LAST_HANDOFF.md` (formato: "Tarea simple: ...").
   - Propón un nombre de formato y estructura mínima.

**Salida esperada (Flujo 1)**:
- Brief o estructura clara (formato YAML/JSON simple).
- Comando listo (`flujo render ... --for illustrator`, `flujo cotizaciones ...`, etc.).
- Archivos generados alineados a flujo.
- Decisión clara: "Usa formato existente X" o "Propongo nueva sección en flujo: [nombre]".
- Nota de herramienta final (Illustrator / Photoshop / Blender).

**Nunca inventes** formatos nuevos sin proponerlos primero.

## Flujo 2: Mejoras al Repo (Evolutivo)

Te mandaron el repo + instrucción de continuar mejoras.

**Pasos obligatorios:**

1. Lee primero:
   - `context/flujo_hub.html` (estado actual de herramientas)
   - `context/LAST_HANDOFF.md` (tareas abiertas + contexto)
   - `proposals/mejoras_herramientas_2026-06.md` (si existe)
2. Identifica mejoras que fortalezcan los dos flujos arriba (especialmente intake manual + matching de formatos).
3. Prioriza:
   - Cosas que hagan más fácil que un agente procese pedidos.
   - Integración más fuerte con Illustrator / Photoshop / Blender.
   - Reducir tokens para agentes (mejor documentación, más estructura).
4. Entrega cambios como si fuera un airdrop (usa la estructura esperada).
5. Actualiza `LAST_HANDOFF.md` con el nuevo estado y tareas pendientes claras.

**Reglas importantes**:
- Mantén el hub como herramienta principal.
- Todo debe ser usable en Windows (`py`).
- Español prioritario.
- Siempre actualiza LAST_HANDOFF al terminar.

## Reglas generales para ambos flujos

- Punto de entrada: siempre `context/flujo_hub.html`.
- Usa las herramientas del repo (`flujo ...`).
- Mantén consistencia con flujo.
- Los archivos finales deben ser directamente usables en Illustrator, Photoshop o Blender.
- Si algo no existe, propón crearlo de forma mínima y accionable.
- Al final, resume qué hiciste y qué tareas simples quedan para otros agentes.

---

---

**Texto listo para copiar cuando mandes el repo a un agente:**

**Opción 1 (Pedido):**
"Revisa mi repo. Este es el correo/mensaje que me llegó recientemente: [PEGAR AQUÍ]

Sigue las instrucciones en docs/FOR_EXTERNAL_AI.md (Flujo 1: Pedido Reciente).
Usa el hub (context/flujo_hub.html) como punto de entrada.
Revisa si calza en formatos existentes (flujo + INDEX_FORMATOS).
Si calza, genera lo necesario. Si no, propone nueva sección o déjalo como tarea clara."

**Opción 2 (Mejoras):**
"Revisa mi repo completo. Continúa con las mejoras.
Sigue las instrucciones en docs/FOR_EXTERNAL_AI.md (Flujo 2: Mejoras al Repo).
Empieza por el hub + LAST_HANDOFF.md.
Prioriza hacer más fácil el Flujo 1 para futuros agentes."

Este archivo existe precisamente para que cuando manden el repo a otra IA, sepa exactamente cómo actuar según el tipo de trabajo.
