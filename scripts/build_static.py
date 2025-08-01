#!/usr/bin/env python3
"""Build static assets into an isolated output directory."""
import gzip
import json
import pathlib
import shutil
from typing import Callable

import htmlmin
import rcssmin
import rjsmin

STATIC_DIR = pathlib.Path("app/static")
BUILD_DIR = pathlib.Path("build")


def minify_js(path: pathlib.Path) -> pathlib.Path:
    """Minify a JS file using rjsmin. Returns the minified file path."""
    dest = path
    if path.stem == "app":
        dest = path.with_suffix(".min.js")
    minified = rjsmin.jsmin(path.read_text())
    dest.write_text(minified)
    return dest


def minify_css(path: pathlib.Path) -> pathlib.Path:
    minified = rcssmin.cssmin(path.read_text())
    path.write_text(minified)
    return path


def minify_html(path: pathlib.Path) -> pathlib.Path:
    minified = htmlmin.minify(
        path.read_text(), remove_empty_space=True, remove_comments=True
    )
    path.write_text(minified)
    return path


def minify_json_file(path: pathlib.Path) -> pathlib.Path:
    data = json.loads(path.read_text())
    path.write_text(json.dumps(data, separators=(",", ":")))
    return path


def gzip_file(path: pathlib.Path) -> pathlib.Path:
    gz_path = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as src, gzip.open(gz_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    return gz_path


MINIFIERS: dict[str, Callable[[pathlib.Path], pathlib.Path]] = {
    ".js": minify_js,
    ".css": minify_css,
    ".html": minify_html,
    ".json": minify_json_file,
}


def process_file(path: pathlib.Path) -> None:
    if path.suffix in MINIFIERS and not path.name.endswith(".min.js"):
        target = MINIFIERS[path.suffix](path)
        gzip_file(target)
        print(f"Minified and compressed {target}")
    elif path.is_file() and path.suffix in {".js", ".css", ".html", ".json"}:
        gzip_file(path)
        print(f"Compressed {path}")


def build_static(
    source_dir: pathlib.Path = STATIC_DIR, build_dir: pathlib.Path = BUILD_DIR
) -> None:
    """Build assets from ``source_dir`` into ``build_dir`` without altering ``source_dir``."""
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(
        source_dir, build_dir, ignore=shutil.ignore_patterns("*.min.js", "*.gz")
    )

    for path in build_dir.rglob("*"):
        if path.is_file() and path.suffix != ".gz":
            process_file(path)


def main() -> None:
    build_static()


if __name__ == "__main__":
    main()
