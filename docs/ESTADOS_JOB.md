# Estados de job — flujo v0.16

Estados definidos en `flujo.jobs.brief.EstadoJob` y validados en
`flujo.jobs.lifecycle`.

## Estados

```txt
borrador                            # recién creado, sin texto
brief_extraido_pendiente_revision   # extraído del correo, sin revisar
pendiente_datos                     # faltan datos críticos o hay riesgo privacidad
listo_para_disenar                  # brief aprobado, puede crearse proyecto
en_diseno                           # proyecto base creado, pendiente diseño/render
generado                            # outputs creados, pendiente entrega
entregado                           # enviado o listo final
pausado                             # detenido temporalmente
cancelado                           # no continuar
```

## Transiciones válidas

| Desde | Hacia |
|-------|-------|
| `borrador` | `brief_extraido_pendiente_revision`, `pendiente_datos`, `listo_para_disenar`, `cancelado` |
| `brief_extraido_pendiente_revision` | `pendiente_datos`, `listo_para_disenar`, `pausado` |
| `pendiente_datos` | `listo_para_disenar`, `pausado`, `cancelado` |
| `listo_para_disenar` | `en_diseno`, `pausado` |
| `en_diseno` | `generado`, `pausado` |
| `generado` | `entregado`, `en_diseno` |
| `pausado` | `pendiente_datos`, `listo_para_disenar`, `en_diseno`, `cancelado` |
| `entregado` | (terminal) |
| `cancelado` | (terminal) |

## Cómo se calcula el estado siguiente

`flujo job prepare` aplica automáticamente:

1. **Privacidad alta** → `pendiente_datos`
2. **Hay pendientes en el brief** → `pendiente_datos`
3. **Faltan datos críticos** (tipo + medidas) → `pendiente_datos`
4. **Si todo OK** → `listo_para_disenar`

`flujo job activate` cambia a `en_diseno` después de crear el proyecto.

## Uso programático

```python
from flujo.jobs.brief import Brief, EstadoJob, load_brief, save_brief

brief = load_brief(Path("jobs/.../brief.yaml"))
brief.estado = EstadoJob.LISTO_PARA_DISENAR
save_brief(Path("jobs/.../brief.yaml"), brief)
```

## Uso vía CLI

```bash
flujo job status jobs/<job>     # muestra estado actual + sugerencias
flujo brief show jobs/<job>/brief.yaml
```

## Edición manual

Editar `jobs/<job>/brief.yaml` y cambiar la línea `estado:`.
Si la transición es válida, el sistema la acepta.
Si quieres saltar validaciones, edita el YAML directamente y vuelve a ejecutar
`flujo job prepare` para regenerar el reporte.
