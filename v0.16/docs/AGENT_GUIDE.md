# AGENT_GUIDE — flujo

**Repo:** `flujo` — arte + automatización · v0.16

## Stack

- Python 3.10+
- `py -m pip install -e .` (instala en editable)
- CLI: `flujo` (Typer)
- Descarga IG: solo instaloader
- Tests: pytest

## Comandos esenciales

```bash
flujo version              # ver versión + changelog
flujo health               # chequeo general del repo
flujo job new "x" --email f   # crear job desde correo
flujo job prepare jobs/X      # pipeline: privacidad → brief → estado
flujo job activate jobs/X     # brief → proyecto
flujo render run cfg.json     # renderizar
flujo render formats          # listar plantillas
flujo analyze                 # colores + OCR de flyers
flujo privacy scan file.txt   # escanear PII
flujo daily                   # dashboard
flujo serve                   # interfaz web Gradio
```

Ayuda siempre disponible:

```bash
flujo --help
flujo job --help
flujo render --help
```

## Reglas

- No automatizar Photoshop / Illustrator / Blender
- Solo instaloader (no yt-dlp)
- Mantener checkpoints (`bash scripts/checkpoint.sh "msg"`)
- Privacidad primero: `flujo privacy` antes de IA externa
- Toda la lógica debería estar en `src/flujo/`, no en scripts sueltos
- Tests para nuevos módulos

## Documentación interna

- `docs/CLI.md` — referencia completa de la CLI
- `docs/JOB_PIPELINE.md` — ciclo de vida de jobs
- `docs/RELEASE_v016.md` — release notes v0.16
- `docs/ESTADOS_JOB.md` — estados y transiciones
- `docs/ANALISIS.md` — análisis de colores y OCR
- `docs/OPERADOR_IA_RAPIDO.md` — cheat sheet para IAs

---

**Última actualización:** Junio 2026
