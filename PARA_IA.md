# PARA IA — Cómo continuar este repo

Este repo se llama `flujo`.

Su idea central es: **Dimensiones del Orden**.

Funciona como una zapatilla/alargador organizador para proyectos creativos, automatizaciones e IAs.

No reemplaza el trabajo manual del diseñador. Ordena contexto, proyectos, herramientas, inputs, outputs y checkpoints para no empezar desde cero en cada chat.

## Leer en este orden

1. `README.md`
2. `docs/DIMENSIONES_DEL_ORDEN.md`
3. `context/ESTADO.md`
4. último archivo en `checkpoints/`
5. herramienta activa en `tools/flyer_eventos/SPEC.md`

## Estado actual

La herramienta activa es:

```
flyer_eventos
```

Descarga Instagram: **instaloader únicamente, sin yt-dlp**.

## Flujo actual probado

Crear proyecto manual:

```
bash scripts/new_flyer_evento.sh "nombre evento"
```

O con el comando unificado:

```
py scripts/flujo.py new-flyer "nombre evento"
```

Crear proyectos desde correo con links de Instagram:

```
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
```

Forzar duplicado solo si hace falta:

```
py scripts/flyer_from_email.py "inbox/correo_prueba.txt" --force
```

Reintentar descarga IG en fallidos:

```
py scripts/ig_redownload.py
```

Listar proyectos:

```
bash scripts/flyer_list.sh
```

Ver último proyecto:

```
bash scripts/flyer_latest.sh
```

Setear imagen demo en último proyecto:

```
bash scripts/flyer_set_input_latest_demo.sh
```

Ver estado del último proyecto:

```
bash scripts/flyer_status_latest.sh
```

Generar índice de proyectos flyer:

```
bash scripts/flyer_index.sh
```

Reportar duplicados:

```
bash scripts/flyer_duplicates_report.sh
```

Abrir último proyecto flyer en Explorer:

```
bash scripts/flyer_open_latest.sh
```

Ver estado general:

```
bash scripts/orden_status.sh
```

Aplicar paquete de mejoras airdrop:

```
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
```

Guardar avance:

```
bash scripts/checkpoint.sh "mensaje"
```

Iniciar interfaz web:

```
py scripts/app.py
# o
bash start.sh
```

## Qué ya hace

- Crea estructura de proyectos flyer.
- Mantiene carpetas con `.gitkeep`.
- Crea carpetas `analysis/` y `ai/` en proyectos nuevos.
- Copia imagen input demo.
- Actualiza `manifest.json`.
- Lista proyectos.
- Detecta último proyecto.
- Lee un correo `.txt`.
- Extrae links de Instagram.
- Crea un proyecto por cada link nuevo.
- Evita duplicados por URL/shortcode salvo uso de `--force`.
- Detecta tipo de link: `/p/`, `/reel/`, `/tv/`.
- Marca `media_guess`: imagen/carrusel posible o video posible.
- **Descarga automática con instaloader** (sin yt-dlp).
- Guarda carrusel completo y caption en `ig_caption.txt`.
- Marca proyectos como `from_email_pending_download` o `downloaded_pending_review`.
- Permite aplicar mejoras completas mediante `_airdrop/`.
- Genera índice JSON en `data/flyer_index.json`.
- Genera reporte de duplicados en `data/flyer_duplicates_report.json`.
- Script `ig_redownload.py` para reintentar descargas fallidas.
- Helpers comunes en `scripts/_common.py`.
- Comando unificado en `scripts/flujo.py`.
- Tests de smoke en `tests/test_smoke.py`.
- Pre-commit hooks para validar cambios.

## Nueva herramienta disponible: piezas_vectoriales

Además de `flyer_eventos`, existe una herramienta para pedidos de impresión/Illustrator:

```
tools/piezas_vectoriales/SPEC.md
```

Usarla cuando el usuario pegue un correo o pida:

- etiquetas,
- flyers impresos,
- stickers,
- SVG editables,
- SVG vectorizados,
- letras convertidas a trazados,
- archivos listos para Illustrator/imprenta.

Flujo:

```
brief/correo → config JSON → SVG editable → SVG vectorizado → ZIP/export
```

Comandos:

```
py scripts/piezas_generar.py "projects/piezas_vectoriales/etiquetas_ejemplo/config.json"
py scripts/piezas_check_outputs.py
```

Proyecto real incluido:

```
projects/piezas_vectoriales/suplementos_rd/
```

Para ese proyecto:

```
cd projects/piezas_vectoriales/suplementos_rd
py scripts/generar_flyers.py
```

## Qué NO hace todavía

- No analiza la imagen/video automáticamente.
- No extrae texto del flyer (OCR).
- No abre Photoshop.
- No abre Blender.
- No borra archivos.
- No limpia duplicados automáticamente.

Ya NO aplica: ~~No descarga Instagram automáticamente~~ → **Sí descarga, con instaloader**.

## Descarga automática de Instagram

`flyer_from_email.py` descarga posts públicos de Instagram automáticamente usando **`instaloader` únicamente**.

Si falla (privado, login, rate limit), marca el proyecto para descarga manual.

Archivos generados:
- `input/input_ig.jpg` (primera imagen)
- `input/input_ig_2.jpg`, `input_ig_3.jpg` ... (carrusel)
- `input/input_ig_video.mp4` (si hay video)
- `input/ig_caption.txt`

Manifest guarda: `owner`, `date_utc`, `media_type`, `file_count`.

Reintentar descargas fallidas:
```
py scripts/ig_redownload.py
```

Ver guía completa: `docs/INSTALOADER.md`

## Dashboard diario

Generar reporte y dashboard visual:

```
py scripts/flujo.py daily
```

Salidas:

- `context/DAILY.md` — resumen en Markdown.
- `context/dashboard.html` — dashboard visual para abrir en el navegador.

## Sistema airdrop

Para acelerar cambios:

1. Crear archivos dentro de `_airdrop/` respetando rutas.
2. Probar:

```
bash scripts/apply_airdrop.sh --dry-run
```

3. Aplicar:

```
bash scripts/apply_airdrop.sh --apply
```

4. Guardar:

```
bash scripts/checkpoint.sh "aplicar mejoras airdrop"
```

## Reglas

- Avanzar paso a paso.
- No hacer cambios gigantes.
- No automatizar Photoshop/Blender todavía.
- No subir archivos pesados.
- No borrar nada sin confirmación.
- Usar `py` en Windows, `python3` en Linux/macOS.
- Mantener compatibilidad con Git Bash en Windows.
- Después de cada mejora pequeña, hacer checkpoint.
- **Solo instaloader para descargas. No volver a yt-dlp.**

## Próximo paso recomendado

Flujo de análisis / manual review post-descarga:

- Si el post es público y simple, descarga automática ya funciona.
- Siguiente: extraer colores dominantes, dimensiones, texto OCR.
- Mantener revisión humana antes de Photoshop/Blender.
- Mejorar `ig_redownload.py` con backoff si hay rate limit.
