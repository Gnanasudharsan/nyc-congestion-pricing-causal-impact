"""Shared figure style: Cordon color tokens and matplotlib defaults.

Series colors are fixed across every figure (CLAUDE.md design tokens):
treated/zone, control/comparison, spillover. They were checked with the
dataviz palette validator (all-pairs CVD ΔE >= 10.3, normal-vision ΔE >= 17.4):

- The control slate is intentionally low-chroma: comparison series should read
  as neutral next to the treated series.
- Spillover amber is below 3:1 contrast on the light paper surface, so every
  amber series is direct-labelled and the site offers a table view.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from cordon.config import REPO_ROOT

INK = "#1A2230"
SLATE = "#586274"
PAPER = "#FAFAF8"
LINE = "#DDE1E6"
ACCENT = "#2F5BD3"

TREATED = "#C8553D"
CONTROL = "#5B7083"
SPILLOVER = "#D99A2B"
BAND_ALPHA = 0.20

FIGURES_DIR = REPO_ROOT / "report" / "figures"

SANS = ["Inter Tight", "Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]


def apply_style() -> None:
    """Set matplotlib defaults: recessive axes, light grid, tabular-friendly sans."""
    mpl.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "font.family": "sans-serif",
            "font.sans-serif": SANS,
            "font.size": 9,
            "text.color": INK,
            "axes.labelcolor": SLATE,
            "axes.edgecolor": LINE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": LINE,
            "grid.linewidth": 0.6,
            "xtick.color": SLATE,
            "ytick.color": SLATE,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "lines.linewidth": 2.0,
            "lines.solid_capstyle": "round",
            "legend.frameon": False,
        }
    )


def new_figure(width: float = 7.0, height: float = 3.4) -> tuple[Figure, Axes]:
    """Create a styled figure with one axis."""
    apply_style()
    figure, axis = plt.subplots(figsize=(width, height), layout="constrained")
    return figure, axis


def titles(axis: Axes, title: str, subtitle: str, width: int = 105) -> None:
    """Takeaway title (bold, figure-level) with a wrapped subtitle above the plot."""
    figure = axis.get_figure()
    if figure is not None:
        figure.suptitle(
            textwrap.fill(title, 88), x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK
        )
    axis.set_title(textwrap.fill(subtitle, width), loc="left", fontsize=8, color=SLATE, pad=6)


def date_axis(axis: Axes) -> None:
    """Concise, non-overlapping date ticks."""
    locator = mdates.AutoDateLocator(minticks=4, maxticks=9)  # type: ignore[no-untyped-call]
    axis.xaxis.set_major_locator(locator)
    formatter = mdates.ConciseDateFormatter(locator)  # type: ignore[no-untyped-call]
    axis.xaxis.set_major_formatter(formatter)


def sentence_case(label: str) -> str:
    """Lower-case the first letter unless the first word is an acronym (e.g. CRZ, NYC)."""
    first_word = label.split()[0]
    if first_word.isupper() or any(ch.isupper() for ch in first_word[1:]):
        return label
    return label[0].lower() + label[1:]


def save(figure: Figure, name: str, directory: Path = FIGURES_DIR) -> Path:
    """Save as PNG (paper, 200 dpi). The site redraws charts from the CSVs in data/final."""
    directory.mkdir(parents=True, exist_ok=True)
    png = directory / f"{name}.png"
    figure.savefig(png, dpi=200)
    plt.close(figure)
    return png
