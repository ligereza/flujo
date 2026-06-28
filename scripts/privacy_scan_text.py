#!/usr/bin/env python3
"""Escaneo básico de privacidad para textos antes de usar IA externa.
No reemplaza revisión legal/humana.
"""
from pathlib import Path
import re, sys

PATTERNS = {
    'email': re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I),
    'rut_chile': re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b'),
    'telefono_cl': re.compile(r'(?<!\d)(?:\+?56\s*)?(?:9\s*)?\d{4}\s*\d{4}(?!\d)'),
    'url': re.compile(r'https?://\S+|www\.\S+', re.I),
}

SENSITIVE_KEYWORDS = [
    'salud', 'diagnóstico', 'diagnostico', 'médico', 'medico', 'psicológica', 'psicologica',
    'consumo', 'sustancias', 'droga', 'drogas', 'menor de edad', 'menores', 'rut',
    'dirección', 'direccion', 'domicilio', 'cuenta bancaria', 'transferencia', 'tarjeta',
    'trabajador', 'trabajadora', 'asistente', 'voluntario', 'voluntaria'
]

def main():
    if len(sys.argv) < 2:
        print('Uso: py scripts/privacy_scan_text.py archivo.txt')
        sys.exit(1)
    p = Path(sys.argv[1])
    text = p.read_text(encoding='utf-8', errors='ignore')
    print(f'# Reporte privacidad: {p}')
    print('')
    total = 0
    risk = 'bajo'
    for name, pat in PATTERNS.items():
        matches = pat.findall(text)
        count = len(matches)
        total += count
        print(f'- {name}: {count}')
        if count:
            risk = 'medio'
            sample = matches[:3]
            print('  muestras:', ', '.join(str(x)[:80] for x in sample))
    found_kw = sorted({kw for kw in SENSITIVE_KEYWORDS if kw.lower() in text.lower()})
    print(f'- palabras_sensibles/contexto: {len(found_kw)}')
    if found_kw:
        print('  detectadas:', ', '.join(found_kw[:20]))
        risk = 'alto' if any(k in found_kw for k in ['salud','diagnóstico','diagnostico','médico','medico','consumo','sustancias','menor de edad','menores']) else risk
    print('')
    print(f'riesgo_privacidad: {risk}')
    print(f'requiere_sanitizacion: {str(total > 0).lower()}')
    print(f'requiere_revision_humana: {str(risk == "alto").lower()}')
    print(f'aprobado_para_ia_externa: {str(risk == "bajo").lower()}')

if __name__ == '__main__':
    main()
