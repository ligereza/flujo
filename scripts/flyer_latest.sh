#!/usr/bin/env bash
set -e

BASE="projects/flyer_eventos"

if [ ! -d "$BASE" ]; then
  echo ""
  exit 0
fi

find "$BASE" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1
