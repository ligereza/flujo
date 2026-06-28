#!/usr/bin/env python3
"""Inspección básica de PDF sin dependencias externas.
Extrae número aproximado de páginas y cajas MediaBox/CropBox/TrimBox/BleedBox/ArtBox.
"""
from pathlib import Path
import re
import sys

PT_TO_CM = 2.54 / 72


def parse_box(s):
    nums = [float(x) for x in re.findall(rb'-?\d+(?:\.\d+)?', s)]
    if len(nums) >= 4:
        x0,y0,x1,y1 = nums[:4]
        return x0,y0,x1,y1
    return None


def main():
    if len(sys.argv) < 2:
        print('Uso: py scripts/pdf_probe_basic.py archivo.pdf')
        sys.exit(1)
    p = Path(sys.argv[1])
    data = p.read_bytes()
    pages = re.findall(rb'/Type\s*/Page\b', data)
    print(f'Archivo: {p}')
    print(f'Tamaño: {p.stat().st_size/1024:.1f} KB')
    print(f'Páginas detectadas: {len(pages)}')
    for box_name in [b'MediaBox', b'CropBox', b'TrimBox', b'BleedBox', b'ArtBox']:
        matches = re.findall(rb'/' + box_name + rb'\s*\[([^\]]+)\]', data)
        if not matches:
            continue
        print(f'\n{box_name.decode()}:')
        seen = []
        for i,m in enumerate(matches[:20], start=1):
            box = parse_box(m)
            if not box:
                continue
            x0,y0,x1,y1 = box
            w_pt,h_pt = x1-x0, y1-y0
            w_cm,h_cm = w_pt*PT_TO_CM, h_pt*PT_TO_CM
            key = (round(w_cm,2), round(h_cm,2))
            seen.append(key)
            print(f'  {i:02d}: {w_pt:.3f} x {h_pt:.3f} pt  ≈  {w_cm:.2f} x {h_cm:.2f} cm')
        uniq = []
        for k in seen:
            if k not in uniq:
                uniq.append(k)
        print('  Únicas aprox:', ', '.join(f'{a}x{b} cm' for a,b in uniq))

if __name__ == '__main__':
    main()
