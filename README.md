# FLUJO

FLUJO es un repositorio autonomo de `ligereza/flujo`: motor portable de
workflow, CLI, workspace web y contratos para RD e ISKVW.

Si llegaste sin contexto, este directorio no es VIBECODEINE/MAK y no es XIO.
No busques otro checkout para decidir que posee este repositorio. Comprueba
Git y el estado actual; usa `STATUS.md`, `MAPA.md` y
`CAPACIDADES_FLUJO.md` sólo para ampliar los datos del checkout.

## Frontera del sistema

- `src/flujo/` es el runtime y la CLI canonicos.
- `web/` es el workspace de la aplicacion.
- RD e ISKVW son perfiles de la aplicacion, no ramas de Git.
- `contracts/` y `schemas/` son la frontera de intercambio.
- `iskvw/`, `svg/`, `assets/`, `projects/` y `data/` contienen superficies o
  configuracion propia de FLUJO, siempre respetando `.gitignore` y privacidad.
- MAK vive en `https://github.com/ligereza/vibecodeine`.
- XIO vive en `https://github.com/ligereza/XIO`.

La integracion con XIO es externa y tipada: XIO-RD puede consumir una vista
revisada de FLUJO/RD; XIO-FOH puede consumir la vista ISKVW/VJ. Ninguna de
esas relaciones convierte los perfiles en ramas ni autoriza copiar el runtime
XIO aqui.

## Git

`main` es la unica rama permanente de este repositorio. Las ramas de trabajo
son temporales; `dependabot/*` puede aparecer como automatizacion efimera. No
existe aqui una rama `FLUJO`, `MAK` o `historia`; la rama
`historia` y la procedencia del antiguo monorepo se conservan en VIBECODEINE y
se describen en [`MIGRATION.md`](MIGRATION.md).

## Desarrollo local

```bash
python -m pip install -r requirements-flujo.txt
python -m pip install -e '.[dev]'
PYTHONPATH=src python -m flujo --help
PYTHONPATH=src python -m pytest -o addopts='' -m flujo
```

El runtime debe degradar de forma explicita cuando un consumidor externo no
esta disponible. No se agregan rutas fisicas de la maquina como dependencia
por defecto.

En una instalacion conjunta con MAK, configura la proyeccion local compartida
sin copiarla al repositorio: `FLUJO_RD_DB=/ruta/al/MAK/data/rd.db` antes de
levantar el hub. Sin esa variable, FLUJO usa su propio `data/rd.db` ignorado,
que puede no existir en un checkout limpio.

## Higiene de cambios

No subas secretos, `.env`, bases SQLite, archivos `*-wal`/`*-shm`, caches,
`node_modules` ni salidas generadas. Antes de entregar una modificacion,
ejecuta `git diff --check`, la prueba afectada y comprueba que el cambio no
cruza la frontera hacia MAK o XIO.
