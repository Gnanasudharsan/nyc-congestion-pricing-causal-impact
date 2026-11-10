"""Quarto post-render step: stop the unused colour-scheme stylesheet blocking first paint.

Quarto writes both Bootstrap themes (light and dark), plus a duplicate "extra" link,
as rel="stylesheet". At load time its own script then sets the inactive ones to
rel="disabled-stylesheet". By then the browser has already blocked rendering on all
of them. Here we start the alternate (dark) and the duplicate as disabled. Quarto's
script still enables whichever scheme the visitor's preference or the toggle asks for,
so dark mode works as before.

It also adds width and height attributes to every PNG <img>, read from the file
header, so the browser reserves space and the layout does not shift when figures
load (Lighthouse CLS). Standard library only, so CI needs no extra packages.
"""

import os
import re
import struct
from pathlib import Path

OUTPUT = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
ALTERNATE = 'rel="stylesheet" append-hash="true" class="quarto-color-scheme quarto-color-alternate"'
EXTRA = 'rel="stylesheet" append-hash="true" class="quarto-color-scheme-extra"'

IMG = re.compile(r'<img src="([^"]+\.png)"([^>]*)>')


def png_size(path: Path) -> tuple[int, int]:
    """Width and height from a PNG's IHDR chunk."""
    with path.open("rb") as handle:
        header = handle.read(24)
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def add_dimensions(page: Path, html: str) -> str:
    """Give every PNG image intrinsic width/height attributes."""

    def replace(match: re.Match[str]) -> str:
        source, rest = match.group(1), match.group(2)
        if "width=" in rest or "height=" in rest:
            return match.group(0)
        image = (page.parent / source).resolve()
        if not image.exists():
            return match.group(0)
        width, height = png_size(image)
        return f'<img src="{source}" width="{width}" height="{height}"{rest}>'

    return IMG.sub(replace, html)


for page in OUTPUT.rglob("*.html"):
    html = page.read_text(encoding="utf-8")
    off = 'rel="disabled-stylesheet"'
    patched = html.replace(ALTERNATE, ALTERNATE.replace('rel="stylesheet"', off))
    patched = patched.replace(EXTRA, EXTRA.replace('rel="stylesheet"', off))
    patched = add_dimensions(page, patched)
    if patched != html:
        page.write_text(patched, encoding="utf-8")
