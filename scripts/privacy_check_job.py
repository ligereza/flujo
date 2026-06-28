#!/usr/bin/env python3
"""Genera reporte y versión sanitizada para un job."""
from pathlib import Path
import subprocess, sys

if len(sys.argv) < 2:
    print('Uso: py scripts/privacy_check_job.py jobs/NOMBRE')
    sys.exit(1)
job = Path(sys.argv[1])
pedido = job / 'pedido_original.txt'
if not pedido.exists():
    print('No existe', pedido); sys.exit(1)
report = job / 'privacy_report.md'
san = job / 'pedido_sanitizado.txt'
scan = subprocess.run([sys.executable, 'scripts/privacy_scan_text.py', str(pedido)], text=True, capture_output=True, check=True).stdout
report.write_text(scan, encoding='utf-8')
subprocess.run([sys.executable, 'scripts/privacy_sanitize_text.py', str(pedido), str(san)], check=True)
print(f'Reporte: {report}')
print(f'Sanitizado: {san}')
