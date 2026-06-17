# AGENT_GUIDE — flujo

> Para IAs que trabajan en este repo. Lee esto primero.

Repo: `flujo` — **arte y automatización**
Objetivo: Dimensiones del Orden — que los proyectos creativos no empiecen desde cero.

## Stack

- Python 3.10+
- `py -m pip install -e .`
- Deps: matplotlib / pyyaml / gradio / instaloader / pydantic / typer / rich
- **Solo instaloader. No yt-dlp.**

## Comandos (nuevo CLI)

```
flujo health
flujo flyer-import inbox/correo.txt
flujo flyer-list
flujo ig-redownload
flujo daily
flujo app
flujo new-flyer "nombre evento"
```

Legacy (todavía funciona):
```
py scripts/flyer_from_email.py "inbox/correo.txt"
bash scripts/flyer_list.sh
```

## Estructura

```
tools/flyer_eventos/     # SPEC de la herramienta activa
projects/flyer_eventos/YYYY-MM-DD_ig_SHORTCODE/
  input/
    input_ig.jpg
    input_ig_2.jpg ...
    ig_caption.txt
  working/ exports/ refs/ analysis/ ai/
  manifest.json
src/flujo/
  models.py      # Manifest pydantic
  flyer/         # crear proyecto, importar email
  ig/download.py # instaloader only
  cli.py         # Typer
```

## Flujo flyer_eventos

1. Correo con links IG → `flujo flyer-import inbox/correo.txt`
2. Se crea `projects/flyer_eventos/ig_<shortcode>/`
3. Descarga automática con instaloader
4. Manifest guarda: owner, date_utc, media_type, file_count, caption
5. Si falla: `manual_download_possible = true`
6. Reintentar: `flujo ig-redownload`

## Manifest (pydantic)

```python
from flujo.models import Manifest
```

Campos clave: `tool`, `name`, `status`, `instagram.url`, `instagram.owner`, `instagram.download_status`, `extracted_info.caption_from_ig`

Siempre usar `flujo.manifest.load_manifest / save_manifest` – preserva campos desconocidos.

## Piezas vectoriales

Segunda herramienta: etiquetas / Illustrator / SVG

```
tools/piezas_vectoriales/SPEC.md
flujo render projects/piezas_vectoriales/etiquetas_ejemplo/config.json
```

## Reglas

- Paso a paso. Sin cambios gigantes.
- No Photoshop / Blender automático todavía.
- No borrar sin confirmación.
- `py` en Windows / `python3` en Linux/macOS
- Checkpoint después de cada mejora: `bash scripts/checkpoint.sh "mensaje"`
- Solo instaloader. No volver a yt-dlp.
- Validar manifests con pydantic, no dicts sueltos.
- Tests antes de commit: `pytest -q`

## Dónde leer

1. `README.md` – presentación
2. `docs/AGENT_GUIDE.md` – este archivo
3. `docs/DIMENSIONES_DEL_ORDEN.md`
4. `context/ESTADO.md`
5. `tools/flyer_eventos/SPEC.md`

Tapiz ASCII: `docs/TAPIZ.md`

---
flujo — arte + automatización
