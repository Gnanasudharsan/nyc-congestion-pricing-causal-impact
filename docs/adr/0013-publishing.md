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
    and optical-size axes);
  - the site self-hosts subset WOFF2 files built by `cordon.viz.webfonts`: Latin characters
    only, only the OpenType features the site uses, and Source Serif's optical-size axis
    pinned at the font's default (its text design; headings are set in Inter Tight). The
    weight axis stays variable. This brings 2.6 MB down to about 140 KB. The `@font-face`
    rules sit inline in `report/preload.html`, next to the preloads, so first paint needs
    no extra stylesheet request.
- **Dark mode** uses Quarto's light/dark themes, which follow the reader's system setting, plus
  a toggle.
- **Post-render step.** `report/scripts/postprocess.py` (standard library only) trims what
  first paint waits for, without changing behaviour:
  - inactive colour-scheme stylesheets start disabled; Quarto's own script enables the one
    the reader's preference or the toggle asks for;
  - Quarto's classic `<head>` scripts are marked `defer`. Its inline code that uses them
    already waits for `DOMContentLoaded`;
  - the tooltip stylesheet loads without blocking (hover popups are off);
  - the Bootstrap Icons web font is replaced with the two icons the site uses, inlined as SVG
    (`report/icons/`, extracted by `cordon.viz.icons`; MIT licence notice kept);
  - PNG figures get intrinsic sizes (no layout shift), and all but the overview's hero
    image load lazily.
  These helpers are unit-tested (`tests/test_postprocess.py`).
- **Interactive chart.** The event-study explorer loads Vega only when it comes near the
  viewport, so about 300 KB of script never competes with first paint.
- **Site features turned off:** search, hover popups, and section anchors. Each adds
  render-blocking scripts, and five pages do not need search.
- **PDF in CI.** The local TeX installation (BasicTeX) lacks packages and its `tlmgr` needs
  admin rights. The PDF is therefore built in GitHub Actions with Quarto's TinyTeX, which
  installs missing packages itself. The HTML is rendered and audited locally.
- **Lighthouse.** `make lighthouse` (`cordon.viz.lighthouse`) audits every page of the live
  site with Lighthouse 13.5.0: mobile and desktop profiles, light and dark schemes, three
  runs each, keeping the median performance run. Results are in
  `results/lighthouse_scores.csv`.

## Consequences
- Every page meets the target of at least 90 in every category, on mobile and desktop and in
  both colour schemes (`results/lighthouse_scores.csv`).
- The first version of this ADR (Phase 6) recorded mobile performance of 67–74, measured
  against a local server, and called replacing Quarto's framework CSS the only fix. That
  was wrong. The remaining cost was the work around that CSS: unused fonts and font
  features, synchronous scripts, an icon font, eager figures, and an eagerly loaded chart
  library. Removing those was enough (v1.0.1). Quarto's Bootstrap CSS (about 70 KB gzipped)
  is still the largest render-blocking file.
- Auditing the dark scheme surfaced a real defect: code blocks were black on the dark
  background (Bootstrap's default `pre` colour). It is fixed in both themes.
- The post-render step relies on the exact markup Quarto 1.11 emits. A Quarto upgrade
  should be followed by `make report`, the post-render tests, and `make lighthouse`.
