# Backlog — herramienta privacidad datos Ley 21.719

Estado: en_cola
Prioridad: alta antes de diciembre 2026

## Objetivo

Crear herramienta para revisar/sanitizar correos, briefs, PDFs y prompts antes de usarlos con IA o subirlos al repo.

## Alcance inicial

- Detectar datos personales en texto.
- Generar versión sanitizada.
- Generar reporte de privacidad.
- Marcar jobs con riesgo de privacidad.
- Evitar que datos personales queden en prompts, GitHub público o artifacts.

## Primer MVP propuesto

```bash
py scripts/privacy_scan_text.py "jobs/.../pedido_original.txt"
py scripts/privacy_sanitize_text.py "jobs/.../pedido_original.txt" > sanitized_prompt.txt
```

## Pendiente

- Definir patrones Chile: RUT, teléfono, email, dirección.
- Definir categorías sensibles.
- Integrar con `job_new` / `job_extract_brief`.
- Agregar campo `privacidad` en `brief.yaml`.
