# Motivos externos del loom (plugins). Cada archivo <nombre>.py define NAME,
# CITATION y color_index(x, y, n_cols, n_rows, n_colors) -> int | None. loom.py
# los carga solo al importar y extiende LOOM_MODES/MOTIF_CITATIONS. Archivos
# que empiezan con "_" se ignoran. Contrato: mismo modelo que loom_color_index
# (indice de paleta en [0, n_colors) o None para vacio; deterministico por
# posicion; definido para todo el canvas incl. 1x1).
