"""Extract the two Bootstrap Icons the site uses as standalone SVG files.

Quarto ships Bootstrap Icons as a 180 KB web font plus a 15 KB render-blocking
stylesheet. The site uses only two glyphs: the GitHub mark in the navbar and the
PDF icon next to the paper's PDF link. This module converts those glyphs to SVG
paths once and writes ``report/icons/<name>.svg``. The post-render step
(``report/scripts/postprocess.py``) inlines them and drops the font stylesheet
(ADR 0013).

Bootstrap Icons is MIT licensed (Copyright 2019-2024 The Bootstrap Authors); the
notice is kept in each SVG.

Run: ``python -m cordon.viz.icons <path to Quarto's bootstrap-icons.woff>``.
The font is in Quarto's install under
``share/formats/html/bootstrap/dist/bootstrap-icons.woff``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from cordon.config import REPO_ROOT

OUTPUT_DIR = REPO_ROOT / "report" / "icons"
# Icon name -> code point, from Quarto's bootstrap-icons.css (Bootstrap Icons 1.13.1).
ICONS = {"github": 0xF3ED, "file-pdf": 0xF640}
NOTICE = "Bootstrap Icons (https://icons.getbootstrap.com/), MIT License, (c) The Bootstrap Authors"


def glyph_svg(font: TTFont, code_point: int) -> str:
    """One glyph as an SVG document in a square viewBox, y-axis flipped to SVG orientation."""
    glyph_name = font.getBestCmap()[code_point]
    glyph_set = font.getGlyphSet()
    size = font["head"].unitsPerEm
    ascent = font["hhea"].ascent
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(TransformPen(pen, (1, 0, 0, -1, 0, ascent)))
    return (
        f"<!-- {NOTICE} -->\n"
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
        f'<path d="{pen.getCommands()}"/></svg>\n'
    )


def main(woff_path: Path) -> None:
    """Write one SVG per icon."""
    font = TTFont(str(woff_path))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, code_point in ICONS.items():
        (OUTPUT_DIR / f"{name}.svg").write_text(glyph_svg(font, code_point))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
