# AGENTS.md

**Punto de entrada obligatorio (diario):** `flujo app` (lanza la app real + sirve el hub pro workspace + APIs).
O abre `context/flujo_hub.html` directamente (fallback estático).

El hub (dentro de la app) es el workspace central: intake de pedidos, visualizadores SVG embebidos por grupos, plano demo interactivo, comandos y sección para delegar a agentes especializados. Hub = pro workspace dentro de `flujo app`.

## Quick start (agentes)

1. Ejecuta `flujo app` (o `flujo app --desktop`) — entrada diaria obligatoria que sirve el hub.
2. Leer `context/LAST_HANDOFF.md` (estado actual + tareas)
3. Leer `docs/AGENT_OPERATING_MANUAL.md` (dos flujos + modelo formal delegación a agentes especializados)
4. Usar el hub (dentro de la app) para pegar pedidos → match + comandos → visualizers → export. Usar sección "Delegar..." para copiar prompts completos por rol.

```bash
py -m pip install -e .
flujo version
flujo health
flujo daily
flujo app
# Todo lo demás se hace desde el hub o copiando comandos/prompts que genera
```

## Delegación

El hub contiene botones para generar y copiar prompts listos para:
- Visual Polish Agent
- Pipeline & Integration Agent
- Brand Guardian
- Future/Modern Agent

Ver modelo completo en AGENT_OPERATING_MANUAL.md. Lanza en clones paralelos.

## Reglas

- No yt-dlp. Solo instaloader.
- Análisis: colores + OCR en `analysis/`
- Privacidad: `flujo privacy scan/sanitize` antes de IAs externas
- Jobs lifecycle: borrador → ... → entregado (ver `docs/JOB_PIPELINE.md`)
- Siempre empezar por `flujo app` + hub + LAST_HANDOFF para ahorrar tokens.
