# Checkpoint — airdrop v2: instaloader-only + docs + ig_redownload

Fecha: 2026-06-16_21-36

## Estado

# Estado del proyecto

Última actualización: 2026-06-16

## Objetivo actual

Mantener un repo limpio que organice proyectos creativos, automatizaciones y flujos con IA. No reemplaza el trabajo manual; acelera el inicio y evita perder contexto entre sesiones.

## Herramientas activas

1. `flyer_eventos` — importar proyectos desde correos/Instagram, mantener estructura y manifest. **Descarga automática con instaloader únicamente.**
2. `piezas_vectoriales` — generar etiquetas, flyers y riders en SVG editable + vectorizado desde JSON.
3. `jobs` — flujo de pedidos: brief → privacidad → preparación → proyecto → render.

## Herramientas en cola

- `slowmo_blender_ae` — todavía no activa.
- `asistente_pedido` — todavía no activa.
- `canva_data` — todavía no activa.
- `privacidad_datos` — MVP disponible, en evolución.

## Regla

No importar scripts viejos automáticamente. Usar `reference_old` solo como referencia manual.

## Próximos pasos completados (fase 1-10)

- [x] Limpiar historial de git.
- [x] Tests mínimos de smoke.
- [x] Portabilidad Windows/macOS/Linux.
- [x] Dependencias documentadas.
- [x] Helpers comunes, comando unificado flujo.py
- [x] Pre-commit hooks, health check
- [x] .gitattributes, licencia MIT
- [x] CI / docs de agentes
- [x] Pipeline automático correo → job → proyecto → render
- [x] Descarga Instagram automática
- [x] Dashboard diario + interfaz Gradio

## Fase 11 — Instagram instaloader-only (completada 2026-06-16)

- [x] Eliminar yt-dlp completamente del repo
- [x] Dejar solo instaloader como downloader
- [x] Descarga carrusel completo + caption
- [x] Manifest guarda owner, date_utc, file_count
- [x] Script `ig_redownload.py` para reintentar fallidos
- [x] `flyer_status.py` mejorado con info IG
- [x] Documentación `docs/INSTALOADER.md`
- [x] README / PARA_IA / AGENTS unificados a `py`
- [x] `start.sh` portable (detecta py/python3)
- [x] `tools/flyer_eventos/SPEC.md` actualizado

Dependencias actuales (ligeras):
- matplotlib
- pyyaml
- gradio
- instaloader

Sin yt-dlp, sin ffmpeg, sin venvs de 400 MB.

## Próximos pasos (fase 12)

- [ ] Extraer colores dominantes del flyer descargado
- [ ] OCR básico para extraer fecha/lugar/texto del flyer
- [ ] Generar palette.json automático en `analysis/`
- [ ] Mejorar `ig_redownload.py` con backoff exponencial
- [ ] Considerar eliminar `reference_old` y `projects/tapiz`
- [ ] Test automático para ig_download (mock)

## Notas

- Comando oficial: `py` en Windows, `python3` en Linux/macOS
- Instalación: `py -m pip install -r requirements.txt`
- Interfaz web: `py scripts/app.py` o `bash start.sh`
- Después de cada mejora: `bash scripts/checkpoint.sh "mensaje"`

## Cambios realizados

-

## Próximo paso

-
