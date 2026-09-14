NAME = "boteh"
CITATION = "boteh: la gota-cipres persa sembrada en el campo, hoja/llama/vida que se esparce (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    b = 10
    lx = (x % b) - b / 2.0
    ly = (y % b) - b / 2.0
    ry = b * 0.42
    rx = b * 0.30
    bend = 1.6 * (ly / max(1.0, ry))
    if (lx - bend) ** 2 / max(1e-6, rx * rx) + ly * ly / max(1e-6, ry * ry) <= 1.0:
        return min(int(abs(ly) / max(1.0, ry) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
