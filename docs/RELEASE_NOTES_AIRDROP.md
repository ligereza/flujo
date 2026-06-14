# Release notes airdrop latest

Este paquete agrega al repo `flujo`:

- Sistema de piezas vectoriales desde JSON.
- Jobs desde correos/briefs.
- Privacidad básica para IA.
- Plantillas y componentes.
- Mantenimiento/health check.
- GitHub Actions para render remoto.

## Comandos principales

```bash
py scripts/flujo.py health
py scripts/flujo.py clean
py scripts/flujo.py job-from-text "nombre" inbox/correo.txt
py scripts/flujo.py job-prepare jobs/NOMBRE
py scripts/flujo.py job-activate jobs/NOMBRE
py scripts/flujo.py render projects/piezas_vectoriales/NOMBRE/config.json
```
