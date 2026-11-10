# ADR 0013 — Publishing the paper and website

- Status: Accepted (2026-11-10, Phase 6)

## Context
CLAUDE.md asks for:
- a Quarto HTML site and PDF, deployed to GitHub Pages;
- design-token typography and colours, and dark mode;
- a Lighthouse score of at least 90;
- no hand-typed numbers.

## Decision
- **Numbers.** `cordon.viz.report_inputs` writes `report/_variables.yml` (Quarto variables used
  in the prose) and `report/_generated/*.md` (tables) from `results/`. The `.qmd` files contain
  no executable code, so CI renders committed inputs and never reruns the analysis.
- **Fonts.** Source Serif 4 and Inter Tight (SIL OFL) are kept in `report/fonts/`:
  - the PDF uses the variable TTFs through LuaLaTeX and fontspec (HarfBuzz renderer, weight
    axis);
  - the site self-hosts subset WOFF2 files (415 KB instead of 2.6 MB) and preloads them.
    This avoids a third-party font request and the layout shift that font swapping causes.
- **Dark mode** uses Quarto's light/dark themes, which follow the reader's system setting, plus
  a toggle. A standard-library post-render step (`report/scripts/postprocess.py`) starts the
  inactive theme's stylesheet as disabled, so it does not block first paint. Quarto's own
  script enables it when needed. The step also adds intrinsic image dimensions.
- **Site features turned off:** search, hover popups, and section anchors. Each adds
  render-blocking scripts, and five pages do not need search.
- **PDF in CI.** The local TeX installation (BasicTeX) lacks packages and its `tlmgr` needs
  admin rights. The PDF is therefore built in GitHub Actions with Quarto's TinyTeX, which
  installs missing packages itself. The HTML is rendered and audited locally.
- **Lighthouse** 13.5.0 is run against a gzip-serving local server that approximates GitHub
  Pages. Scores are in `results/lighthouse_scores.csv`.

## Consequences
- Desktop: performance 96–98 and 100 in every other category on the audited pages.
- **Mobile performance is 67–74, below the 90 target.** Under Lighthouse's simulated slow-4G
  profile, first paint is dominated by the roughly 70 KB of gzipped Bootstrap CSS that Quarto's
  theme needs. Closing the gap would mean replacing Quarto's framework CSS, which risks
  breaking the navbar and the dark-mode toggle. It is recorded as a known gap rather than hidden.
