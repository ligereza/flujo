# Herramienta — flyer_eventos

Estado: flujo base funcional / descarga automática + análisis + export activos
Prioridad: alta
Versión: 0.14

## Objetivo

Ordenar y acelerar el flujo de flyers para eventos sin quitar control manual al diseñador.

El flujo real parte muchas veces desde un correo del jefe que contiene uno o varios links de Instagram. Cada link apunta al flyer base que será usado como referencia/input.

## Idea

```
correo con links Instagram
> extraer links
> crear proyecto por link
> descargar automáticamente con instaloader
> guardar manifest + caption
> marcar revisión manual
> preparar input
> Photoshop manual/semi-automático
> Blender manual/semi-automático
> export final para jefe
```

## Información que interesa rescatar

- nombre del evento
- productora / usuario que publicó (owner de IG)
- lugar o venue
- fecha
- tipo de publicación: post, reel, tv
- si parece imagen/carrusel/video
- caption completo
- archivos descargados

## Casos especiales

- Post normal `/p/`: puede ser imagen o carrusel.
- Reel `/reel/`: probablemente video.
- TV `/tv/`: probablemente video.
- Perfil privado / shadowban / login requerido: descarga manual.
- Rate limit Instagram: reintentar más tarde con `ig_redownload.py`
- Flyer sin ubicación escrita: queda pendiente para revisión manual.

## Estructura de proyecto

```
projects/flyer_eventos/YYYY-MM-DD_ig_SHORTCODE/
├─ input/
│  ├─ input_ig.jpg
│  ├─ input_ig_2.jpg ... (carrusel)
│  ├─ input_ig_video.mp4
│  └─ ig_caption.txt
├─ working/
├─ exports/
├─ refs/
├─ analysis/
├─ ai/
├─ manifest.json
└─ README.md
```

## Scripts actuales

Crear proyecto manual:

```
bash scripts/new_flyer_evento.sh "nombre evento"
```

Crear proyectos desde correo (con descarga automática):

```
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
# o
flujo flyer-import inbox/correo_prueba.txt
```

Reintentar descargas fallidas:

```
py scripts/ig_redownload.py
# o
flujo ig-redownload
```

Analizar flyer (colores + OCR):

```
py scripts/flyer_analyze.py
# o
flujo analyze
flujo analyze --all
```

Indexar flyers en SQLite:

```
flujo index --rebuild
flujo flyer-list
```

Exportar proyecto a ZIP para Photoshop:

```
flujo export projects/flyer_eventos/2026-06-16_ig_XXXX
```

Listar proyectos:

```
bash scripts/flyer_list.sh
```

Último proyecto:

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

Generar índice de proyectos:

```
bash scripts/flyer_index.sh
```

Detectar duplicados:

```
bash scripts/flyer_duplicates_report.sh
```

Abrir último proyecto en Explorer:

```
bash scripts/flyer_open_latest.sh
```

Descarga directa IG:

```
py scripts/ig_download.py "https://www.instagram.com/p/XXXX/" ./output
```

## Estado actual

- [x] Crear proyecto manual.
- [x] Crear carpetas con `.gitkeep`.
- [x] Copiar imagen input demo.
- [x] Actualizar `manifest.json`.
- [x] Listar proyectos.
- [x] Detectar último proyecto.
- [x] Leer correo `.txt`.
- [x] Extraer links Instagram.
- [x] Detectar tipo `/p/`, `/reel/`, `/tv/`.
- [x] Guardar `media_guess`.
- [x] Marcar revisión manual.
- [x] Aplicar mejoras por `_airdrop/`.
- [x] Evitar duplicados por URL/shortcode.
- [x] Descarga automática con instaloader.
- [x] Guardar carrusel completo + caption.
- [x] Reintento de descargas fallidas `ig_redownload.py`.
- [x] Extraer colores dominantes → `analysis/palette.json`
- [x] Extraer texto OCR del flyer → `analysis/ocr.txt` (opcional)
- [x] Export ZIP listo para Photoshop → `flujo export`
- [x] Paleta exportable `.aco` / `.ase` para PS / AI
- [x] Índice SQLite de flyers → `flujo index`
- [ ] Preparar integración Blender.

## Descarga Instagram

- Solo **instaloader**, sin yt-dlp.
- Soporta posts, reels, carruseles.
- Archivos: `input_ig.jpg`, `input_ig_2.jpg`..., `input_ig_video.mp4`, `ig_caption.txt`
- Manifest guarda: owner, date_utc, media_type, file_count
- Ver `docs/INSTALOADER.md`

## Análisis automático

- Colores dominantes con Pillow → `analysis/palette.json` + `palette.png`
- OCR opcional con pytesseract → `analysis/ocr.txt` + `ocr_hints.json`
- Comando: `flujo analyze` / `py scripts/flyer_analyze.py`
- Ver `docs/ANALISIS.md`

## Reglas

- No automatizar Photoshop/Blender todavía.
- No borrar archivos sin confirmación.
- No intentar saltar privacidad/login de Instagram.
- Si una publicación no se puede descargar, marcar `manual_download_needed`.
- Cada cambio debe terminar en checkpoint.
- Solo instaloader. No volver a yt-dlp.
