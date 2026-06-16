# flujo — Dimensiones del Orden

![CI](https://github.com/ligereza/flujo/actions/workflows/ci.yml/badge.svg)
![Render](https://github.com/ligereza/flujo/actions/workflows/render_piezas_vectoriales.yml/badge.svg)

Repositorio para ordenar proyectos creativos, automatizaciones e IAs.

Funciona como una **zapatilla/alargador organizador**: conecta proyectos, herramientas, contexto y checkpoints en un solo lugar.

No reemplaza el trabajo manual. Ayuda a no empezar desde cero.

## Entrada rápida

Si eres una IA o asistente, lee primero:

```txt
PARA_IA.md
```

Luego lee:

```txt
docs/DIMENSIONES_DEL_ORDEN.md
context/ESTADO.md
tools/flyer_eventos/SPEC.md
```

## Instalación

Dependencias:

```bash
python3 -m pip install -r requirements.txt
```

En Windows también puedes usar el launcher `py`:

```bash
py -m pip install -r requirements.txt
```

## Herramienta activa

```txt
flyer_eventos
```

## Comandos actuales

> **Nota sobre `python3` vs `py`**: la documentación usa `python3` (Linux/macOS/Git Bash). En Windows nativo puedes reemplazar `python3` por `py`.

## Pipeline inteligente (recomendado)

Si recibes un correo con un pedido de diseño/impresión, el pipeline puede crear el job, inferir el tipo de pieza y medidas, y generar SVGs automáticamente:

```bash
python3 scripts/flujo_pipeline.py "nombre pedido" inbox/correo.txt
```

Para aplicar inferencias sin preguntar:

```bash
python3 scripts/flujo_pipeline.py "nombre pedido" inbox/correo.txt --confirm
```

Palabras clave soportadas: `etiqueta`, `flyer`, `sticker`, `rider`, `carrusel`, `dossier`, `one page`, `presentacion`, `tarjeta`.


Crear proyecto flyer manual:

```bash
bash scripts/new_flyer_evento.sh "nombre evento"
```

Crear proyectos desde correo con links de Instagram:

```bash
python3 scripts/flyer_from_email.py "inbox/correo_prueba.txt"
```

Forzar duplicado si realmente lo necesitas:

```bash
python3 scripts/flyer_from_email.py "inbox/correo_prueba.txt" --force
```

Listar flyers:

```bash
bash scripts/flyer_list.sh
```

Ver último flyer:

```bash
bash scripts/flyer_latest.sh
```

Setear input demo en último flyer:

```bash
bash scripts/flyer_set_input_latest_demo.sh
```

Ver status del último flyer:

```bash
bash scripts/flyer_status_latest.sh
```

Generar índice de flyers:

```bash
bash scripts/flyer_index.sh
```

Detectar duplicados:

```bash
bash scripts/flyer_duplicates_report.sh
```

Abrir último flyer en Explorer:

```bash
bash scripts/flyer_open_latest.sh
```

Ver estado general del orden:

```bash
bash scripts/orden_status.sh
```

Aplicar mejoras por airdrop:

```bash
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
```

Guardar avance:

```bash
bash scripts/checkpoint.sh "mensaje"
```

Comando unificado (salud, limpieza, jobs, etc.):

```bash
python3 scripts/flujo.py health
```

## Flujo actual recomendado

```bash
python3 scripts/flyer_from_email.py "inbox/correo_prueba.txt"
bash scripts/flyer_list.sh
bash scripts/flyer_index.sh
bash scripts/flyer_duplicates_report.sh
bash scripts/flyer_status_latest.sh
bash scripts/checkpoint.sh "mensaje"
```

## Herramienta adicional: piezas vectoriales / archivos de impresión

Para etiquetas, flyers de impresión, SVG editables, SVG vectorizados y archivos para Illustrator:

```txt
tools/piezas_vectoriales/SPEC.md
```

Generar proyecto genérico desde JSON:

```bash
python3 scripts/piezas_generar.py "projects/piezas_vectoriales/etiquetas_ejemplo/config.json"
```

Generar proyecto real Suplementos RD:

```bash
cd projects/piezas_vectoriales/suplementos_rd
python3 scripts/generar_flyers.py
```

Validar salidas vectoriales:

```bash
python3 scripts/piezas_check_outputs.py
```

Para pedirle trabajo a otra IA con un correo del jefe, usar:

```txt
briefs/PROMPT_PARA_OTRA_IA_ARCHIVOS_IMPRESION.md
```

## Reglas

- Avanzar paso a paso.
- No subir archivos pesados.
- No automatizar Photoshop/Blender todavía.
- No borrar sin confirmación.
- Usar `python3` en Linux/macOS y `py` en Windows según convenga.
- Después de cada mejora, hacer checkpoint.

## Sobre este repo

**Dimensiones del Orden** — flujo creativo + IA.
