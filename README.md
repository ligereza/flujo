# flujo — Dimensiones del Orden (arte + automatización)

**Punto de entrada diario (OBLIGATORIO y ÚNICO):** `flujo app` (recomendado) o `flujo app --desktop`

Esto lanza **la app real** local: servidor HTTP stdlib + APIs reales (brand, jobs, SVG, parse, delegate, SSE live, tokens) + sirve los HTMLs pro como UI (hub + visualizadores embebidos) + bridge pywebview/desktop.
- **UI real = los tres HTMLs:** `context/flujo_hub.html` (hub principal), `context/svg_visualizer.html`, `context/plano_demo.html`. Cuando corres `flujo app` tienes datos live + acciones reales (jobs, delegate paralelo, etc.). Abrir HTML directo = fallback estático perfecto (sin backend).
- El **hub** (`context/flujo_hub.html` servido por app) es el workspace pro principal (intake + visual + delegación).
- `flujo app --desktop` abre en ventana nativa premium (pywebview + tray opcional).
- `flujo serve --legacy` solo para Gradio antiguo (legacy, opcional).
- Intake, visualización SVG/plano, comandos, export y prompts de delegación listos. `flujo app` = centro diario. Todo apunta al hub + LAST_HANDOFF.

El hub + visualizadores es el **main del flujo**:
- Intake de pedidos (pega email/pedido → brief ordenado + match de formatos)
- `context/svg_visualizer.html` — visualizador embebido real (no links a índices)
- `context/plano_demo.html` — plano interactivo con flujo
- Export directo a Illustrator / Photoshop / Blender
- Separación clara: parte PRO (usuario) + RAW para agentes IA (bajo token)

**Nota de higiene:** La raíz tiene carpetas históricas movidas a `.archive/` (_archive, checkpoints, reference_old, etc.). No uses esos archivos para trabajo actual. Todo lo vivo está en `context/`, `projects/` y `src/`. Ver `.archive/README.md`.

**Estado actual (2026-06):**
- App principal: `flujo app` (o `--desktop`) = entrada única diaria. Sirve backend real (APIs) + los tres HTMLs como UI completa (hub + svg_visualizer + plano_demo).
- Los HTMLs **son la UI de la app real**: con conexión backend detectada ("CONECTADO (APIs reales + delegate)"), live jobs/SVG/brand/SSE, delegate multi-agente, parse real, create-job etc. Fallback estático cuando abres .html directo.
- Workspace pro: usa `flujo app` → hub (intake + visual SVG/plano embebidos por grupos), abre `svg_visualizer.html` y `plano_demo.html` desde el hub.
- Agentes: LAST_HANDOFF + AGENT_OPERATING_MANUAL (delegación paralela a 5 roles especializados incl. Packaging). Siempre `flujo app` primero.
- Visualizadores reales (embebidos) para SVG y planos.
- Todo alineado a flujo + export AI/PS/Blender. Fuente de verdad diaria: hub (vía app) + LAST_HANDOFF.
- Root hygiene ejecutado: histórico movido a `.archive/`.
- Caches fully cleaned (2026-06-22): 16 __pycache__ dirs + 123 *.pyc + .pytest_cache removed (only generated). Improves `flujo app` startup + hub nav + IA resumption.
- Delegación agentes completada (2026-06-22, restart + refresh): UI de `flujo app` optimizada (tabs para no todo en página principal; Brand consolidado a 1 solo botón + modal); plano_demo arreglado (recalcular reactivo + lógica real de stands/mesas desde engine); datadrop (airdrop inverso) listo para subir fotos reales de flyers/etiquetas terminados (manifests con for_future_ai para que IA "sepa qué buscar"); linea editorial v4 → v4.1.md con §10 validación datadrops + integración. Supervisor + scheduler cada 3min para evitar pérdida contexto/repetitions. Join datadrop + linea pendiente de uploads reales.
- Docs consolidadas: `flujo app` + hub como centro. Gradio = legacy.

**Dos flujos de trabajo para agentes:**
1. Repo + pedido reciente → pega en hub → match o proponer nueva sección/tarea
2. Repo + "continúa con las mejoras" → lee LAST_HANDOFF + AGENT_OPERATING_MANUAL → 1-2 tareas → actualiza handoff

**SVG:** cada pieza tiene visualizador real (embedded) + botones "Usar como base", "Editar editable", "Vectorizado". No uses los índices de carpeta.

**Proyectos** alineados a flujo (la fuente de verdad de paleta, tono y reglas).

Ver también: ejecuta `flujo app` (entrada diaria) → usa hub como workspace principal. `context/flujo_hub.html`, `context/svg_visualizer.html`, `context/plano_demo.html`, `projects/README.md`, `context/LAST_HANDOFF.md`, `docs/AGENT_OPERATING_MANUAL.md`. **Hub + LAST_HANDOFF = fuente de verdad para continuar.**

Windows: `py -m flujo ...` | Español prioritario.

---

## 📖 Índice

1. [Para quién es este README](#-para-quién-es-este-readme)
2. [Qué es flujo y para qué sirve](#-qué-es-flujo-y-para-qué-sirve)
3. [Cómo trabaja otra IA aquí (LECTURA OBLIGATORIA)](#-cómo-trabaja-otra-ia-aquí-lectura-obligatoria)
4. [El sistema de Airdrops (cómo se entregan mejoras)](#-el-sistema-de-airdrops-cómo-se-entregan-mejoras)
5. [Quick start](#-quick-start)
6. [El pipeline: de pedido a pieza](#-el-pipeline-de-pedido-a-pieza)
7. [Intake por JSON (para colegas)](#-intake-por-json-para-colegas)
8. [Catálogo de formatos](#-catálogo-de-formatos)
9. [La app (nueva realidad)](#-la-app-nueva-realidad-hub-pro-como-workspace-principal)
10. [Delegating to Specialized Agents](#-delegating-to-specialized-agents)
11. [Reglas innegociables](#-reglas-innegociables)
12. [Estructura del repo](#-estructura-del-repo)
13. [Referencia de comandos CLI](#-referencia-de-comandos-cli)

---

## 👤 Para quién es este README

Este repo lo usan **dos tipos de operador**:

- **El dueño (humano):** recibe pedidos de diseño de jefes/clientes/colegas y
  los produce. Trabaja en Windows con Git Bash (`py` como intérprete).
- **Agentes de IA (tú, si estás leyendo esto):** ayudan a mejorar el código,
  procesar pedidos, y mantener el sistema. **No tienes acceso de escritura
  directa al repo**: entregas tu trabajo como un **airdrop** (ver más abajo).

Si eres una IA y quieres **ahorrar tokens** para continuar trabajo:
1. Lee `PARA_IA_CONTEXT.md`
2. Lee **`context/LAST_HANDOFF.md`** (esto es lo más importante)
3. Ejecuta `flujo handoff`, `flujo daily` y `flujo job next`

Solo si necesitas más detalle, lee la sección completa [Cómo trabaja otra IA aquí](#-cómo-trabaja-otra-ia-aquí-lectura-obligatoria).

---

## 🎯 Qué es flujo y para qué sirve

El dueño es diseñador. Recibe pedidos por correo / WhatsApp / Instagram y debe:
acusar recibo, entender qué se pide, definir formato y medidas, producir el
arte y entregarlo. **flujo automatiza todo lo que rodea al diseño manual** para
que el dueño pueda:

- **Recibir un pedido aunque esté ausente** y que quede registrado y ordenado.
- **No perder información** (medidas, productos, links, datos sensibles).
- **Arrancar el proyecto** con la plantilla y medidas correctas, listo para
  abrir en Illustrator/Photoshop.

> **Lo que flujo NO hace:** no automatiza Photoshop / Illustrator / Blender.
> El diseño fino es manual. flujo prepara, ordena, valida y entrega el andamiaje.

**Pipeline mental:**

```
Pedido (correo / mensaje / JSON)
   → Privacy scan (PII)
   → Brief (qué, medidas, formato, productos)
   → Job (carpeta de trabajo con estado)
   → Proyecto (config.json + plantilla de formato)
   → Render (SVG/preview) → Export (ZIP para PS/AI)
```

---

## 🤖 Cómo trabaja otra IA aquí (LECTURA OBLIGATORIA)

Si eres una IA mejorando este repo, este es **exactamente** tu protocolo:

### 1. Entiende antes de tocar
Ejecuta `flujo app` (o abre `context/flujo_hub.html`).
Luego lee `PARA_IA_CONTEXT.md` + `context/LAST_HANDOFF.md` + `docs/AGENT_OPERATING_MANUAL.md`.
Clona el repo y corre `py -m pytest tests/ -q` y `flujo health`
para conocer el estado real. La app (`flujo app`) + hub + visualizadores + UI delegación son la fuente actualizada.

### 2. Trabaja en tu propio clon, no en el repo del dueño
Haces tus cambios, los **pruebas** (`pytest`, `compileall`, prueba manual de
los comandos afectados).

### 3. Entrega TODO como un airdrop dentro de un ZIP
El dueño NO te da push. Tu único canal de entrega es un **ZIP** que contiene
una carpeta `_airdrop/` que **replica la estructura del repo**. Reglas:

- **Cada archivo que crees, modifiques o quieras reemplazar** va dentro de
  `_airdrop/` en su ruta final. Ej: si arreglas `src/flujo/cli.py`, lo pones en
  `_airdrop/src/flujo/cli.py`.
- **Sin subcarpetas de versión.** No uses `_airdrop/v0.24/...`. El diseño es
  "drop directo": `_airdrop/<ruta exacta en el repo>`.
- **Incluye SIEMPRE un documento de handoff** (`_airdrop/HANDOFF_<fecha>.md` o
  `HOTFIX_<fecha>.md`) explicando: qué arreglaste, por qué, cómo probarlo, y
  qué deuda queda. Es lo que permite a la **siguiente** IA continuar.
- **Actualiza la doc relevante** (este README, changelog en `version.py`,
  `PARA_IA_CONTEXT.md`) dentro del mismo airdrop.
- **Bump de versión** en `src/flujo/version.py` Y `pyproject.toml` (deben
  coincidir). Agrega entrada al changelog en `version.py`.
- Entrega el resultado como **un ZIP**, ubicado en una carpeta `_airdrop/`
  (ej. `_airdrop/airdrop_<fecha>.zip`). El dueño lo descomprime en la raíz.

### 4. El dueño aplica tu airdrop así
```bash
# opción A (manual, siempre funciona):
bash scripts/apply_airdrop.sh --dry-run   # ver qué cambiaría
bash scripts/apply_airdrop.sh --apply     # copiar + backup
bash scripts/checkpoint.sh "mensaje"      # commit + push (en UNA corrida)

# opción B (integrado en la CLI):
flujo airdrop apply "mensaje"             # backup → apply → checkpoint → push
```

### 5. Qué NO hacer
- ❌ No uses `yt-dlp` (solo `instaloader` para Instagram).
- ❌ No crees venvs pesados ni dependencias nuevas sin justificarlo.
- ❌ No mandes datos a IAs externas sin pasar `flujo privacy` primero.
- ❌ No borres archivos por las malas: el airdrop solo COPIA. Para limpiar usa
  `scripts/cleanup_safe.sh` (mueve a `_archive/`, reversible).
- ❌ No dejes mensajes de commit vacíos ni placeholder.

> **Checklist de calidad antes de entregar un airdrop**
> `compileall` OK · `pytest` verde · comando afectado probado a mano ·
> versión bumpeada y sincronizada · handoff escrito · doc actualizada.

---

## 📦 El sistema de Airdrops (cómo se entregan mejoras)

El "airdrop" es el mecanismo central de colaboración. Resuelve: *"una IA no
tiene push, ¿cómo le hace llegar cambios al repo de forma segura y trazable?"*

### Validación local antes de aplicar

Antes de aplicar cualquier airdrop externo, usar:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion"

# Solo si el airdrop toca src/flujo/airdrop.py y ya fue revisado explícitamente:
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion" --allow-airdrop-engine
```

Esto evita ZIPs vacíos, archivos generados, rutas deformadas por Markdown y checkpoints con pruebas fallidas. Desde v0.34.8, `flujo airdrop apply` también valida antes de aplicar (usa `--allow-airdrop-engine` solo si revisaste cambios al motor). Ver `docs/AIRDROP_REVIEW.md` y `docs/AGENT_AIRDROP_PROTOCOL.md`.

### Cómo funciona el motor (`src/flujo/airdrop.py`)
1. **Escanea** `_airdrop/` recursivamente (ignora `.gitkeep`, dotfiles).
2. Para cada archivo, calcula su **destino** = misma ruta relativa en la raíz.
   Marca `NEW` (no existe) o `REPLACE` (ya existe).
3. Al **aplicar**: escribe un manifest en `_airdrop_backups/<timestamp>/`,
   hace **backup** de cada `REPLACE`, copia cada archivo a su destino y da
   permiso de ejecución a los `.sh`.
4. Dispara **auto-checkpoint** (commit + push) si se usó `flujo airdrop apply`.
5. **Rollback**: `flujo airdrop rollback` usa el manifest para restaurar
   archivos `REPLACE` y eliminar archivos `NEW` creados por el airdrop.

> Las rutas se normalizan con `/` (`rel.as_posix()`) para que funcione igual en
> Windows y Linux/macOS.

### Anatomía de un ZIP de airdrop bien hecho
```
airdrop_2026-06-18.zip
└── _airdrop/
    ├── HANDOFF_2026-06-18.md        # contexto para la próxima IA (OBLIGATORIO)
    ├── README.md                    # doc actualizada (si aplica)
    ├── pyproject.toml               # versión bumpeada (si aplica)
    ├── src/flujo/
    │   ├── cli.py                   # archivo modificado, ruta exacta
    │   └── version.py               # versión + changelog
    ├── tests/
    │   └── test_xxx.py              # tests nuevos/actualizados
    └── scripts/
        └── algo.sh                  # scripts nuevos
```

`_airdrop/` y `_airdrop_backups/` están en `.gitignore`: **no se commitean**.
Solo se commitea el resultado de aplicarlos (los archivos en sus rutas reales).

---

## 🚀 Quick start

```bash
py -m pip install -e .
flujo health
flujo version

# ENTRADA DIARIA OBLIGATORIA (ÚNICA): `flujo app` (o `flujo app --desktop`)
# Lanza la app real: backend + APIs reales + sirve los tres HTMLs como UI (hub pro + visualizadores).
# - Intake real + match formatos + crear jobs
# - Visualizadores embebidos SVG (por grupos) + plano
# - Comandos live, tokens export, SSE live updates
# - Delegación multi-agente paralela (5 roles incl. Packaging): ingresa tarea en hub, copia prompts completos listos o usa "Delegar seleccionados (live API)"
# (Todo gratis/local-first. `flujo app` + hub = centro. Fallback: abre context/flujo_hub.html directo.)

# Intake manual (recomendado):
# Ejecuta `flujo app`, pega correo/pedido en hub → brief + match formato + acción

# Ejemplos CLI
flujo job new "etiquetas acme" --email inbox/correo.txt
flujo job prepare jobs/...
flujo job activate jobs/...
flujo render run projects/piezas_vectoriales/<proyecto>/config.json --for illustrator|blender
flujo cotizaciones <json> --para productora
flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider --costs
flujo daily
```

---

## 🖥️ El Hub (pro workspace dentro de la app `flujo app` — UI principal)

`flujo app` (o --desktop) lanza el backend real + sirve los tres HTMLs como UI de la app (flujo_hub.html + visualizers embebidos). El hub (`context/flujo_hub.html`) es el workspace pro diario (intake, visual, delegación, comandos). Cuando app activa: live APIs. HTMLs directos: fallback estático completo. Brand = 'flujo' (projects/flujo/flujo.json).

- **Status + nav**: enlaces directos a `svg_visualizer.html` y `plano_demo.html`
- **Intake pro**: caja para pegar pedido. Genera brief estructurado + match contra formatos reales (svg + catálogos) + comando listo + decisión (MATCH / NUEVO).
- **SVG Works teaser + visual**: tarjetas por grupos (Eventos/Flyers/Riders vs Suplementos) con previews. Botón principal abre el visualizador completo con `<object>` embebido, botones "Usar como base", "Editar", "Vectorizado" y notas de mejoras por sección.
- **Plano teaser**: link al plano_demo interactivo (genera SVG paramétrico + rider + costos en vivo, flujo integrado).
- **Herramientas**: grid de comandos (copy-paste directo). Siempre con `py` en Windows.
- **Delegación integrada** (first-class): sección "Delegar a Agentes Especializados" con guía práctica "Cómo delegar desde el hub", tarea editable, 5 roles (incl. Packaging), botones copiar prompts completos + multi "Delegar seleccionados (live API)".
- **Separación usuario / agente**: arriba workspace pro; abajo RAW + datos para agentes (bajo token).
- **Export bridge**: secciones para AI / PS / Blender + comandos + tokens.

**Visualizadores dedicados (conectados, accesibles desde app/hub):**
- `context/svg_visualizer.html` — visualizador completo de todas las piezas de `/svg`. Agrupado exactamente como las carpetas. Cada trabajo tiene preview embebido + acciones.
- `context/plano_demo.html` — demo mejorado del motor de planos: controles, SVG vivo, rider, costos, simulación Blender.

Nunca más links directos a carpetas que devuelven index feos. Todo tiene visual + acción inmediata.

**Cómo usar la nueva app (guía corta):**
1. **`flujo app`** (o `--desktop` para nativa sin browser/terminal).
2. Hub pro aparece (HTMLs servidos + APIs activas o fallback estático).
3. Intake → brief + match (real o local).
4. Abre visualizadores embebidos (SVG/plano) desde hub.
5. Comandos + export tokens (live cuando app activa).
6. **Delegación:** usa sección "Delegar a Agentes Especializados" (tarea + 5 roles con prompts completos copiables y live paralelo). Lanza en clones.
7. Para parar: Ctrl+C. Todo local-first y gratis.

(Directo HTML = fallback útil. `flujo app` = APIs + delegación + live.)

---

## 🔄 El pipeline: de pedido a pieza

```
                 ┌─────────────────────────────────────────────┐
   PEDIDO  ──►   │ inbox/correo.txt   o   intake JSON (colegas) │
                 └───────────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────▼─────────────────────┐
   PRIVACY  ──►  │ flujo privacy scan → riesgo bajo/medio/alto  │
                 │ (PII: email, RUT, teléfono, tarjeta, dirección)│
                 └───────────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────▼─────────────────────┐
   BRIEF    ──►  │ brief.yaml: tipo_pieza, medidas, productos,  │
                 │ entrega, restricciones, pendientes           │
                 └───────────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────▼─────────────────────┐
   JOB      ──►  │ jobs/YYYY-MM-DD_slug/ con estado (lifecycle) │
                 │ borrador → brief_extraido → listo → en_diseno│
                 │ → generado → entregado                       │
                 └───────────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────▼─────────────────────┐
   PROYECTO ──►  │ projects/piezas_vectoriales/<slug>/config.json│
                 │ (elige plantilla de formato por medida/tipo) │
                 └───────────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────▼─────────────────────┐
   RENDER   ──►  │ SVG / preview  →  export ZIP para PS/AI      │
                 └─────────────────────────────────────────────┘
```

**Estados del job** (`EstadoJob` en `src/flujo/jobs/brief.py`):
`borrador → brief_extraido_pendiente_revision → pendiente_datos →
listo_para_disenar → en_diseno → generado → entregado`
(+ `pausado`, `cancelado`). Las transiciones válidas están codificadas en
`TRANSICIONES_VALIDAS`.

---

## 📨 Intake por JSON (para colegas)

**Objetivo:** que jefes/colegas entreguen los pedidos en un **JSON estructurado**
en vez de texto libre. Así el sistema sabe exactamente el formato, medidas y
contenido sin adivinar, y el dueño se independiza de responder mensajes.

👉 **La especificación completa, el esquema validable y los ejemplos por formato
están en [`docs/INTAKE_JSON.md`](docs/INTAKE_JSON.md) y en `schemas/`.**

### Idea en 30 segundos
Un colega llena un JSON como este y lo manda (correo adjunto, o lo deja en
`inbox/`):

```json
{
  "intake_version": "1.0",
  "pedido": {
    "id_externo": "WA-2026-06-18-001",
    "solicitante": { "nombre": "Juan", "canal": "whatsapp" },
    "tipo_pieza": "etiqueta",
    "formato_sugerido": "etiqueta_horizontal_165x65",
    "medidas": { "ancho_cm": 16.5, "alto_cm": 6.5, "orientacion": "horizontal" },
    "productos": ["Miel orgánica 500g"],
    "contenido": {
      "titulo": "MIEL ORGÁNICA",
      "subtitulo": "Cosecha 2026",
      "cuerpo": "Producto natural de la cordillera.",
      "extras": { "lote": "L-2026-06", "qr": "https://..." }
    },
    "entrega": { "formatos": ["editable_svg", "vectorizado_svg", "zip"], "fecha_limite": "2026-06-25" },
    "notas": "Usar tonos tierra. No inventar claims de salud."
  }
}
```

flujo lo recibe, **acusa recibo automáticamente**, lo valida contra el esquema,
escanea PII, crea el brief + job, y elige la plantilla de formato. El dueño solo
revisa y diseña.

> **Estado:** la estructura JSON está **definida y documentada** (este airdrop).
> El comando `flujo intake json <archivo>` que la consume end-to-end es el
> **siguiente paso de implementación** (ver roadmap en `docs/INTAKE_JSON.md`).
> Hoy ya existe el intake desde texto: `flujo job new --email`.

---

## 🎨 Catálogo de formatos

Los formatos viven en `tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json`
(schema v2.0). Cada uno define **medida real (cm)**, **canvas (px)**, **área**
(eventos/suplementos), **medio** (impresión/digital) y **herramienta**
(Illustrator/Photoshop/Blender). Consúltalos con `flujo render formats`.

> **Catálogo completo y explicado en [`docs/CATALOGO_FORMATOS.md`](docs/CATALOGO_FORMATOS.md).**

**Regla de oro:** Illustrator = impresión real · Photoshop = digital · Blender =
recursos (frasco) y export de carteleras.

```bash
flujo render formats                 # todos (12)
flujo render formats -a eventos      # por área
flujo render formats -m impresion    # solo lo que va a Illustrator
flujo render formats --herramienta blender   # carteleras
```

| área | id | medida | medio · herramienta |
|---|---|---|---|
| eventos | `evt_flyer_fisico_10x14` | 10×14 cm | impresión · Illustrator |
| eventos | `evt_cartelera_individual_1080x1920` | 1080×1920 | digital · Photoshop+Blender |
| eventos | `evt_cartelera_triple_1080x1920` | 1080×1920 | digital · Photoshop+Blender |
| eventos | `evt_post_ig_1080x1350` | 1080×1350 | digital · Photoshop |
| eventos | `evt_brief_productora_pdf_universal` | A4 univ. | impresión · Illustrator |
| eventos | `evt_historia_flexible_1080x1920` | 1080×1920 | digital · Photoshop |
| eventos | `rider_eventos_a4_horizontal` | 29.7×21 cm | impresión · Illustrator |
| suplementos | `sup_etiqueta_165x65` | 16.5×6.5 cm | impresión · Illustrator |
| suplementos | `sup_etiqueta_140x100` | 14×10 cm | impresión · Illustrator |
| suplementos | `sup_flyer_informativo_a5` | 14.8×21 cm | impresión · Illustrator |
| suplementos | `sup_pendon_rectangular` | paramétrico | impresión · Illustrator |
| suplementos | `sup_bandera_poligonal` | paramétrico | impresión · Illustrator |

> **Sugerencia automática:** `flujo render formats -w 16.5 -h 6.5 -t etiqueta`
> puntúa por proporción + cercanía de medida + tipo y devuelve el mejor match.
> Los **paramétricos** (pendones/banderas) definen su medida en cada pedido.

**Cómo se compone una pieza** (estructura de `config.json`):
- `project`: nombre, slug, marca, web, nota.
- `canvas`: `width`/`height` (px), `real_size_cm`, `safe_margin_px`.
- `palette`: colores con nombre (`ink`, `accent`, `paper`...).
- `background`: color de fondo (nombre de la paleta).
- `global_elements`: elementos repetidos en todos los documentos (marco, marca).
- `documents[]`: cada documento tiene `id`, `title` y `elements[]`
  (`text`, `paragraph`, `rect`, `panel`, ...) con coordenadas, tamaño y color.

La estructura JSON específica que debe entregar un colega por cada tipo de
pieza está en [`docs/INTAKE_JSON.md`](docs/INTAKE_JSON.md).

---

## 🌐 La app (nueva realidad: `flujo app` como entrada diaria única + UI real = HTMLs + backend)

**Entrada diaria clara y obligatoria (única recomendada):** `flujo app` (o `flujo app --desktop`).

Lanza **la app real**: servidor Python (stdlib) + APIs reales + sirve los tres HTMLs de context/ como UI pro completa + bridge pywebview (desktop nativo, tray, JS↔Python directo).

**Los tres HTMLs = la UI de la app real:**
- `context/flujo_hub.html` — hub principal (intake, visual teaser, comandos, delegación).
- `context/svg_visualizer.html` — visualizador embebido real de todas las piezas SVG por grupos exactos de /svg.
- `context/plano_demo.html` — demo interactivo del motor de planos + rider + costos.

Cuando `flujo app` corre: UI detecta backend → "CONECTADO (APIs reales + delegate)", carga brand/SVG/jobs live, permite crear jobs reales, delegate paralelo, SSE.
Abrir cualquiera de los .html directo: funciona 100% (fallback estático, datos mock/local).

Arquitectura:
- UI = HTMLs pro dark brand-enforced (de projects/flujo/flujo.json).
- Backend ligero (src/flujo/web/hub.py): /api/ping, /api/load-flujo-brand, /api/list-svg-works, /api/list-jobs, /api/parse-real-pedido, /api/run-safe-command, /api/create-job-draft, /api/delegate (5 roles), /api/events (SSE), /api/export-tokens, PWA on-the-fly.
- Desktop y packaging gratis: `flujo package` → .exe (PyInstaller + icon + launcher desktop).
- Fallback estático perfecto.

El hub (`context/flujo_hub.html` servido) es el workspace pro principal diario.

- `flujo serve --legacy`: solo Gradio antiguo (legacy).
- Todo free, local-first, Windows-first (`py`).

### Cómo usar la app (guía corta — usa el hub)
1. `py -m pip install -e .` (una vez).
2. **`flujo app`** (o `flujo app --desktop`) — **entrada diaria única obligatoria**.
3. Hub aparece (con backend APIs live o fallback estático perfecto).
4. **Intake rápido:** pega pedido en hub → "Generar brief ordenado + match" (real vía API o local) → copia + acción.
5. Abre visualizadores embebidos **desde hub**: SVG (por grupos exactos) + Plano demo.
6. Herramientas: botones copy (usa `py -m flujo ...` en Windows). Live cmds vía app.
7. **Delegación multi-agente paralela (5 roles):** sección "Delegar a Agentes Especializados" en el hub. Ingresa tarea → copia prompt completo por rol o usa multi-select + "Delegar seleccionados (live API)". Lanza cada uno en clon git separado. Roles: Visual Polish, Pipeline & Integration, Brand Guardian, Future/Modern, **Packaging & Distribution**.
8. Exporta con render/extract.
9. Para parar: Ctrl+C. 100% local/gratis.

**Siempre:** `flujo app` primero + lee hub + LAST_HANDOFF. Recepción auto es futuro. Intake hoy vía hub o `flujo job new --email`.

### Plan recomendado (para "recibir aunque esté ausente")
La arquitectura objetivo separa **recepción** de **operación** (igual que antes, JSON como contrato):

```
   Colega/Jefe                 RECEPCIÓN (24/7)            OPERACIÓN
 ┌─────────────┐         ┌───────────────────────┐     ┌──────────────┐
 │ Correo +    │  ──►    │ Webhook / poll buzón   │ ──► │ inbox/*.json │
 │ JSON adjunto│         │  · valida esquema      │     │ + brief+job  │
 │  o formulario│        │  · ACUSA RECIBO (auto) │     │  creados     │
 └─────────────┘         │  · privacy scan        │     └──────┬───────┘
                         └───────────────────────┘            │
                                                        ┌──────▼───────┐
                                                        │ dueño revisa │
                                                        │ y diseña     │
                                                        └──────────────┘
```

Opciones técnicas (a decidir; ninguna implementada aún):
- **Correo (recomendado para empezar):** poller IMAP...
- **Formulario web + API**...
- **Webhook de WhatsApp/Telegram**...

> **Decisión pendiente.** El contrato JSON ya está fijado (ver `docs/INTAKE_JSON.md`). La app actual prepara el terreno.

---

## 🤝 Delegating to Specialized Agents

**Modelo formal de delegación multi-agente (paralelo real en clones git separados).**

Principal (dueño o IA) divide trabajo y lanza sub-agentes en **clones git independientes** (nunca escribir directo en repo principal).

Cada sub-agente:
- **Obligatorio:** ejecuta `flujo app` (o `--desktop`) como entrada diaria única.
- Lee `context/LAST_HANDOFF.md` + `docs/AGENT_OPERATING_MANUAL.md`.
- Usa el **hub** (dentro de la app) para intake/visual + delegación.
- Entrega **su propio airdrop** independiente (con handoff propio).

El principal integra airdrops + actualiza LAST_HANDOFF central. **Siempre referencia hub + LAST_HANDOFF como fuente.**

**Coordinación (estricta):**
- Visual Polish revisa **todos** outputs visuales finales.
- Brand Guardian valida **antes** de tocar `projects/flujo/flujo.json` o linea editorial.
- Packaging & Distribution coordina con Pipeline en paths, assets y launchers.
- Future/Modern **nunca** toca core sin aprobación explícita Pipeline+Brand en su handoff.

**Roles actuales (5 — nombres exactos):**
- **Visual Polish Agent**: Pulido visual total + brand enforcement en todos los HTMLs, SVGs, previews, tapiz. Fuente única: `projects/flujo/flujo.json` + linea_editorial.md. Dark pro premium.
- **Pipeline & Integration Agent**: CLI, jobs, intake, render, airdrop, hub backend (SSE, delegate, tokens), tests. Dueño de que `flujo app` sea sólido.
- **Brand Guardian**: Custodio de `projects/flujo/` (flujo.json, linea_editorial, paletas). Valida todo lo que tocan los demás.
- **Future/Modern Agent**: Nuevas integraciones (webhooks, tokens, live extendido, etc.). Prototipos solo; no core sin revisión.
- **Packaging & Distribution Agent**: `flujo package` + PyInstaller (gratis), pywebview desktop, bundling de assets (context/svg/brand), paths frozen, launcher onefile/onedir, icono, tray, hints Inno Setup. Coordina con Pipeline/Brand.

**Cómo delegar desde el hub (método recomendado diario — usa dentro de `flujo app`):**
1. `flujo app` (o `--desktop`) — abre el workspace pro (UI HTMLs + backend APIs).
2. Baja a sección **"Delegar a Agentes Especializados"** (incluye guía práctica copyable para humano/IA).
3. Ingresa la tarea (usa botones de ejemplo o edita).
4. Selecciona múltiples roles (checkboxes = paralelo real) y pulsa "Copiar prompt completo" o "Delegar seleccionados (live API)".
5. Pega prompts en clones separados. Cada sub-agente: `flujo app` + LAST_HANDOFF primero.
6. (CLI): `flujo delegate packaging "mejorar..."` (usa templates idénticos).

Prompts listos-para-copiar (5 templates de alta calidad, incl Packaging) + modelo completo: **docs/AGENT_OPERATING_MANUAL.md**. Templates centralizados en hub.py y sincronizados con flujo_hub.html.

Todo alineado al estado actual: los tres HTMLs = UI de la app real con backend. Brand = 'flujo'. App = gratis/local-first. **Fuente de verdad: `flujo app` → hub + context/LAST_HANDOFF.md**.

---

## 🔒 Reglas innegociables

1. **Instagram:** descargas SOLO con `instaloader`. Prohibido `yt-dlp`.
2. **Entorno:** sin venvs pesados; usar `py` (Windows) / `python3` (Linux/mac).
3. **Privacidad primero:** `flujo privacy scan/sanitize` antes de enviar texto a
   IAs externas.
4. **No automatizar** Photoshop / Illustrator / Blender.
5. **Checkpoints:** cada avance se registra (commit + push). Sin mensajes vacíos.
6. **Borrado:** nunca destructivo a mano; usar `scripts/cleanup_safe.sh`.
7. **Lógica nueva** → como módulo en `src/flujo/` **con tests**.

---

## Entender el repo rápido

Lee primero:
- Ejecuta `flujo app` (entrada diaria) / abre `context/flujo_hub.html` (pro workspace)
- `projects/README.md`

El resto (código, docs, herramientas) soporta el flujo texto → imagen. Ver `docs/REPO_MAP.md` solo si necesitas profundidad.

## 🗂️ Estructura del repo

```
src/flujo/        # paquete Python (CLI + módulos)
  cli.py          # CLI unificada Typer (20+ comandos)
  airdrop.py      # motor de airdrops (apply/rollback/checkpoint)
  version.py      # versión + changelog (FUENTE DE VERDAD de la versión)
  paths.py        # resolución de rutas del repo
  jobs/           # lifecycle de jobs + modelo Brief
  privacy/        # escaneo y sanitización de PII
  render/         # formatos + render de piezas vectoriales
  intake/         # parseo de correos + pipeline
  flyer/          # importación de flyers desde Instagram
  analyze/        # colores dominantes + OCR
  export/         # ZIP + scripts JSX para PS/AI
  index/          # índice SQLite de flyers
  ig/             # descarga Instagram (instaloader)
  dashboard/      # reporte diario con scoring
  templates/      # plantillas base de jobs + JSX
tools/piezas_vectoriales/plantillas/   # INDEX_FORMATOS.json + config.json base
scripts/          # utilidades: checkpoint.sh, apply_airdrop.sh, app.py (legacy Gradio), cleanup_safe.sh
# (app principal ahora en src/flujo/web/hub.py + CLI `flujo app`)
tests/            # pytest (69+ tests)
docs/             # documentación detallada (CLI, formatos, intake JSON, etc.)
schemas/          # esquema JSON de intake + ejemplos
jobs/             # trabajos creativos (gitignored, salvo _template)
projects/         # proyectos satélite (piezas_vectoriales, flyer_eventos, plano, tapiz, flujo)
inbox/            # bandeja de entrada de pedidos
context/          # reportes diarios / estado
_airdrop/         # (gitignored) zona de aterrizaje de airdrops
_airdrop_backups/ # (gitignored) backups automáticos al aplicar airdrops
_archive/         # material legacy archivado (reversible)
```

---

## 🛠️ Referencia de comandos CLI

```bash
flujo health                  # chequeo general
flujo version                 # versión y changelog
flujo init                    # inicializa estructura de carpetas

# Jobs (pedidos de diseño)
flujo job new "<nombre>" --email inbox/correo.txt
flujo job prepare jobs/<job>  # privacy → brief → estado
flujo job list                # listar jobs y estados
flujo job status <path>       # estado de un job
flujo job next                # próximas acciones sugeridas
flujo job activate jobs/<job> # brief → proyecto
flujo job report <path>       # reporte detallado

# Brief
flujo brief extract <job>
flujo brief to-project <brief.yaml>
flujo brief show <brief.yaml>

# Privacidad
flujo privacy scan <archivo>
flujo privacy sanitize <archivo> --out <salida>
flujo privacy check <job>

# Render / formatos
flujo render formats                       # listar plantillas
flujo render formats -w 16.5 -h 6.5 -t etiqueta   # sugerir
flujo render validate <config.json>
flujo render run <config.json>
flujo render rescale <config.json> --dpi 300        # subir resolución (anti-pixelado)
flujo render rescale <config.json> -w 14 -h 10      # cambiar proporción/medida

# Flyers desde Instagram (legacy - usa el hub para intake moderno)
flujo flyer-import <correo.txt>
flujo flyer-list
flujo ig-redownload [--all]
flujo analyze [--all] [--force-ocr]
flujo export <proyecto>
flujo index [--rebuild | --duplicates]

**Nota:** Para uso diario se recomienda el intake desde `context/flujo_hub.html` en vez de comandos legacy.

# Operación diaria
flujo daily                   # dashboard del día
flujo app                     # nueva app principal (hub pro workspace) — entrada diaria
flujo serve                   # alias (usa --legacy solo para Gradio viejo)
flujo clean [--generated]

# Airdrops (colaboración / mejoras)
flujo airdrop list            # archivos pendientes en _airdrop/
flujo airdrop dry-run         # simular sin aplicar
flujo airdrop apply "mensaje" # backup → apply → checkpoint → push
flujo airdrop rollback        # restaurar último backup
flujo airdrop status          # versión actual

# Planos de stands (proyecto satélite plano)
flujo plano projects/plano/ejemplos/evento_ejemplo.json
flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider
flujo plano projects/plano/ejemplos/evento_ejemplo.json --costs
flujo plano <evento.json> -o plano.svg
```

> Editor visual autocontenido: `projects/plano/plano_editor.html`.

---

## Licencia

MIT
