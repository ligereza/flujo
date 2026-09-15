# Venue 3D / SCD

Primer prototipo de FLUJO para unir XIO con venues, renders, riders, planos y
layouts: una planta 2D se transforma en una proyección 3D declarativa que se
puede orbitar, medir por aristas y exportar en secuencia.

```text
tools/venue2d/referencia_plano_teatro.py  referencia visual 2D radial
tools/venue_geometria_scd.py              genera la geometría demo 2D→3D
data/venues/*.json                        fuente declarativa por venue
tools/venue.py                            registro y validación
tools/venue3d/index.html                  visor 3D sin dependencias
tools/venue3d_contexto.mjs                grafo ejecutable compartido
tools/venue3d_smoke.mjs                   prueba del visor y del presupuesto
tools/venue_secuencia.mjs                 salida reproducible por cuadros
```

La SCD actual es una DEMO derivada de constantes del plano: las cotas y alturas
no deben presentarse como levantamiento técnico. Esta herramienta está fuera
de las dos pieles del portafolio ISKVW y no participa en el selector de obras.
XIO aún no consume este registro directamente. Gaussian splat queda fuera de la
implementación actual hasta definir captura, calibración, escala y procedencia.
