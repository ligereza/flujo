import math

NAME = "tree_of_life"
CITATION = "arbol de la vida: eje que une tierra y cielo, axis mundi de las alfombras de jarron (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    nc = max(1, n_cols)
    nr = max(1, n_rows)
    cx = (nc - 1) / 2.0
    if abs(x - cx) <= 1.0 and y > nr * 0.18:
        return 0  # tronco central
    dx = (x - cx) / max(1.0, cx)
    dy = y / max(1, nr - 1)  # foco (copa) hacia arriba: asimetrico
    dist = math.sqrt(dx * dx + dy * dy)
    return min(int(dist * ncol), ncol - 1)
