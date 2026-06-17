# AIRDROP v2 – flujo instaloader-only + mejoras

Fecha: 2026-06-16

## Qué corrige

1. **start.sh** – Ya NO usa `./.venv/Scripts/python`. Ahora detecta automáticamente `py` / `python3` / `python`. Este era el script que te corrompió el ENV de 400 MB.

2. **Comandos unificados a `py`** – README.md, PARA_IA.md, AGENTS.md todos actualizados a `py` (Windows) con nota `python3` para Linux/macOS. Se eliminó la confusión python3/py mezclada.

3. **Documentación Instagram actualizada** – PARA_IA.md ya NO dice "No descarga Instagram automáticamente". Ahora dice que SÍ descarga, con instaloader únicamente.

4. **tools/flyer_eventos/SPEC.md** – checklist actualizado, descarga automática marcada como completada, estructura de proyecto con carrusel + caption.

## Mejoras nuevas

### scripts/flyer_from_email.py
- Nombre de proyecto: `ig_<shortcode>` en lugar de `email_evento_01` (más trazable)
- Guarda en manifest: `owner`, `date_utc`, `media_type`, `file_count`
- Guarda `producer_suggested` desde owner de IG
- Compatible con descarga carrusel

### scripts/ig_download.py
- Versión instaloader-only pulida
- Detecta `rate_limit` (429)
- Devuelve `file_count`, `owner`, `date`
- Guarda carrusel completo

### scripts/flyer_status.py
- Muestra info Instagram: owner, fecha, media_type, file_count
- Lista archivos `input_ig*` encontrados físicamente
- Preview de caption (120 chars)
- Muestra `producer_suggested` y `caption_from_ig`

### scripts/ig_redownload.py (NUEVO)
- Reintenta descargas fallidas en todos los proyectos flyer
- `py scripts/ig_redownload.py` – solo pendientes
- `py scripts/ig_redownload.py --all` – todos
- `py scripts/ig_redownload.py --project projects/flyer_eventos/XXXX`
- Actualiza manifest con `download_retry_at`

### scripts/flujo.py
- Nuevo comando: `ig-redownload`
- `py scripts/flujo.py ig-redownload`

### docs/INSTALOADER.md (NUEVO)
- Guía completa de descarga IG
- Errores comunes y soluciones
- Buenas prácticas rate limit
- Por qué solo instaloader, no yt-dlp

### context/ESTADO.md
- Fase 11 marcada como completada (Instagram instaloader-only)
- Fase 12 con próximos pasos: colores dominantes, OCR, palette.json

### requirements.txt
- Comentario actualizado a `py -m pip install`
- Sin yt-dlp, solo: matplotlib, pyyaml, gradio, instaloader

## Archivos en este airdrop

```
README.md
PARA_IA.md
AGENTS.md
requirements.txt
start.sh
context/ESTADO.md
tools/flyer_eventos/SPEC.md
docs/INSTALOADER.md
scripts/ig_download.py
scripts/flyer_from_email.py
scripts/flyer_status.py
scripts/flujo.py
scripts/ig_redownload.py
```

## Aplicar

```bash
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
py scripts/flujo.py health
py -m pytest tests/ -q
bash scripts/checkpoint.sh "airdrop v2: instaloader-only + docs + ig_redownload"
```

## Test rápido

```bash
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
bash scripts/flyer_status_latest.sh
py scripts/ig_redownload.py
```

---
flujo – Dimensiones del Orden
