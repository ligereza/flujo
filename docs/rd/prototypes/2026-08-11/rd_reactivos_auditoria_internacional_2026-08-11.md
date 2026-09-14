# Auditoría internacional de reactivos colorimétricos RD

## Resultado

Se contrastó la biblioteca local de doce reactivos con material internacional de DanceSafe, NUAA Drug Checking, un documento técnico de UNODC y una revisión científica publicada por la Royal Society of Chemistry.

La conclusión no es que la tabla de RD esté “mal”, sino que **no todos los colores pueden convertirse en reglas universales**. La base debe conservar la fuente, la fecha, el mercado y el nivel de certeza.

## Correcciones más importantes

### Simon’s y la relación MDMA/MDA

Simon’s sirve como señal de amina secundaria, pero un azul no identifica por sí solo MDMA: también puede corresponder a metanfetamina y otras aminas secundarias. DanceSafe documenta además que MDA puede no reaccionar o producir una reacción gris-verde/negra turbia. [DanceSafe: actualización de reacciones](https://dancesafe.org/important-reagent-reaction-updates/) · [DanceSafe: instrucciones](https://dancesafe.org/wp-content/uploads/2024/05/DS_Instructions_Reagents_v17Spring24.pdf)

Para el futuro post `MDMA vs MDA`, la relación correcta no es:

```text
azul = MDMA
sin reacción = MDA
```

Sino:

```text
Marquis + Simon’s + Froehde/Robadope
=> conjunto de señales que puede apoyar una hipótesis
=> nunca una confirmación doméstica completa
```

### Cocaína, Marquis y Liebermann

Este es el mayor punto de conflicto con tablas antiguas. DanceSafe actualizó sus datos porque la cocaína puede presentar un rango amplio con Marquis y Liebermann. Ya no recomienda usar el color de Liebermann para diagnosticar específicamente levamisol o lidocaína. [DanceSafe: actualización de reacciones](https://dancesafe.org/important-reagent-reaction-updates/)

Por eso la base debe guardar colores como rangos esperados y no como una traducción rígida:

```text
expected_range
unexpected_range
source_interpretation
not_a_confirmatory_result
```

Morris conserva una función más estable como prueba primaria de señal: azul brillante para cocaína y violeta/púrpura para ketamina, siempre con procedimiento A/B y control del tamaño de muestra. [DanceSafe: instrucciones](https://dancesafe.org/wp-content/uploads/2024/05/DS_Instructions_Reagents_v17Spring24.pdf) · [NUAA Drug Checking](https://testkits.nuaa.org.au/pages/charts)

### Ehrlich y Hofmann

Ehrlich debe modelarse como una señal de la **familia de indoles**, no como un identificador automático de LSD. Hofmann funciona mejor como punto adicional de información para psicodélicos; las fuentes internacionales no lo presentan como una prueba aislada y universal. [NUAA Drug Checking](https://testkits.nuaa.org.au/pages/charts) · [Royal Society of Chemistry](https://pubs.rsc.org/en/content/articlehtml/2026/ay/d6ay00085a)

### Zimmermann y benzodiacepinas

La ficha de RD puede conservarse, pero su afirmación de fiabilidad debe quedar en revisión. DanceSafe advierte que la mayoría de las benzodiacepinas no reaccionan consistentemente con la mayoría de los reactivos, y una revisión química recuerda que Zimmermann puede tener respuestas cruzadas. [DanceSafe: instrucciones](https://dancesafe.org/wp-content/uploads/2024/05/DS_Instructions_Reagents_v17Spring24.pdf) · [Royal Society of Chemistry](https://pubs.rsc.org/en/content/articlehtml/2026/ay/d6ay00085a)

## Consecuencia para la base semántica

No guardaremos solamente `sustancia -> color`. La unidad correcta es:

```text
reactivo
familia_quimica
entidad_o_clase
rango_de_color
ventana_temporal
procedimiento
fuente
fecha_de_fuente
mercado_o_contexto
limitacion
nivel_de_confianza
```

Y para la tabla interactiva:

```text
color_quimico_del_reactivo != color_visual_de_la_matriz
riesgo_de_la_matriz != resultado_del_test
presencia_probable != pureza_o_dosis
```

## Estado de los doce reactivos

- **Respaldados como señal primaria o de clase:** Morris, Robadope, Simon’s con limitaciones.
- **Respaldados como señales complementarias:** Marquis, Ehrlich, Froehde, Mecke, Hofmann.
- **Con conflicto que impide una regla rígida:** Liebermann, Zimmermann.
- **Con cobertura insuficiente para publicar una tabla completa:** Mandelin, CBD:THC.

El detalle máquina-legible está en:

[rd_reactivos_auditoria_internacional_2026-08-11.json](C:/Users/issvk/claude_sesiones_recuperadas/rd_reactivos_auditoria_internacional_2026-08-11.json)

## Decisión recomendada

La interfaz pública debería mostrar “señal esperada”, “señal inesperada” y “límite del método”, no “seguro” o “confirmado”. Esta formulación coincide mejor con la postura de reducción de daños y evita que el sistema convierta una tabla de colores en una falsa garantía.
