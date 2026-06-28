#!/usr/bin/env bash
set -e

echo ""
echo "========================================"
echo " DIMENSIONES DEL ORDEN"
echo "========================================"
echo ""

echo "Repo:"
basename "$(pwd)"
echo ""

echo "Contexto:"
if [ -f context/ESTADO.md ]; then
  head -n 20 context/ESTADO.md
else
  echo "No existe context/ESTADO.md"
fi

echo ""
echo "----------------------------------------"
echo "Herramientas:"
if [ -d tools ]; then
  find tools -mindepth 1 -maxdepth 1 -type d | sort
else
  echo "No existe tools/"
fi

echo ""
echo "----------------------------------------"
echo "Proyectos flyer:"
if [ -d projects/flyer_eventos ]; then
  find projects/flyer_eventos -mindepth 1 -maxdepth 1 -type d | sort
else
  echo "No hay proyectos flyer."
fi

echo ""
echo "----------------------------------------"
echo "Último proyecto flyer:"
if [ -f scripts/flyer_latest.sh ]; then
  bash scripts/flyer_latest.sh
else
  echo "No existe scripts/flyer_latest.sh"
fi

echo ""
echo "----------------------------------------"
echo "Último checkpoint:"
if [ -d checkpoints ]; then
  find checkpoints -type f | sort | tail -n 1
else
  echo "No hay checkpoints."
fi

echo ""
echo "========================================"
