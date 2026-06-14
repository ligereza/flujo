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

```txt
flyer_eventos
```

## Flujo actual probado

Crear proyecto manual:

```bash
bash scripts/new_flyer_evento.sh "nombre evento"
```

Crear proyectos desde correo con links de Instagram:

```bash
py scripts/flyer_from_email.py "inbox/correo_prueba.txt"
```

Forzar duplicado solo si hace falta:

```bash
py scripts/flyer_from_email.py "inbox/correo_prueba.txt" --force
```

Listar proyectos:

```bash
bash scripts/flyer_list.sh
```

Ver último proyecto:

```bash
bash scripts/flyer_latest.sh
```

Setear imagen demo en último proyecto:

```bash
bash scripts/flyer_set_input_latest_demo.sh
```

Ver estado del último proyecto:

```bash
bash scripts/flyer_status_latest.sh
```

Generar índice de proyectos flyer:

```bash
bash scripts/flyer_index.sh
```

Reportar duplicados:

```bash
bash scripts/flyer_duplicates_report.sh
```

Abrir último proyecto flyer en Explorer:

```bash
bash scripts/flyer_open_latest.sh
```

Ver estado general:

```bash
bash scripts/orden_status.sh
```

Aplicar paquete de mejoras airdrop:

```bash
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
```

Guardar avance:

```bash
bash scripts/checkpoint.sh "mensaje"
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
- Marca esos proyectos como `from_email_pending_download`.
- Permite aplicar mejoras completas mediante `_airdrop/`.
- Genera índice JSON en `data/flyer_index.json`.
- Genera reporte de duplicados en `data/flyer_duplicates_report.json`.



## Nueva herramienta disponible: piezas_vectoriales

Además de `flyer_eventos`, existe una herramienta para pedidos de impresión/Illustrator:

```txt
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

```txt
brief/correo → config JSON → SVG editable → SVG vectorizado → ZIP/export
```

Comandos:

```bash
py scripts/piezas_generar.py "projects/piezas_vectoriales/etiquetas_ejemplo/config.json"
py scripts/piezas_check_outputs.py
```

Proyecto real incluido:

```txt
projects/piezas_vectoriales/suplementos_rd/
```

Para ese proyecto:

```bash
cd projects/piezas_vectoriales/suplementos_rd
py scripts/generar_flyers.py
```

## Qué NO hace todavía

- No descarga Instagram automáticamente.
- No analiza la imagen/video.
- No extrae texto del flyer.
- No abre Photoshop.
- No abre Blender.
- No borra archivos.
- No limpia duplicados automáticamente.

## Sistema airdrop

Para acelerar cambios:

1. Crear archivos dentro de `_airdrop/` respetando rutas.
2. Probar:

```bash
bash scripts/apply_airdrop.sh --dry-run
```

3. Aplicar:

```bash
bash scripts/apply_airdrop.sh --apply
```

4. Guardar:

```bash
bash scripts/checkpoint.sh "aplicar mejoras airdrop"
```

## Próximo paso recomendado

Crear flujo de descarga/manual review.

Idea:

- Si el post es público y simple, preparar descarga futura.
- Si es reel/video/privado/shadowban, marcar descarga manual.
- Mantener todo como revisión humana antes de Photoshop/Blender.

## Reglas

- Avanzar paso a paso.
- No hacer cambios gigantes.
- No automatizar Photoshop/Blender todavía.
- No subir archivos pesados.
- No borrar nada sin confirmación.
- Usar `py` para scripts Python.
- Mantener compatibilidad con Git Bash en Windows.
- Después de cada mejora pequeña, hacer checkpoint.
