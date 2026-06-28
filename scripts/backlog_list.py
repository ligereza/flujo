#!/usr/bin/env python3
from pathlib import Path
print('Backlog:')
for p in sorted(Path('jobs/_backlog').glob('*.md')):
    first=''
    for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
        if line.startswith('# '): first=line[2:]; break
    print(f'- {p}: {first}')
