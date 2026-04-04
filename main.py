"""CLI entrypoint for the evolution simulator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cooperation_ga.config import SimulationConfig, VisualizationConfig
from cooperation_ga.evolution import EvolutionEngine
from cooperation_ga.metrics import final_population_summary_rows, load_metrics_json
from cooperation_ga.runtime import bundled_sample_config_path, copy_example_configs


def _write_status(path: Path, phase: str, **payload: object) -> None:
    """Write a plain-text JSON status snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"phase": phase, **payload}
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a JSON configuration file. Defaults to the bundled sample config.",
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
        help="Optional JSON file with visualization-only settings. Defaults to built-in visualization defaults when omitted.",
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
    parser.add_argument(
        "--copy-example-configs",
        type=Path,
        default=None,
        help="Copy the bundled example JSON configs into the given directory and exit.",
    )
    return parser


def main() -> None:
    """Run a simulation and export its metrics."""
    args = build_parser().parse_args()
    if args.copy_example_configs is not None:
        copied = copy_example_configs(args.copy_example_configs)
        print(f"Copied {len(copied)} example config files to {args.copy_example_configs}", flush=True)
        for path in copied:
            print(path, flush=True)
        return
    if args.render_from_metrics is not None:
        from cooperation_ga.visualization import export_visualizations

        if args.render_config is not None:
            visualization_config = VisualizationConfig.from_json(args.render_config)
        else:
            visualization_config = VisualizationConfig()
        _write_status(
            Path(visualization_config.output_dir) / "status.txt",
            "load_metrics",
            metrics_path=str(args.render_from_metrics),
            output_dir=visualization_config.output_dir,
        )
        print(
            f"Loading metrics from {args.render_from_metrics} and writing rendered outputs to "
            f"{visualization_config.output_dir}...",
            flush=True,
        )
        metrics = load_metrics_json(args.render_from_metrics)
        export_visualizations(metrics, visualization_config.output_dir, visualization_config)
        print(f"Rendered visuals from metrics: {args.render_from_metrics}", flush=True)
        print(f"HTML report: {Path(visualization_config.output_dir) / 'report.html'}", flush=True)
        print(f"Static infographic: {Path(visualization_config.output_dir) / 'summary_infographic.png'}", flush=True)
        return
    if args.render_config is not None:
        raise ValueError(
            "--render-config is only supported together with --render-from-metrics. "
            "Simulation runs export metrics only."
        )
    config = SimulationConfig.from_json(args.config or bundled_sample_config_path())
    if args.verbose:
        config.verbose = True
    if args.debug:
        config.debug = True
        config.verbose = True
    if args.trace:
        config.trace = True
        config.debug = True
        config.verbose = True
    engine = EvolutionEngine.from_config(config)
    _write_status(Path(config.output_dir) / "status.txt", "starting", total_steps=config.num_steps, output_dir=config.output_dir)
    print(
        f"Starting simulation for {config.num_steps} steps. Output directory: {config.output_dir}",
        flush=True,
    )
    metrics = engine.run()
    print(
        f"Simulation finished. Writing results to: {config.output_dir}..."
        " The program is still running and has not hung.",
        flush=True,
    )
    engine.export(metrics)
    print("Finished writing results.", flush=True)
    final = metrics[-1]
    winning_dna = final.dominant_dna if final.total_population_size > 0 else "no surviving strategy"
    print(f"Steps: {len(metrics)}", flush=True)
    print(f"Final unique strategies: {final.num_unique_strategies}", flush=True)
    print(f"Final population size: {final.total_population_size}", flush=True)
    print(f"Winning DNA: {winning_dna}", flush=True)
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


if __name__ == "__main__":
    main()
