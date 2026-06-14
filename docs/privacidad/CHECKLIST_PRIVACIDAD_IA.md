# Checklist privacidad para IA/chat/web

Antes de pegar información en una IA externa o subirla a GitHub:

- [ ] ¿El texto contiene nombres de personas naturales?
- [ ] ¿Contiene RUT, pasaporte u otro identificador?
- [ ] ¿Contiene correos personales?
- [ ] ¿Contiene teléfonos?
- [ ] ¿Contiene direcciones?
- [ ] ¿Contiene datos de salud, consumo, orientación, menores, biometría, finanzas o datos sensibles?
- [ ] ¿Contiene información de asistentes, voluntarios, trabajadores o proveedores?
- [ ] ¿Todos esos datos son necesarios para la tarea?
- [ ] ¿Se puede reemplazar por `[NOMBRE]`, `[EMAIL]`, `[TELEFONO]`, `[DIRECCION]`?
- [ ] ¿El repo donde se subirá es público?
- [ ] ¿Los artifacts/outputs pueden contener datos personales?
- [ ] ¿Hay base/autorización para el tratamiento?
- [ ] ¿Debe revisarlo una persona antes de compartir?

Resultado recomendado:

```txt
riesgo_privacidad: bajo / medio / alto
aprobado_para_ia_externa: sí / no
requiere_sanitizacion: sí / no
requiere_revision_humana: sí / no
```
