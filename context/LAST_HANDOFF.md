# Ultimo handoff de FLUJO

Fecha de corte: 2026-09-14.

Este checkout es el repositorio autonomo `ligereza/flujo`. La entrada para una
sesion nueva esta en `../AGENTS.md` y el estado breve en `../STATUS.md`.

La unica rama permanente es `main`. RD e ISKVW son perfiles de aplicacion.
XIO y MAK son repositorios externos; las integraciones deben pasar por
contratos, `source_ref`, API o esquemas versionados.

No usar un checkout vecino para completar rutas faltantes. Si aparece una
dependencia externa, registrar el contrato y el motivo de degradacion antes de
continuar.
