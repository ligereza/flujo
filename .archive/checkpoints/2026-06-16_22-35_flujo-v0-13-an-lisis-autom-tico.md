# Checkpoint — flujo v0.13 - análisis automático

Fecha: 2026-06-16_22-35

## Estado

# Estado del proyecto

Última actualización: 2026-06-16 — flujo v0.12 pro

## Objetivo

Arte y automatización. Un tapiz donde los proyectos respiran.

No reemplaza la mano del diseñador. Guarda contexto, inputs, checkpoints.

## Herramientas activas

1. `flyer_eventos` — importar desde Instagram, descarga automática instaloader-only
2. `piezas_vectoriales` — etiquetas / flyers SVG editable + vectorizado
3. `jobs` — brief → privacidad → proyecto → render

## Stack actual (v0.12)

- Python package: `src/flujo/`, instalable con `py -m pip install -e .`
- CLI: `flujo` (Typer + Rich)
- Modelos: Pydantic `Manifest`
- Descarga IG: instaloader únicamente
- Docs unificadas: `docs/AGENT_GUIDE.md`

Dependencias: matplotlib / pyyaml / gradio / instaloader / pydantic / typer / rich

Sin yt-dlp. Sin venvs de 400 MB.

## Completado (v0.13)

- [x] Estructura pro pyproject.toml + src/
- [x] CLI unificado Typer
- [x] Manifest validado con Pydantic
- [x] IG download con retry/backoff
- [x] README artístico + TAPIZ.md separado
- [x] Docs unificadas AGENT_GUIDE.md
- [x] .gitignore corregido (permite imágenes en docs/)
- [x] shims de compatibilidad para scripts legacy
- [x] **Análisis automático de flyers**
- [x] Colores dominantes → `analysis/palette.json` + `palette.png`
- [x] OCR opcional con pytesseract → `analysis/ocr.txt`
- [x] Comando `flujo analyze`

## Próximo (fase 13)

- [ ] SQLite index para flyers (`flujo index`)
- [ ] Gradio con auth
- [ ] Tests unitarios ig_download con mock
- [ ] Export ZIP listo para Photoshop
- [ ] Palette export .aco / .ase para Photoshop/Illustrator

## Comando

```
flujo health
flujo flyer-import inbox/correo.txt
flujo ig-redownload
flujo analyze
flujo app
```

Ver `docs/AGENT_GUIDE.md`

## Cambios realizados

-

## Próximo paso

-
