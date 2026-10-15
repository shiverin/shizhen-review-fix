#!/usr/bin/env python3
"""Install an isolated review/fix pair without overwriting existing workflows."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess


def install(destination, login, identity):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', login):
        raise ValueError('Expected a GitHub login')
    if type(identity) is not int or identity < 1:
        raise ValueError('Expected a positive GitHub user ID')
    source = Path(__file__).resolve().parent / 'templates'
    files = [p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    conflicts = [str(p.relative_to(source)) for p in files
                 if (destination / p.relative_to(source)).exists()]
    if conflicts:
        raise FileExistsError('Existing files would be overwritten: ' + ', '.join(conflicts))
    for original in files:
        target = destination / original.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    settings = destination / '.github/shizhen-fix/config.json'
    config = json.loads(settings.read_text())
    config.update(author_login=login, author_id=identity)
    settings.write_text(json.dumps(config, indent=2) + '\n')
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--author', required=True, help='Only this GitHub author may receive fixes')
    parser.add_argument('--author-id', type=int, help='Verified numeric ID; otherwise resolved with gh')
    args = parser.parse_args()
    identity = args.author_id
    if identity is None:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.author):
            parser.error('Invalid GitHub login')
        identity = int(subprocess.check_output(
            ['gh', 'api', f'users/{args.author}', '--jq', '.id'], text=True).strip())
    count = install(args.destination.resolve(), args.author, identity)
    print(f'Installed {count} files. Fixes are restricted to {args.author} (ID {identity}).')
    print('No secrets, repository settings, commits, pushes, or merges were changed.')


if __name__ == '__main__':
    main()
