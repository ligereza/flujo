# Pipeline de Jobs — flujo v0.16

Este documento describe el ciclo completo de un job creativo en `flujo`,
desde que llega un correo hasta que se entrega el diseño final.

## Diagrama

```txt
correo/texto          jobs/                projects/                 exports/
─────────────         ──────               ────────────              ────────
                  ┌─ borrador ─┐
inbox/correo.txt ──┤            ├─→ brief_extraido ─┐
                  └────────────┘                    │
                                                   ├─→ pendiente_datos
                                                   │     │
                                                   │     ├─→ listo_para_disenar
                                                   │     │     │
                                                   │     │     └─→ en_diseno
                                                   │     │           │
                                                   │     │           ├─→ render
                                                   │     │           │
                                                   │     │           └─→ generado
                                                   │     │
                                                   │     └─→ (cancelado)
                                                   │
                                                   └─→ (pausado)
                                                          ↓
                                                       entregado
```

## Pasos en detalle

### 1. Crear job

```bash
flujo job new "etiquetas acme" --email inbox/correo.txt
```

Esto crea `jobs/YYYY-MM-DD_etiquetas-acme/` con:
- `brief.yaml` — plantilla vacía
- `pedido_original.txt` — copia del correo
- `estado.md` — estado actual
- `resultado.md` — resultado (vacío hasta activación)

### 2. Preparar job

```bash
flujo job prepare jobs/2026-06-17_etiquetas-acme
```

Ejecuta el pipeline:

1. **Privacidad** — escanea `pedido_original.txt` con regex (email, RUT, teléfono, URL)
   y genera `privacy_report.md` + `pedido_sanitizado.txt`.
2. **Brief automático** — extrae tipo, medidas, productos del texto sanitizado.
3. **Reporte** — escribe `reporte_job.md`.
4. **Estado sugerido** — calcula el estado siguiente según:
   - ¿hay riesgo de privacidad alto? → `pendiente_datos`
   - ¿hay pendientes en el brief? → `pendiente_datos`
   - ¿faltan datos críticos (tipo + medidas)? → `pendiente_datos`
   - ¿todo OK? → `listo_para_disenar`

### 3. Revisar y completar

Editar `jobs/.../brief.yaml` manualmente:
- completar `cliente`, `proyecto`
- confirmar `tipo_pieza`, `medidas`
- agregar productos reales (no inventar)
- aprobar texto (`contenido.texto_aprobado: true`)

```bash
flujo brief show jobs/.../brief.yaml
flujo job status jobs/...
flujo job next
```

### 4. Activar job

```bash
flujo job activate jobs/2026-06-17_etiquetas-acme
```

Convierte el brief en un proyecto en `projects/piezas_vectoriales/<slug>/`:
- elige plantilla por tamaño/proporción si hay medidas
- elige plantilla por tipo si no hay medidas
- genera `config.json` base
- marca el job como `en_diseno`

### 5. Ajustar config y renderizar

```bash
flujo render validate projects/piezas_vectoriales/.../config.json
flujo render run projects/piezas_vectoriales/.../config.json
```

Editar `config.json` (paleta, textos, elementos) antes de renderizar.

### 6. Validar y entregar

```bash
flujo render validate ...
flujo job report jobs/...
flujo daily
```

## Estados y transiciones

Definidos en `flujo.jobs.brief.EstadoJob`:

| Estado | Siguiente natural | Acción |
|--------|-------------------|--------|
| `borrador` | `brief_extraido` | pegar texto + `flujo job prepare` |
| `brief_extraido_pendiente_revision` | `listo_para_disenar` o `pendiente_datos` | revisar brief |
| `pendiente_datos` | `listo_para_disenar` | resolver pendientes |
| `listo_para_disenar` | `en_diseno` | `flujo job activate` |
| `en_diseno` | `generado` | `flujo render run` |
| `generado` | `entregado` | revisar outputs |
| `entregado` | — | (terminal) |
| `pausado` | varios | manual |
| `cancelado` | — | (terminal) |

## Privacidad

`flujo privacy` aplica la Ley 21.719 (Chile) y buenas prácticas generales:

- Detecta: emails, RUT, teléfonos CL, URLs, tarjetas, direcciones.
- Palabras sensibles: salud, sustancias, menores, datos bancarios.
- Niveles de riesgo: **bajo** | **medio** | **alto**.
- Si el riesgo es **alto**, el estado sugerido es `pendiente_datos` y se
  requiere revisión humana antes de pasar a una IA externa.

**No reemplaza revisión legal/humana.**

## Integración con otros sistemas

- **Flyers**: links IG en el correo se procesan en `flujo flyer-import`.
- **Análisis**: `flujo analyze` extrae colores y OCR de flyers descargados.
- **Export**: `flujo export` genera ZIP con palette + scripts PS/AI.
- **Dashboard**: `flujo daily` da visibilidad de todo el pipeline.
