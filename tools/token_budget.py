#!/usr/bin/env python3
"""Estima tokens de un set de archivos antes de mandarlos a un modelo.

Uso: py tools/token_budget.py <ruta|glob>...
Estimacion ~ chars/4 (aprox GPT/Claude). Sirve para no gastar de mas.
"""
import sys, glob, os
from pathlib import Path

def est(n): return max(1, n // 4)

def main():
    files = []
    for a in sys.argv[1:]:
        files += [p for p in glob.glob(a, recursive=True) if os.path.isfile(p)]
    files = sorted(dict.fromkeys(files))
    if not files:
        print("uso: py tools/token_budget.py <ruta|glob>..."); return
    tot_c = 0
    print(f"{'tokens~':>9}  {'chars':>8}  archivo")
    for f in files:
        try:
            n = len(Path(f).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        tot_c += n
        print(f"{est(n):>9}  {n:>8}  {f}")
    print(f"{'-'*30}")
    print(f"{est(tot_c):>9}  {tot_c:>8}  TOTAL ({len(files)} archivos)")

if __name__ == "__main__":
    main()
