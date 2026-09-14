NAME = "zigzag"
CITATION = "zigzag: banda en chevron del kilim a peine plano, agua/montana/rayo (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    period = 6
    v = abs(((x + y) % (2 * period)) - period)
    return v % ncol
