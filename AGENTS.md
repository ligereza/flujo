# AGENTS.md

**Punto de entrada obligatorio:** abre `context/flujo_hub.html`

Este es el workspace central del repo (intake de pedidos, visualizadores SVG embebidos por grupos, plano demo interactivo, comandos y datos crudos para agentes).

## Quick start (agentes)

1. Abrir `context/flujo_hub.html`
2. Leer `context/LAST_HANDOFF.md` (estado actual + tareas)
3. Leer `docs/AGENT_OPERATING_MANUAL.md` (dos flujos: pedido reciente + mejoras continuas)
4. Usar el hub para pegar pedidos → match de formatos + comandos listos

```bash
py -m pip install -e .
flujo version
flujo health
flujo daily
# Todo lo demás se hace desde el hub o copiando comandos que genera
```

## Reglas

- No yt-dlp. Solo instaloader.
- Análisis: colores + OCR en `analysis/`
- Privacidad: `flujo privacy scan/sanitize` antes de IAs externas
- Jobs lifecycle: borrador → ... → entregado (ver `docs/JOB_PIPELINE.md`)
- Siempre empezar por el hub + LAST_HANDOFF para ahorrar tokens.
