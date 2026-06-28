#!/usr/bin/env bash
# cleanup_legacy_scripts.sh — Limpia scripts legacy duplicados (moderado)

set -e

echo "════════════════════════════════════════════════════════════"
echo "           FLUJO — Limpieza de Scripts Legacy"
echo "════════════════════════════════════════════════════════════"
echo ""

LEGACY=(
  "flyer_analyze.py"
  "flyer_create_project.py"
  "flyer_from_email.py"
  "flyer_index.py"
  "flyer_index.sh"
  "flyer_latest.sh"
  "flyer_list.sh"
  "flyer_status.py"
  "flyer_status_latest.sh"
  "ig_download.py"
  "ig_redownload.py"
)

mkdir -p _archive/legacy_scripts_$(date +%Y%m%d)

for script in "${LEGACY[@]}"; do
    if [ -f "scripts/$script" ]; then
        mv "scripts/$script" "_archive/legacy_scripts_$(date +%Y%m%d)/" 2>/dev/null || true
        echo "Archivado: $script"
    fi
done

echo ""
echo "Limpieza de scripts legacy completada."
echo "Los scripts fueron movidos a _archive/legacy_scripts_$(date +%Y%m%d)/"
