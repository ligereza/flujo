# Capacidades vigentes de FLUJO

Esta ficha describe solo el repositorio autonomo `ligereza/flujo`. No declara
servicios, bases, agentes ni departamentos de MAK; tampoco declara el runtime
movil de XIO.

## Superficies propias

| Superficie | Ubicacion | Funcion |
| --- | --- | --- |
| Runtime y CLI | `src/flujo/` | comandos, motores, contratos y adaptadores |
| Hub local | `src/flujo/web/hub.py` | workspace HTTP y perfiles de aplicacion |
| RD | `src/flujo/rd/` | eventos, venues, cotizacion, pedidos y lectura de datos |
| ISKVW/VJ | `src/flujo/vj/`, `web/`, `iskvw/` | contexto visual, show kit y portafolio |
| Contratos | `contracts/`, `schemas/` | intercambio tipado y validacion |
| Herramientas | `tools/` | generadores, validadores y comprobaciones deterministas; incluye la cadena venue 2D→3D |

## Perfiles de aplicacion

`main`, `rd`, `iskvw` y `rd-plano` son modos de la aplicacion. No son ramas,
repositorios ni autoridades Git distintas.

## Consumidores externos

- XIO-RD consume una vista revisada de datos y contexto RD.
- XIO-FOH consume contexto ISKVW/VJ y portafolio para la superficie FOH.
- MAK puede consumir o proyectar contratos FLUJO desde su propio repositorio.

El sentido de intercambio se expresa con JSON tipado, `source_ref`, API o
esquemas versionados. No se importan hubs vecinos ni se asumen rutas locales.

## Verificacion minima

```bash
PYTHONPATH=src python -m flujo --help
PYTHONPATH=src python -m pytest -o addopts='' -m flujo
git diff --check
```

Los artefactos historicos del monorepo no son parte de esta ficha. La
procedencia y la lista de exclusiones estan en `MIGRATION.md`.
