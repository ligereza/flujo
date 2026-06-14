# GitHub Issue → Job

Cuando un pedido llegue por GitHub Issue:

1. Copiar el cuerpo del issue a un archivo temporal o `inbox/`.
2. Crear job:

```bash
py scripts/flujo.py job-from-text "nombre issue" inbox/issue.txt
```

3. Preparar job:

```bash
py scripts/flujo.py job-prepare jobs/YYYY-MM-DD_nombre-issue
```

4. Revisar:

```bash
py scripts/flujo.py job-next
```

5. Si queda `listo_para_disenar`:

```bash
py scripts/flujo.py brief-to-project jobs/YYYY-MM-DD_nombre-issue/brief.yaml
```

## Respuesta sugerida al issue

```txt
Job creado: jobs/...
Estado: pendiente_datos / listo_para_disenar
Privacidad: revisar privacy_report.md
Siguiente acción: ...
```
