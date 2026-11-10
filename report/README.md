# report/

The Quarto website and paper. `paper.qmd` renders to HTML and to PDF (LuaLaTeX).

- **Numbers:** every number in the text comes from `_variables.yml`, and every table comes from
  `_generated/`. Both are written by `python -m cordon.viz.report_inputs` from `results/`.
  Nothing is typed by hand.
- **Charts:** `figures/` holds the static figures. The interactive event-study chart
  (`_generated/event_study_chart.html`) comes from `cordon.viz.site_charts`.
- **Fonts:** `fonts/` holds Source Serif 4 and Inter Tight (SIL OFL; licences included). The
  TTFs are used by the PDF. The subset WOFF2 files, built by `cordon.viz.webfonts`, are used
  by the site.
- **Post-render step:** `scripts/postprocess.py` stops the unused colour-scheme stylesheet
  from blocking first paint, and adds image dimensions.
- **Build:** `make report` (set `QUARTO=/path/to/quarto` if it is not on `PATH`). GitHub
  Actions (`.github/workflows/pages.yml`) renders the site and PDF and deploys them to GitHub
  Pages.
