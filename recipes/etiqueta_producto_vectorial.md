# Receta: etiqueta producto vectorial

Usar cuando pidan etiquetas para impresión/Illustrator.

## Flujo

1. Crear job en `jobs/YYYY-MM-DD_nombre/` copiando `jobs/_template/`.
2. Pegar correo en `pedido_original.txt`.
3. Completar `brief.yaml`.
4. Si falta info crítica, preguntar máximo 3 cosas.
5. Crear proyecto en `projects/piezas_vectoriales/NOMBRE/` desde plantilla.
6. Editar `config.json`.
7. Generar:

```bash
py scripts/piezas_generar.py "projects/piezas_vectoriales/NOMBRE/config.json"
```

8. Validar:

```bash
py scripts/piezas_check_outputs.py
```

9. Completar `resultado.md`.

## Acelerar extracción desde correo

Después de pegar el correo en `pedido_original.txt`:

```bash
py scripts/job_extract_brief.py "jobs/YYYY-MM-DD_nombre"
```

Revisar `brief.yaml` antes de generar.

## Crear proyecto base desde brief

```bash
py scripts/brief_to_project.py "jobs/YYYY-MM-DD_nombre/brief.yaml"
```

Luego ajustar `config.json` y generar.
