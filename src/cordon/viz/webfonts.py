"""Build subset WOFF2 web fonts for the site from the vendored OFL TTFs.

The full variable TTFs in ``report/fonts`` (2.6 MB) are used for the PDF. The site
only needs Latin text plus a few symbols, so we:

- subset to those characters;
- keep only the OpenType layout features the site uses (kerning, ligatures, mark
  positioning, and the numeral styles used in tables);
- pin Source Serif's optical-size axis at the font's own default (its text-size
  design), keeping the weight axis variable. Headings use Inter Tight, so the serif
  only sets body text, where a single optical size is what most browsers would pick;
- compress to WOFF2.

The three files total about 140 KB instead of 2.6 MB (Lighthouse performance,
ADR 0013). The PDF still uses the full variable fonts, optical sizing included.

Run: ``python -m cordon.viz.webfonts``.
"""

from __future__ import annotations

from fontTools import subset
from fontTools.varLib import instancer

from cordon.config import REPO_ROOT

FONTS = REPO_ROOT / "report" / "fonts"
SOURCES = {
    "SourceSerif4[opsz,wght].ttf": "source-serif-4.woff2",
    "SourceSerif4-Italic[opsz,wght].ttf": "source-serif-4-italic.woff2",
    "InterTight[wght].ttf": "inter-tight.woff2",
}
# Basic Latin, Latin-1, general punctuation, and the symbols the site prints
# (minus, less/greater-or-equal, micro sign, subscript 2, combining macron for M-bar).
UNICODES = ",".join(
    [
        "U+0000-00FF",
        "U+0131",
        "U+0152-0153",
        "U+02C6",
        "U+02DA",
        "U+02DC",
        "U+0304",
        "U+2000-206F",
        "U+2070-209F",
        "U+2190-2193",
        "U+2212",
        "U+2264-2265",
        "U+2082",
    ]
)


LAYOUT_FEATURES = [
    "ccmp",
    "locl",
    "mark",
    "mkmk",
    "kern",
    "liga",
    "calt",
    "lnum",
    "pnum",
    "tnum",
]
PINNED_AXIS = "opsz"


def build() -> None:
    """Write one WOFF2 per source font."""
    for source, target in SOURCES.items():
        options = subset.Options()
        options.layout_features = LAYOUT_FEATURES
        options.name_IDs = ["*"]
        options.notdef_outline = True
        font = subset.load_font(str(FONTS / source), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
        subsetter.subset(font)
        axes = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
        if PINNED_AXIS in axes:
            # Subset first: instancing the full font trips over glyphs the subset drops.
            font = instancer.instantiateVariableFont(font, {PINNED_AXIS: axes[PINNED_AXIS]})
        font.flavor = "woff2"
        font.save(str(FONTS / target))


if __name__ == "__main__":
    build()
