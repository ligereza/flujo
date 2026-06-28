# Metodo de aprendizaje

El aprendizaje de este proyecto parte simple: registrar pruebas reales y usar esos datos para ajustar reglas del script.

## Por que no usar IA directa todavia

Una IA puede proponer cambios, pero no debe reemplazar criterio visual en logos.

Primero necesitamos datos:

- que modo se uso;
- que palabra era;
- que letras fallaron;
- que tolerancias uso el script;
- cuantos puntos elimino;
- si el resultado fue aprobado.

## Archivo acumulativo

```txt
projects/logo_clean_lab/learning/logo_clean_results.jsonl
```

Cada linea es una prueba independiente.

Ejemplo:

```json
{"sample":"codeine_001","mode":"W","word":"CODEINE","before_points":320,"after_points":302,"removed":18,"moved":44,"collapsed":11,"round_fixed":3,"approved":true,"note":"bien, no deformo O"}
```

## Campos recomendados

```txt
sample
mode
word
before_points
after_points
removed
moved
collapsed
round_fixed
approved
note
script_version
```

## Criterio de ajuste

Si se repite un error:

```txt
B/R pierde curva
```

entonces ajustar reglas de MIXED antes de tocar ROUND/ORTHO.

Si se repite:

```txt
E queda con curva residual
```

entonces reforzar cierre de handles solo en segmentos rectos ORTHO.

Si se repite:

```txt
O se anguliza
```

entonces bajar intervencion en ROUND.
