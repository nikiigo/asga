"""CLI entrypoint for the evolution simulator."""

from __future__ import annotations

import argparse
from pathlib import Path

from cooperation_ga.config import SimulationConfig, VisualizationConfig
from cooperation_ga.evolution import EvolutionEngine
from cooperation_ga.metrics import final_population_summary_rows, load_metrics_json
from cooperation_ga.visualization import export_visualizations


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("sample_config.json"),
        help="Path to a JSON configuration file.",
    )
    parser.add_argument(
        "--render-from-metrics",
        type=Path,
        default=None,
        help="Path to an existing metrics.json file. If set, skip simulation and render visuals from saved metrics.",
    )
    parser.add_argument(
        "--render-config",
        type=Path,
        default=None,
        help="Optional JSON file with visualization-only settings. Defaults to --config.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-step progress during simulation runs.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed per-step plain-text logs during simulation runs.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print trace-level event logs during simulation runs.",
    )
    return parser


def main() -> None:
    """Run a simulation and export its metrics."""
    args = build_parser().parse_args()
    config = SimulationConfig.from_json(args.config)
    if args.verbose:
        config.verbose = True
    if args.debug:
        config.debug = True
        config.verbose = True
    if args.trace:
        config.trace = True
        config.debug = True
        config.verbose = True
    render_config_path = args.render_config or args.config
    visualization_config = VisualizationConfig.from_json(render_config_path)
    if args.render_from_metrics is not None:
        print(
            f"Loading metrics from {args.render_from_metrics} and writing rendered outputs to "
            f"{visualization_config.output_dir}...",
            flush=True,
        )
        metrics = load_metrics_json(args.render_from_metrics)
        export_visualizations(metrics, visualization_config.output_dir, visualization_config)
        print(f"Rendered visuals from metrics: {args.render_from_metrics}", flush=True)
        print(f"Visual report: {Path(visualization_config.output_dir) / 'report.html'}", flush=True)
        return
    engine = EvolutionEngine.from_config(config, visualization_config)
    print(
        f"Starting simulation for {config.num_steps} steps. Output directory: {config.output_dir}",
        flush=True,
    )
    metrics = engine.run()
    print(
        f"Simulation finished. Writing results to {config.output_dir}..."
        " The program is still running and has not hung.",
        flush=True,
    )
    engine.export(metrics)
    print("Finished writing results.", flush=True)
    final = metrics[-1]
    print(f"Steps: {len(metrics)}", flush=True)
    print(f"Final unique strategies: {final.num_unique_strategies}", flush=True)
    print(f"Final population size: {final.total_population_size}", flush=True)
    print(f"Winning DNA: {final.dominant_dna}", flush=True)
    print(f"Winning group size: {final.dominant_group_size}", flush=True)
    print(f"Final cooperation rate: {final.overall_cooperation_rate:.3f}", flush=True)
    print(f"Final dominant share: {final.dominant_strategy_share:.3f}", flush=True)
    print("Final strategies:", flush=True)
    for row in final_population_summary_rows(metrics):
        print(
            f"- {row['strategy_name']}: population={row['population']}, dna={row['dna']}, "
            f"explanation={row['strategy_explanation']}",
            flush=True,
        )
    if config.export_visuals:
        print(f"Visual report: {Path(visualization_config.output_dir) / 'report.html'}", flush=True)


if __name__ == "__main__":
    main()
