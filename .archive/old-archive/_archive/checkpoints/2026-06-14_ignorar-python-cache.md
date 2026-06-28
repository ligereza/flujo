# Checkpoint — ignorar Python cache

Fecha: 2026-06-14

## Cambio

Se agregó a `.gitignore`:

```txt
__pycache__/
*.py[cod]
*$py.class
```

## Motivo

Evitar subir archivos generados por Python como `.pyc`.
