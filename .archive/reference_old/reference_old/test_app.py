#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test rápido de la app"""

import sys
sys.path.insert(0, r'c:\rd\AUTOMATIZACION')

try:
    from automatizador_flyers_v2 import AppV2, main
    print("OK: Importacion exitosa")
    print("OK: AppV2 disponible")
    print("OK: main disponible")
    print("\nLa app esta lista. Ejecuta:")
    print("  python automatizador_flyers_v2.pyw")
    print("\nO haz doble click en:")
    print("  automatizador_flyers_v2.pyw")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
