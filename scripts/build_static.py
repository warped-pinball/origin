#!/usr/bin/env python3
"""Build static assets and mirror the app directory into an isolated output directory."""
import json
import pathlib
import shutil
from typing import Callable

import htmlmin
import rcssmin
import rjsmin

APP_DIR = pathlib.Path("app")
BUILD_DIR = pathlib.Path("build")


def copy_app(source: pathlib.Path, target: pathlib.Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def minify_js(path: pathlib.Path) -> pathlib.Path:
    """Minify JavaScript files.

    Most files are written to ``<name>.min.js`` to mirror the behaviour of
    other assets. The service worker is an exception: it must remain
    ``service-worker.js`` so the browser can locate it at the expected path
    after the build process. In that case the file is minified in place.
    """
    dest = path if path.name == "service-worker.js" else path.with_suffix(".min.js")
    content = rjsmin.jsmin(path.read_text())
    dest.write_text(content)
    if dest != path:
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


def build_static(
    source_dir: pathlib.Path = APP_DIR,
    build_dir: pathlib.Path = BUILD_DIR,
) -> None:
    copy_app(source_dir, build_dir)
    minify_all(build_dir)


def main() -> None:
    build_static()


if __name__ == "__main__":
    main()
