# HANDOFF - Limpieza estructural raíz (v0.34.11)

**Fecha:** 2026-06-22
**Estado:** Completado
**Autor:** Grok + Maximiliano

## Cambios realizados
- Movidos todos los `HANDOFF_*`, `HOTFIX_*`, `AUDITORIA_*`, `REVISION_*` → `docs/handoffs/`
- Actualizar `docs/REPO_MAP.md` y `docs/HIGIENE_REPO.md` (agregar sección sobre handoffs)
- Actualizar referencias en `README.md` si mencionan archivos viejos en raíz

## Próximos pasos recomendados
- Bump versión a v0.34.11
- Sincronizar docs de agentes
- Verificar que `flujo` CLI siga funcionando (`pip install -e .`)

**Validación:** `ls docs/handoffs/ | wc -l` debería mostrar muchos archivos.
