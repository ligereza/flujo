# Biblioteca inicial de reactivos colorimétricos RD

## Estado

Se normalizaron doce reactivos a partir del scraping realizado con Firecrawl sobre páginas públicas de Reduciendo Daño. El archivo estructurado es:

[rd_reactivos_normalizados_2026-08-11.json](C:/Users/issvk/claude_sesiones_recuperadas/rd_reactivos_normalizados_2026-08-11.json)

El resultado es un **candidato de integración**, no una guía médica nueva ni una validación química independiente. Conserva los colores, tiempos, sustancias y advertencias que aparecen en las páginas scrapeadas.

## Reactivos incluidos

Marquis, Ehrlich, Liebermann, Morris, Froehde, Simon’s, Zimmermann, Mecke, Mandelin, Hofmann, Robadope y CBD:THC.

## Lo que ya permite la estructura

Cada gotario queda asociado a:

- sustancias o familias mencionadas;
- secuencia cromática observada;
- ventana temporal de observación;
- interpretación textual de RD;
- limitaciones;
- reactivos complementarios;
- URL de producto y, cuando existe, URL de guía.

Esto permite construir relaciones como:

```text
MDMA -> Marquis -> violeta a negro -> Simon’s para diferenciar
MDA -> Simon’s/Robadope -> señal de amina primaria
Cocaína <-> Ketamina -> Morris -> azul frente a violeta
LSD/Hongos/DMT -> Ehrlich -> familia de indoles -> Hofmann como complemento
GHB -> sin detección por reactivos colorimétricos comunes -> test específico
```

## Advertencias de normalización

La fuente utiliza a veces la palabra “confirmado”. En el archivo se conserva como `source_wording`, pero no se convierte automáticamente en certeza química. La guía general de RD indica que los reactivos señalan presencia probable y no miden cantidad ni pureza. [Guía de reactivos colorimétricos](https://reduciendodano.cl/que-son-los-reactivos-colorimetricos/)

También aparecen diferencias que requieren revisión antes de convertir los datos en una interfaz pública:

- Morris aparece como prueba de diferenciación entre cocaína y ketamina, pero exige respetar el procedimiento A/B y una muestra pequeña.
- Ehrlich identifica presencia de indoles, pero no distingue por sí solo LSD, psilocibina y DMT. [Guía Ehrlich](https://reduciendodano.cl/lsd-y-alucinogenos-como-usar-el-reactivo-ehrlich/)
- Simon’s contiene dos componentes y es especialmente útil para separar señales de MDMA, MDA, anfetamina y metanfetamina.
- GHB no debe aparecer como “sin reacción = seguro”; debe modelarse como una limitación de los reactivos comunes.
- Mandelin quedó con cobertura parcial porque su página no expuso una tabla completa durante esta pasada.
- Hofmann tiene reacciones normalizadas, pero su ventana temporal quedó pendiente de una revisión específica.

## Próximo paso

No conviene diseñar todavía los colores visuales de la tabla a partir de estos colores químicos. Primero hay que crear una capa separada:

```text
color_reaccion_quimica
color_visual_rd
forma_semantica
nivel_de_evidencia
estado_de_revision
```

Así el amarillo, rojo o símbolo de la matriz no se confunde con el color producido por un reactivo. Son sistemas visuales distintos.

La siguiente revisión humana debería comenzar con los cuatro pares que ya tienen una relación clara en el material público: **MDMA/MDA**, **cocaína/ketamina**, **GHB/alcohol** y **popper/Viagra**.
