#!/usr/bin/env python3
"""Minify a JavaScript file.

Usage:
    python scripts/minify_js.py path/to/file.js [output.js]

Writes a minified copy of the source file. If the output path is not
provided, ``.min.js`` is appended to the source filename.
"""
import argparse
import pathlib
import re

def minify_js(source: str) -> str:
    """A tiny JS minifier: strips comments and collapses whitespace."""
    # Remove multiline comments
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    # Remove single line comments
    source = re.sub(r"//.*", "", source)
    # Collapse whitespace
    source = re.sub(r"\s+", " ", source)
    return source.strip()

def main() -> None:
    parser = argparse.ArgumentParser(description="Minify a JavaScript file")
    parser.add_argument("src", help="Source JS file")
    parser.add_argument("dest", nargs="?", help="Destination file")
    args = parser.parse_args()

    src_path = pathlib.Path(args.src)
    if not src_path.exists():
        raise SystemExit(f"Source file {src_path} does not exist")
    dest_path = pathlib.Path(args.dest) if args.dest else src_path.with_suffix(".min.js")

    minified = minify_js(src_path.read_text())
    dest_path.write_text(minified)
    print(f"Wrote {dest_path}")

if __name__ == "__main__":
    main()
