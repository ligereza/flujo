#!/usr/bin/env python3
"""Soft cleanup: trim trailing whitespace beyond two spaces in text files.

Rules:
- Preserve up to two trailing spaces (Markdown hard line break).
- Remove trailing tabs.
- Normalize lines that are only whitespace to empty lines.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '_airdrop', '_airdrop_backups', '.gitignore'}
PATTERNS = ['*.md', '*.markdown', '*.txt', 'README*']

def should_exclude(path: Path):
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False

def process_file(path: Path):
    changed = False
    with path.open('r', encoding='utf-8', newline='') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # remove trailing tabs
        line = line.rstrip('\t')
        # separate newline
        nl = ''
        if line.endswith('\n'):
            nl = '\n'
            line = line[:-1]
        # count trailing spaces
        stripped = line.rstrip(' ')
        trailing = len(line) - len(stripped)
        if trailing > 2:
            line = stripped + '  '
        else:
            line = line
        # if line is only whitespace, make it empty
        if line.strip(' ') == '':
            line = ''
        new_lines.append(line + nl)

    if new_lines != lines:
        changed = True
        with path.open('w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)
    return changed

def main():
    modified = []
    for pat in PATTERNS:
        for path in ROOT.rglob(pat):
            if path.is_file() and not should_exclude(path):
                try:
                    if process_file(path):
                        modified.append(str(path.relative_to(ROOT)))
                except Exception as e:
                    print(f"skip {path}: {e}", file=sys.stderr)

    if modified:
        print('Modified files:')
        for p in modified:
            print(' -', p)
        return 0
    else:
        print('No changes')
        return 0

if __name__ == '__main__':
    sys.exit(main())
