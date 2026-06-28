# Job → Proyecto → Render

Cuando un job ya está revisado o se quiere activar diseño:

```bash
py scripts/job_activate.py "jobs/YYYY-MM-DD_nombre"
```

Esto:

1. Ejecuta `brief_to_project.py`.
2. Crea proyecto en `projects/piezas_vectoriales/`.
3. Cambia estado del job a `en_diseno`.
4. Escribe `resultado.md` con próxima acción.

Para renderizar el proyecto:

```bash
py scripts/project_render.py "projects/piezas_vectoriales/NOMBRE/config.json"
```

Esto:

1. Valida config.
2. Genera outputs.
3. Escribe `render_report.md` dentro del proyecto.
