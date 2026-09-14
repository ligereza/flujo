# Mapa operativo de FLUJO

Este mapa es la orientacion rapida del repositorio autonomo
`ligereza/flujo`. No describe VIBECODEINE, MAK ni XIO.

## Entrada

1. `AGENTS.md`: contrato para agentes.
2. `README.md`: proposito y frontera.
3. `STATUS.md`: estado medido de esta migracion.
4. `CAPACIDADES_FLUJO.md`: superficies propias.
5. `MIGRATION.md`: procedencia y exclusiones.

## Arbol de propiedad

- `src/flujo/`: runtime Python y CLI canonicos.
- `src/flujo/web/`: Hub HTTP y rutas del workspace.
- `src/flujo/rd/`: modelo y operaciones RD.
- `src/flujo/vj/`, `web/`, `iskvw/`: superficies ISKVW/VJ.
- `contracts/`, `schemas/`: contratos de intercambio.
- `data/`: configuracion y fixtures pequenos; nunca bases locales ni secretos.
- `docs/`: documentacion vigente por superficie.
- `tests/`: pruebas propias del motor o de higiene del repositorio.
- `tools/`: validadores y generadores que no sustituyen al runtime.

## Relacion con otros repositorios

```text
ligereza/flujo       -- contratos/vistas --> ligereza/XIO
       |                                  XIO-RD / XIO-FOH
       +-- contratos/proyecciones <------ ligereza/vibecodeine (MAK)
```

La flecha no significa dependencia de filesystem. Un consumidor externo debe
usar contratos, `source_ref`, API o una exportacion revisada.

## Git

`main` es el unico tronco permanente. Las ramas de trabajo son temporales.
Los nombres `FLUJO`, `MAK`, `integration` e `historia` pertenecen al contexto
del antiguo VIBECODEINE y no deben crearse en este repositorio.

## Comandos de entrada

<!-- COMANDOS:INICIO -- generado por tools/gen_mapa_comandos.py, no editar a mano -->

Medido sobre el CLI real: **98 comandos** (25 sueltos + 73 dentro de 17 grupos).

### Comandos sueltos

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo ai-prompt` | Genera un prompt listo para copiar en una IA web y convertir pedidos en briefs/cotizaciones. | nada |
| `py -m flujo analyze` | Analizar colores dominantes y OCR de un proyecto flyer. | nada |
| `py -m flujo app` | Alias de serve. Lanza la nueva app (hub pro workspace recomendado como entrada diaria). Real backend + parse/create jobs live cuando activo. | nada |
| `py -m flujo clean` | Limpiar archivos temporales del repo. | nada |
| `py -m flujo code-index` | Crear un índice AST consultable sin incluir texto fuente. | nada |
| `py -m flujo cotizaciones` | Genera cotización dual integrada con flujo. | nada |
| `py -m flujo daily` | Generar reporte diario (md + html). | nada |
| `py -m flujo delegate` | Genera prompt preciso para delegar a agente especializado (5 roles; soporta paralelo via hub o clones). Salida lista para copiar a otra sesión IA. Ideal para multi-agente workflow. | nada |
| `py -m flujo diagnose` | Genera un reporte local, sanitizado y copiable para otro agente. | nada |
| `py -m flujo doctor` | Diagnóstico humano del entorno local: Python, Git, encoding, index, hub y airdrop. | nada |
| `py -m flujo export` | Exportar ZIP listo para tus herramientas (AI / PS / Blender). | nada |
| `py -m flujo flyer-import` | Importar flyers desde correo con links de Instagram. | casilla de correo: `FLUJO_IMAP_HOST`, `FLUJO_IMAP_USER`, `FLUJO_IMAP_PASSWORD`, `FLUJO_IMAP_ALLOWED_SENDERS` |
| `py -m flujo flyer-list` | Listar flyers indexados. | nada |
| `py -m flujo github-sync` | Sincroniza el repo local con GitHub de forma simple y segura. | nada |
| `py -m flujo health` | Chequeo general del repo. | nada |
| `py -m flujo ig-redownload` | Reintentar descarga de posts de Instagram que fallaron. | `pip install parth-dl` |
| `py -m flujo index` | Reconstruir o consultar el índice SQLite de flyers. | `FLUJO_RD_ROOT` apuntando al arbol de material |
| `py -m flujo init` | Inicializa carpetas del repo/workspace (jobs/_template, data, inbox, datadrops). | nada |
| `py -m flujo package` | Empaqueta el hub pro como aplicación de escritorio real .exe (Windows). | solo Windows; empaqueta un .exe |
| `py -m flujo plano` | Generar plano SVG, rider o costos de stands desde un JSON de evento. | nada |
| `py -m flujo route` | Selecciona el packet minimo para una idea sin leer todo el repo. | nada |
| `py -m flujo serve` | Iniciar el workspace local: el hub, que es la entrada diaria. | nada |
| `py -m flujo tapiz` | Ecosistema Tapiz<->Psicosis<->Fungi: pipeline generativo (tools/compete_engine.py). | nada |
| `py -m flujo verify` | Verificación integral local/CI: compileall, tests, health, version y hub smoke. | nada |
| `py -m flujo version` | Muestra versión y changelog. | nada |

### Grupo `airdrop` -- Sistema de actualización profesional (airdrops).

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo airdrop status` | Muestra la versión actual del sistema flujo. | nada |
| `py -m flujo airdrop list` | Lista los archivos pendientes de aplicar en _airdrop/. | nada |
| `py -m flujo airdrop dry-run` | Simula la aplicación del airdrop sin realizar cambios. | nada |
| `py -m flujo airdrop sign` | Genera el manifiesto SHA-256 y la firma HMAC del payload de _airdrop/. | nada |
| `py -m flujo airdrop verify` | Verifica la firma HMAC y los hashes SHA-256 del payload de _airdrop/. | nada |
| `py -m flujo airdrop apply` | Aplica los archivos de _airdrop/, crea backup y dispara checkpoint + push. | nada |
| `py -m flujo airdrop rollback` | Revierte los cambios al último backup de airdrop. | nada |
| `py -m flujo airdrop finish` | Finaliza el proceso de airdrop (estatus y sugerencias). | nada |

### Grupo `autonomia` -- Orquestacion externa MAK: estado, tandas, ledger y juez local.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo autonomia status` | Mide si el circuito remoto/local -> juez local -> ledger esta listo. | nada |
| `py -m flujo autonomia run` | Ejecuta tandas controladas; por defecto corre providers/Ollama en MAK. | La ejecucion remota esta fuera de este entorno; `--executor local` solo para pruebas/dry-run con autoridad explicita |

### Grupo `brief` -- Operaciones sobre briefs.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo brief extract` | Re-extraer brief desde el texto del job. | nada |
| `py -m flujo brief to-project` | Convertir brief.yaml en proyecto en projects/piezas_vectoriales/. | nada |
| `py -m flujo brief paquete-cotizacion` | Generar brief imagen/texto + cotización base para flyer/etiqueta/pendón/post IG. | nada |
| `py -m flujo brief show` | Mostrar brief en formato legible. | nada |

### Grupo `datadrop` -- Gestión de datadrops (fotos reales terminadas).

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo datadrop list` | Lista datadrops (fotos reales de entregados) desde workspace/datadrops/. | nada |
| `py -m flujo datadrop scan` | Escanea la carpeta datadrops/incoming/ y procesa las fotos convirtiéndolas en datadrops. | nada |
| `py -m flujo datadrop ingest` | Importar un PDF o imagen como datadrop de referencia real. | nada |
| `py -m flujo datadrop prepare` | Genera paquete de revisión persistente (_review_package.txt) con manifests + notas 'for_future_ai'. Para que otra IA (linea_editorial) lea y sepa exactamente qué buscar en trabajos reales terminados. | nada |

### Grupo `eventos` -- Automatizaciones del area EVENTOS.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo eventos flyer-auto` | EVENTOS: descargar Instagram, crear palette_ig y opcionalmente lanzar Photoshop/Blender. | `pip install parth-dl`; para render tambien Blender |

### Grupo `hub` -- Hub: servidor local + index/route del arbol de material ($FLUJO_RD_ROOT, ver MAPA.md).

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo hub serve` | Levanta el servidor local del hub (HTML + /api). | nada |
| `py -m flujo hub index` | Indexa el arbol de material ($FLUJO_RD_ROOT) para agentes. Pasa args tal cual al indexador. Ej: py -m flujo hub index agent-brief "necesito la etiqueta de creatina" | `FLUJO_RD_ROOT` apuntando al arbol de material |
| `py -m flujo hub route` | Resuelve donde esta/va una pieza. Ej: py -m flujo hub route where --area eventos --pieza flyer | `FLUJO_RD_ROOT` apuntando al arbol de material |

### Grupo `intake` -- Intake estructurado de pedidos (JSON 1.0).

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo intake json` | Validar intake JSON 1.0, crear job, brief y acuse de recibo. | nada |

### Grupo `job` -- Gestión de jobs y briefs.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo job new` | Crear un nuevo job desde un nombre (y opcionalmente texto fuente). | nada |
| `py -m flujo job prepare` | Pipeline: privacidad → brief → estado. | nada |
| `py -m flujo job list` | Listar jobs y sus estados. | nada |
| `py -m flujo job status` | Estado detallado de un job. | nada |
| `py -m flujo job next` | Próximas acciones sugeridas para cada job. | nada |
| `py -m flujo job activate` | brief → proyecto en projects/piezas_vectoriales/. | nada |
| `py -m flujo job report` | Generar reporte detallado de un job. | nada |

### Grupo `knowledge` -- Knowledge base local: productoras, venues, logos y ejemplos.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo knowledge list` | Lista entidades de la knowledge base. | nada |
| `py -m flujo knowledge show` | Muestra una entidad YAML como JSON legible. | nada |
| `py -m flujo knowledge classify` | Clasifica un texto usando productoras/venues conocidos. | nada |
| `py -m flujo knowledge ingest-example` | Copia un ejemplo real a knowledge/examples y crea manifest para IA. | nada |
| `py -m flujo knowledge logo-source` | Registra una fuente de logo para logo clean lab. | nada |
| `py -m flujo knowledge logo-lab` | Bridge para Logo Clean Lab: prepara estructura de carpetas y manifest. | nada |

### Grupo `laser` -- Estetica vectorial para laser/plotter (vpype): rayado, campos de flujo.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo laser estado` | Que parte de la cadena vpype esta instalada, medido ejecutandola. | nada |
| `py -m flujo laser hatched` | Zonas oscuras a rayado: un logo solido deja de llegar hueco al laser. | nada |
| `py -m flujo laser flow` | La imagen se vuelve trazos largos de campo de flujo, casi sin saltos. | nada |
| `py -m flujo laser lote` | Deriva una pieza laser por imagen y escribe el manifiesto del archivo. | nada |
| `py -m flujo laser medir` | Los numeros reales del frame: puntos, trazos, dibujo y viaje apagado. | nada |
| `py -m flujo laser ild` | SVG a ILDA Type 5 (RGB): el formato que QuickShow SI importa. | nada |

### Grupo `micelio` -- El sobre micelio/1: semilla, fruto y nutriente entre un modelo web sin API y el organismo.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo micelio formato` | Imprime el formato para PEGARSELO al modelo web antes de contarle la idea. | nada |
| `py -m flujo micelio validar` | Dice si el sobre sirve, y si no, QUE le falta -- en castellano, para poder pegarle la respuesta de vuelta al modelo que lo escribio. | nada |
| `py -m flujo micelio fruto` | Mide un dataset y arma un fruto que CABE en una ventana de chat. | nada |
| `py -m flujo micelio verificar` | Corre el criterio y devuelve VERDE o ROJO. Es el semaforo del ciclo. | nada |
| `py -m flujo micelio cosechar` | Corre el criterio y devuelve el SOBRE de vuelta: fruto si crecio, hongo si no. | nada |
| `py -m flujo micelio depositar` | Mete el sobre en la cola de trabajo del organismo. | nada |

### Grupo `privacy` -- Privacidad para textos antes de IA externa.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo privacy scan` | Escanear un texto en busca de datos personales. | nada |
| `py -m flujo privacy sanitize` | Sanitizar texto reemplazando PII por placeholders. | nada |
| `py -m flujo privacy check` | Escanear pedido_original.txt de un job + sanitizar. | nada |

### Grupo `rd-datos` -- Ingesta privacy-first de datos de campo RD (testeo, atenciones, encuestas).

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo rd-datos ingest` | Ingesta un CSV de datos de campo (testeo de reactivos, atenciones o encuestas) a la DB privacy-first data/rd.db. Toda fila pasa por flujo.privacy.scan_text ANTES de persistir: RUT chileno o numero... | un CSV de campo; la DB privacy-first se crea sola |
| `py -m flujo rd-datos informe` | Genera el informe trimestral de datos de campo RD (markdown): 3 tablas (tendencias por sustancia/mes, tasa de no-coincidencia por sustancia, atenciones por tipo) precedidas por el disclaimer obliga... | nada |

### Grupo `rd-db` -- Base de datos RD: reactivos, packs, suplementos, productoras, eventos.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo rd-db build` | Construye la proyección portable o promueve una fuente RD completa. | fuentes de datos en `data/` (la DB se regenera, no se versiona) |
| `py -m flujo rd-db reactivo` | Consulta la colorimetria presuntiva. El test es PRESUNTIVO: indica familia posible, no identifica ni mide pureza. | nada |
| `py -m flujo rd-db packs` | Lista los packs de servicio con precio e inclusiones. | nada |
| `py -m flujo rd-db eventos` | Lista los eventos registrados con su pack sugerido. | nada |
| `py -m flujo rd-db testeos` | Show only the internal summary of imported testing evidence. | nada |
| `py -m flujo rd-db productora` | Perfil completo: instagram, aliases, tipos de fecha, venues (preferido marcado) y logos. | nada |
| `py -m flujo rd-db venues` | Venues canonicos con preset recomendado y voluntarios minimos. | nada |
| `py -m flujo rd-db por-tipo` | Que productoras hacen fechas de un tipo dado. | nada |
| `py -m flujo rd-db lookup` | Consulta de operador en terreno: reactivos que marcan la familia + packs que incluyen testeo + disclaimer, en una sola vista (JOIN reactivos+packs). | nada |

### Grupo `render` -- Render y validación de piezas vectoriales.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo render run` | Renderizar un proyecto piezas_vectoriales. | Blender instalado |
| `py -m flujo render illustrator` | Preparar un paquete listo para abrir en Illustrator desde uno o varios SVG. | Adobe Illustrator (solo Windows/macOS) |
| `py -m flujo render bridge` | Generar un script JSX para Illustrator a partir de un JSON de entrada. | Adobe Illustrator (solo Windows/macOS) |
| `py -m flujo render validate` | Validar un config.json sin renderizar. | nada |
| `py -m flujo render formats` | Listar, filtrar o sugerir formatos/plantillas. | nada |
| `py -m flujo render rescale` | Reescalar proporción (medida cm) o resolución (DPI) de un config.json. | nada |

### Grupo `resolume` -- Automatizacion de shows Resolume/Chataigne por SMPTE/OSC.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo resolume automatizar` | Generar XML pre-flight Chataigne/OSC para Resolume desde un setlist SMPTE. | Chataigne y Resolume abiertos en la maquina del show |

### Grupo `suplementos` -- Generación de contraportadas para suplementos RD.

| Comando | Que hace | Que necesita antes |
|---|---|---|
| `py -m flujo suplementos list` | Listar suplementos disponibles. | nada |
| `py -m flujo suplementos contraportada` | Regenerar las contraportadas desde la plantilla aprobada. | nada |
| `py -m flujo suplementos validate` | Validar SVGs de suplementos antes de revisar/exportar en Illustrator. | nada |
| `py -m flujo suplementos illustrator` | Preparar un paquete Illustrator con varias contraportadas de suplementos. | Adobe Illustrator (solo Windows/macOS) |

<!-- COMANDOS:FIN -->

```bash
PYTHONPATH=src python -m flujo --help
PYTHONPATH=src python -m pytest -o addopts='' -m flujo
python tools/test_lane_map.py --format text
```
