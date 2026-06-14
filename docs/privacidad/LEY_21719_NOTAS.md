# Notas Ley 21.719 Chile — privacidad de datos

## Fuentes de referencia

- BCN / Historia de la Ley 21.719: https://www.bcn.cl/historiadelaley/nc/historia-de-la-ley/8352/
- Referencias públicas consultadas indican vigencia plena el 1 de diciembre de 2026 y creación de la Agencia de Protección de Datos Personales.

## Ideas operativas para el repo

Este repo no busca dar asesoría legal, sino reducir riesgo operacional cuando se trabaja con IA y archivos creativos.

### Principios a cuidar

- Finalidad: usar datos solo para el propósito del pedido.
- Minimización: no incluir datos personales innecesarios en prompts/configs.
- Seguridad: no exponer datos en repos públicos, logs o artifacts.
- Responsabilidad: dejar evidencia de revisión cuando haya datos personales.
- Derechos de titulares: considerar acceso, rectificación, cancelación/supresión, oposición y portabilidad según corresponda.

### Riesgos típicos del flujo actual

- Pegar correos completos en IA web con teléfonos, correos, RUT o direcciones.
- Subir PDFs internos a GitHub público.
- Dejar datos personales dentro de `jobs/`, `briefs/`, `outputs` o artifacts.
- Generar prompts que incluyan datos sensibles no necesarios.
- Procesar datos de salud, consumo, menores, trabajadores o asistentes sin revisión.

### Regla práctica

Antes de usar IA externa:

```txt
1. Copiar el correo/documento.
2. Sanitizar datos personales no necesarios.
3. Guardar original fuera del repo público.
4. Usar versión sanitizada en jobs/prompts.
5. Marcar privacidad en el job.
```
