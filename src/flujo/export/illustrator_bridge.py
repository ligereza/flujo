from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_illustrator_payload(spec: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    """Convertir un spec JSON simple en un payload listo para un script JSX de Illustrator."""
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    document = spec.get("document", {})
    image = spec.get("image", {})
    text_blocks = spec.get("text_blocks", [])

    image_path = str(image.get("path", "") or "")
    if image_path:
        image_path = image_path.replace("\\", "/")

    payload = {
        "document": {
            "name": document.get("name", "flujo_flyer"),
            "width": int(document.get("width", 1080)),
            "height": int(document.get("height", 1920)),
            "colorMode": document.get("colorMode", "RGB"),
        },
        "image": {
            "path": image_path,
            "linked": bool(image.get("linked", True)),
            "x": int(image.get("x", 0)),
            "y": int(image.get("y", 0)),
        },
        "text_blocks": [
            {
                "text": str(item.get("text", "")),
                "x": float(item.get("x", 0)),
                "y": float(item.get("y", 0)),
                "fontSize": float(item.get("fontSize", 36)),
                "fontFamily": item.get("fontFamily", "Arial"),
                "fill": item.get("fill", "#000000"),
            }
            for item in text_blocks
        ],
        "base_dir": str(base),
    }
    return payload


def build_illustrator_artboards_payload(spec: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    """Convertir un spec con varias tarjetas de suplemento en un payload para JSX con mesas de trabajo."""
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    document = spec.get("document", {})
    artboards = spec.get("artboards", [])
    normalized_artboards = []
    for item in artboards:
        normalized_artboards.append(
            {
                "name": str(item.get("name", "Suplemento")),
                "title": str(item.get("title", "")),
                "body": [str(part) for part in item.get("body", [])],
                "cta": str(item.get("cta", "")),
                "contact": str(item.get("contact", "")),
            }
        )
    return {
        "document": {
            "name": document.get("name", "suplementos_rd"),
            "width": int(document.get("width", 1181)),
            "height": int(document.get("height", 1654)),
            "colorMode": document.get("colorMode", "RGB"),
        },
        "artboards": normalized_artboards,
        "base_dir": str(base),
    }


def write_illustrator_bridge(spec: dict[str, Any], output_path: str | Path, base_dir: str | Path | None = None) -> Path:
    """Escribir un script JSX simple que lea un JSON y lo replique en Illustrator."""
    payload = build_illustrator_payload(spec, base_dir=base_dir)
    output_path = Path(output_path)
    output_path.write_text(_build_jsx(payload), encoding="utf-8")
    return output_path


def write_illustrator_artboards(spec: dict[str, Any], output_path: str | Path, base_dir: str | Path | None = None) -> Path:
    """Escribir un script JSX con una mesa de trabajo por suplemento."""
    payload = build_illustrator_artboards_payload(spec, base_dir=base_dir)
    output_path = Path(output_path)
    output_path.write_text(_build_artboards_jsx(payload), encoding="utf-8")
    return output_path


def _build_jsx(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"""// flujo_illustrator_bridge.jsx
#target illustrator

function main() {{
    var payload = {payload_json};
    var doc = app.documents.add(DocumentColorSpace.RGB, payload.document.width, payload.document.height);
    doc.artboards[0].name = payload.document.name;

    if (payload.image && payload.image.path) {{
        var imageFile = new File(payload.base_dir + '/' + payload.image.path);
        if (imageFile.exists) {{
            var placed = doc.placedItems.add();
            placed.file = imageFile;
            placed.name = 'Imagen';
            placed.position = [payload.image.x, payload.image.y];
        }}
    }}

    for (var i = 0; i < payload.text_blocks.length; i++) {{
        var block = payload.text_blocks[i];
        var textFrame = doc.textFrames.add();
        textFrame.position = [block.x, block.y];
        textFrame.contents = block.text;
        textFrame.textRange.characterAttributes.size = block.fontSize;
        textFrame.textRange.characterAttributes.textFont = textFonts.getByName(block.fontFamily);
    }}

    alert('Payload aplicado desde flujo');
}}

main();
"""


def _build_artboards_jsx(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"""// flujo_illustrator_artboards.jsx
#target illustrator

function addText(frame, text, size, fontName, fill) {{
    frame.contents = text;
    frame.textRange.characterAttributes.size = size;
    frame.textRange.characterAttributes.textFont = textFonts.getByName(fontName);
    frame.textRange.characterAttributes.fillColor = new RGBColor();
    frame.textRange.characterAttributes.fillColor.red = fill[0];
    frame.textRange.characterAttributes.fillColor.green = fill[1];
    frame.textRange.characterAttributes.fillColor.blue = fill[2];
}}

function main() {{
    var payload = {payload_json};
    var doc = app.documents.add(DocumentColorSpace.RGB, payload.document.width, payload.document.height);
    doc.artboards[0].name = payload.document.name;
    doc.artboards[0].artboardRect = [0, 0, payload.document.width, payload.document.height];

    var baseWidth = payload.document.width;
    var baseHeight = payload.document.height;
    var columns = 2;
    var rows = Math.ceil(payload.artboards.length / columns);
    var spacingX = 80;
    var spacingY = 80;
    var boardWidth = (baseWidth - spacingX * (columns + 1)) / columns;
    var boardHeight = (baseHeight - spacingY * (rows + 1)) / rows;

    for (var i = 0; i < payload.artboards.length; i++) {{
        var item = payload.artboards[i];
        if (i > 0) {{
            doc.artboards.add();
        }}
        var board = doc.artboards[i];
        var col = i % columns;
        var row = Math.floor(i / columns);
        var x0 = spacingX + col * (boardWidth + spacingX);
        var y0 = baseHeight - spacingY - (row + 1) * boardHeight - row * spacingY;
        board.artboardRect = [x0, y0, x0 + boardWidth, y0 + boardHeight];
        board.name = item.name;

        var rect = doc.pathItems.rectangle(y0 - boardHeight, x0, boardWidth, boardHeight);
        rect.filled = true;
        rect.stroked = true;
        rect.fillColor = new RGBColor();
        rect.fillColor.red = 246; rect.fillColor.green = 239; rect.fillColor.blue = 227;
        rect.strokeColor = new RGBColor();
        rect.strokeColor.red = 207; rect.strokeColor.green = 194; rect.strokeColor.blue = 178;

        var titleFrame = doc.textFrames.add();
        titleFrame.position = [x0 + 40, y0 - 80];
        titleFrame.contents = item.title;
        titleFrame.textRange.characterAttributes.size = 32;
        titleFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');

        var bodyFrame = doc.textFrames.add();
        bodyFrame.position = [x0 + 40, y0 - 140];
        bodyFrame.contents = item.body.join('\n');
        bodyFrame.textRange.characterAttributes.size = 18;
        bodyFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');

        if (item.cta) {{
            var ctaFrame = doc.textFrames.add();
            ctaFrame.position = [x0 + 40, y0 - 220];
            ctaFrame.contents = item.cta;
            ctaFrame.textRange.characterAttributes.size = 16;
            ctaFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');
        }}

        if (item.contact) {{
            var contactFrame = doc.textFrames.add();
            contactFrame.position = [x0 + 40, y0 - 280];
            contactFrame.contents = item.contact;
            contactFrame.textRange.characterAttributes.size = 16;
            contactFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');
        }}
    }}

    alert('Mesas de trabajo creadas desde flujo');
}}

main();
"""
