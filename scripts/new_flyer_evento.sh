#!/usr/bin/env bash
set -e

NAME="$1"

if [ -z "$NAME" ]; then
  echo "Uso: bash scripts/new_flyer_evento.sh \"nombre del evento\""
  exit 1
fi

py scripts/flyer_create_project.py "$NAME"
