# PARA IA

Este repo se llama **flujo** — arte y automatización. v0.16.

Lee primero: `docs/AGENT_GUIDE.md` y `docs/CLI.md`.

Resumen rápido:

```bash
flujo version
flujo health
flujo flyer-import inbox/correo.txt
flujo analyze
flujo job new "pedido" --email inbox/correo.txt
flujo job prepare jobs/<job>
flujo job activate jobs/<job>
flujo render run projects/piezas_vectoriales/<proyecto>/config.json
flujo daily
```

Herramienta activa: `flyer_eventos` — descarga Instagram con **instaloader únicamente**.
Análisis automático: colores dominantes + OCR → `analysis/`
Privacidad: `flujo privacy` antes de enviar texto a IAs externas.

Documentación completa en `docs/AGENT_GUIDE.md`, `docs/CLI.md`, `docs/JOB_PIPELINE.md`,
`README.md`, `context/ESTADO.md`, `docs/RELEASE_v016.md`.

**No uses yt-dlp. No crees venvs pesados. Usa `py`.**
