# GitHub Actions · piezas vectoriales

Este workflow permite generar archivos desde GitHub sin correr scripts localmente.

Archivo:

```txt
.github/workflows/render_piezas_vectoriales.yml
```

## Qué hace

Cuando se ejecuta:

1. Instala Python y matplotlib.
2. Genera todos los proyectos genéricos con:

```bash
python scripts/piezas_generar.py "projects/piezas_vectoriales/*/config.json"
```

3. Genera el proyecto especial Suplementos RD si existe.
4. Valida con:

```bash
python scripts/piezas_check_outputs.py
```

5. Sube los resultados como artifact:

```txt
piezas-vectoriales-generadas
```

## Cómo usarlo desde GitHub

1. Ir a la pestaña **Actions**.
2. Elegir **Render piezas vectoriales**.
3. Click en **Run workflow**.
4. Esperar que termine.
5. Descargar el artifact generado.

## Cuándo se ejecuta solo

Se ejecuta automáticamente si hay cambios en:

```txt
projects/piezas_vectoriales/**
tools/piezas_vectoriales/**
scripts/piezas_*.py
```

También corre en Pull Requests que toquen esos archivos.

## Nota

Los outputs generados siguen ignorados por git. GitHub los entrega como artifacts descargables.
