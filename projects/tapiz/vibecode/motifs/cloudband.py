import math

NAME = "cloudband"
CITATION = "cloudband / chi: cinta de nube china que cruza el campo, aliento del cielo y longevidad (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    nr = max(1, n_rows)
    band_h = max(2, nr // 5)
    ripple = int(round(2 * math.sin(x * 0.4)))
    yy = y + ripple
    if yy % band_h < 2:
        return 0
    if ncol <= 1:
        return 0
    return 1 + ((yy // band_h) % (ncol - 1))
