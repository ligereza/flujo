# Decisiones y crítica del flujo

## Crítica de pasos anteriores

El camino es bueno porque separa fuente, brief, proyecto y salida. Pero había dos riesgos:

1. **Demasiadas capas pueden confundir** si no existe una regla clara de cuándo usar cada una.
2. **La auto-elección de plantilla podía fallar** cuando el brief no tenía medidas pero sí intención (`dossier`, `one_page`, `carrusel`).

## Ajuste aplicado

`brief_to_project.py` ahora prioriza `tipo_pieza` y `posibles_formatos` cuando la medida está vacía. Si hay medidas, mantiene la lógica universal por proporción.

## Regla actual recomendada

- Si hay medida clara: elegir por proporción.
- Si no hay medida pero hay intención: elegir por tipo/formato.
- Si no hay nada: crear base universal 14×10 cm y dejar pendiente.

## No sobre-automatizar todavía

No conviene generar diseños finales automáticamente desde briefs largos. Mejor:

```txt
correo → job → brief.yaml → proyecto base → diseño humano/IA guiado → outputs
```

## Próxima mejora futura

Agregar `estado` de job más formal: `borrador`, `brief_extraido`, `pendiente_datos`, `listo_para_disenar`, `generado`, `entregado`.

## Contexto institucional RD

Se agregó referencia web en:

```txt
docs/REFERENCIA_REDUCIENDO_DANO_WEB.md
```

Usar solo como contexto de tono/vocabulario. No reemplaza texto aprobado del cliente.
