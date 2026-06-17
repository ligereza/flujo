# flujo — Dimensiones del Orden

![CI](https://github.com/ligereza/flujo/actions/workflows/ci.yml/badge.svg)![Render](https://github.com/ligereza/flujo/actions/workflows/render_piezas_vectoriales.yml/badge.svg)

Repositorio para ordenar proyectos creativos, automatizaciones e IAs.

Funciona como una **zapatilla/alargador organizador**: conecta proyectos, herramientas, contexto y checkpoints en un solo lugar.

No reemplaza el trabajo manual. Ayuda a no empezar desde cero.

## Entrada rápida

Si eres una IA o asistente, lee primero:

```
PARA_IA.md
```

Luego lee:

```
docs/DIMENSIONES_DEL_ORDEN.md
context/ESTADO.md
tools/flyer_eventos/SPEC.md
```

## Instalación

Dependencias:

```
py -m pip install -r requirements.txt
```

En Linux/macOS usa `python3` en lugar de `py`.

## Herramienta activa

```
flyer_eventos
```

## Comandos actuales

> **Nota sobre `python`**: en Windows usa `py`. En Linux/macOS usa `python3`.

## Pipeline inteligente (recomendado)

Si recibes un correo con un pedido de diseño/impresión, el pipeline puede crear el job, inferir el tipo de pieza y medidas, y generar SVGs automáticamente:

```
py scripts/flujo_pipeline.py "nombre pedido" inbox/correo.txt
```

Para aplicar inferencias sin preguntar:

```
py scripts/flujo_pipeline.py "nombre pedido" inbox/correo.txt --confirm
```

Palabras clave soportadas: `etiqueta`, `flyer`, `sticker`, `rider`, `carrusel`, `dossier`, `one page`, `presentacion`, `tarjeta`.

Crear proyecto flyer manual:

```
bash scripts/new_flyer_evento.sh "nombre evento"
```

Crear proyectos desde correo con links de Instagram (descarga automática con instaloader):

```
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
```

Forzar duplicado si realmente lo necesitas:

```
py scripts/flyer_from_email.py "inbox/correo_prueba.txt" --force
```

Reintentar descarga de IG en proyectos fallidos:

```
py scripts/ig_redownload.py
py scripts/ig_redownload.py --all
```

Listar flyers:

```
bash scripts/flyer_list.sh
```

Ver último flyer:

```
bash scripts/flyer_latest.sh
```

Setear input demo en último flyer:

```
bash scripts/flyer_set_input_latest_demo.sh
```

Ver status del último flyer:

```
bash scripts/flyer_status_latest.sh
```

Generar índice de flyers:

```
bash scripts/flyer_index.sh
```

Detectar duplicados:

```
bash scripts/flyer_duplicates_report.sh
```

Abrir último flyer en Explorer:

```
bash scripts/flyer_open_latest.sh
```

Ver estado general del orden:

```
bash scripts/orden_status.sh
```

Aplicar mejoras por airdrop:

```
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
```

Guardar avance:

```
bash scripts/checkpoint.sh "mensaje"
```

Comando unificado (salud, limpieza, jobs, etc.):

```
py scripts/flujo.py health
```

Iniciar interfaz web Gradio:

```
py scripts/app.py
# o
bash start.sh
```

## Flujo actual recomendado

```
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
bash scripts/flyer_list.sh
bash scripts/flyer_index.sh
bash scripts/flyer_duplicates_report.sh
bash scripts/flyer_status_latest.sh
bash scripts/checkpoint.sh "mensaje"
```

## Herramienta adicional: piezas vectoriales / archivos de impresión

Para etiquetas, flyers de impresión, SVG editables, SVG vectorizados y archivos para Illustrator:

```
tools/piezas_vectoriales/SPEC.md
```

Generar proyecto genérico desde JSON:

```
py scripts/piezas_generar.py "projects/piezas_vectoriales/etiquetas_ejemplo/config.json"
```

Generar proyecto real Suplementos RD:

```
cd projects/piezas_vectoriales/suplementos_rd
py scripts/generar_flyers.py
```

Validar salidas vectoriales:

```
py scripts/piezas_check_outputs.py
```

Para pedirle trabajo a otra IA con un correo del jefe, usar:

```
briefs/PROMPT_PARA_OTRA_IA_ARCHIVOS_IMPRESION.md
```

## Descarga Instagram

`flyer_eventos` descarga automáticamente posts públicos de Instagram usando **instaloader** únicamente. Sin yt-dlp.

- Soporta `/p/`, `/reel/`, `/tv/`
- Guarda carrusel completo: `input_ig.jpg`, `input_ig_2.jpg`, ...
- Guarda caption en `ig_caption.txt`
- Si falla (privado / login requerido / rate limit), marca `manual_download_needed`
- Reintentar con: `py scripts/ig_redownload.py`

Ver: `docs/INSTALOADER.md`

## Reglas

- Avanzar paso a paso.
- No subir archivos pesados.
- No automatizar Photoshop/Blender todavía.
- No borrar sin confirmación.
- Usar `py` en Windows, `python3` en Linux/macOS.
- Después de cada mejora, hacer checkpoint.

## Sobre este repo

**Dimensiones del Orden** — flujo creativo + IA.
