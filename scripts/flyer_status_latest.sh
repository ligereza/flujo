#!/usr/bin/env bash
set -e

PROJECT=$(bash scripts/flyer_latest.sh)

if [ -z "$PROJECT" ]; then
  echo "No hay proyectos flyer."
  exit 1
fi

py scripts/flyer_status.py "$PROJECT"
