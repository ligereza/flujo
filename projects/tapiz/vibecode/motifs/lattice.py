NAME = "lattice"
CITATION = "lattice: la red de rombos que sostiene el jardin, enrejado de la parra (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    m = 8
    if (x + y) % m < 1 or (x - y) % m < 1:
        return 0
    if ncol <= 1:
        return 0
    return 1 + (((x // m) + (y // m)) % (ncol - 1))
