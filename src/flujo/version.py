"""Versión y changelog de flujo."""

__version__ = "0.43.3"
VERSION = __version__
__version_info__ = (0, 43, 3)


def get_version():
    return __version__


def get_changelog():
    return {
        "0.43.3": {
            "titulo": "Rider requirements restore 17 items + icons + layer ordering + export",
            "fecha": "2026-06-28",
            "highlights": [
                "Rider restaurado a 17 requerimientos con iconos Lucide",
                "Soporta persistencia de checklist en impresion",
                "Ordenamiento de capas con traer al frente y color picker",
                "Exportar checklist como markdown (.md)",
                "Corrige boton de navegacion Ir al Plano",
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
                "`eventos flyer-auto` genera `palette_ig.png` y `palette_ig.json` desde la imagen descargada",
                "Agrega soporte `--render-blender` para renderizar frame 1 de `cartelera.blend` a `preview_cartelera.png`",
                "Agrega soporte `--open-blender` para abrir `cartelera.blend` con autorizacion humana",
            ],
        },
    }
