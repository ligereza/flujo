# HANDOFF 2026-06-28 - logo_clean_lab experimental

## Resumen

Se agrega un proyecto experimental nuevo para limpieza de logos en Illustrator:

```txt
projects/logo_clean_lab/
```

Tambien se agrega una carpeta de herramientas Illustrator:

```txt
tools/illustrator/
```

El script principal queda en:

```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

## Contexto

El usuario esta arreglando logos en Illustrator. Necesita micro-limpieza de palabras/logos ya hechos:

- alinear nodos casi verticales/horizontales;
- enderezar lineas perimetrales casi H/V;
- eliminar puntos extra innecesarios;
- evitar deformar letras redondas;
- evitar matar curvas de B/R/P/D.

## Aprendizajes importantes

No funciono bien:

- alinear palabra completa por baseline global;
- forzar diagonales a 45 grados;
- cerrar todos los handles de un nodo;
- intentar clasificar todo automaticamente sin feedback.

Decision actual:

- cerrar solo handles del segmento recto: `p1.rightDirection` y `p2.leftDirection`;
- preservar handles vecinos;
- usar modo Word cuando la palabra puede mapearse;
- registrar resultados para aprender.

## Archivos incluidos

```txt
README_AIRDROP.md
HANDOFF_2026-06-28_logo_clean_lab.md
context/LAST_HANDOFF.md
tools/illustrator/README.md
tools/illustrator/scripts/logo_clean_master.jsx
tools/illustrator/analyze_logo_learning.py
projects/logo_clean_lab/README.md
projects/logo_clean_lab/docs/PRUEBAS_Y_ERRORES.md
projects/logo_clean_lab/docs/METODO_APRENDIZAJE.md
projects/logo_clean_lab/samples/README.md
projects/logo_clean_lab/reports/README.md
projects/logo_clean_lab/learning/README.md
projects/logo_clean_lab/learning/logo_clean_results.example.jsonl
```

## Comandos de aplicacion

Windows/Git Bash:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "logo clean lab experimental"
```

Verificacion opcional:

```bash
py -m flujo verify
py tools/illustrator/analyze_logo_learning.py projects/logo_clean_lab/learning/logo_clean_results.example.jsonl
```

## Tareas simples (low token)

1. Probar `logo_clean_master.jsx` en Illustrator con una palabra simple, modo `A` y luego modo `W`.
2. Guardar 3 reportes de aprendizaje con nota: bueno / malo / que letra fallo.
3. Ajustar reglas de MIXED si B/R/P/D siguen perdiendo curvas.

## Nota plataforma

Windows: usar `py`.
Linux/macOS: usar `python3` si hace falta.
