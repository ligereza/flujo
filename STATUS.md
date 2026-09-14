# STATUS — FLUJO autonomo

Fecha de corte: 2026-09-14

## Estado

- Separacion completada y publicada en `https://github.com/ligereza/flujo.git`.
- Commit de migracion: `e28038c9458ebc58699d3fc929c0a722414c8e35`.
- `main` es la unica rama permanente de este repositorio.
- XIO no forma parte del arbol; la relacion XIO-RD/FLUJO-RD y
  XIO-FOH/FLUJO-ISKVW queda documentada como integracion externa.
- RD e ISKVW siguen siendo perfiles de aplicacion, no ramas Git.

## Preservacion

La procedencia del antiguo worktree y su historia permanecen en VIBECODEINE;
este checkout no depende de esa copia ni de una ruta local vecina.

## Siguiente comprobacion

```bash
PYTHONPATH=src python -m flujo --help
PYTHONPATH=src python -m pytest -o addopts='' -m flujo
git diff --check
```

Si una prueba o herramienta pide una ruta de MAK, XIO o `/home/mak`, se trata
de una dependencia cruzada que debe degradar o convertirse en contrato
externo; no se debe volver a copiar el checkout vecino.
