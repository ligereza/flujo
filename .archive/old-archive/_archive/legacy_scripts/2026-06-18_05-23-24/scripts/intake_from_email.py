#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from flujo.intake.email_parser import parse_email_file

def main():
    if len(sys.argv) < 2:
        print("Uso: py scripts/intake_from_email.py <correo.txt>")
        sys.exit(1)
    result = parse_email_file(Path(sys.argv[1]))
    if 'error' in result:
        print(f"Error: {result['error']}")
        return
    print(f"Tipo: {result['project_type']}")
    print(f"Links: {result['link_count']}")
    for w in result.get('warnings', []):
        print(w)

if __name__ == "__main__":
    main()
