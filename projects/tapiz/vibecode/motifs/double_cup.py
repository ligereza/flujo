NAME = "double_cup"
CITATION = "double cup: el vaso doble de vibecodeine (vibe+codeine), iconografia contemporanea tejida (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    tw, th = 16, 16
    lx = x % tw
    ly = y % th
    cx = tw / 2.0
    top, bottom = th * 0.18, th * 0.72
    if top <= ly <= bottom:
        frac = (ly - top) / max(1e-6, bottom - top)
        half = (tw * 0.30) * (1 - 0.45 * frac)
        dx = abs(lx - cx)
        if abs(dx - half) < 1.1 or abs(ly - top) < 1.1:
            return 0
        if dx < half:
            return min(int((1 - dx / max(1e-6, half)) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
