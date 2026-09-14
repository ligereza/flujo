NAME = "comb"
CITATION = "peine / comb: peine bereber tejido como amuleto de higiene ritual y proteccion contra el mal de ojo (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    g = 8
    lx = x % g
    ly = y % g
    if ly == g - 1:
        return 0  # lomo del peine
    if lx % 2 == 0 and ly >= g // 2:
        return min(ly % ncol, ncol - 1)  # dientes verticales
    return ((x // 4) + (y // 2)) % ncol
