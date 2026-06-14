# Referencia: etiquetas relieve COMROESS

Archivo analizado por el usuario:

```txt
ETIQUETAS.RELIEVE.comroess.pdf
```

No se incluye el PDF en el repo por ser referencia/binario; se registra la información útil para el flujo.

## Datos detectados

- PDF de 8 páginas.
- Formato principal aproximado: **16.5 × 6.5 cm**.
- Una página detectada en formato aproximado: **13.0 × 6.5 cm**.
- El PDF parece estar compuesto principalmente por imágenes/raster dentro de páginas PDF.

## Uso en el sistema

Para crear una etiqueta similar en proporción principal:

```txt
16.5 × 6.5 cm
```

A 200 px/cm:

```txt
3300 × 1300 px
```

Plantilla agregada:

```txt
tools/piezas_vectoriales/plantillas/etiqueta_horizontal_165x65.config.json
```

## Comando útil

Para inspeccionar PDFs similares:

```bash
py scripts/pdf_probe_basic.py "ruta/archivo.pdf"
```
