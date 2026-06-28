#!/usr/bin/env bash
# cleanup_moderate.sh — Limpieza moderada del repo

set -e

echo "════════════════════════════════════════════════════════════"
echo "           FLUJO — Limpieza Moderada"
echo "════════════════════════════════════════════════════════════"
echo ""

read -p "¿Mover jobs/, briefs/ y recipes/ a _archive/? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p _archive
    [ -d jobs ] && mv jobs _archive/jobs_$(date +%Y%m%d) && echo "Movido: jobs/"
    [ -d briefs ] && mv briefs _archive/briefs_$(date +%Y%m%d) && echo "Movido: briefs/"
    [ -d recipes ] && mv recipes _archive/recipes_$(date +%Y%m%d) && echo "Movido: recipes/"
fi

echo ""
echo "Limpieza de archivos temporales..."
find . -name "*.tmp" -o -name "*.temp" -o -name "*~" 2>/dev/null | head -20 | xargs rm -f 2>/dev/null || true

echo ""
echo "Limpieza completada."
echo "Revisa con: git status"
