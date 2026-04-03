"""Metrics collection and export helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
import math
from pathlib import Path
from typing import Any, TypedDict

from cooperation_ga.dna import baseline_name_by_dna_string, explain_dna
from cooperation_ga.population import Population
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
) -> GenerationMetrics:
    """Create a serializable metrics snapshot for a step."""
    counts = population.dna_counts()
    labeled_counts = {dna.to_string(): count for dna, count in counts.items()}
    scores = [agent.score for agent in population.agents] or [0.0]
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
        average_score=sum(scores) / len(scores),
        best_score=max(scores),
        worst_score=min(scores),
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


def export_metrics_csv(metrics: list[GenerationMetrics], path: str | Path) -> None:
    """Write metrics to CSV format."""
    if not metrics:
        return
    flat_rows: list[dict[str, Any]] = []
    for metric in metrics:
        row = asdict(metric)
        row["population_count_per_dna"] = json.dumps(row["population_count_per_dna"], sort_keys=True)
        row["score_distribution"] = json.dumps(row["score_distribution"], sort_keys=True)
        flat_rows.append(row)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)


def export_metrics_json(metrics: list[GenerationMetrics], path: str | Path) -> None:
    """Write metrics to JSON format."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps([asdict(metric) for metric in metrics], indent=2), encoding="utf-8")


def load_metrics_json(path: str | Path) -> list[GenerationMetrics]:
    """Load metrics snapshots from a JSON export."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Metrics JSON must contain a top-level list.")
    if not all(isinstance(item, dict) for item in raw):
        raise ValueError("Metrics JSON list items must be objects.")
    return [GenerationMetrics(**item) for item in raw]


def export_population_breakdown_csv(metrics: list[GenerationMetrics], path: str | Path) -> None:
    """Write per-step DNA population breakdown ordered by descending population."""
    rows = _population_breakdown_rows(metrics)
    csv_rows: list[dict[str, Any]] = [dict(row) for row in rows]
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "dna", "strategy_name", "strategy_explanation", "population"])
        writer.writeheader()
        writer.writerows(csv_rows)


def export_population_breakdown_json(metrics: list[GenerationMetrics], path: str | Path) -> None:
    """Write per-step DNA population breakdown ordered by descending population."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(_population_breakdown_rows(metrics), indent=2), encoding="utf-8")


def export_final_population_summary_csv(metrics: list[GenerationMetrics], path: str | Path) -> None:
    """Write the final-step population summary ordered by descending population."""
    rows = final_population_summary_rows(metrics)
    csv_rows: list[dict[str, Any]] = [dict(row) for row in rows]
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "strategy_name", "dna", "population", "strategy_explanation"])
        writer.writeheader()
        writer.writerows(csv_rows)


def export_final_population_summary_json(metrics: list[GenerationMetrics], path: str | Path) -> None:
    """Write the final-step population summary ordered by descending population."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(final_population_summary_rows(metrics), indent=2), encoding="utf-8")


def _score_distribution(scores: list[float]) -> dict[str, int]:
    """Bucket scores by floored integer value."""
    buckets: dict[str, int] = {}
    for score in scores:
        bucket = str(math.floor(score))
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return buckets


def _population_breakdown_rows(metrics: list[GenerationMetrics]) -> list[PopulationBreakdownRow]:
    """Flatten per-step DNA counts into sorted rows."""
    strategy_names = strategy_name_by_dna(metrics)
    rows: list[PopulationBreakdownRow] = []
    for metric in metrics:
        ordered = sorted(
            metric.population_count_per_dna.items(),
            key=lambda item: (-item[1], item[0]),
        )
        for dna, population in ordered:
            rows.append(
                {
                    "step": metric.step,
                    "dna": dna,
                    "strategy_name": strategy_names[dna],
                    "strategy_explanation": explain_dna(dna),
                    "population": population,
                }
            )
    return rows


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
