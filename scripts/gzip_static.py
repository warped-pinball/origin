#!/usr/bin/env python3
"""Gzip compress static assets in app/static."""
import pathlib
import gzip
import shutil

STATIC_DIR = pathlib.Path('app/static')

def gzip_file(path: pathlib.Path) -> None:
    gz_path = path.with_suffix(path.suffix + '.gz')
    with path.open('rb') as src, gzip.open(gz_path, 'wb') as dst:
        shutil.copyfileobj(src, dst)


def main() -> None:
    for path in STATIC_DIR.rglob('*'):
        if path.is_file() and path.suffix in {'.js', '.css', '.html', '.json'}:
            gzip_file(path)
            print(f'Compressed {path}')

if __name__ == '__main__':
    main()