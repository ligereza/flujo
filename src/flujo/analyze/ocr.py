from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

def run_ocr(image_path: Path) -> Dict[str, Any]:
    """
    OCR opcional con pytesseract.
    Si no está instalado, devuelve {"available": False}
    """
    try:
        from PIL import Image
        import pytesseract
    except Exception as e:
        return {
            "available": False,
            "reason": str(e),
            "hint": "pip install pytesseract  &&  apt install tesseract-ocr tesseract-ocr-spa  # en Debian/Ubuntu /  brew install tesseract  # macOS"
        }

    try:
        im = Image.open(image_path)
        # intentar español + inglés
        text = ""
        for lang in ("spa+eng", "spa", "eng"):
            try:
                text = pytesseract.image_to_string(im, lang=lang)
                if text.strip():
                    break
            except Exception:
                continue
        if not text.strip():
            text = pytesseract.image_to_string(im)

        return {
            "available": True,
            "text": text,
            "chars": len(text),
            "lines": len(text.splitlines()),
        }
    except Exception as e:
        return {"available": True, "error": str(e), "text": ""}

def extract_hints_from_text(text: str) -> Dict[str, Any]:
    """Extrae posibles fechas, horas, arrobas, hashtags del OCR"""
    import re
    hints = {}

    # fechas tipo 12/06, 12-06-2026, 12 junio, jun 12
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\b",
    ]
    dates = []
    for pat in date_patterns:
        dates.extend(re.findall(pat, text, re.IGNORECASE))
    if dates:
        hints["possible_dates"] = sorted(set(dates))[:5]

    # horas 22:00, 23h, 10pm
    times = re.findall(r"\b\d{1,2}[:h]\d{2}\b|\b\d{1,2}\s*(?:am|pm|hrs|hs)\b", text, re.IGNORECASE)
    if times:
        hints["possible_times"] = sorted(set(times))[:5]

    # @usuarios / #hashtags
    users = re.findall(r"@[\w.]+", text)
    if users:
        hints["mentions"] = sorted(set(users))[:10]

    tags = re.findall(r"#[\wáéíóúñ]+", text, re.IGNORECASE)
    if tags:
        hints["hashtags"] = sorted(set(tags))[:10]

    return hints
