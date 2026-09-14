#!/usr/bin/env python3
"""
Wrapper de compatibilidad. La implementacion vive en vibecode/spaces.py
(reconciliacion 2026-07-10: una sola implementacion, primitivas compartidas
en vibecode/ansi.py). La CLI documentada sigue funcionando igual:

    python projects/tapiz/vibecode_spaces.py archivo.py -m flow -a -p flujo
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vibecode.spaces import (  # noqa: E402,F401
    PALETTES,
    SAMPLE_CODE,
    main,
    render_frame,
    render_spaces,
    render_static,
)

if __name__ == "__main__":
    main()
