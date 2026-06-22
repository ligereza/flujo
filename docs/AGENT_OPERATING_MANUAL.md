# AGENT OPERATING MANUAL — flujo (token-efficient)

**Leer esto primero. Solo esto + el hub.**

## Flujo 1: Pedido Reciente (operativo)
Recibes: link del repo + correo o mensaje WhatsApp/Gmail.

**Proceso exacto:**
1. Abre `context/flujo_hub.html`
2. Pega el texto completo en la caja "Pedidos"
3. Pulsa "Generar brief ordenado"
4. Revisa el "Format match" en la salida.
5. Si hay match → genera brief + comando + archivos para AI/PS/Blender usando aistetic.
6. Si no hay match → 
   - Propón sección nueva mínima en aistetic, **o**
   - Agrega tarea clara en LAST_HANDOFF.md

**Salida mínima esperada:**
- Brief estructurado (copia-pega)
- 1-2 comandos exactos
- Nota de herramienta final + aistetic
- Decisión: "Usar formato X" o "Nueva sección / tarea de mejora"

## Flujo 2: Mejoras al Repo
Recibes: repo + "continúa con las mejoras".

**Proceso:**
1. Abre el hub + lee LAST_HANDOFF.md
2. Lee este manual
3. Elige 1-2 tareas de la sección de tareas simples
4. Trabaja
5. Actualiza LAST_HANDOFF al final

## Reglas (ambos flujos)
- Windows: `py -m flujo ...`
- Español primero
- Siempre usa aistetic
- Archivos finales listos para Illustrator/Photoshop/Blender
- Mantén respuestas cortas. Hub = verdad

## Formatos actuales (chequea rápido)
- flyer 10x14 (illustrator)
- etiqueta 16.5x6.5 (illustrator)
- plano/stand + cotizacion (dual)
- cartelera IG / post (ps + blender)

Si no calza → nueva sección o tarea.

**Este archivo + hub = única fuente para agentes (bajo consumo de tokens).**

El hub hace el matching básico y te da la decisión lista.
Usa siempre la salida del hub como base.