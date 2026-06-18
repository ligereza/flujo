# AGENTS.md

Ver `docs/AGENT_GUIDE.md` y `docs/CLI.md` — referencia completa.

## Quick start

```bash
py -m pip install -e .
flujo version
flujo health
flujo job new "etiquetas acme" --email inbox/correo.txt
flujo job prepare jobs/<job>
flujo job activate jobs/<job>
flujo render run projects/piezas_vectoriales/<proyecto>/config.json
flujo daily
py -m pytest tests/ -q
```

## Reglas

- No yt-dlp. Solo instaloader.
- Análisis: colores + OCR en `analysis/`
- Privacidad: `flujo privacy scan/sanitize` antes de IAs externas
- Jobs lifecycle: borrador → ... → entregado (ver `docs/JOB_PIPELINE.md`)
