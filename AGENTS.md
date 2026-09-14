# Contrato de entrada para agentes

Este directorio es el repositorio autonomo `ligereza/flujo`. Su contenido no
se interpreta como un worktree de otro repositorio.

## Lectura obligatoria

1. Lee este archivo.
2. Lee `README.md`.
3. Lee `STATUS.md`, `MAPA.md` y `CAPACIDADES_FLUJO.md`.
4. Lee `MIGRATION.md` solo cuando necesites procedencia o limites historicos.

Si dos documentos difieren, el codigo y los contratos actuales tienen
precedencia; `MIGRATION.md` solo explica de donde provino este checkout.

## Limites de propiedad

- Este repositorio contiene el motor portable FLUJO, su CLI, workspace web,
  contratos, esquemas y superficies RD/ISKVW.
- `ligereza/vibecodeine` es el repositorio externo de MAK. No se debe buscar
  aqui su Hub, sus departamentos, sus bases locales ni sus instrucciones.
- `ligereza/XIO` es el repositorio externo de campo movil. XIO-RD consume
  contexto RD y XIO-FOH consume contexto ISKVW mediante contratos; XIO no se
  copia dentro de este repositorio.
- RD e ISKVW son perfiles de la aplicacion y superficies de datos, no ramas de
  Git.

No importes modulos desde un checkout vecino, no uses rutas como
`/home/mak/flujo` como contrato y no reintroduzcas un Hub de MAK dentro de
FLUJO. Las integraciones externas deben usar JSON tipado, `source_ref`, API o
los esquemas versionados en este repositorio.

## Git

- `main` es la unica rama permanente y el unico tronco de despliegue.
- Las ramas de trabajo son temporales y deben volver a `main` tras revision.
- No crees aqui ramas `FLUJO`, `MAK`, `historia`, `integration` ni ramas por
  checkout vecino. `historia` pertenece al registro historico de VIBECODEINE.
- Antes de modificar, mide `git status`, lee el contrato relevante y ejecuta
  una prueba acotada. No borres trabajo ajeno ni resuelvas divergencias con
  `reset --hard`.

## Higiene

No versionar bases SQLite, WAL/SHM, secretos, `.env`, caches, `node_modules`,
salidas generadas ni datos privados. Un documento historico no es una
instruccion vigente: si debe conservarse por procedencia, ponlo en
`MIGRATION.md` o en un enlace externo, no lo presentes como autoridad activa.
