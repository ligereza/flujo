# STATUS — FLUJO autonomo

Fecha de corte: 2026-09-14 — verificación de transporte Unix del Hub

## Estado

- Separacion completada y publicada en `https://github.com/ligereza/flujo.git`.
- Commit de migracion: `e28038c9458ebc58699d3fc929c0a722414c8e35`.
- `main` es la unica rama permanente de este repositorio.
- El remoto puede mostrar ramas temporales `dependabot/*` generadas por
  GitHub; no son ramas permanentes ni de dominio.
- XIO no forma parte del arbol; la relacion XIO-RD/FLUJO-RD y
  XIO-FOH/FLUJO-ISKVW queda documentada como integracion externa.
- RD e ISKVW siguen siendo perfiles de aplicacion, no ramas Git.
- La proyeccion SQLite no se versiona en este repositorio. En la instalacion
  conjunta actual, FLUJO y XIO-RD deben usar `FLUJO_RD_DB=/home/mak/data/rd.db`;
  sin esa configuracion, un checkout limpio reporta RD como no construido.

## Preservacion

La procedencia del antiguo worktree y su historia permanecen en VIBECODEINE;
este checkout no depende de esa copia ni de una ruta local vecina.

## Verificacion local

- `PYTHONPATH=src python -m pytest -o addopts='' -m flujo`: `1631 passed`;
  los skips corresponden a dependencias o entornos no disponibles.
- Hub `:8765`: ping, summary/topics RD, read-only context, RD panel, VJ/ISKVW
  context, dashboard y SVG respondieron correctamente.
- La base RD local no se versiona. Para compartir la única proyección del host
  con MAK/XIO se usa `FLUJO_RD_DB`; en esta máquina apunta a
  `/home/mak/data/rd.db`. El read model VJ regenerable vive aparte en
  `data/vj_event_context.db` y contiene 7 eventos.
- `rd_datos.db` no es una segunda base activa: las tablas de campo viven en la
  proyección `rd.db`; el archivo vacío histórico quedó archivado por MAK.
- El estado operativo local reconoce la topología consolidada: Hub TCP en
  `:8900` y Research/Codex por sockets Unix privados del Hub, con TCP antiguo
  solo como fallback de ejecución aislada. No se abrieron listeners nuevos.
- La simplificación de navegación pertenece a MAK: el Hub deja cinco
  superficies principales visibles y agrupa las operativas secundarias bajo
  `más`, sin cambiar rutas ni contratos de FLUJO.
- Esta actualización del detector quedó publicada en `main` como
  `d96b9f7` (`fix(status): detect private consumer sockets`).

## Siguiente comprobacion

```bash
PYTHONPATH=src python -m flujo --help
PYTHONPATH=src python -m pytest -o addopts='' -m flujo
git diff --check
```

Si una prueba o herramienta pide una ruta de MAK, XIO o `/home/mak`, se trata
de una dependencia cruzada que debe degradar o convertirse en contrato
externo; no se debe volver a copiar el checkout vecino.
