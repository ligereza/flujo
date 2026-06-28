#!/usr/bin/env python3
"""Lista y sugiere formatos/plantillas de piezas_vectoriales."""
from pathlib import Path
import json, sys, math

INDEX = Path('tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json')

def load():
    return json.loads(INDEX.read_text(encoding='utf-8'))['formatos']

def score(fmt, w, h, tipo=''):
    fw = fmt['real_size_cm']['width']; fh = fmt['real_size_cm']['height']
    ratio_diff = abs((fw/fh) - (w/h))
    size_diff = abs(fw-w) + abs(fh-h)
    type_bonus = 0 if not tipo or tipo.lower() in fmt.get('tipo','').lower() else 10
    return ratio_diff*10 + size_diff + type_bonus

def main():
    formatos = load()
    if len(sys.argv) >= 3:
        w = float(sys.argv[1].replace(',', '.')); h = float(sys.argv[2].replace(',', '.'))
        tipo = sys.argv[3] if len(sys.argv) >= 4 else ''
        ranked = sorted(formatos, key=lambda f: score(f,w,h,tipo))
        print(f'Sugerencia para {w:g} x {h:g} cm {tipo}:')
        for f in ranked[:5]:
            s=f['real_size_cm']; c=f['canvas']
            print(f"- {f['id']} | {s['width']}x{s['height']} cm | {c['width']}x{c['height']} px | {f['template']}")
    else:
        print('Formatos disponibles:')
        for f in formatos:
            s=f['real_size_cm']; c=f['canvas']
            print(f"- {f['id']} ({f['tipo']}): {s['width']}x{s['height']} cm → {c['width']}x{c['height']} px")
        print('\nSugerir: py scripts/piezas_formatos.py 16.5 6.5 etiqueta')

if __name__ == '__main__': main()
