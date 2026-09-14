"""
NOTA Ω (12-jul-2026): este meter mide tokens. La Tilde del sistema Ω NO es
ahorro de tokens -- es el residuo intraducible (Quine/Lotman). Este modulo
usa el nombre en dialecto degradado; ver puente/TILDE_NOTA.md. Registrado
como ⊕₃.

tilde_meter -- mide que le pasa al espanol cuando se comprime.

Pieza de datos del proyecto artistico "tilde" (projects/tilde/): cada vez que
el modo Idea comprime una idea en espanol a un prompt para Claude, este modulo
cuenta las marcas que construyen significado (n con tilde, vocales acentuadas,
apertura de pregunta/exclamacion) en la entrada y en la salida, detecta palabras
degradadas (ano vs el año que era) y acumula un corpus local en JSONL.

Puro stdlib, sin red, sin tkinter. El log es material del usuario: queda
gitignored en desktop/tilde_log.jsonl.

Uso directo:
    python tilde_meter.py resumen    # aprendizaje acumulado del corpus
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections import Counter
from typing import Dict, List, Optional

MARKS = "áéíóúüñÁÉÍÓÚÜÑ¿¡"

_LOG_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tilde_log.jsonl")

_WORD_RE = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", re.UNICODE)


def count_marks(text: str) -> Dict[str, int]:
    """Cuenta cada marca de MARKS presente en el texto (solo las que aparecen)."""
    counter = Counter(ch for ch in text if ch in MARKS)
    return dict(counter)


def strip_marks(word: str) -> str:
    """Colapsa la palabra: sin tildes, sin dieresis, la n pierde su ñ."""
    decomposed = unicodedata.normalize("NFD", word)
    base = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return base.replace("¿", "").replace("¡", "")


def degraded_words(original: str, compressed: str) -> List[List[str]]:
    """
    Palabras con marcas en el original que aparecen COLAPSADAS en la salida:
    la version con marca ya no esta, pero su esqueleto sin marca si.
    Devuelve pares [palabra_original, palabra_colapsada], sin duplicados.
    """
    comp_words = set(_WORD_RE.findall(compressed.lower()))
    pairs: List[List[str]] = []
    seen = set()
    for word in _WORD_RE.findall(original):
        low = word.lower()
        if low in seen or not any(ch in MARKS for ch in low):
            continue
        seen.add(low)
        stripped = strip_marks(low)
        if stripped != low and low not in comp_words and stripped in comp_words:
            pairs.append([low, stripped])
    return pairs


def measure(original: str, compressed: str) -> Dict:
    """Metrica de una compresion: cuantas marcas entran, cuantas sobreviven."""
    in_marks = count_marks(original)
    out_marks = count_marks(compressed)
    total_in = sum(in_marks.values())
    total_out = sum(out_marks.values())
    return {
        "chars_in": len(original),
        "chars_out": len(compressed),
        "marks_in": total_in,
        "marks_out": total_out,
        "survival": round(total_out / total_in, 3) if total_in else None,
        "per_mark": {m: [in_marks.get(m, 0), out_marks.get(m, 0)]
                     for m in sorted(set(in_marks) | set(out_marks))},
        "degraded": degraded_words(original, compressed),
    }


def measure_and_log(original: str, compressed: str, path: Optional[str] = None) -> Dict:
    """Mide y acumula la muestra en el corpus JSONL local. Nunca lanza."""
    result = measure(original, compressed)
    try:
        entry = dict(result)
        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry["original"] = original
        entry["compressed"] = compressed
        with open(path or _LOG_DEFAULT, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 -- el medidor jamas rompe la app
        pass
    return result


def summarize(path: Optional[str] = None) -> Dict:
    """Aprendizaje acumulado del corpus: supervivencia media, marcas mas perdidas."""
    log_path = path or _LOG_DEFAULT
    samples = []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
    except FileNotFoundError:
        return {"samples": 0}

    survivals = [s["survival"] for s in samples if s.get("survival") is not None]
    lost = Counter()
    degraded = Counter()
    for s in samples:
        for mark, (n_in, n_out) in s.get("per_mark", {}).items():
            if n_in > n_out:
                lost[mark] += n_in - n_out
        for pair in s.get("degraded", []):
            degraded[f"{pair[0]} -> {pair[1]}"] += 1
    return {
        "samples": len(samples),
        "avg_survival": round(sum(survivals) / len(survivals), 3) if survivals else None,
        "marks_most_lost": lost.most_common(8),
        "words_most_degraded": degraded.most_common(12),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "resumen":
        print(json.dumps(summarize(), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
