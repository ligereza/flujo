#!/usr/bin/env python3
"""Crea un proyecto flyer_eventos desde la terminal."""
import sys
from _common import repo_root, create_flyer_project


def main():
    if len(sys.argv) < 2:
        print('Uso: py scripts/flyer_create_project.py "nombre del evento"')
        sys.exit(1)

    name = sys.argv[1]
    base = repo_root() / "projects" / "flyer_eventos"
    project = create_flyer_project(base, name, source_type="manual")
    print(f"Proyecto creado en: {project}")


if __name__ == "__main__":
    main()
