"""Interactive charts for the website (Altair -> Vega-Lite), generated from results/.

Writes ``report/_generated/event_study_chart.html``, an HTML fragment that the
results page includes. It holds the event-study coefficients for every DiD
outcome, with a dropdown to pick the outcome and tooltips on each bin. The
pre-registered and detrended specifications are drawn in the design-token data
colours. Axis colours are chosen at load time for light or dark mode.

Vega libraries are loaded from jsDelivr at pinned versions, and only once the
chart is near the viewport.
Run: ``python -m cordon.viz.site_charts``.
"""

from __future__ import annotations

import json

import altair as alt
import polars as pl

from cordon.config import REPO_ROOT
from cordon.designs.run import DID_OUTCOMES
from cordon.viz import style
from cordon.viz.estimates import bin_start

RESULTS = REPO_ROOT / "results"
OUTPUT = REPO_ROOT / "report" / "_generated" / "event_study_chart.html"
VERSIONS = {"vega": "6.4.0", "vega-lite": "6.4.1", "vega-embed": "7.2.0"}


def chart_data() -> pl.DataFrame:
    """Event-study rows with calendar dates and readable labels."""
    event = pl.read_csv(RESULTS / "event_study.csv")
    monthly = {o.key for o in DID_OUTCOMES if o.frequency == "month"}
    names = {o.key: f"{o.key}: {o.description}" for o in DID_OUTCOMES if o.family != "check"}
    rows = []
    for r in event.iter_rows(named=True):
        if r["key"] not in names:
            continue
        b = None if r["term"] == "anticipation" else int(r["bin"])
        rows.append(
            {
                "outcome": names[r["key"]],
                "specification": "Detrended (ADR 0011)"
                if "detrended" in r["spec"]
                else "Pre-registered",
                "date": bin_start(b, r["key"] in monthly).isoformat(),
                "bin": "anticipation" if b is None else str(b),
                "estimate": round(100 * r["estimate"], 3),
                "low": round(100 * r["ci_low"], 3),
                "high": round(100 * r["ci_high"], 3),
            }
        )
    return pl.DataFrame(rows)


def build_chart(data: pl.DataFrame) -> alt.LayerChart | alt.FacetChart:
    """Layered line + band chart with an outcome dropdown."""
    outcomes = sorted(data["outcome"].unique().to_list())
    default = next(o for o in outcomes if o.startswith("T2:"))
    pick = alt.param(
        name="outcome", value=default, bind=alt.binding_select(options=outcomes, name="Outcome ")
    )
    colours = alt.Scale(
        domain=["Pre-registered", "Detrended (ADR 0011)"], range=[style.TREATED, style.CONTROL]
    )
    values = alt.Data(values=data.to_dicts())  # type: ignore[no-untyped-call]
    base = (
        alt.Chart(values)
        .transform_filter(alt.datum.outcome == pick)
        .encode(
            x=alt.X("date:T", title=None),
            color=alt.Color(
                "specification:N", scale=colours, title=None, legend=alt.Legend(orient="top")
            ),
        )
    )
    band = base.mark_area(opacity=style.BAND_ALPHA).encode(y="low:Q", y2="high:Q")
    line = base.mark_line(point=alt.OverlayMarkDef(size=30)).encode(
        y=alt.Y("estimate:Q", title="Treated minus comparison (x100: log points or levels)"),
        tooltip=[
            alt.Tooltip("specification:N"),
            alt.Tooltip("bin:N", title="4-week bin"),
            alt.Tooltip("date:T", title="starts"),
            alt.Tooltip("estimate:Q", format="+.2f"),
            alt.Tooltip("low:Q", format="+.2f", title="95% CI low"),
            alt.Tooltip("high:Q", format="+.2f", title="95% CI high"),
        ],
    )
    origin = alt.Data(values=[{"y": 0}])  # type: ignore[no-untyped-call]
    zero = alt.Chart(origin).mark_rule(strokeWidth=0.8).encode(y="y:Q")
    return (
        alt.layer(band, line, zero)
        .add_params(pick)
        .properties(
            width="container",
            height=320,
            title="Event-study coefficients relative to Sep 19-Nov 13, 2024 (95% CIs)",
        )
    )


def fragment(spec: dict[str, object]) -> str:
    """HTML fragment embedding the spec with light/dark axis colours.

    The Vega libraries (about 300 KB) load only when the chart comes within
    600 px of the viewport, so they never compete with first paint (ADR 0013).
    """
    sources = json.dumps(
        [f"https://cdn.jsdelivr.net/npm/{name}@{version}" for name, version in VERSIONS.items()]
    )
    return f"""```{{=html}}
<div id="event-study-chart" style="width:100%;min-height:380px" role="img"
     aria-label="Interactive event-study chart; choose an outcome from the dropdown."></div>
<script>
(function () {{
  var target = document.getElementById("event-study-chart");
  var sources = {sources};
  function loadScript(index, done) {{
    if (index === sources.length) {{ done(); return; }}
    var script = document.createElement("script");
    script.src = sources[index];
    script.onload = function () {{ loadScript(index + 1, done); }};
    document.head.appendChild(script);
  }}
  function draw() {{
    var dark = document.body.classList.contains("quarto-dark");
    var ink = dark ? "#E7EAEF" : "{style.INK}";
    var slate = dark ? "#A7B0BD" : "{style.SLATE}";
    var line = dark ? "#2C3441" : "{style.LINE}";
    var spec = {json.dumps(spec)};
    spec.config = {{
      background: null, view: {{stroke: null}},
      font: "Inter Tight, Helvetica Neue, Arial, sans-serif",
      axis: {{labelColor: slate, titleColor: slate, gridColor: line, domainColor: line,
              tickColor: line}},
      legend: {{labelColor: ink}}, title: {{color: ink, anchor: "start", fontWeight: 600}},
      rule: {{color: slate}}
    }};
    vegaEmbed(target, spec, {{actions: false, renderer: "svg"}});
  }}
  function start() {{ loadScript(0, draw); }}
  if (!("IntersectionObserver" in window)) {{ start(); return; }}
  var observer = new IntersectionObserver(function (entries) {{
    if (entries.some(function (entry) {{ return entry.isIntersecting; }})) {{
      observer.disconnect();
      start();
    }}
  }}, {{rootMargin: "600px 0px"}});
  observer.observe(target);
}})();
</script>
```
"""


def main() -> None:
    """Write the event-study chart fragment."""
    spec = build_chart(chart_data()).to_dict()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(fragment(spec))


if __name__ == "__main__":
    main()
