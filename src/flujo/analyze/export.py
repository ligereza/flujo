from __future__ import annotations
from pathlib import Path
import struct
import json

def save_aco(palette_data: dict, output_path: Path) -> bool:
    """Guarda paleta como .aco (Adobe Color Swatch) v1 – compatible Photoshop"""
    colors = palette_data.get("colors", [])
    if not colors:
        return False
    try:
        with open(output_path, "wb") as f:
            # version 1
            f.write(struct.pack(">H", 1))
            f.write(struct.pack(">H", len(colors)))
            for c in colors:
                r, g, b = c["rgb"]
                # ACO RGB: 0-65535
                f.write(struct.pack(">HHHHH",
                    0,  # RGB color space
                    int(r * 257),
                    int(g * 257),
                    int(b * 257),
                    0
                ))
        return True
    except Exception:
        return False

def save_ase(palette_data: dict, output_path: Path, name: str = "Flujo Palette") -> bool:
    """Guarda paleta como .ase (Adobe Swatch Exchange) – Illustrator/InDesign
    Implementación mínima, compatible.
    """
    colors = palette_data.get("colors", [])
    if not colors:
        return False
    try:
        with open(output_path, "wb") as f:
            f.write(b"ASEF")  # signature
            f.write(struct.pack(">HH", 1, 0))  # version
            # número de bloques
            num_blocks = len(colors)
            f.write(struct.pack(">I", num_blocks))
            for i, c in enumerate(colors):
                # Block type: 0x0001 = color
                f.write(struct.pack(">H", 0x0001))
                # block length placeholder, we'll compute
                name_str = f"{name} {i+1}"
                name_utf16 = name_str.encode("utf-16be")
                # length: 2 (name_len) + len(name_utf16)+2 + 4 (model) + 12 (rgb) + 2 (type)
                block_len = 2 + len(name_utf16) + 2 + 4 + 12 + 2
                f.write(struct.pack(">I", block_len))
                # name length (chars + 1 null)
                f.write(struct.pack(">H", len(name_str) + 1))
                f.write(name_utf16)
                f.write(b"\x00\x00")  # null terminator
                # color model
                f.write(b"RGB ")
                r, g, b = [x / 255.0 for x in c["rgb"]]
                f.write(struct.pack(">fff", r, g, b))
                # color type: 0 = global, 2 = spot/normal
                f.write(struct.pack(">H", 2))
        return True
    except Exception:
        return False
