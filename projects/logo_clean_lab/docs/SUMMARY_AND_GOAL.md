# Summary and goal - logo_clean_lab

## Goal

Crear un sistema practico para probar scripts de limpieza de logos en Illustrator, sin prometer automatizacion perfecta.

El script debe ayudar cuando el logo ya esta hecho y se ve bien, pero tiene imperfecciones tecnicas:

- nodos casi alineados que deberian compartir X o Y;
- perimetros casi verticales/horizontales que deben quedar a 90 grados;
- puntos extra sobre tramos rectos;
- handles que curvan hacia afuera en letras rectas;
- letras mixtas donde hay que preservar curvas, por ejemplo B/R/P/D.

## Summary

Se consolido un script principal:

```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

El flujo recomendado es:

1. Convertir texto a contornos.
2. Seleccionar palabra completa o forma.
3. Correr primero modo Audit.
4. Correr modo Word con la palabra ingresada.
5. Guardar reporte.
6. Registrar resultado bueno/malo en `learning/logo_clean_results.jsonl`.

Principios decididos:

- El logo ya existe; no hay que redibujarlo.
- Las correcciones deben ser pequenas.
- La palabra ingresada solo da pistas: recta, redonda, angular o mixta.
- No usar alineacion global agresiva de palabra.
- No destruir handles de curvas en letras mixtas.
- Aprender con evidencia: reportes, notas y comparacion antes/despues.

## Estado actual

Unfinished / experimental.

El siguiente paso no es agregar mas complejidad, sino probar 3 a 5 logos simples y registrar fallos concretos.
