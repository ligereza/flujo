#!/usr/bin/env bash
set -e

PROJECT="$1"

if [ -z "$PROJECT" ]; then
  echo "Uso: bash scripts/flyer_set_input_demo.sh \"projects/flyer_eventos/NOMBRE_PROYECTO\""
  exit 1
fi

py scripts/flyer_set_input.py "$PROJECT" "C:\rd\AUTOMATIZACION\input_ig.jpg"
