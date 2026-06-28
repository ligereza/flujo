# Workflow de ayuda remota con IA web

Este documento mejora la forma de pedir ayuda a una IA web cuando trabajas sobre este repo, especialmente para pedidos de suplementos, cotizaciones y briefs.

## Regla de oro

No envíes mensajes vagos como "ayúdame con mi repo". Da contexto corto, objetivo claro, formato esperado y el texto real a procesar.

## Flujo recomendado

1. Abre el hub del repo:
   ```bash
   py -m flujo app
   ```
2. Lee primero la fuente de continuidad:
   - `context/LAST_HANDOFF.md`
   - `docs/FLUJO_AREAS_EVENTOS_SUPLEMENTOS.md`
3. Pega un prompt corto y estructurado a la IA web.
4. Pide una salida concreta: clasificación, resumen, datos faltantes o texto listo para copiar.
5. Verifica el resultado contra el repo antes de entregarlo.

## Prompt base para copiar y pegar

```txt
Hola, necesito ayuda con este repo.

Repo: ligereza/vibecodeine
Objetivo: convertir un pedido en una cotización o brief útil para flujo.
Contexto: este repo gestiona pedidos -> jobs -> briefs -> diseño -> entrega.
Para suplementos, el input suele venir como un correo o mensaje con una solicitud de cotización, modificación o corrección.

Quiero que trabajes así:
- Responde en español.
- Clasifica el mensaje como nuevo pedido, modificación, corrección o cotización.
- Si es de suplementos, extrae producto, formato, medidas, cantidad, fecha, cliente y observaciones.
- Si falta información, indícala explícitamente como "pendiente".
- No inventes datos.
- Devuelve una salida breve y lista para copiar en un issue, brief o JSON.

Texto a procesar:
[PEGAR PEDIDO O CORREO AQUI]

Salida esperada:
1. Clasificación
2. Resumen corto del pedido
3. Datos extraídos
4. Datos faltantes
5. Texto listo para enviar como cotización o pedido
```

## Versión corta para casos rápidos

```txt
Hola, este es mi repo. Necesito ayuda para convertir este mensaje en un pedido claro de suplementos y luego en una cotización breve. Quiero que me respondas en español, identifiques si es pedido o cotización, extraigas los datos clave y me digas qué falta.
```

## Ejemplo práctico

```txt
Hola, este es mi repo. Necesito enviar una cotización sobre suplementos, pero primero necesito este pedido. Por favor conviértelo en un pedido claro para flujo y dame una propuesta de cotización breve, en formato simple y listo para copiar.
```

## Estructura ideal de salida

La IA debe responder con este formato simple:

```txt
Clasificación: [pedido | cotización | modificación | corrección]
Area: [suplementos | eventos]
Resumen: [1-2 líneas]
Datos extraídos: [lista]
Datos faltantes: [lista]
Texto listo: [bloque corto para copiar]
```

Esto reduce el ruido, mantiene el contexto del repo y evita que la IA haga suposiciones innecesarias.
