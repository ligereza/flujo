# Migracion a repositorio autonomo

## Identidad

- Destino: `https://github.com/ligereza/flujo.git`
- Rama permanente: `main`
- Fecha de preparacion: 2026-09-14
- Fuente principal: `ligereza/vibecodeine`
- Fuente funcional: rama historica `FLUJO`, commit `87c849fd1ea23b940a3ec2cd7e4fd29cba67fc7c`
- Cambios locales integrados: checkout `integration/flujo-canonical-20260911`,
  commit base `f2d08916f8237529035bd2584bcd6806cc9eac25`

La migracion crea una historia Git propia sobre el repositorio destino. La
historia completa del monorepo no se copia como ramas activas: queda
preservada en VIBECODEINE, junto con su rama `historia` y sus referencias de
archivo. Esto evita que un checkout nuevo vuelva a interpretar MAK y FLUJO
como ramas del mismo proyecto.

## Incluido

- `src/flujo/`, CLI, runtime web, RD, VJ y contratos.
- Workspace web, superficies ISKVW, SVG, assets y proyectos pequenos ligados a
  FLUJO.
- Esquemas, configuracion acotada, documentacion vigente, herramientas y
  pruebas del motor.
- Este contrato de entrada, el estado medido y la frontera entre repositorios.

## Excluido deliberadamente

- `xio/`: runtime, plugins, Android y operaciones de XIO; pertenece a
  `ligereza/XIO`.
- Hub, departamentos, investigacion y bases locales de MAK.
- Worktrees de agentes, `context-history`, datadrops, inbox, experimentos,
  documentos recuperados y archivos de trabajo de la maquina.
- Bases SQLite y sus archivos WAL/SHM, secretos, caches, `node_modules` y
  salidas generadas.
- Workflows que dependian de hacer checkout de MAK o XIO dentro de este
  repositorio.

## Regla de continuidad

Un agente nuevo que llegue a `ligereza/flujo` debe poder trabajar sin montar
`/home/mak`, sin conocer la estructura de VIBECODEINE y sin crear una rama
paralela llamada `FLUJO`. Si necesita comunicarse con MAK o XIO, debe localizar
el contrato en `contracts/` o `schemas/` y registrar el `source_ref` de la
proyeccion usada.
