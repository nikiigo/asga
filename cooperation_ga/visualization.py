"""Visualization helpers for simulation outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import plotly.graph_objects as go
from plotly.graph_objs.bar import Marker as BarMarker
from plotly.graph_objs.layout import Font as LayoutFont, Legend, Margin
from plotly.graph_objs.scatter import Line as ScatterLine
from plotly.graph_objs.table.cells import Fill as TableCellsFill
from plotly.graph_objs.table.cells import Font as TableCellsFont
from plotly.graph_objs.table.header import Fill as TableHeaderFill
from plotly.graph_objs.table.header import Font as TableHeaderFont
from plotly.graph_objs.table import Cells as TableCells, Header as TableHeader
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

from cooperation_ga.config import VisualizationConfig
from cooperation_ga.metrics import (
    FinalPopulationSummaryRow,
    GenerationMetrics,
    final_population_summary_rows,
    strategy_name_by_dna,
)


@dataclass(frozen=True, slots=True)
class TimelineSeries:
    """One named series across simulation steps."""

    label: str
    values: list[float]
    color: str


@dataclass(frozen=True, slots=True)
class StrategyTimeline:
    """One strategy trajectory across simulation steps."""

    dna: str
    name: str
    explanation: str
    color: str
    counts: list[int]


@dataclass(frozen=True, slots=True)
class VisualizationBundle:
    """Normalized data used by all visualization renderers."""

    metrics: list[GenerationMetrics]
    steps: list[int]
    initial: GenerationMetrics
    final: GenerationMetrics
    strategy_names: dict[str, str]
    final_rows: list[FinalPopulationSummaryRow]
    top_strategy_timelines: list[StrategyTimeline]
    overview_series: list[TimelineSeries]
    births: list[int]
    deaths: list[int]
    max_population: int
    max_strategy_count: int
    hybrid_total_count: int
    top_hybrid_row: FinalPopulationSummaryRow | None
    new_hybrids_per_step: list[int]
    cumulative_hybrids: list[int]
    hybrid_share: list[float]
    baseline_share: list[float]


def _palette(config: VisualizationConfig) -> Sequence[str]:
    """Return a non-empty palette with a concrete non-optional type."""
    if config.viz_palette is None:
        raise ValueError("VisualizationConfig.viz_palette must be initialized.")
    return config.viz_palette


def export_visualizations(
    metrics: list[GenerationMetrics],
    output_dir: str | Path,
    config: VisualizationConfig,
) -> None:
    """Create infographic and HTML report assets for a simulation run."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    bundle = _build_bundle(metrics, config)
    infographic_path = destination / "summary_infographic.png"
    report_path = destination / "report.html"
    _create_infographic(bundle, infographic_path, config)
    _create_html_report(bundle, report_path, infographic_path.name, config)


def _build_bundle(metrics: list[GenerationMetrics], config: VisualizationConfig) -> VisualizationBundle:
    """Normalize metrics into a renderer-friendly bundle."""
    palette = _palette(config)
    strategy_names = strategy_name_by_dna(metrics)
    final_rows = final_population_summary_rows(metrics)
    top_dna = _fixed_dna_order(metrics, top_n=config.top_strategies_to_plot)
    timeline_colors = {
        dna: palette[index % len(palette)]
        for index, dna in enumerate(top_dna)
    }
    top_strategy_timelines = [
        StrategyTimeline(
            dna=dna,
            name=strategy_names[dna],
            explanation=next(
                (str(row["strategy_explanation"]) for row in final_rows if row["dna"] == dna),
                "Strategy explanation unavailable.",
            ),
            color=timeline_colors[dna],
            counts=[metric.population_count_per_dna.get(dna, 0) for metric in metrics],
        )
        for dna in top_dna
    ]
    steps = [metric.step for metric in metrics]
    overview_series = [
        TimelineSeries("Cooperation", [metric.overall_cooperation_rate for metric in metrics], config.viz_cooperation_color),
        TimelineSeries("Defection", [metric.overall_defection_rate for metric in metrics], config.viz_defection_color),
        TimelineSeries("Unique strategies", [float(metric.num_unique_strategies) for metric in metrics], config.viz_unique_color),
        TimelineSeries("Entropy", [metric.diversity_entropy for metric in metrics], config.viz_entropy_color),
        TimelineSeries("Dominant share", [metric.dominant_strategy_share for metric in metrics], config.viz_dominant_color),
    ]
    max_population = max(metric.total_population_size for metric in metrics)
    max_strategy_count = max(
        (max(metric.population_count_per_dna.values(), default=0) for metric in metrics),
        default=0,
    )
    hybrid_names = {dna: name for dna, name in strategy_names.items() if name.startswith("Hybrid")}
    seen_hybrids: set[str] = set()
    new_hybrids_per_step: list[int] = []
    cumulative_hybrids: list[int] = []
    hybrid_share: list[float] = []
    baseline_share: list[float] = []
    for metric in metrics:
        step_hybrids = {
            dna for dna in metric.population_count_per_dna
            if strategy_names.get(dna, "").startswith("Hybrid")
        }
        new_count = len(step_hybrids - seen_hybrids)
        seen_hybrids.update(step_hybrids)
        new_hybrids_per_step.append(new_count)
        cumulative_hybrids.append(len(seen_hybrids))
        total_population = max(metric.total_population_size, 1)
        hybrid_population = sum(
            count
            for dna, count in metric.population_count_per_dna.items()
            if strategy_names.get(dna, "").startswith("Hybrid")
        )
        hybrid_share.append(hybrid_population / total_population)
        baseline_share.append(1.0 - hybrid_share[-1])
    top_hybrid_row = next(
        (row for row in final_rows if str(row["strategy_name"]).startswith("Hybrid")),
        None,
    )
    return VisualizationBundle(
        metrics=metrics,
        steps=steps,
        initial=metrics[0],
        final=metrics[-1],
        strategy_names=strategy_names,
        final_rows=final_rows,
        top_strategy_timelines=top_strategy_timelines,
        overview_series=overview_series,
        births=[metric.births_this_step for metric in metrics],
        deaths=[metric.deaths_this_step for metric in metrics],
        max_population=max_population,
        max_strategy_count=max_strategy_count,
        hybrid_total_count=len(hybrid_names),
        top_hybrid_row=top_hybrid_row,
        new_hybrids_per_step=new_hybrids_per_step,
        cumulative_hybrids=cumulative_hybrids,
        hybrid_share=hybrid_share,
        baseline_share=baseline_share,
    )


def _create_infographic(bundle: VisualizationBundle, path: Path, config: VisualizationConfig) -> None:
    """Build a static infographic summarizing the run."""
    fig = plt.figure(figsize=(17, 10), facecolor=config.viz_bg_color)
    grid = fig.add_gridspec(3, 4, height_ratios=[0.9, 1.15, 1.15], wspace=0.25, hspace=0.3)

    ax_title = fig.add_subplot(grid[0, 0:2])
    ax_score = fig.add_subplot(grid[0, 2:4])
    ax_dynamics = fig.add_subplot(grid[1, 0:3])
    ax_final = fig.add_subplot(grid[1:, 3])
    ax_structure = fig.add_subplot(grid[2, 0:2])
    ax_flow = fig.add_subplot(grid[2, 2])

    for ax in (ax_title, ax_score, ax_dynamics, ax_final, ax_structure, ax_flow):
        ax.set_facecolor(config.viz_panel_color)
        for spine in ax.spines.values():
            spine.set_visible(False)

    _draw_title_card(ax_title, bundle, config)
    _draw_overview_panel(ax_score, bundle, config)
    _draw_strategy_area_panel(ax_dynamics, bundle, config)
    _draw_final_population_panel(ax_final, bundle, config)
    _draw_structure_panel(ax_structure, bundle, config)
    _draw_flow_panel(ax_flow, bundle, config)

    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _draw_title_card(ax: plt.Axes, bundle: VisualizationBundle, config: VisualizationConfig) -> None:
    """Render the headline summary block."""
    ax.axis("off")
    card = FancyBboxPatch(
        (0.02, 0.06),
        0.96,
        0.88,
        boxstyle="round,pad=0.025,rounding_size=0.04",
        fc=config.viz_panel_color,
        ec=config.viz_ink_color,
        lw=2,
    )
    ax.add_patch(card)
    ax.text(0.06, 0.82, config.viz_title_text, fontsize=28, fontweight="bold", color=config.viz_ink_color)
    ax.text(0.06, 0.70, config.viz_subtitle_text, fontsize=12, color=config.viz_muted_color)
    lines = [
        f"Initial population: {bundle.initial.total_population_size}",
        f"Final population: {bundle.final.total_population_size}",
        f"Initial cooperation: {bundle.initial.overall_cooperation_rate:.1%}",
        f"Final cooperation: {bundle.final.overall_cooperation_rate:.1%}",
        f"Hybrids created: {bundle.hybrid_total_count}",
        f"Top hybrid: {bundle.top_hybrid_row['strategy_name']} ({bundle.top_hybrid_row['population']})" if bundle.top_hybrid_row else "Top hybrid: none",
        f"Winning strategy: {bundle.strategy_names.get(bundle.final.dominant_dna or '', bundle.final.dominant_dna or 'n/a')}",
        f"Dominant share: {bundle.final.dominant_strategy_share:.1%}",
    ]
    for index, line in enumerate(lines):
        ax.text(0.06, 0.54 - index * 0.09, line, fontsize=14, color="#1f1f1f")


def _draw_overview_panel(ax: plt.Axes, bundle: VisualizationBundle, config: VisualizationConfig) -> None:
    """Render behavior overview line charts."""
    cooperation = next(series for series in bundle.overview_series if series.label == "Cooperation")
    defection = next(series for series in bundle.overview_series if series.label == "Defection")
    ax.plot(bundle.steps, cooperation.values, color=cooperation.color, linewidth=3, label=cooperation.label)
    ax.plot(bundle.steps, defection.values, color=defection.color, linewidth=3, label=defection.label)
    ax.fill_between(bundle.steps, cooperation.values, color=cooperation.color, alpha=0.12)
    ax.fill_between(bundle.steps, defection.values, color=defection.color, alpha=0.08)
    ax.set_title(config.viz_behavior_title, loc="left", fontsize=18, fontweight="bold", color=config.viz_ink_color)
    ax.set_xlabel("Step")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, loc="upper right")


def _draw_strategy_area_panel(ax: plt.Axes, bundle: VisualizationBundle, config: VisualizationConfig) -> None:
    """Render the main population dynamics panel with fixed strategy lanes."""
    cumulative = [0] * len(bundle.steps)
    for timeline in bundle.top_strategy_timelines:
        lower = cumulative[:]
        upper = [base + value for base, value in zip(cumulative, timeline.counts)]
        ax.fill_between(bundle.steps, lower, upper, color=timeline.color, alpha=0.8, label=timeline.name)
        cumulative = upper
    ax.set_title("Strategy Landscape", loc="left", fontsize=18, fontweight="bold", color=config.viz_ink_color)
    ax.set_xlabel("Step")
    ax.set_ylabel("Population count")
    ax.grid(alpha=0.15)
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)


def _draw_final_population_panel(ax: plt.Axes, bundle: VisualizationBundle, config: VisualizationConfig) -> None:
    """Render final population ranking."""
    palette = _palette(config)
    top_rows = bundle.final_rows[:10]
    labels = [str(row["strategy_name"]) for row in reversed(top_rows)]
    values = [int(row["population"]) for row in reversed(top_rows)]
    colors = [palette[index % len(palette)] for index in range(len(labels))][::-1]
    ax.barh(labels, values, color=colors)
    ax.set_title("Final Population", loc="left", fontsize=18, fontweight="bold", color=config.viz_ink_color)
    ax.set_xlabel("Population")
    ax.grid(axis="x", alpha=0.18)


def _draw_structure_panel(ax: plt.Axes, bundle: VisualizationBundle, config: VisualizationConfig) -> None:
    """Render structural metrics over time."""
    unique = next(series for series in bundle.overview_series if series.label == "Unique strategies")
    entropy = next(series for series in bundle.overview_series if series.label == "Entropy")
    dominant = next(series for series in bundle.overview_series if series.label == "Dominant share")
    ax.plot(bundle.steps, unique.values, color=unique.color, linewidth=3, label=unique.label)
    ax.plot(bundle.steps, entropy.values, color=entropy.color, linewidth=3, label=entropy.label)
    ax.plot(bundle.steps, dominant.values, color=dominant.color, linewidth=3, label=dominant.label)
    ax.set_title(config.viz_structure_title, loc="left", fontsize=18, fontweight="bold", color=config.viz_ink_color)
    ax.set_xlabel("Step")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, loc="upper right")


def _draw_flow_panel(ax: plt.Axes, bundle: VisualizationBundle, config: VisualizationConfig) -> None:
    """Render births and deaths."""
    ax.bar(bundle.steps, bundle.births, width=0.8, color=config.viz_cooperation_color, alpha=0.75, label="Births")
    ax.bar(bundle.steps, [-value for value in bundle.deaths], width=0.8, color=config.viz_defection_color, alpha=0.65, label="Deaths")
    ax.axhline(0, color=config.viz_ink_color, linewidth=1)
    ax.set_title("Births and Deaths", loc="left", fontsize=18, fontweight="bold", color=config.viz_ink_color)
    ax.set_xlabel("Step")
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False, loc="upper right")


def _create_html_report(
    bundle: VisualizationBundle,
    path: Path,
    infographic_name: str,
    config: VisualizationConfig,
) -> None:
    """Create an interactive Plotly HTML report plus static fallback asset."""
    overview_fig = _plotly_overview_figure(bundle, config)
    timeline_fig = _plotly_timeline_figure(bundle, config)
    final_population_fig = _plotly_final_population_figure(bundle, config)
    hybrid_fig = _plotly_hybrid_figure(bundle, config)
    final_table_fig = _plotly_final_table(bundle, config)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{config.viz_report_title}</title>
  <style>
    :root {{
      --bg: {config.viz_bg_color};
      --panel: {config.viz_panel_color};
      --ink: {config.viz_ink_color};
      --muted: {config.viz_muted_color};
      --accent: {config.viz_accent_color};
      --line: rgba(0,61,91,0.14);
    }}
    body {{
      margin: 0;
      font-family: "Trebuchet MS", "DejaVu Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(237,174,73,0.24), transparent 30%),
        radial-gradient(circle at bottom right, rgba(0,121,140,0.18), transparent 28%),
        var(--bg);
    }}
    .wrap {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 30px 18px 54px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 18px;
      align-items: start;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 2px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 14px 30px rgba(0,0,0,0.05);
      padding: 18px 20px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
    }}
    .stat {{
      background: rgba(255,255,255,0.4);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px 16px;
    }}
    .label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    .metric {{
      font-size: 30px;
      font-weight: 700;
      color: var(--accent);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 46px;
      line-height: 1.03;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 22px;
    }}
    p {{
      color: var(--muted);
      max-width: 80ch;
    }}
    .grid {{
      display: grid;
      gap: 18px;
    }}
    .grid.two {{
      grid-template-columns: 1.25fr 0.95fr;
    }}
    .media {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    img {{
      width: 100%;
      display: block;
      border-radius: 20px;
      border: 2px solid var(--line);
      background: var(--panel);
    }}
    .note {{
      font-size: 13px;
      color: var(--muted);
      margin-top: 10px;
    }}
    @media (max-width: 980px) {{
      .hero, .grid.two, .media {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
  <script>{get_plotlyjs()}</script>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="panel">
        <h1>{config.viz_report_heading}</h1>
        <p>{config.viz_report_description}</p>
        <div class="stats">
          <div class="stat"><div class="label">Steps</div><div class="metric">{len(bundle.metrics)}</div></div>
          <div class="stat"><div class="label">Initial Population</div><div class="metric">{bundle.initial.total_population_size}</div></div>
          <div class="stat"><div class="label">Final Population</div><div class="metric">{bundle.final.total_population_size}</div></div>
          <div class="stat"><div class="label">Winning Strategy</div><div class="metric" style="font-size:22px">{bundle.strategy_names.get(bundle.final.dominant_dna or '', bundle.final.dominant_dna or 'n/a')}</div></div>
          <div class="stat"><div class="label">Final Cooperation</div><div class="metric">{bundle.final.overall_cooperation_rate:.1%}</div></div>
          <div class="stat"><div class="label">Hybrids Created</div><div class="metric">{bundle.hybrid_total_count}</div></div>
          <div class="stat"><div class="label">Top Hybrid</div><div class="metric" style="font-size:22px">{bundle.top_hybrid_row['strategy_name'] if bundle.top_hybrid_row else 'None'}</div></div>
        </div>
      </div>
      <div class="panel">
        <h2>Static Export</h2>
        <div class="media">
          <img src="{infographic_name}" alt="Static infographic summary">
        </div>
        <div class="note">The report below is interactive. The PNG remains available as a static export for sharing.</div>
      </div>
    </section>
    <section class="grid">
      <div class="panel">
        <h2>Run Overview</h2>
        {overview_fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})}
      </div>
      <div class="grid two">
        <div class="panel">
          <h2>Strategy Landscape</h2>
          {timeline_fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})}
        </div>
        <div class="panel">
          <h2>Final Population Ranking</h2>
          {final_population_fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})}
        </div>
      </div>
      <div class="panel">
        <h2>Hybrid Emergence</h2>
        {hybrid_fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})}
      </div>
      <div class="panel">
        <h2>Final Strategy Catalog</h2>
        {final_table_fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})}
      </div>
    </section>
  </div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _plotly_overview_figure(bundle: VisualizationBundle, config: VisualizationConfig) -> go.Figure:
    """Build an interactive multi-panel run overview."""
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Cooperation vs Defection", "Births and Deaths", "Diversity", "Dominant Share"),
        vertical_spacing=0.16,
    )
    cooperation = next(series for series in bundle.overview_series if series.label == "Cooperation")
    defection = next(series for series in bundle.overview_series if series.label == "Defection")
    unique = next(series for series in bundle.overview_series if series.label == "Unique strategies")
    entropy = next(series for series in bundle.overview_series if series.label == "Entropy")
    dominant = next(series for series in bundle.overview_series if series.label == "Dominant share")

    fig.add_trace(go.Scatter(x=bundle.steps, y=cooperation.values, mode="lines", name=cooperation.label, line=ScatterLine(color=cooperation.color, width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=bundle.steps, y=defection.values, mode="lines", name=defection.label, line=ScatterLine(color=defection.color, width=3)), row=1, col=1)
    fig.add_trace(go.Bar(x=bundle.steps, y=bundle.births, name="Births", marker=BarMarker(color=config.viz_cooperation_color)), row=1, col=2)
    fig.add_trace(go.Bar(x=bundle.steps, y=bundle.deaths, name="Deaths", marker=BarMarker(color=config.viz_defection_color)), row=1, col=2)
    fig.add_trace(go.Scatter(x=bundle.steps, y=unique.values, mode="lines", name=unique.label, line=ScatterLine(color=unique.color, width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=bundle.steps, y=entropy.values, mode="lines", name=entropy.label, line=ScatterLine(color=entropy.color, width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=bundle.steps, y=dominant.values, mode="lines", name=dominant.label, line=ScatterLine(color=dominant.color, width=3)), row=2, col=2)
    fig.update_layout(
        paper_bgcolor=config.viz_panel_color,
        plot_bgcolor=config.viz_panel_color,
        font=LayoutFont(color=config.viz_ink_color),
        margin=Margin(l=40, r=20, t=30, b=40),
        legend=Legend(orientation="h", yanchor="bottom", y=1.04, x=0.0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    return fig


def _plotly_timeline_figure(bundle: VisualizationBundle, config: VisualizationConfig) -> go.Figure:
    """Build an interactive stacked area chart for strategy populations."""
    fig = go.Figure()
    for timeline in bundle.top_strategy_timelines:
        fig.add_trace(
            go.Scatter(
                x=bundle.steps,
                y=timeline.counts,
                mode="lines",
                name=timeline.name,
                stackgroup="population",
                line=ScatterLine(width=1.2, color=timeline.color),
                customdata=[[timeline.dna, timeline.explanation]] * len(bundle.steps),
                hovertemplate="<b>%{fullData.name}</b><br>Step %{x}<br>Population %{y}<br>DNA %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            )
        )
    fig.update_layout(
        paper_bgcolor=config.viz_panel_color,
        plot_bgcolor=config.viz_panel_color,
        font=LayoutFont(color=config.viz_ink_color),
        margin=Margin(l=40, r=20, t=20, b=40),
        legend=Legend(orientation="h", yanchor="bottom", y=1.03, x=0.0),
        yaxis_title="Population",
        xaxis_title="Step",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    return fig


def _plotly_final_population_figure(bundle: VisualizationBundle, config: VisualizationConfig) -> go.Figure:
    """Build an interactive final ranking chart."""
    palette = _palette(config)
    rows = bundle.final_rows[:12]
    rows = list(reversed(rows))
    fig = go.Figure(
        go.Bar(
            x=[int(row["population"]) for row in rows],
            y=[str(row["strategy_name"]) for row in rows],
            orientation="h",
            marker=BarMarker(color=[palette[index % len(palette)] for index in range(len(rows))]),
            customdata=[[row["dna"], row["strategy_explanation"]] for row in rows],
            hovertemplate="<b>%{y}</b><br>Population %{x}<br>DNA %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        )
    )
    fig.update_layout(
        paper_bgcolor=config.viz_panel_color,
        plot_bgcolor=config.viz_panel_color,
        font=LayoutFont(color=config.viz_ink_color),
        margin=Margin(l=20, r=20, t=20, b=40),
        xaxis_title="Population",
        yaxis_title="",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    return fig


def _plotly_hybrid_figure(bundle: VisualizationBundle, config: VisualizationConfig) -> go.Figure:
    """Build an interactive hybrid emergence and share figure."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.14,
        subplot_titles=("New and cumulative hybrids", "Baseline vs hybrid population share"),
    )
    fig.add_trace(
        go.Bar(
            x=bundle.steps,
            y=bundle.new_hybrids_per_step,
            name="New hybrids",
            marker=BarMarker(color=config.viz_accent_color),
            hovertemplate="Step %{x}<br>New hybrids %{y}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bundle.steps,
            y=bundle.cumulative_hybrids,
            mode="lines+markers",
            name="Cumulative hybrids",
            line=ScatterLine(color=config.viz_ink_color, width=3),
            hovertemplate="Step %{x}<br>Cumulative hybrids %{y}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bundle.steps,
            y=bundle.baseline_share,
            mode="lines",
            stackgroup="share",
            name="Baseline share",
            line=ScatterLine(width=1.2, color=config.viz_cooperation_color),
            hovertemplate="Step %{x}<br>Baseline share %{y:.1%}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bundle.steps,
            y=bundle.hybrid_share,
            mode="lines",
            stackgroup="share",
            name="Hybrid share",
            line=ScatterLine(width=1.2, color=config.viz_accent_color),
            hovertemplate="Step %{x}<br>Hybrid share %{y:.1%}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        paper_bgcolor=config.viz_panel_color,
        plot_bgcolor=config.viz_panel_color,
        font=LayoutFont(color=config.viz_ink_color),
        margin=Margin(l=40, r=20, t=20, b=40),
        legend=Legend(orientation="h", yanchor="bottom", y=1.02, x=0.0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)", title_text="Step", row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)", title_text="Hybrid count", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)", title_text="Population share", tickformat=".0%", row=2, col=1)
    return fig


def _plotly_final_table(bundle: VisualizationBundle, config: VisualizationConfig) -> go.Figure:
    """Build a final strategy catalog table."""
    rows = bundle.final_rows
    fig = go.Figure(
        data=[
            go.Table(
                header=TableHeader(
                    values=["Strategy", "Population", "DNA", "Explanation"],
                    fill=TableHeaderFill(color=config.viz_ink_color),
                    font=TableHeaderFont(color="white", size=12),
                    align="left",
                ),
                cells=TableCells(
                    values=[
                        [row["strategy_name"] for row in rows],
                        [row["population"] for row in rows],
                        [row["dna"] for row in rows],
                        [row["strategy_explanation"] for row in rows],
                    ],
                    fill=TableCellsFill(color=config.viz_panel_color),
                    font=TableCellsFont(color=config.viz_ink_color, size=11),
                    align="left",
                    height=26,
                ),
                columnwidth=[100, 60, 190, 320],
            )
        ]
    )
    fig.update_layout(
        paper_bgcolor=config.viz_panel_color,
        margin=Margin(l=10, r=10, t=10, b=10),
    )
    return fig


def _fixed_dna_order(metrics: list[GenerationMetrics], top_n: int) -> list[str]:
    """Return a fixed DNA order for plotting across all steps."""
    first_step = metrics[0].population_count_per_dna
    totals: dict[str, int] = {}
    for metric in metrics:
        for dna, count in metric.population_count_per_dna.items():
            totals[dna] = totals.get(dna, 0) + count
    ordered: list[str] = []
    for dna, _ in sorted(first_step.items(), key=lambda item: (-item[1], item[0])):
        if dna not in ordered:
            ordered.append(dna)
    for dna, _ in sorted(totals.items(), key=lambda item: (-item[1], item[0])):
        if dna not in ordered:
            ordered.append(dna)
    return ordered[:top_n]
