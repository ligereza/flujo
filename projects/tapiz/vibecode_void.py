#!/usr/bin/env python3
"""
Wrapper de compatibilidad. La implementacion vive en vibecode/void.py
(reconciliacion 2026-07-10: una sola implementacion, primitivas compartidas
en vibecode/ansi.py). La CLI documentada sigue funcionando igual:

    python projects/tapiz/vibecode_void.py archivo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vibecode.void import (  # noqa: E402,F401
    auto_generator,
    generate_line,
    main,
    render_line_blocks,
    render_line_negative,
    stream_window,
)

if __name__ == "__main__":
    main()
