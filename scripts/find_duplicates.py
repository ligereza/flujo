#!/usr/bin/env python3
"""find_duplicates.py — Detecta archivos duplicados por contenido"""

import hashlib
from pathlib import Path
from collections import defaultdict

def find_duplicates(root: Path):
    hashes = defaultdict(list)

    for file in root.rglob("*"):
        if file.is_file() and ".git" not in str(file):
            try:
                h = hashlib.md5(file.read_bytes()).hexdigest()
                hashes[h].append(str(file))
            except:
                pass

    duplicates = {k: v for k, v in hashes.items() if len(v) > 1}

    if not duplicates:
        print("No se encontraron duplicados.")
        return

    print(f"\nSe encontraron {len(duplicates)} grupos de duplicados:\n")
    for h, files in duplicates.items():
        print(f"Hash: {h[:8]}...")
        for f in files:
            print(f"  - {f}")
        print()

if __name__ == "__main__":
    find_duplicates(Path("."))
