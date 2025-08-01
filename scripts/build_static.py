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

def copy_static(source: pathlib.Path, target: pathlib.Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("*.min.js", "*.gz"),
    )
    print(f"Copied {source} → {target}")

def minify_js(path: pathlib.Path) -> pathlib.Path:
    dest = path.with_suffix(".min.js")
    content = rjsmin.jsmin(path.read_text())
    dest.write_text(content)
    path.unlink()
    return dest

def minify_css(path: pathlib.Path) -> pathlib.Path:
    content = rcssmin.cssmin(path.read_text())
    path.write_text(content)
    return path

def minify_html(path: pathlib.Path) -> pathlib.Path:
    content = htmlmin.minify(
        path.read_text(),
        remove_empty_space=True,
        remove_comments=True,
    )
    path.write_text(content)
    return path

def minify_json(path: pathlib.Path) -> pathlib.Path:
    data = json.loads(path.read_text())
    path.write_text(json.dumps(data, separators=(",", ":")))
    return path

def gzip_file(path: pathlib.Path) -> pathlib.Path:
    gz_path = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as src, gzip.open(gz_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    path.unlink()  # Remove the original file after zipping
    return gz_path

MINIFIERS: dict[str, Callable[[pathlib.Path], pathlib.Path]] = {
    ".js": minify_js,
    ".css": minify_css,
    ".html": minify_html,
    ".json": minify_json,
}

def minify_all(build_dir: pathlib.Path) -> None:
    for path in build_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in MINIFIERS and not path.name.endswith(".min.js"):
            new_path = MINIFIERS[path.suffix](path)
            print(f"Minified {path} → {new_path}")

def gzip_all(build_dir: pathlib.Path) -> None:
    for path in build_dir.rglob("*"):
        if not path.is_file() or path.name.endswith(".gz"):
            continue
        gz = gzip_file(path)
        print(f"Gzipped {path} → {gz}")

def build_static(
    source_dir: pathlib.Path = STATIC_DIR,
    build_dir: pathlib.Path = BUILD_DIR,
) -> None:
    copy_static(source_dir, build_dir)
    minify_all(build_dir)
    gzip_all(build_dir)

def main() -> None:
    build_static()

if __name__ == "__main__":
    main()
