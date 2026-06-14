# AGENTS.md — Instrucciones rápidas para agentes IA

Este repo se llama `flujo`. Lee primero:

1. `PARA_IA.md`
2. `README.md`
3. `context/ESTADO.md`

## Si el pedido es sobre archivos de impresión, etiquetas, flyers o Illustrator

Lee además:

```txt
tools/piezas_vectoriales/SPEC.md
tools/piezas_vectoriales/README_SISTEMA_FORMATOS.md
briefs/PROMPT_PARA_OTRA_IA_ARCHIVOS_IMPRESION.md
```

Flujo esperado:

```txt
correo/brief → JSON/config → generar SVG editable → generar SVG vectorizado → validar → entregar rutas/ZIPs
```

Reglas:

- Editar JSON/config antes que SVG generado.
- No inventar textos legales o claims nutricionales.
- Preguntar máximo 3 cosas si falta información crítica.
- Validar con `python3 scripts/piezas_check_outputs.py`.
- Mantener compatibilidad con Git Bash/Windows; usar `py` o `python3` según entorno.

## Flujo de jobs para pedidos nuevos

Para pedidos nuevos de impresión, crear primero un job:

```bash
bash scripts/job_new.sh "nombre pedido"
```

Completar:

```txt
jobs/YYYY-MM-DD_nombre/brief.yaml
jobs/YYYY-MM-DD_nombre/pedido_original.txt
jobs/YYYY-MM-DD_nombre/estado.md
jobs/YYYY-MM-DD_nombre/resultado.md
```

Usar checklist:

```txt
docs/CHECKLIST_IMPRESION.md
```

Recetas disponibles:

```txt
recipes/etiqueta_producto_vectorial.md
recipes/suplementos_rd_ficha_producto.md
```

## GitHub Actions para render remoto

Si el usuario trabaja vía web/chat y no local, puede usar:

```txt
.github/workflows/render_piezas_vectoriales.yml
```

Después de modificar configs/proyectos de `projects/piezas_vectoriales/`, el workflow genera outputs y los sube como artifact `piezas-vectoriales-generadas`.

Documentación:

```txt
docs/GITHUB_ACTIONS_PIEZAS.md
```

## Extraer brief inicial desde correo

Si existe `jobs/.../pedido_original.txt`, acelerar con:

```bash
py scripts/job_extract_brief.py "jobs/YYYY-MM-DD_nombre"
```

Luego revisar `brief.yaml`; no asumir que la extracción automática es final.

## Crear proyecto base desde brief

Cuando un `brief.yaml` ya esté revisado o se quiera crear una base de diseño:

```bash
py scripts/brief_to_project.py "jobs/YYYY-MM-DD_nombre/brief.yaml"
```

Luego generar:

```bash
py scripts/piezas_generar.py "projects/piezas_vectoriales/NOMBRE/config.json"
```

## Formatos/proporciones

Listar o sugerir formatos:

```bash
py scripts/piezas_formatos.py
py scripts/piezas_formatos.py 16.5 6.5 etiqueta
```

`brief_to_project.py` usa plantillas conocidas si calzan con la medida; si no, crea una base proporcional universal.

## Estado de jobs

Listar jobs:

```bash
py scripts/job_status.py
py scripts/job_status.py --examples
```

Cambiar estado:

```bash
py scripts/job_set_status.py "jobs/NOMBRE" listo_para_disenar
```

Estados documentados en:

```txt
docs/ESTADOS_JOB.md
```

## Privacidad / Ley de datos Chile

Hay una herramienta en cola:

```txt
tools/privacidad_datos/SPEC.md
```

Antes de pegar correos o documentos con datos personales a IA externa, revisar:

```txt
docs/privacidad/CHECKLIST_PRIVACIDAD_IA.md
docs/privacidad/LEY_21719_NOTAS.md
```

Si un pedido contiene RUT, teléfonos, correos personales, direcciones, salud, consumo, menores, trabajadores, asistentes o datos sensibles, no compartir completo: sanitizar o pedir revisión humana.

## MVP privacidad

Antes de usar un correo/job con IA externa:

```bash
py scripts/privacy_check_job.py "jobs/NOMBRE"
```

Usar `pedido_sanitizado.txt` para prompts si hay datos personales.

## Roadmap multistep

Clasificación de dificultad:

```txt
docs/ROADMAP_MULTISTEP.md
```

Reporte rápido de job:

```bash
py scripts/job_report.py "jobs/NOMBRE"
```

## Componentes y validación piezas_vectoriales

Insertar componente:

```bash
py scripts/piezas_add_component.py "projects/piezas_vectoriales/MI_PROYECTO/config.json" qr_placeholder.json doc
```

Validar configs y resumir proyectos:

```bash
py scripts/piezas_validate_config.py
py scripts/piezas_project_summary.py
```

## Mantenimiento antes de commit

Antes de proponer commit/push:

```bash
py scripts/flujo_clean_generated.py
py scripts/flujo_health.py
```

Documentación:

```txt
docs/MANTENIMIENTO_REPO.md
```

## Flujo rápido pedido → job preparado

Desde un correo `.txt`:

```bash
py scripts/job_from_text.py "nombre pedido" inbox/correo.txt
py scripts/job_prepare.py "jobs/YYYY-MM-DD_nombre-pedido"
py scripts/job_next_actions.py
```

Documentación:

```txt
docs/FLUJO_PEDIDO_A_JOB.md
```

## Comando unificado

Preferir atajos:

```bash
py scripts/flujo.py health
py scripts/flujo.py clean
py scripts/flujo.py job-from-text "nombre" inbox/correo.txt
py scripts/flujo.py job-prepare jobs/NOMBRE
py scripts/flujo.py job-next
```

Ver:

```txt
docs/COMANDO_UNIFICADO.md
```

## Respuestas estándar

Usar plantillas:

```txt
briefs/RESPUESTA_IA_TRABAJO_COMPLETADO.md
briefs/RESPUESTA_IA_FALTAN_DATOS.md
```

Para issues:

```txt
docs/ISSUE_A_JOB.md
```

## Activar job y renderizar proyecto

```bash
py scripts/job_activate.py "jobs/NOMBRE"
py scripts/project_render.py "projects/piezas_vectoriales/NOMBRE/config.json"
```

Documentación:

```txt
docs/JOB_A_PROYECTO_RENDER.md
```

## Operador rápido

Resumen operativo:

```txt
docs/OPERADOR_IA_RAPIDO.md
```

Nuevos comandos:

```bash
py scripts/job_validate.py "jobs/NOMBRE"
py scripts/project_new_from_template.py "nombre" plantilla.json
py scripts/project_delivery_manifest.py "projects/piezas_vectoriales/NOMBRE"
```

## Comandos extra de inspección

```bash
py scripts/flujo.py components
py scripts/flujo.py inspect projects/piezas_vectoriales/NOMBRE
py scripts/flujo.py backlog
py scripts/project_clone_variant.py projects/piezas_vectoriales/origen "nuevo nombre"
py scripts/job_complete.py jobs/NOMBRE
```

Quality gates:

```txt
docs/QUALITY_GATES.md
```
