# Checkpoint — flujo v0.14 - analisis + index + export

Fecha: 2026-06-16_23-13

## Estado

# Estado del proyecto

Última actualización: 2026-06-16 — flujo v0.14

## Objetivo

Arte y automatización. Un tapiz donde los proyectos respiran.

No reemplaza la mano del diseñador. Guarda contexto, inputs, checkpoints.

## Herramientas activas

1. `flyer_eventos` — importar desde Instagram, descarga automática instaloader-only, análisis automático
2. `piezas_vectoriales` — etiquetas / flyers SVG editable + vectorizado
3. `jobs` — brief → privacidad → proyecto → render

## Stack actual (v0.14)

- Python package: `src/flujo/`, instalable con `py -m pip install -e .`
- CLI: `flujo` (Typer + Rich)
- Modelos: Pydantic `Manifest`
- Descarga IG: instaloader únicamente
- Análisis: colores dominantes + OCR opcional
- Index: SQLite `data/flujo.db`
- Export: ZIP listo para Photoshop
- Docs unificadas: `docs/AGENT_GUIDE.md`

Dependencias: matplotlib / pyyaml / gradio / instaloader / pydantic / typer / rich

Sin yt-dlp. Sin venvs de 400 MB.

## Completado (v0.14)

- [x] Estructura pro pyproject.toml + src/
- [x] CLI unificado Typer
- [x] Manifest validado con Pydantic
- [x] IG download con retry/backoff
- [x] README artístico + TAPIZ.md separado
- [x] Docs unificadas AGENT_GUIDE.md
- [x] .gitignore corregido (permite imágenes en docs/)
- [x] shims de compatibilidad para scripts legacy
- [x] Análisis automático de flyers
- [x] Colores dominantes → `analysis/palette.json` + `palette.png`
- [x] Export palette `.aco` (Photoshop) + `.ase` (Illustrator)
- [x] OCR opcional con pytesseract → `analysis/ocr.txt`
- [x] Comando `flujo analyze`
- [x] **Índice SQLite** → `flujo index --rebuild`
- [x] **Export ZIP** → `flujo export <proyecto>`
- [x] Tests: color, index, export

## Próximo (fase 14)

- [ ] Gradio con auth
- [ ] Tests unitarios ig_download con mock
- [ ] OCR con EasyOCR (sin tesseract externo)
- [ ] Detección de layout / bounding boxes
- [ ] Publicar a PyPI

## Comando

```
flujo health
flujo flyer-import inbox/correo.txt
flujo ig-redownload
flujo analyze
flujo index --rebuild
flujo export projects/flyer_eventos/2026-06-16_ig_XXXX
flujo app
```

Ver `docs/AGENT_GUIDE.md`

## Cambios realizados

-

## Próximo paso

-
