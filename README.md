# # # flujo — Dimensiones del Orden (arte + automatización)

**Uso diario:** abre `context/flujo_hub.html` (todo en un lugar: reportes, botones, visualizadores, pedidos manuales, aistetic, cómo trabajo).

**Pedidos (manual por ahora):** pega WhatsApp/Gmail en el hub → genera estructura ordenada.

Proyectos alineados a aistetic (línea editorial):
- piezas_vectoriales, flyer_eventos, plano, cotizaciones (dual: productora / interno), aistetic.

Ver `projects/README.md` y `context/LAST_HANDOFF.md` (tareas claras para agentes).

Windows: `py -m flujo ...` | Español prioritario para reducir errores.

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
9. [La app / recepción automática (estado y plan)](#-la-app--recepción-automática-estado-y-plan)
10. [Reglas innegociables](#-reglas-innegociables)
11. [Estructura del repo](#-estructura-del-repo)
12. [Referencia de comandos CLI](#-referencia-de-comandos-cli)

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
Lee, en orden: este README → `PARA_IA_CONTEXT.md` → `docs/AGENT_GUIDE.md` →
`docs/CLI.md`. Clona el repo y corre `py -m pytest tests/ -q` y `flujo health`
para conocer el estado real (no asumas que la doc está 100% al día).

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

flujo health                 # chequeo general del repo
flujo version                # versión + changelog

# Procesar un pedido por correo/texto:
flujo job new "etiquetas acme" --email inbox/correo.txt
flujo job prepare jobs/2026-06-17_etiquetas-acme      # privacy → brief → estado
flujo job activate jobs/2026-06-17_etiquetas-acme     # brief → proyecto

# Renderizar:
flujo render run projects/piezas_vectoriales/etiquetas-acme/config.json

# Panorama del día:
flujo daily

# Interfaz web local (Gradio):
flujo serve
```

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

## 🌐 La app / recepción automática (estado y plan)

Pregunta clave del dueño: *"¿la app será Gradio, o se integrará con mi correo /
una API para recibir pedidos aunque esté ausente?"*

### Hoy (estado real)
- `flujo serve` levanta el **editor visual** propio (`src/flujo/web/`,
  http://127.0.0.1:7860). Flujo: elegir formato del catálogo (filtrable por área)
  → editar datos (título/subtítulo/cuerpo) → ajustar **proporción/DPI** →
  **preview SVG en vivo** → **exportar SVG + config.json** a
  `projects/piezas_vectoriales/<slug>/`. Luego `flujo render run` produce el SVG
  de producción (editable + vectorizado) para Illustrator.
  - Opciones: `flujo serve --port 7860 --host 0.0.0.0` (red local),
    `flujo serve --legacy` (usa el antiguo `scripts/app.py`).
- Es **local y manual**: hay que tenerlo corriendo. No recibe pedidos por sí
  solo (la recepción automática es el plan de abajo).

### Plan recomendado (para "recibir aunque esté ausente")
La arquitectura objetivo separa **recepción** de **operación**:

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
- **Correo (recomendado para empezar):** un poller IMAP lee un buzón dedicado,
  extrae JSON adjunto o cuerpo, y responde automáticamente *"pedido recibido,
  folio #…"*. Cero infraestructura nueva, funciona aunque el dueño duerma.
- **Formulario web + API:** una página simple genera el JSON válido (evita que
  el colega se equivoque en el esquema) y lo postea a un endpoint.
- **Webhook de WhatsApp/Telegram:** para canales de mensajería.

> **Decisión pendiente del dueño.** Mientras tanto, el formato de intercambio
> (JSON) ya queda fijado, así cualquier canal que se elija después solo tiene
> que producir ese JSON. Ver opciones y trade-offs en `docs/INTAKE_JSON.md`.

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
- `context/flujo_hub.html` (tu punto de entrada diario)
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
scripts/          # utilidades: checkpoint.sh, apply_airdrop.sh, app.py (Gradio), cleanup_safe.sh
tests/            # pytest (69+ tests)
docs/             # documentación detallada (CLI, formatos, intake JSON, etc.)
schemas/          # esquema JSON de intake + ejemplos
jobs/             # trabajos creativos (gitignored, salvo _template)
projects/         # proyectos satélite (piezas_vectoriales, flyer_eventos, plano, tapiz, aistetic)
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

# Flyers desde Instagram
flujo flyer-import <correo.txt>
flujo flyer-list
flujo ig-redownload [--all]
flujo analyze [--all] [--force-ocr]
flujo export <proyecto>
flujo index [--rebuild | --duplicates]

# Operación diaria
flujo daily                   # dashboard del día
flujo serve                   # interfaz web Gradio (local)
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
