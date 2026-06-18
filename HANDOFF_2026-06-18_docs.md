# 🤝 Handoff 2026-06-18 — flujo v0.25.0 — README maestro + Intake JSON

> Airdrop de **documentación + contrato de datos**. No cambia código ejecutable
> (salvo bump de versión). Seguro de aplicar.

## Por qué este airdrop

El dueño pidió dos cosas:

1. **Un README que explique al máximo cómo otra IA debe trabajar aquí**, sobre
   todo el tema de los **zips/airdrops**.
2. Empezar a definir **datos específicos**: composición de **formatos** (flyers,
   etiquetas, etc.), cómo funcionará realmente **la app** (Gradio vs. correo vs.
   API), y establecer una **estructura JSON clara por formato** para que sus
   colegas entreguen los pedidos estructurados (y así independizarse de
   responder mensajes / acusar recibo cuando está ausente).

## Qué incluye

| Archivo | Qué es |
|---|---|
| `README.md` | **Reescrito de cero** como guía maestra para agentes: protocolo de trabajo de una IA, anatomía de un airdrop/ZIP, pipeline completo, catálogo de formatos, intake JSON, y sección honesta sobre el estado de "la app" + plan de recepción automática. |
| `docs/INTAKE_JSON.md` | Especificación completa del **intake por JSON 1.0**: estructura base, campos por formato (etiqueta/flyer/one_page/carrusel/rider/otros), validación, acuse de recibo y **roadmap de implementación**. |
| `schemas/intake.schema.json` | **JSON Schema draft-07** validable del pedido. Sirve para validar y para que un formulario web genere JSON correcto. |
| `schemas/ejemplos/*.json` | 3 ejemplos reales y válidos: `etiqueta_miel`, `flyer_evento`, `carrusel_ig`. |
| `PARA_IA_CONTEXT.md` | Handover corto actualizado a v0.25.0. |
| `src/flujo/version.py` + `pyproject.toml` | Bump a **0.25.0** + changelog. |

## Decisiones tomadas (y por qué)

- **El contrato JSON se fija AHORA, la recepción se decide después.** El dueño
  aún no decidió si la app será Gradio / correo / API. En vez de bloquearnos,
  fijamos el **formato de intercambio** (JSON `intake_version 1.0`). Así
  cualquier canal que elija después solo tiene que producir ese JSON. El README
  y `docs/INTAKE_JSON.md` explican las opciones (IMAP recomendado para empezar)
  con sus trade-offs.
- **Honestidad sobre "la app":** documenté que hoy `flujo serve` es Gradio local
  y manual (no recibe nada solo), y separé la arquitectura objetivo en
  RECEPCIÓN (24/7) vs OPERACIÓN.
- **Formatos basados en el catálogo real** (`INDEX_FORMATOS.json`), no inventados:
  6 formatos con sus medidas/canvas verificados leyendo el código.
- **El esquema mapea 1:1 al `Brief`** existente (`src/flujo/jobs/brief.py`) para
  que la futura implementación sea directa.

## Verificación hecha

```
✅ JSON Schema válido (Draft7Validator.check_schema)
✅ Los 3 ejemplos pasan la validación
✅ Un payload inválido (sin título ni medidas/formato) FALLA correctamente
✅ version.py parsea (ast.parse) y pyproject sincronizado a 0.25.0
```

## ⚠️ Lo que este airdrop NO hace (para la próxima IA)

- **No implementa `flujo intake json`.** Solo define el contrato. El roadmap de
  implementación está en `docs/INTAKE_JSON.md` §6, en pasos de menor a mayor
  esfuerzo. Empieza por el módulo `src/flujo/intake/json_intake.py` + tests.
- **No toca el motor de la app ni agrega poller de correo.** Eso requiere
  decisión del dueño sobre el canal.

## Cómo aplicar

```bash
flujo airdrop apply "v0.25.0 - README maestro + intake JSON"
# o:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.25.0 - README maestro + intake JSON"

# verificar:
py -m pip install -e .
flujo version            # 0.25.0
py -m pytest tests/ -q   # 69 passed, 1 skipped (sin cambios en tests)
```

> Nota: este airdrop incluye `pyproject.toml` y `version.py`; tras aplicarlo
> reinstala con `py -m pip install -e .` para que `flujo version` muestre 0.25.0.
