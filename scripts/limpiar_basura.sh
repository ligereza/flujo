#!/usr/bin/env bash
# Limpia archivos basura, generados y de prueba del repo.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Limpiando basura de flujo ==="

# Pycache
find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true

# Outputs generados de piezas vectoriales
find projects/piezas_vectoriales -type d -name "salida_generada" -exec rm -rf {} + 2>/dev/null || true

# Reportes diarios generados
rm -f context/DAILY.md
rm -f context/PIPELINE_RESULT.md
rm -f context/dashboard.html

# Data generada
rm -f data/flyer_index.json
rm -f data/flyer_duplicates_report.json

# Backups de airdrop antiguos
rm -rf _airdrop_backups/* 2>/dev/null || true

# Limpiar directorios vacíos de airdrop backups
find _airdrop_backups -type d -empty -delete 2>/dev/null || true

echo "Limpieza completa."
