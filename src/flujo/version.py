"""Versión y changelog de flujo."""

__version__ = "0.48.1"
VERSION = __version__
__version_info__ = (0, 48, 1)


def get_version():
    return __version__


def get_changelog():
    return {
        "0.48.1": {
            "titulo": "Operational agent workspace baseline",
            "fecha": "2026-06-30",
            "highlights": [
                "Squash de main a un baseline operacional limpio",
                "AGENTS.md queda como contrato operativo principal para agentes",
                "Airdrop queda estandarizado con _airdrop/, HANDOFF y LAST_HANDOFF",
                "Repo hygiene aplicado y raiz limpia de handoffs historicos",
                "Verificacion integral con compileall, pytest, health, version y hub smoke",
            ],
        },
        "0.47.13": {
            "titulo": "Rider PDF alineado al editor y SVG Studio configurable real",
            "fecha": "2026-06-30",
            "highlights": [
                "El PDF del rider vuelve a respetar colores, iconos tecnicos y posicion de la leyenda del editor",
                "Evita doble disparo de impresion y mantiene impresion directa por iframe",
                "Formato PDF vuelve a A4 natural, no forzado horizontal extremo",
                "Config Editor lista SVGs reales del repo y permite cargar SVG local",
                "El boton Configurar este SVG ahora pasa el SVG abierto al editor sin quedarse en demos",
            ],
        },
        "0.47.12": {
            "titulo": "PDF directo con color y puente Galeria→Config SVG",
            "fecha": "2026-06-30",
            "highlights": [
                "Imprimir Rider vuelve a abrir el dialogo directo usando iframe oculto, sin descargar HTML",
                "El plano imprimible recupera color de zonas y simbolos",
                "SVG Studio agrega boton Configurar este SVG dentro del modal de galeria",
                "Config Editor puede cargar el SVG seleccionado desde la galeria como documento editable base",
                "Mantiene Actualizar repo y Carpeta local para ubicar SVGs reales",
            ],
        },
        "0.47.11": {
            "titulo": "Hotfix PDF Plano/Rider en ventana imprimible aislada",
            "fecha": "2026-06-30",
            "highlights": [
                "Reemplaza la impresion React/Tailwind del rider por un HTML imprimible aislado",
                "El boton Imprimir Rider abre una ventana PDF limpia con 3 paginas: checklist, mapa y detalle",
                "El plano se renderiza como SVG autonomo dentro de la hoja de mapa para evitar que desaparezca",
                "Mantiene fixes de SVG Studio: cargar SVGs reales, Actualizar repo y Carpeta local",
            ],
        },
        "0.47.10": {
            "titulo": "Fix SVG previews reales y PDF multipagina Plano/Rider",
            "fecha": "2026-06-30",
            "highlights": [
                "SVG Studio ahora carga el contenido real de /svg desde la API y evita tarjetas con icono generico",
                "Agrega botones Actualizar repo y Carpeta local para refrescar o seleccionar SVGs manualmente",
                "Plano/Rider fuerza PDF multipagina A4 horizontal y separa portada/checklist, mapa y detalle",
                "El mapa imprimible escala dentro de la pagina para evitar recortes",
                "Se mantiene Plano/Rider estable y el Config Editor de SVG Studio",
            ],
        },
        "0.47.9": {
            "titulo": "SVG Studio y Hub web revisado sobre Plano/Rider estable",
            "fecha": "2026-06-30",
            "highlights": [
                "Integra las mejores mejoras web del airdrop externo sin reemplazar el Plano/Rider estable",
                "Convierte el visualizador SVG en SVG Studio con galeria, inspector, preview, descarga y export PNG",
                "Agrega Config Editor visual para config.json con drag, seleccion multiple, alineado, distribucion e import/export",
                "Mejora dashboard, sidebar, jobs, intake y comandos manteniendo fallback demo/local",
                "Mantiene build single-file para context/flujo_hub.html, plano_demo.html y svg_visualizer.html",
            ],
        },
        "0.47.8": {
            "titulo": "Plano/Rider integrado: capas estables, mezcla aditiva y knowledge operativo",
            "fecha": "2026-06-30",
            "highlights": [
                "Integra hotfixes pendientes de Plano/Rider sobre el repo web remoto actual",
                "Seleccionar elementos ya no reordena capas; se agrega ordenamiento base explicito",
                "Auto ordenar respeta prioridad de capas y distribuye simbolos en grilla compacta",
                "Zonas solapadas usan mezcla visual tipo screen para evitar acumulacion opaca",
                "Sincroniza checklist y mapa en ambos sentidos, preservando color, posicion y tamano de simbolos",
                "Mejora exportacion/impresion con leyenda tecnica debajo del mapa y schema knowledge operativo",
            ],
        },
        "0.47.0": {
            "titulo": "QA operativo para rider/plano y SVGs de suplementos",
            "fecha": "2026-06-29",
            "highlights": [
                "Agrega validacion CLI para eventos antes de imprimir/exportar rider y plano",
                "Completa simbolos tecnicos del Plano/Rider y sincroniza los 17 items del checklist al mapa",
                "Agrega validador tecnico de SVGs de suplementos y contraportadas para detectar placeholders y tamano incorrecto",
                "Documenta comandos Windows-first y mantiene entrega por airdrop",
            ],
        },
        "0.46.0": {
            "titulo": "Post Fiesta Flyer creation + complete 8-flyer master generation run",
            "fecha": "2026-06-28",
            "highlights": [
                "Agrega la ficha de contenido individual y la generacion de Post Fiesta en el JSON maestro",
                "Soporta la creacion del 8vo flyer de suplementos con renderizado automatico editable y vectorizado",
                "Bumpea la version del sistema a 0.46.0 y empaqueta el entregable unificado en airdrop_v0.46.0.zip",
            ],
        },
        "0.45.0": {
            "titulo": "Plano element resizing + direct label editing + automated flyer generator run",
            "fecha": "2026-06-28",
            "highlights": [
                "Permite modificar el tamano (ancho y alto en px) de los elementos en el editor de propiedades del Plano SVG",
                "Permite editar de forma directa el texto interno / nombre de los elementos del plano",
                "Ejecuta de forma automatizada la creacion y renderizado maestro de los 7 flyers vectorizados de suplementos de la ONG",
                "Bumpea la version del sistema a 0.45.0 y empaqueta el entregable unificado en airdrop_v0.45.0.zip",
            ],
        },
        "0.44.0": {
            "titulo": "Rider requirements restore 17 items + icons + layer ordering + export",
            "fecha": "2026-06-28",
            "highlights": [
                "Rider restaurado a 17 requerimientos con iconos Lucide y live-sync al plano SVG",
                "Fondo de pantalla oscuro para el canvas del plano en modo de diseño",
                "Alinea el viewBox de SVG a las proporciones de 2970x2100 px del catalogo de la ONG",
                "Soporta persistencia de checklist en impresion y exportacion a Markdown (.md)",
                "Ordenamiento de capas con traer al frente y color picker para zonas y simbolos",
                "Corrige boton de navegacion Ir al Plano conectandolo con inyeccion automatica de elementos",
            ],
        },
        "0.43.2": {
            "titulo": "Fix CI health check – ignore node_modules/web",
            "fecha": "2026-06-28",
            "highlights": [
                "flujo_health ignora web/tsconfig.json (JSONC)",
                "CI render_piezas_vectoriales verde",
            ],
        },
        "0.43.1": {
            "titulo": "Contraportadas suplementos con automatizacion y CLI",
            "fecha": "2026-06-28",
            "highlights": [
                "Automatiza generacion de contraportadas SVG cuando se crea un job de suplementos en el hub",
                "Agrega soporte en CLI para contraportadas con el flag --brief para sobreescribir beneficios",
                "Soporta busqueda dinamica de los 11 suplementos de la linea RD uniendo config y spec JSON",
                "Corrige bug critico de layout en el reemplazo de texto de nombres de suplementos multilinea",
                "Agrega documentacion de operacion y guias pre-prensa en docs/CONTRAPORTADAS_SUPLEMENTOS_OPERATIVO.md",
                "Integra especificaciones tecnicas de contraportadas en la linea_editorial v4.1",
            ],
        },
        "0.43.0": {
            "titulo": "Rider Pro + Cotizacion + Flyers Techno",
            "fecha": "2026-06-28",
            "highlights": [
                "Rider Pro: Requerimientos + Plano imprimible",
                "Iconografia tecnica sin emojis",
                "Configuracion persistente ONG/precios",
                "Cotizacion operativa Presets + Items Manuales",
                "Flyers v4.1 Techno-Elegant layout",
            ],
        },
        "0.42.1": {
            "titulo": "Example ingest templates",
            "fecha": "2026-06-28",
            "highlights": [
                "Agrega templates `knowledge/templates/*.for_ai.json` para analisis visual por IA",
                "Knowledge ingest ahora crea `manifest.json`, `for_ai.json` y `README.md`",
                "Soporta templates para cartelera digital, flyer 10x14, supplement flyer y logo source",
                "Ordena el flujo para que una IA con vision devuelva `analysis.json` reutilizable",
            ],
        },
        "0.42.0": {
            "titulo": "Knowledge base skeleton",
            "fecha": "2026-06-28",
            "highlights": [
                "Agrega `knowledge/` con productoras, venues, logos y examples",
                "Registra Creamfields, The Grid, template Rave Under y Espacio Riesco",
                "Agrega comandos `py -m flujo knowledge list/show/classify/ingest-example/logo-source`",
                "Documenta Agent Visual Director para generar JSON desde ejemplos reales",
            ],
        },
        "0.41.2": {
            "titulo": "Demo jefe y cotizacion base",
            "fecha": "2026-06-28",
            "highlights": [
                "Agrega vista React de Cotizacion con preset UNDER/BASE/MAINSTREAM",
                "Agrega `/api/cotizacion/render` para cotizacion referencial local",
                "Agrega ACTIVE_PLAN, SESSION_STATE y demo jefe para continuidad anti-interrupcion",
                "Documenta roadmap AI Memory para productoras, venues, logos, ejemplos reales e internet enrichment",
            ],
        },
        "0.41.1": {
            "titulo": "Presets EVENTOS e intake con metadata",
            "fecha": "2026-06-28",
            "highlights": [
                "Agrega presets UNDER, BASE y MAINSTREAM para estimar rider/plano desde flyers de eventos",
                "PlanoTool permite seleccionar preset y enviarlo a `/api/plano/render`",
                "El parser sugiere `event_preset` para correos de eventos, rider, cartelera e Instagram",
                "Create job draft guarda `intake.json` y resumen de metadata parseada cuando existe",
            ],
        },
        "0.41.0": {
            "titulo": "Hub React operativo unificado",
            "fecha": "2026-06-28",
            "highlights": [
                "Convierte `flujo_hub.html` en la misma app React single-file usada por Plano y SVG",
                "Agrega AppShell, HubDashboard, JobsPanel, IntakePanel y CommandPanel conectados a APIs reales con fallback",
                "El build `npm run build:context` genera `flujo_hub.html`, `plano_demo.html` y `svg_visualizer.html`",
                "Agrega endpoints livianos de jobs/intake al servidor stdlib para que `hub serve` no quede inutil",
            ],
        },
        "0.40.5": {
            "titulo": "SVG Visualizer conectado a SVG reales",
            "fecha": "2026-06-28",
            "highlights": [
                "`SvgVisualizer` carga `/api/list-svg-works` y usa los SVG reales del repo con fallback demo",
                "Agrega alias `/api/svg-index` y soporte de endpoint en `flujo hub serve`",
                "Renombra el build web principal a `npm run build:context` manteniendo `build:plano` como alias",
                "Sirve `/svg/...` desde el servidor stdlib y agrega checks Node al CI",
            ],
        },
        "0.40.4": {
            "titulo": "React SVG Visualizer integrado",
            "fecha": "2026-06-28",
            "highlights": [
                "Integra `SvgVisualizer.tsx` and `svgIndex.ts` en la capa `web/`",
                "El build single-file ahora actualiza `context/plano_demo.html` y `context/svg_visualizer.html`",
                "Agrega navegacion React Plano/SVG manteniendo uso diario con `py -m flujo app`",
                "Mantiene Node como capa local/gratis de desarrollo UI y Python como backend operativo",
            ],
        },
        "0.40.3": {
            "titulo": "Frontend React/Vite para Plano Pro",
            "fecha": "2026-06-28",
            "highlights": [
                "Agrega `web/` como capa Node/React local y gratis para avanzar mas rapido en UI",
                "Compila con Vite single-file y copia el resultado a `context/plano_demo.html`",
                "Integra PlanoTool React con canvas editable, checklist, capas, export SVG e impresion",
                "Agrega boton Motor Python para usar `/api/plano/render` cuando se abre via `py -m flujo app`",
            ],
        },
        "0.40.2": {
            "titulo": "Plano/Rider Pro integrado al hub vanilla",
            "fecha": "2026-06-28",
            "highlights": [
                "Reemplaza `context/plano_demo.html` por una herramienta util de plano, rider y costos sin React ni build",
                "Integra ideas del prototipo PlanoTool: requerimientos, checklist, capas, zonas arrastrables, grilla, zoom y leyenda",
                "Mantiene conexion real a `POST /api/plano/render` y fallback demo local para doble clic",
                "Agrega export SVG, JSON, copiar rider/costos e impresion desde la UI",
            ],
        },
        "0.40.1": {
            "titulo": "Fix dispatcher y addons hub",
            "fecha": "2026-06-28",
            "highlights": [
                "Restaura `py -m flujo` para delegar en la CLI Typer principal sin ocultar comandos vivos",
                "Registra `serve`, `index` y `route` bajo el namespace seguro `py -m flujo hub ...`",
                "Corrige continuidad operacional: version, handoff activo y documentacion de comandos hub",
                "Mantiene airdrop Python-only con validacion, backup, checks y checkpoint",
            ],
        },
        "0.35.13": {
            "titulo": "EVENTOS palette y preview Blender",
            "fecha": "2026-06-24",
            "highlights": [
                "Revision Gmail automatica cambia a cada 8 horas",
                "`eventos flyer-auto` genera `palette_ig.png` and `palette_ig.json` desde la imagen descargada",
                "Agrega soporte `--render-blender` para renderizar frame 1 de `cartelera.blend` a `preview_cartelera.png`",
                "Agrega soporte `--open-blender` para abrir `cartelera.blend` con autorizacion humana",
            ],
        },
    }
