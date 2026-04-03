"""Metrics collection and export helpers."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterator, TypedDict

from cooperation_ga.dna import baseline_name_by_dna_string, explain_dna
from cooperation_ga.tournament import InteractionResult


@dataclass(frozen=True, slots=True)
class GenerationMetrics:
    """Metrics captured for one simulation step."""

    step: int
    total_population_size: int
    num_unique_strategies: int
    population_count_per_dna: dict[str, int]
    dominant_dna: str | None
    dominant_group_size: int
    average_score: float
    best_score: float
    worst_score: float
    score_distribution: dict[str, int]
    overall_cooperation_rate: float
    overall_defection_rate: float
    diversity_entropy: float
    dominant_strategy_share: float
    matches_played: int
    deaths_this_step: int
    births_this_step: int
    reproduction_step: bool
    mutation_count: int
    crossover_count: int


@dataclass(frozen=True, slots=True)
class PreparedExportData:
    """Precomputed export rows and labels shared by multiple exporters."""

    metric_csv_rows: list[dict[str, Any]]
    metric_json_rows: list[dict[str, Any]]
    strategy_names: dict[str, str]
    population_breakdown_rows: list[PopulationBreakdownRow]
    final_population_rows: list[FinalPopulationSummaryRow]


class PopulationBreakdownRow(TypedDict):
    """One per-step DNA population row for exports."""

    step: int
    dna: str
    strategy_name: str
    strategy_explanation: str
    population: int


class FinalPopulationSummaryRow(TypedDict):
    """One final-step population row for exports and visualization."""

    step: int
    strategy_name: str
    dna: str
    population: int
    strategy_explanation: str


def build_generation_metrics(
    step: int,
    population: Population,
    interactions: InteractionResult,
    deaths_this_step: int,
    births_this_step: int,
    reproduction_step: bool,
    mutation_count: int,
    crossover_count: int,
    score_snapshot: list[float] | None = None,
) -> GenerationMetrics:
    """Create a serializable metrics snapshot for a step."""
    counts = population.dna_counts()
    labeled_counts = {dna.to_string(): count for dna, count in counts.items()}
    scores = score_snapshot if score_snapshot is not None else [agent.score for agent in population.agents]
    total_population = population.total_size()
    entropy = 0.0
    dominant_share = 0.0
    dominant_dna = None
    dominant_group_size = 0
    for count in counts.values():
        probability = count / total_population if total_population else 0.0
        if probability <= 0.0:
            continue
        entropy -= probability * math.log2(probability)
        dominant_share = max(dominant_share, probability)
    if labeled_counts:
        dominant_dna, dominant_group_size = max(
            labeled_counts.items(),
            key=lambda item: (item[1], item[0]),
        )
    return GenerationMetrics(
        step=step,
        total_population_size=total_population,
        num_unique_strategies=len(counts),
        population_count_per_dna=labeled_counts,
        dominant_dna=dominant_dna,
        dominant_group_size=dominant_group_size,
        average_score=(sum(scores) / len(scores) if scores else 0.0),
        best_score=(max(scores) if scores else 0.0),
        worst_score=(min(scores) if scores else 0.0),
        score_distribution=_score_distribution(scores),
        overall_cooperation_rate=interactions.cooperation_rate,
        overall_defection_rate=interactions.defection_rate,
        diversity_entropy=entropy,
        dominant_strategy_share=dominant_share,
        matches_played=interactions.matches_played,
        deaths_this_step=deaths_this_step,
        births_this_step=births_this_step,
        reproduction_step=reproduction_step,
        mutation_count=mutation_count,
        crossover_count=crossover_count,
    )


def export_metrics_csv(
    metrics: list[GenerationMetrics],
    path: str | Path,
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Write metrics to CSV format."""
    if not metrics:
        return
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        if prepared_export is not None:
            rows = prepared_export.metric_csv_rows
        else:
            rows = None
        first_row = rows[0] if rows else _metric_row(metrics[0])
        writer = csv.DictWriter(handle, fieldnames=list(first_row.keys()))
        writer.writeheader()
        if rows is not None:
            writer.writerows(rows)
        else:
            writer.writerow(first_row)
            for metric in metrics[1:]:
                writer.writerow(_metric_row(metric))


def export_metrics_json(
    metrics: list[GenerationMetrics],
    path: str | Path,
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Write metrics to JSON format."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = prepared_export.metric_json_rows if prepared_export is not None else None
    with destination.open("w", encoding="utf-8") as handle:
        handle.write("[\n")
        source = rows if rows is not None else (_metric_json_row(metric) for metric in metrics)
        first = True
        for row in source:
            if not first:
                handle.write(",\n")
            json.dump(row, handle, indent=2)
            first = False
        handle.write("\n]\n")


def load_metrics_json(path: str | Path) -> list[GenerationMetrics]:
    """Load metrics snapshots from a JSON export."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Metrics JSON must contain a top-level list.")
    if not all(isinstance(item, dict) for item in raw):
        raise ValueError("Metrics JSON list items must be objects.")
    loaded: list[GenerationMetrics] = []
    for item in raw:
        population_count = item.get("population_count_per_dna")
        if isinstance(population_count, str):
            item["population_count_per_dna"] = json.loads(population_count)
        score_distribution = item.get("score_distribution")
        if isinstance(score_distribution, str):
            item["score_distribution"] = json.loads(score_distribution)
        loaded.append(GenerationMetrics(**item))
    return loaded


def export_population_breakdown_csv(
    metrics: list[GenerationMetrics],
    path: str | Path,
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Write per-step DNA population breakdown ordered by descending population."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "dna", "strategy_name", "strategy_explanation", "population"])
        writer.writeheader()
        if prepared_export is not None:
            writer.writerows(dict(row) for row in prepared_export.population_breakdown_rows)
        else:
            for row in _iter_population_breakdown_rows(metrics):
                writer.writerow(row)


def export_population_breakdown_json(
    metrics: list[GenerationMetrics],
    path: str | Path,
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Write per-step DNA population breakdown ordered by descending population."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = (
        prepared_export.population_breakdown_rows
        if prepared_export is not None
        else _iter_population_breakdown_rows(metrics)
    )
    with destination.open("w", encoding="utf-8") as handle:
        handle.write("[\n")
        first = True
        for row in rows:
            if not first:
                handle.write(",\n")
            json.dump(row, handle, indent=2)
            first = False
        handle.write("\n]\n")


def export_final_population_summary_csv(
    metrics: list[GenerationMetrics],
    path: str | Path,
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Write the final-step population summary ordered by descending population."""
    rows = (
        prepared_export.final_population_rows
        if prepared_export is not None
        else final_population_summary_rows(metrics)
    )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "strategy_name", "dna", "population", "strategy_explanation"])
        writer.writeheader()
        writer.writerows(dict(row) for row in rows)


def export_final_population_summary_json(
    metrics: list[GenerationMetrics],
    path: str | Path,
    prepared_export: PreparedExportData | None = None,
) -> None:
    """Write the final-step population summary ordered by descending population."""
    rows = (
        prepared_export.final_population_rows
        if prepared_export is not None
        else final_population_summary_rows(metrics)
    )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _score_distribution(scores: list[float]) -> dict[str, int]:
    """Bucket scores by floored integer value."""
    if not scores:
        return {}
    buckets: dict[str, int] = {}
    for score in scores:
        bucket = str(math.floor(score))
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return buckets


def _metric_row(metric: GenerationMetrics) -> dict[str, Any]:
    """Build one shallow serializable metrics CSV row."""
    return {
        "step": metric.step,
        "total_population_size": metric.total_population_size,
        "num_unique_strategies": metric.num_unique_strategies,
        "population_count_per_dna": json.dumps(metric.population_count_per_dna, sort_keys=True),
        "dominant_dna": metric.dominant_dna,
        "dominant_group_size": metric.dominant_group_size,
        "average_score": metric.average_score,
        "best_score": metric.best_score,
        "worst_score": metric.worst_score,
        "score_distribution": json.dumps(metric.score_distribution, sort_keys=True),
        "overall_cooperation_rate": metric.overall_cooperation_rate,
        "overall_defection_rate": metric.overall_defection_rate,
        "diversity_entropy": metric.diversity_entropy,
        "dominant_strategy_share": metric.dominant_strategy_share,
        "matches_played": metric.matches_played,
        "deaths_this_step": metric.deaths_this_step,
        "births_this_step": metric.births_this_step,
        "reproduction_step": metric.reproduction_step,
        "mutation_count": metric.mutation_count,
        "crossover_count": metric.crossover_count,
    }


def _metric_json_row(metric: GenerationMetrics) -> dict[str, Any]:
    """Build one shallow serializable metrics JSON row."""
    return {
        "step": metric.step,
        "total_population_size": metric.total_population_size,
        "num_unique_strategies": metric.num_unique_strategies,
        "population_count_per_dna": dict(metric.population_count_per_dna),
        "dominant_dna": metric.dominant_dna,
        "dominant_group_size": metric.dominant_group_size,
        "average_score": metric.average_score,
        "best_score": metric.best_score,
        "worst_score": metric.worst_score,
        "score_distribution": dict(metric.score_distribution),
        "overall_cooperation_rate": metric.overall_cooperation_rate,
        "overall_defection_rate": metric.overall_defection_rate,
        "diversity_entropy": metric.diversity_entropy,
        "dominant_strategy_share": metric.dominant_strategy_share,
        "matches_played": metric.matches_played,
        "deaths_this_step": metric.deaths_this_step,
        "births_this_step": metric.births_this_step,
        "reproduction_step": metric.reproduction_step,
        "mutation_count": metric.mutation_count,
        "crossover_count": metric.crossover_count,
    }


def prepare_export_data(metrics: list[GenerationMetrics]) -> PreparedExportData:
    """Precompute rows and labels shared by multiple export formats."""
    strategy_names = strategy_name_by_dna(metrics)
    explanation_cache: dict[str, str] = {}

    def explanation_for(dna: str) -> str:
        if dna not in explanation_cache:
            explanation_cache[dna] = explain_dna(dna)
        return explanation_cache[dna]

    breakdown_rows: list[PopulationBreakdownRow] = []
    for metric in metrics:
        ordered = sorted(
            metric.population_count_per_dna.items(),
            key=lambda item: (-item[1], item[0]),
        )
        for dna, population in ordered:
            breakdown_rows.append(
                {
                    "step": metric.step,
                    "dna": dna,
                    "strategy_name": strategy_names[dna],
                    "strategy_explanation": explanation_for(dna),
                    "population": population,
                }
            )

    final_rows: list[FinalPopulationSummaryRow] = []
    if metrics:
        final_metric = metrics[-1]
        ordered = sorted(
            final_metric.population_count_per_dna.items(),
            key=lambda item: (-item[1], item[0]),
        )
        final_rows = [
            {
                "step": final_metric.step,
                "strategy_name": strategy_names[dna],
                "dna": dna,
                "population": population,
                "strategy_explanation": explanation_for(dna),
            }
            for dna, population in ordered
        ]

    return PreparedExportData(
        metric_csv_rows=[_metric_row(metric) for metric in metrics],
        metric_json_rows=[_metric_json_row(metric) for metric in metrics],
        strategy_names=strategy_names,
        population_breakdown_rows=breakdown_rows,
        final_population_rows=final_rows,
    )


def _iter_population_breakdown_rows(metrics: list[GenerationMetrics]) -> Iterator[PopulationBreakdownRow]:
    """Yield per-step DNA population rows in descending population order."""
    strategy_names = strategy_name_by_dna(metrics)
    explanation_cache: dict[str, str] = {}
    for metric in metrics:
        ordered = sorted(
            metric.population_count_per_dna.items(),
            key=lambda item: (-item[1], item[0]),
        )
        for dna, population in ordered:
            if dna not in explanation_cache:
                explanation_cache[dna] = explain_dna(dna)
            yield {
                "step": metric.step,
                "dna": dna,
                "strategy_name": strategy_names[dna],
                "strategy_explanation": explanation_cache[dna],
                "population": population,
            }


def final_population_summary_rows(metrics: list[GenerationMetrics]) -> list[FinalPopulationSummaryRow]:
    """Return the final-step population summary ordered by descending population."""
    if not metrics:
        return []
    strategy_names = strategy_name_by_dna(metrics)
    final_metric = metrics[-1]
    ordered = sorted(
        final_metric.population_count_per_dna.items(),
        key=lambda item: (-item[1], item[0]),
    )
    return [
        {
            "step": final_metric.step,
            "strategy_name": strategy_names[dna],
            "dna": dna,
            "population": population,
            "strategy_explanation": explain_dna(dna),
        }
        for dna, population in ordered
    ]


def strategy_name_by_dna(metrics: list[GenerationMetrics]) -> dict[str, str]:
    """Assign stable output labels, using baseline names first and HybridN for novel DNA."""
    names = dict(baseline_name_by_dna_string())
    hybrid_index = 1
    for metric in metrics:
        for dna, _population in sorted(
            metric.population_count_per_dna.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            if dna in names:
                continue
            names[dna] = f"Hybrid{hybrid_index}"
            hybrid_index += 1
    return names
