# learning

Esta carpeta guarda ejemplos de resultados para aprender de pruebas reales.

Archivos recomendados:

```txt
logo_clean_results.jsonl        # archivo local con resultados de trabajo real
mini_dataset.jsonl             # dataset base de referencia para pruebas
logo_clean_results.example.jsonl
```

Para validar el dataset base:

```bash
python projects/logo_clean_lab/scripts/validate_dataset.py projects/logo_clean_lab/learning/mini_dataset.jsonl
```

Se recomienda no subir logos reales ni datos sensibles. El ejemplo incluido sirve para documentar el formato sin exponer información privada.
