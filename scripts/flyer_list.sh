#!/usr/bin/env bash
set -e

BASE="projects/flyer_eventos"

if [ ! -d "$BASE" ]; then
  echo "No existe $BASE"
  exit 0
fi

echo "Proyectos flyer:"
echo ""

find "$BASE" -mindepth 1 -maxdepth 1 -type d | sort
