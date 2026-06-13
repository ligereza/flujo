#!/usr/bin/env bash
set -e

NAME="$1"

if [ -z "$NAME" ]; then
  echo "Uso: bash scripts/new_flyer_evento.sh \"nombre del evento\""
  exit 1
fi

SAFE_NAME=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//')
DATE=$(date +%Y-%m-%d)

DIR="projects/flyer_eventos/${DATE}_${SAFE_NAME}"

mkdir -p "$DIR/input" "$DIR/working" "$DIR/exports" "$DIR/refs"

cat > "$DIR/manifest.json" <<EOC
{
  "tool": "flyer_eventos",
  "name": "$NAME",
  "date": "$DATE",
  "status": "created",
  "input": {
    "main_image": "",
    "event_name": "$NAME",
    "event_date": "",
    "format": "",
    "notes": ""
  },
  "steps": {
    "photoshop": "pending",
    "blender": "pending",
    "export": "pending"
  },
  "outputs": []
}
EOC

cat > "$DIR/README.md" <<EOC
# Flyer evento — $NAME

Fecha: $DATE

## Objetivo

Crear flyer para evento.

## Inputs

- Imagen principal:
- Fecha evento:
- Formato:
- Notas:

## Flujo

1. Poner imagen base en \`input/\`.
2. Procesar en Photoshop.
3. Exportar JPG a \`working/\`.
4. Usar en Blender.
5. Export final en \`exports/\`.

## Estado

- [ ] Input listo
- [ ] Photoshop
- [ ] Blender
- [ ] Export final
EOC

echo "Proyecto creado en: $DIR"

