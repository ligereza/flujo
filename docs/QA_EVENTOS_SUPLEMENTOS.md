# QA operativo EVENTOS/SUPLEMENTOS

Comandos desde la raiz de MAK para revisar piezas antes de exportar o imprimir.

## EVENTOS: validar rider/plano

Antes de imprimir rider o exportar plano SVG:

```bash
PYTHONPATH=src python3 -m flujo plano projects/plano/ejemplos/evento_ejemplo.json --validate
PYTHONPATH=src python3 -m flujo plano projects/plano/ejemplos/evento_ejemplo.json --validate --rider
PYTHONPATH=src python3 -m flujo plano projects/plano/ejemplos/evento_ejemplo.json --validate -o exports/plano_evento.svg
```

La validacion revisa:

- nombre, duracion, voluntarios y asistentes estimados;
- `layout_mode` permitido (`row` o `grid_2x`);
- consistencia de testeo, evento masivo, zona de contencion, mesas y dimensiones.

Si hay errores, el comando sale con codigo distinto de cero y no debe cerrarse entrega.
Las advertencias no bloquean, pero deben revisarse con produccion.

## SUPLEMENTOS: validar SVGs de contraportada

Despues de generar una contraportada:

```bash
PYTHONPATH=src python3 -m flujo suplementos contraportada "Impulso" --output exports/impulso_contraportada.svg
PYTHONPATH=src python3 -m flujo suplementos validate exports/impulso_contraportada.svg
```

Para varios archivos:

```bash
PYTHONPATH=src python3 -m flujo suplementos validate exports/*.svg
```

La validacion revisa:

- XML/SVG parseable;
- tamano esperado de contraportada 10x14 cm (`1181x1654 px`);
- placeholders sin reemplazar;
- presencia basica de textos y grupos editables.

Para SVGs genericos no contraportada:

```bash
PYTHONPATH=src python3 -m flujo suplementos validate pieza.svg --generic
```

## Nota

Esto no reemplaza QA visual en Illustrator. Es un preflight mecanico para evitar
fallas obvias antes de abrir, ajustar fuentes, convertir textos a curvas y exportar PDF.
