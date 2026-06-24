"""Versión y changelog de flujo."""

__version__ = "0.35.7"
VERSION = __version__
__version_info__ = (0, 35, 7)


def get_version():
    return __version__


def get_changelog():
    return {
        "0.35.7": {
            "titulo": "ASCII handoff y guardrails Windows Git Bash",
            "fecha": "2026-06-24",
            "highlights": [
                "Reescribe `context/LAST_HANDOFF.md` en ASCII-only para evitar mojibake en Windows/Git Bash",
                "Aclara que el usuario usa `py`, no `python`, en comandos y documentacion operativa",
                "Deja reglas de encoding para futuras IAs: handoff sin acentos, codigo/logs en ingles/ASCII si conviene",
            ],
        },
        "0.35.6": {
            "titulo": "README limpio purple y brief suplementos RD",
            "fecha": "2026-06-24",
            "highlights": [
                "README principal reescrito y simplificado alrededor de Gmail/GitHub/portal/jobs",
                "Paleta PURPLE aplicada como línea visual del portal y documentación principal",
                "Agrega `docs/BRIEF_SUPLEMENTOS_RD.md` como fuente operativa para área suplementos RD",
                "Deja candidatos de limpieza identificados para aprobación antes de borrar",
            ],
        },
        "0.35.5": {
            "titulo": "Guía Gmail a GitHub Issues para pedidos",
            "fecha": "2026-06-24",
            "highlights": [
                "Agrega `tools/gmail_to_github_issues.gs`, puente Google Apps Script para Gmail → GitHub Issues",
                "Documenta configuración gratuita con etiquetas Gmail, PAT fino de GitHub y trigger cada 10 minutos",
                "Integra Gmail en el flujo portal/jefatura sin guardar credenciales ni tokens en el repo",
            ],
        },
        "0.35.4": {
            "titulo": "Portal jefe gratuito y reemplazo de monday.com",
            "fecha": "2026-06-24",
            "highlights": [
                "Nuevo `flujo portal` exporta `context/portal_jefe.html` con tablero visual de estados para jefatura",
                "Issue Forms gratuitos para nuevo pedido y cambios/correcciones vía GitHub Issues",
                "Documento `docs/PORTAL_JEFE_GRATIS.md` define flujo GitHub Issues + Projects + portal HTML",
                "Tests cubren export del portal vacío y con jobs locales",
            ],
        },
        "0.35.3": {
            "titulo": "Intake JSON end-to-end con job, brief y acuse",
            "fecha": "2026-06-24",
            "highlights": [
                "Nuevo comando `flujo intake json <archivo.json>` para validar schema 1.0 y crear jobs estructurados",
                "El intake JSON escribe `brief.yaml`, `estado.md` y `resultado.md` con folio, resumen, warnings y pendientes",
                "Mapea formato sugerido/medidas al catálogo local y conserva modificación/rescale con comandos sugeridos",
                "Docs y tests cubren CLI, validación de schema y acuse end-to-end",
            ],
        },
        "0.35.2": {
            "titulo": "Hotfix Python 3.11 para paquete comercial multiformato",
            "fecha": "2026-06-24",
            "highlights": [
                "Corrige f-string incompatible con Python 3.11 en flujo.comercial.multiformato",
                "Precalcula secciones markdown antes del f-string para mantener compatibilidad Windows",
                "Desbloquea compileall dentro de run_airdrop_checks.py en Windows/Python 3.11",
            ],
        },
        "0.35.1": {
            "titulo": "Paquete comercial multiformato + cotización base",
            "fecha": "2026-06-24",
            "highlights": [
                "Nuevo módulo `flujo.comercial.multiformato` para generar brief imagen/texto + cotización base",
                "Nuevo comando `flujo brief paquete-cotizacion <job_o_txt>` con salida comercial en markdown",
                "Intake detecta pedidos multiformato con cotización como `paquete_cotizacion`",
                "Extracción de brief evita colapsar estos pedidos a `etiqueta` y conserva formatos detectados",
                "Tests cubren parser, brief y generación de documentos para flyer/etiqueta/pendón/post IG",
            ],
        },
        "0.35.0": {
            "titulo": "Doctor, init fresh y cierre de airdrops más claro",
            "fecha": "2026-06-23",
            "highlights": [
                "Nuevo `flujo doctor` diagnostica entorno local sin correr tests pesados",
                "`flujo init --fresh` prepara workspace, inbox, data, datadrops e índice opcional",
                "run_airdrop_checks.py escribe un resumen final con versión, rama, commit, checks y próximo paso",
                "Tests smoke cubren doctor e init fresh para flujo de primera instalación",
            ],
        },
        "0.34.13": {
            "titulo": "Workflow hardening: verify, hub smoke, Windows CI y resume",
            "fecha": "2026-06-23",
            "highlights": [
                "Nuevo comando `flujo verify` para compileall, pytest, health, version y hub smoke en un solo paso",
                "Nuevo `scripts/hub_smoke.py` prueba /api/ping, SSE concurrente y bloqueo de archivos internos",
                "CI ahora corre en Ubuntu y Windows con `python -m flujo verify`",
                "run_airdrop_checks.py agrega `--resume` para continuar checks/checkpoint tras un apply ya realizado",
                "Servidor del hub ya no expone archivos internos del repo como pyproject.toml o src/*.py por static serving",
            ],
        },
        "0.34.12": {
            "titulo": "Hotfix Windows UTF-8 en CLI",
            "fecha": "2026-06-23",
            "highlights": [
                "Configura stdout/stderr en UTF-8 en Windows antes de crear la consola Rich",
                "Evita UnicodeEncodeError en Git Bash/cp1252 al imprimir advertencias, símbolos y changelog",
                "Desbloquea `flujo health` y `flujo version` dentro de run_airdrop_checks.py",
            ],
        },
        "0.34.11": {
            "titulo": "Hotfix seguridad hub, export ZIP e intake",
            "fecha": "2026-06-23",
            "highlights": [
                "Bloquea path traversal en el servidor del hub y usa ThreadingHTTPServer para no congelar APIs con SSE",
                "export_flyer incluye compose.jsx, compose_ai.jsx y blender_setup.py dentro del ZIP final",
                "Parser de pedidos detecta plano/stand/cotización/cartelera y flyer-import soporta URLs IG con usuario/sin esquema",
                "Índice SQLite inicializa esquema en consultas fresh, setup instala pre-commit y render preserva llaves literales en textos",
            ],
        },
        "0.34.10": {
            "titulo": "Hotfix runner airdrop: evitar sombra scripts/flujo.py",
            "fecha": "2026-06-22",
            "highlights": [
                "run_airdrop_checks.py mantiene src/ por delante de scripts/ en sys.path",
                "El validador se carga por ruta con importlib para no priorizar scripts/",
                "Corrige el error: No module named 'flujo.airdrop'; 'flujo' is not a package",
                "Agrega tests de regresión para evitar que scripts/flujo.py sombree al paquete flujo",
            ],
        },
        "0.34.9": {
            "titulo": "Sincronización de documentación para agentes",
            "fecha": "2026-06-22",
            "highlights": [
                "PARA_IA_CONTEXT, AGENT_GUIDE y CLI quedan sincronizados con v0.34.9",
                "Documenta el flujo real post-airdrop: clonar limpio, instalar, compileall, pytest, health y version",
                "Aclara que rollback de airdrop usa manifest y también elimina archivos NEW",
                "Actualiza comandos de validación con --allow-airdrop-engine para cambios al motor",
            ],
        },
        "0.34.8": {
            "titulo": "Confiabilidad de airdrop, base universal y setup",
            "fecha": "2026-06-21",
            "highlights": [
                "La base universal de proyectos escribe config.json con json.dumps y soporta comillas/texto humano",
                "Rollback de airdrop usa manifest y elimina archivos NEW además de restaurar REPLACE",
                "flujo airdrop apply valida _airdrop/ antes de aplicar; --allow-airdrop-engine queda explícito",
                "Alias real flujo app -> flujo serve y setup más portable entre Windows/Linux",
                "Fallback YAML simple ahora reconoce listas escalares en brief.yaml",
            ],
        },
        "0.34.7": {
            "titulo": "Fix runner Windows/Git Bash",
            "fecha": "2026-06-21",
            "highlights": [
                "run_airdrop_checks.py deja de invocar bash internamente para apply/checkpoint",
                "El runner usa flujo.airdrop en Python puro para dry-run, apply y checkpoint",
                "Mantiene logs en _logs/ y se detiene antes del checkpoint si fallan pruebas",
            ],
        },
        "0.34.6": {
            "titulo": "Mapa del repo e higiene estructural",
            "fecha": "2026-06-21",
            "highlights": [
                "Nuevo docs/REPO_MAP.md para separar núcleo vivo, operación diaria, docs, histórico y generados",
                "Nuevo docs/SCRIPTS_INVENTORY.md para clasificar scripts activos, wrappers y legacy",
                "Nuevo docs/HIGIENE_REPO.md con política de archivos que no deben entrar en airdrops",
                "README/PARA_IA/AGENT_GUIDE apuntan al mapa antes de tocar archivos",
            ],
        },
        "0.34.5": {
            "titulo": "Guardrails de airdrop y logs de error",
            "fecha": "2026-06-21",
            "highlights": [
                "Nuevo validador scripts/validate_airdrop.py para detectar ZIPs vacíos, rutas rotas y archivos generados",
                "Nuevo runner scripts/run_airdrop_checks.py que detiene el flujo si fallan compileall/pytest/health/version",
                "Logs locales en _logs/airdrop_error_*.txt para compartir errores sin deformación por la web",
                "Nuevo protocolo docs/AIRDROP_REVIEW.md y docs/AGENT_AIRDROP_PROTOCOL.md",
            ],
        },
        "0.34.4": {
            "titulo": "Reparación real de CI, dependencias, compileall y versionado",
            "fecha": "2026-06-21",
            "highlights": [
                "CI vuelve a fallar correctamente: sin || true y con compileall",
                "requirements.txt sincronizado con pyproject.toml y sin yt-dlp",
                "project_delivery_manifest.py compatible con Python 3.10/3.11",
                "Versionado y changelog vuelven a estar sincronizados tras hotfixes fallidos",
            ],
        },
        "0.34.3": {
            "titulo": "Checkpoint fallido de reparación CI/deps/compileall",
            "fecha": "2026-06-21",
            "highlights": [
                "Checkpoint histórico conservado; no resolvió los problemas previstos",
                "Reparado posteriormente en v0.34.4",
            ],
        },
        "0.34.2": {
            "titulo": "Hotfix incompleto de higiene CI/deps/versionado",
            "fecha": "2026-06-21",
            "highlights": [
                "Checkpoint histórico conservado; dejó CI/deps y changelog incompletos",
                "Reparado posteriormente en v0.34.4",
            ],
        },
        "0.34.1": {
            "titulo": "Higiene parcial de comandos y docs",
            "fecha": "2026-06-21",
            "highlights": [
                "Corrige algunas referencias legacy de comandos job/render",
                "Dejó pendientes CI, requirements y changelog; reparado posteriormente en v0.34.4",
            ],
        },
        "0.34.0": {
            "titulo": "Limpieza estructural de demos/tests",
            "fecha": "2026-06-21",
            "highlights": [
                "Nuevo script scripts/cleanup_demo_artifacts.sh para eliminar jobs/proyectos de prueba",
                "Política de repo chico: jobs reales quedan fuera de Git; solo se conserva jobs/_template",
                "Mantiene ejemplos intencionales y limpia artefactos etiquetas-acme/pieza-x",
            ],
        },
        "0.33.3": {"titulo": "Hotfix: tests plano_stands.py decodifican UTF-8", "fecha": "2026-06-21", "highlights": ["tests/test_plano_stands.py ahora fuerza encoding utf-8 y PYTHONIOENCODING=utf-8 en el subprocess", "Evita mojibake en Windows cuando el script imprime caracteres Unicode", "Incluye todos los cambios de v0.33.2"]},
        "0.33.2": {"titulo": "Hotfix: encoding UTF-8 en plano_stands.py + flecha ASCII", "fecha": "2026-06-21", "highlights": ["Reemplazada flecha Unicode '->' por '->' en rider de plano para evitar UnicodeEncodeError en Windows cp1252", "plano_stands.py reconfigura stdout/stderr a UTF-8", "Incluye todos los cambios de v0.33.1"]},
        "0.33.1": {"titulo": "Hotfix: plano_stands.py robusto en Windows + tests subprocess", "fecha": "2026-06-21", "highlights": ["plano_stands.py ahora es más robusto al importar flujo.plano (PYTHONPATH + sys.path)", "tests/test_plano_stands.py ahora inyecta PYTHONPATH para el subprocess", "Diagnóstico de errores visible con traceback en stderr"]},
        "0.33.0": {"titulo": "Plano como módulo propio + costos + editor + fixes", "fecha": "2026-06-18", "highlights": ["Motor de planos migrado a src/flujo/plano/ (engine + costs)", "flujo plano ahora usa el módulo directamente (sin subprocess)", "Nuevo flag --costs en flujo plano para desglose de cotización", "Editor visual autocontenido: projects/plano/plano_editor.html", "projects/plano/plano_stands.py delega en flujo.plano", "Fix patrón de tarjeta en privacy/scan.py con validación Luhn", "Cache de repo_root() con lru_cache para mejorar rendimiento", "Nueva ruta plano_base() en paths.py", "Tests para flujo.plano y flujo plano --costs"]},
        "0.32.0": {"titulo": "Airdrop integral: limpieza, plano CLI, docs y fixes", "fecha": "2026-06-18", "highlights": ["Eliminadas carpetas temporales de Instagram commitadas por error", "Nuevo comando: flujo plano <evento.json> (generador de stands)", "Fix advertencia de deprecación Pillow 14 en analyze/colors.py", "Tests para plano_stands.py", "Sincronizadas versiones de README/PARA_IA/AGENT_GUIDE", "Script de limpieza para carpetas temp ig_*", "Fix SyntaxError en scripts/sanitize_sensitive.py", "Motor airdrop ahora permite actualizar .gitignore"]},
        "0.31.0": {"titulo": "Proyecto satélite 'plano' (generador paramétrico)", "fecha": "2026-06-18", "highlights": ["projects/plano/: planos de stands por 'constantes de realidad' (sin AutoCAD)", "Motor headless plano_stands.py: constantes + reglas operativas + layout + SVG", "Rider derivado por reglas (>4h colación, >5h alimentación, +mesa por 5 voluntarios, testeo, masivo)", "Referencia: generador radial de teatro original. Estado: por desarrollar (estilo tapiz)"]},
        "0.30.2": {"titulo": "IG: usuario en URL + descarga + paleta en el editor", "fecha": "2026-06-18", "highlights": ["Detecta instagram.com/<usuario>/p/CODE/", "descarga + paleta en pestaña INSTAGRAM"]},
        "0.30.1": {"titulo": "Fixes editor: IG sin esquema, preview responsive, orientación", "fecha": "2026-06-18", "highlights": ["IG sin https://", "preview responsive", "formatos verticales correctos"]},
        "0.30.0": {"titulo": "Auto-fit de texto + avisos IG + acuse de recibo", "fecha": "2026-06-18", "highlights": ["Auto-fit de texto", "pestañas INSTAGRAM y ACUSE"]},
        "0.29.0": {"titulo": "Auto-checkpoint en Python puro (fix Windows/bash)", "fecha": "2026-06-18", "highlights": ["run_auto_checkpoint sin bash"]},
        "0.28.0": {"titulo": "Editor visual Gradio (src/flujo/web)", "fecha": "2026-06-18", "highlights": ["Editor catálogo -> preview SVG -> exportar"]},
        "0.27.0": {"titulo": "Catálogo oficial de formatos ONG (v2.0)", "fecha": "2026-06-18", "highlights": ["12 formatos area/medio/herramienta"]},
        "0.26.0": {"titulo": "Render rescale + bloque modificacion", "fecha": "2026-06-18", "highlights": ["render rescale proporción/DPI"]},
        "0.25.0": {"titulo": "README maestro + Intake JSON spec", "fecha": "2026-06-18", "highlights": ["intake JSON + schema"]},
        "0.20.0": {"titulo": "Zero-Friction Airdrop System", "fecha": "2026-06-18", "highlights": ["Airdrop automatizado + push"]},
    }
