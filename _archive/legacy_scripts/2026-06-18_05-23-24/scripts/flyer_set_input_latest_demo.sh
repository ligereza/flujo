#!/usr/bin/env bash
set -e

PROJECT=$(bash scripts/flyer_latest.sh)

if [ -z "$PROJECT" ]; then
  echo "No hay proyectos flyer."
  exit 1
fi

echo "Usando proyecto: $PROJECT"

py scripts/flyer_set_input.py "$PROJECT" "C:\rd\AUTOMATIZACION\input_ig.jpg"
