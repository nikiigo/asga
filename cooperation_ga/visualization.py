"""Visualization helpers for simulation outputs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import os
from typing import Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from cooperation_ga.config import VisualizationConfig
from cooperation_ga.metrics import (
    FinalPopulationSummaryRow,
    GenerationMetrics,
    PreparedExportData,
    prepare_export_data,
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
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Create static visualization assets from saved metrics."""
    if not metrics:
        raise ValueError("Cannot render visualizations from an empty metrics sequence.")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    status_path = destination / "status.txt"
    _write_render_status(status_path, "build_visualization_bundle", output_dir=str(destination), metrics_steps=len(metrics))
    print("Building visualization bundle...", flush=True)
    bundle = _build_bundle(metrics, config, prepared_export)
    infographic_path = destination / "summary_infographic.png"
    _write_render_status(status_path, "write_static_infographic", infographic_path=str(infographic_path))
    print(f"Writing static infographic: {infographic_path}", flush=True)
    _create_infographic(bundle, infographic_path, config)
    _write_render_status(status_path, "done", infographic_path=str(infographic_path))
    print("Finished rendering visual outputs.", flush=True)


def _write_render_status(path: Path, phase: str, **payload: object) -> None:
    """Write a plain-text JSON render status snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"phase": phase, **payload}
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _build_bundle(
    metrics: list[GenerationMetrics],
    config: VisualizationConfig,
    prepared_export: PreparedExportData | None = None,
) -> VisualizationBundle:
    """Normalize metrics into a renderer-friendly bundle."""
    palette = _palette(config)
    export_data = prepared_export or prepare_export_data(metrics)
    strategy_names = export_data.strategy_names
    final_rows = export_data.final_population_rows
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
    winning_strategy = (
        bundle.strategy_names.get(bundle.final.dominant_dna or "", bundle.final.dominant_dna or "n/a")
        if bundle.final.total_population_size > 0
        else "no surviving strategy"
    )
    lines = [
        f"Initial population: {bundle.initial.total_population_size}",
        f"Final population: {bundle.final.total_population_size}",
        f"Initial cooperation: {bundle.initial.overall_cooperation_rate:.1%}",
        f"Final cooperation: {bundle.final.overall_cooperation_rate:.1%}",
        f"Hybrids created: {bundle.hybrid_total_count}",
        f"Top hybrid: {bundle.top_hybrid_row['strategy_name']} ({bundle.top_hybrid_row['population']})" if bundle.top_hybrid_row else "Top hybrid: none",
        f"Winning strategy: {winning_strategy}",
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
