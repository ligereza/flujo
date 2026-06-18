# Comandos — flujo v0.16

## CLI unificada

```bash
flujo --help            # ayuda general
flujo job --help        # subcomandos de jobs
flujo privacy --help    # subcomandos de privacidad
flujo brief --help      # subcomandos de briefs
flujo render --help     # subcomandos de render
```

## Salud / info

```bash
flujo version
flujo health
```

## Intake / flyers

```bash
flujo flyer-import inbox/correo.txt
flujo ig-redownload
flujo analyze                       # último flyer
flujo analyze --all                 # todos
flujo analyze projects/flyer_eventos/<proj>
flujo export <proyecto>
```

## Index / DB

```bash
flujo index --rebuild
flujo index --duplicates
flujo flyer-list
flujo flyer-list --status downloaded_pending_review
```

## Jobs

```bash
flujo job new "etiquetas acme" --email inbox/correo.txt
flujo job prepare jobs/2026-06-17_etiquetas-acme
flujo job prepare jobs/<job> --no-privacy
flujo job list
flujo job list --status listo_para_disenar
flujo job list --examples
flujo job status jobs/<job>
flujo job next
flujo job activate jobs/<job>
flujo job activate jobs/<job> --name mi-proyecto --template rider_eventos_a4_horizontal.config.json
flujo job report jobs/<job>
```

## Privacidad

```bash
flujo privacy scan inbox/correo.txt
flujo privacy sanitize inbox/correo.txt --out inbox/correo_san.txt
flujo privacy check jobs/<job>
```

## Brief

```bash
flujo brief extract jobs/<job>
flujo brief to-project jobs/<job>/brief.yaml
flujo brief to-project jobs/<job>/brief.yaml --name mi-proyecto --template X
flujo brief show jobs/<job>/brief.yaml
```

## Render

```bash
flujo render validate projects/.../config.json
flujo render run projects/.../config.json
flujo render formats                                # listar todos
flujo render formats -w 16.5 -h 6.5 -t etiqueta     # sugerir
flujo render formats -w 21 -h 29.7                  # sin tipo
```

## Dashboard

```bash
flujo daily
flujo daily --md context/DAILY.md --html context/dashboard.html
```

## Otros

```bash
flujo init            # crear jobs/_template
flujo clean           # limpiar __pycache__
flujo clean --generated  # limpiar salida_generada/
flujo serve           # interfaz web Gradio
```

## Tests

```bash
py -m pytest tests/ -q
py -m pytest tests/test_jobs_brief.py -q
py -m pytest tests/test_cli_smoke.py -q
```

## Versionado

```bash
flujo version            # versión actual + changelog
```
