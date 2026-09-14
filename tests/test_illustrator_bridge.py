from pathlib import Path

from flujo.export.illustrator_bridge import (
    build_illustrator_artboards_payload,
    build_illustrator_payload,
)


def test_build_illustrator_payload_includes_text_and_image(tmp_path: Path) -> None:
    spec = {
        "document": {"width": 1080, "height": 1920, "name": "demo"},
        "image": {"path": "input/input_ig.jpg", "linked": True},
        "text_blocks": [
            {"text": "Hola", "x": 100, "y": 100, "fontSize": 48, "fontFamily": "Arial"}
        ],
    }

    payload = build_illustrator_payload(spec, base_dir=tmp_path)

    assert payload["document"]["name"] == "demo"
    assert payload["text_blocks"][0]["text"] == "Hola"
    assert payload["image"]["path"].endswith("input/input_ig.jpg")


def test_build_illustrator_artboards_payload_creates_multiple_boards() -> None:
    spec = {
        "document": {"width": 1080, "height": 1920, "name": "suplementos_rd"},
        "artboards": [
            {"name": "Impulso", "title": "IMPULSO", "body": ["Aumenta el foco y la alerta."]},
            {"name": "Creatina", "title": "CREATINA", "body": ["Energía celular y recuperación."]},
        ],
    }

    payload = build_illustrator_artboards_payload(spec)

    assert payload["document"]["name"] == "suplementos_rd"
    assert len(payload["artboards"]) == 2
    assert payload["artboards"][0]["title"] == "IMPULSO"
