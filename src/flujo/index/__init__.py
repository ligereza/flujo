"""flujo.index - indexador del arbol de material ($FLUJO_RD_ROOT) para agentes/IA (solo lectura)."""
from .indexer import (  # noqa: F401
    load_index, find, versions, dupes, cleanup, stats,
    build_from_inventory, build_from_walk, save_index,
)
from .code_index import (  # noqa: F401
    build_index as build_code_index,
    load_index as load_code_index,
    make_brief as make_code_brief,
    save_index as save_code_index,
)
