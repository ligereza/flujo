#!/usr/bin/env python3
"""Sanitiza texto reemplazando datos personales frecuentes por placeholders."""
from pathlib import Path
import re, sys

REPLACEMENTS = [
    (re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I), '[EMAIL]'),
    (re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b'), '[RUT]'),
    (re.compile(r'(?<!\d)(?:\+?56\s*)?(?:9\s*)?\d{4}\s*\d{4}(?!\d)'), '[TELEFONO]'),
    (re.compile(r'https?://\S+|www\.\S+', re.I), '[URL]'),
]

def main():
    if len(sys.argv) < 2:
        print('Uso: py scripts/privacy_sanitize_text.py archivo.txt [salida.txt]', file=sys.stderr)
        sys.exit(1)
    src = Path(sys.argv[1])
    text = src.read_text(encoding='utf-8', errors='ignore')
    for pat, repl in REPLACEMENTS:
        text = pat.sub(repl, text)
    header = '[[SANITIZADO: revisar manualmente antes de compartir con IA externa]]\n\n'
    out = header + text
    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(out, encoding='utf-8')
        print(f'Sanitizado escrito en: {sys.argv[2]}')
    else:
        print(out)

if __name__ == '__main__':
    main()
