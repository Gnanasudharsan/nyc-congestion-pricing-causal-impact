"""Build subset WOFF2 web fonts for the site from the vendored OFL TTFs.

The full variable TTFs in ``report/fonts`` (2.6 MB) are used for the PDF. The site
only needs Latin text plus a few symbols, so we subset to those characters, keep
the variable axes (weight, optical size), and compress to WOFF2. This cuts the
font download by roughly 90% (Lighthouse performance).

Run: ``python -m cordon.viz.webfonts``.
"""

from __future__ import annotations

from fontTools import subset

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


def build() -> None:
    """Write one WOFF2 per source font."""
    for source, target in SOURCES.items():
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.notdef_outline = True
        font = subset.load_font(str(FONTS / source), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
        subsetter.subset(font)
        subset.save_font(font, str(FONTS / target), options)


if __name__ == "__main__":
    build()
