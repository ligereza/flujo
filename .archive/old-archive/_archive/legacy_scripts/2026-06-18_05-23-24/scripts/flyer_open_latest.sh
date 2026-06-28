#!/usr/bin/env bash
set -e

PROJECT=$(bash scripts/flyer_latest.sh)

if [ -z "$PROJECT" ]; then
  echo "No hay proyectos flyer."
  exit 1
fi

echo "Abriendo: $PROJECT"

if command -v explorer.exe >/dev/null 2>&1; then
  explorer.exe "$(cygpath -w "$PROJECT")"
else
  echo "No encontré explorer.exe. Proyecto: $PROJECT"
fi
