NAME = "running_dog"
CITATION = "running dog / perro corriente: greca ondulada de los bordes, ola continua que protege el campo (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    p = 8
    if x % p == 0:
        return 0  # gancho de la greca
    phase = (x // p) % 2
    crest = y % p
    step = crest if phase == 0 else (p - 1 - crest)
    return step % ncol
