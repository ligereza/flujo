# Operador IA rápido

## Si el usuario pega un correo

```bash
py scripts/flujo.py job-from-text "nombre pedido" inbox/correo.txt
py scripts/flujo.py job-prepare jobs/YYYY-MM-DD_nombre
py scripts/flujo.py job-next
```

## Si el job está listo

```bash
py scripts/flujo.py job-activate jobs/YYYY-MM-DD_nombre
py scripts/flujo.py render projects/piezas_vectoriales/NOMBRE/config.json
py scripts/piezas_check_outputs.py
```

## Si faltan datos

Usar:

```txt
briefs/RESPUESTA_IA_FALTAN_DATOS.md
```

## Antes de commit

```bash
py scripts/flujo.py clean
py scripts/flujo.py health
```
