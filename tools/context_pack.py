#!/usr/bin/env python3
"""Paquete minimo de contexto para pasar a Aider / Qwen / Claude (bajo consumo).

Uso:
  py tools/context_pack.py <ruta|glob>... [--max-lines N]
Imprime cada archivo con cabecera + fence (copiable directo), y un estimado de
tokens a stderr. La idea: mandar SOLO lo relevante, no todo el repo.
"""
import sys, glob, os
from pathlib import Path

def est_tokens(s): return max(1, len(s) // 4)

def main():
    argv = sys.argv[1:]
    maxl = None
    if "--max-lines" in argv:
        i = argv.index("--max-lines"); maxl = int(argv[i + 1]); del argv[i:i + 2]
    files = []
    for a in argv:
        files += [p for p in glob.glob(a, recursive=True) if os.path.isfile(p)]
    files = sorted(dict.fromkeys(files))
    if not files:
        print("sin archivos. uso: py tools/context_pack.py <ruta|glob>... [--max-lines N]")
        return
    total = ""
    for f in files:
        try:
            txt = Path(f).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if maxl:
            lines = txt.splitlines()
            if len(lines) > maxl:
                txt = "\n".join(lines[:maxl]) + f"\n... [truncado: {len(lines) - maxl} lineas mas]"
        ext = Path(f).suffix.lstrip(".") or "text"
        block = f"\n### {f}\n```{ext}\n{txt}\n```\n"
        sys.stdout.write(block); total += block
    print(f"\n--- ~{est_tokens(total)} tokens estimados, {len(files)} archivo(s) ---", file=sys.stderr)

if __name__ == "__main__":
    main()
