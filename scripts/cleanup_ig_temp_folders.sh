#!/usr/bin/env bash
# cleanup_ig_temp_folders.sh — elimina carpetas temporales de Instagram
# que pudieron quedar commitadas por error (rutas tipo C：.../Temp/ig_*).
#
# Uso:
#   bash scripts/cleanup_ig_temp_folders.sh
#   git add -A
#   git commit -m "chore: eliminar carpetas temporales de Instagram"

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COUNT=0

for dir in C：*/; do
  [ -d "$dir" ] || continue
  echo "Eliminando carpeta temporal: $dir"
  rm -rf "$dir"
  COUNT=$((COUNT + 1))
done

# Patrón de respaldo para nombres de Windows con caracteres de ancho completo
for dir in C＊*/; do
  [ -d "$dir" ] || continue
  echo "Eliminando carpeta temporal: $dir"
  rm -rf "$dir"
  COUNT=$((COUNT + 1))
done

if [ "$COUNT" -eq 0 ]; then
  echo "No se encontraron carpetas temporales de Instagram."
else
  echo "Eliminadas $COUNT carpeta(s)."
fi
