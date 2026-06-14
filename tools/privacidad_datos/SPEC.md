# Tool: privacidad_datos

Herramienta en cola para prevenir riesgos de datos personales en flujos con IA, diseño, briefs, correos, repos y archivos de impresión.

## Contexto Chile

Chile cuenta con la Ley 21.719, que regula la protección y el tratamiento de datos personales y crea la Agencia de Protección de Datos Personales. La vigencia plena se considera para diciembre de 2026.

## Objetivo de la herramienta

Antes de pegar correos, briefs, PDFs, bases de clientes o documentos internos a una IA o subirlos al repo, la herramienta debe ayudar a:

1. Detectar datos personales.
2. Detectar datos sensibles.
3. Minimizar información innecesaria.
4. Anonimizar o seudonimizar datos.
5. Clasificar riesgo del pedido.
6. Recomendar si se puede usar IA externa, IA local o revisión humana.
7. Dejar evidencia/checklist de tratamiento.

## Casos de uso

- Correos del jefe/cliente con nombres, teléfonos, RUT, direcciones, pagos o datos de asistentes.
- Briefs de eventos con información de producción, seguridad, salud o asistentes.
- Archivos PDF/Excel con clientes, voluntarios, trabajadores o proveedores.
- Prompts enviados a IA web.
- Repositorios GitHub con documentos internos.
- Logs de generación que podrían contener datos personales.

## Reglas iniciales

- No subir RUT, teléfonos, correos, direcciones, datos de salud, datos financieros o listas de personas si no son necesarios.
- No pegar en IA externa datos sensibles sin base, autorización y minimización.
- Si el dato no aporta al diseño/producción, eliminarlo antes del prompt.
- Mantener archivo original en zona privada/local, y trabajar con versión sanitizada.
- Para datos sensibles o alto riesgo, marcar `requiere_revision_humana: true`.

## Salidas futuras deseadas

```txt
privacy_report.md
sanitized_prompt.txt
sanitized_brief.yaml
privacy_checklist.yaml
```

## Estados de privacidad sugeridos

```txt
sin_revisar
sanitizado
requiere_revision
alto_riesgo_no_compartir
aprobado_para_ia_externa
```

## Próximos scripts propuestos

```txt
scripts/privacy_scan_text.py
scripts/privacy_sanitize_text.py
scripts/privacy_check_job.py
```

## MVP implementado

```bash
py scripts/privacy_scan_text.py "archivo.txt"
py scripts/privacy_sanitize_text.py "archivo.txt" "archivo_sanitizado.txt"
py scripts/privacy_check_job.py "jobs/NOMBRE"
```

`privacy_check_job.py` genera:

```txt
privacy_report.md
pedido_sanitizado.txt
```
