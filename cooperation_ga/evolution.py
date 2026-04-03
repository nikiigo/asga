"""Evolution engine for repeated Prisoner's Dilemma populations."""

from __future__ import annotations

import json
from math import ceil, floor
from random import Random
from dataclasses import dataclass
from pathlib import Path

from cooperation_ga.config import SimulationConfig, VisualizationConfig
from cooperation_ga.dna import baseline_name_by_dna_string
from cooperation_ga.dna import StrategyDNA
from cooperation_ga.metrics import (
    GenerationMetrics,
    build_generation_metrics,
    export_metrics_csv,
    export_metrics_json,
    export_final_population_summary_csv,
    export_final_population_summary_json,
    export_population_breakdown_csv,
    export_population_breakdown_json,
    prepare_export_data,
)
from cooperation_ga.population import Agent, Population
from cooperation_ga.tournament import run_interactions


@dataclass(slots=True)
class EvolutionEngine:
    """Drive the simulation across multiple steps."""

    config: SimulationConfig
    visualization_config: VisualizationConfig
    population: Population
    rng: Random

    def _status_path(self) -> Path:
        """Return the main status-file path for this run."""
        return Path(self.config.output_dir) / "status.txt"

    def _write_status(self, phase: str, **payload: object) -> None:
        """Write a plain-text JSON status snapshot for external monitoring."""
        path = self._status_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"phase": phase, **payload}
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def from_config(
        cls,
        config: SimulationConfig,
        visualization_config: VisualizationConfig | None = None,
    ) -> "EvolutionEngine":
        """Construct an engine with deterministic RNG and initialized population."""
        rng = Random(config.random_seed)
        if config.initialization_mode == "seeded":
            population = Population.seeded_initial(config, rng)
        else:
            population = Population.random_initial(config, rng)
        return cls(
            config=config,
            visualization_config=visualization_config or VisualizationConfig.from_simulation_config(config),
            population=population,
            rng=rng,
        )

    def run_generation(self, generation: int) -> GenerationMetrics:
        """Backward-compatible alias for one step."""
        return self.run_step(generation + 1)

    def run_step(self, step: int) -> GenerationMetrics:
        """Execute one step of interaction, death, aging, and scheduled reproduction."""
        interactions = run_interactions(self.population, self.config, self.rng)
        self._apply_scores(interactions.score_by_agent_id)
        deaths_this_step, low_score_victims = self._eliminate_lowest_scoring_agents()
        self.population.increment_age()

        reproduction_step = step % self.config.reproduction_interval == 0
        births_this_step = 0
        mutation_count = 0
        crossover_count = 0
        reproduction_trace: list[str] = []
        if reproduction_step:
            births_this_step, mutation_count, crossover_count, reproduction_trace = self._reproduce()

        overflow_deaths, overflow_victims = self._apply_population_cap()
        deaths_this_step += overflow_deaths
        score_snapshot = [agent.score for agent in self.population.agents]

        metric = build_generation_metrics(
            step=step,
            population=self.population,
            interactions=interactions,
            deaths_this_step=deaths_this_step,
            births_this_step=births_this_step,
            reproduction_step=reproduction_step,
            mutation_count=mutation_count,
            crossover_count=crossover_count,
            score_snapshot=score_snapshot,
        )
        if reproduction_step and getattr(self.config, "reset_scores_after_reproduction", True):
            self.population.reset_scores()
        if self.config.trace:
            self._print_trace(step, interactions, low_score_victims, overflow_victims, reproduction_trace)
        return metric

    def run(self, num_generations: int | None = None) -> list[GenerationMetrics]:
        """Run the simulator for the configured number of steps."""
        total_steps = self.config.num_steps if num_generations is None else num_generations
        history: list[GenerationMetrics] = []
        for step in range(1, total_steps + 1):
            starting_population = self.population.total_size()
            starting_unique = len(self.population.dna_counts())
            self._write_status(
                "simulation",
                current_step=step,
                total_steps=total_steps,
                start_population=starting_population,
                start_unique_strategies=starting_unique,
            )
            metric = self.run_step(step)
            if self.config.verbose or self.config.debug or self.config.trace:
                print(
                    f"Step {step}/{total_steps}: "
                    f"matches={metric.matches_played}, "
                    f"start_population={starting_population}, "
                    f"start_unique_strategies={starting_unique}"
                )
            if self.config.debug or self.config.trace:
                dominant_name = self._strategy_label(metric.dominant_dna)
                top_strategies = self._top_strategy_summary(metric)
                overflow_note = ""
                if (
                    self.config.max_population_size is not None
                    and starting_population >= self.config.max_population_size
                ):
                    overflow_note = (
                        f", overflow_cap={self.config.max_population_size}, "
                        f"overflow_cull_rate={self.config.overflow_cull_rate:.2f}, "
                        f"overflow_score_corr={self.config.overflow_cull_score_correlation:.2f}"
                    )
                print(
                    f"  reproduction={metric.reproduction_step}, "
                    f"avg_score={metric.average_score:.2f}, "
                    f"best_score={metric.best_score:.2f}, "
                    f"worst_score={metric.worst_score:.2f}, "
                    f"births={metric.births_this_step}, "
                    f"deaths={metric.deaths_this_step}, "
                    f"mutations={metric.mutation_count}, "
                    f"crossovers={metric.crossover_count}, "
                    f"end_population={metric.total_population_size}, "
                    f"end_unique_strategies={metric.num_unique_strategies}, "
                    f"dominant={dominant_name}{overflow_note}"
                )
                print(f"  top_strategies={top_strategies}")
            history.append(metric)
            if self.config.checkpoint_interval > 0 and step % self.config.checkpoint_interval == 0:
                self.export_checkpoint(history, step)
        self._write_status("simulation_complete", total_steps=total_steps, final_population=self.population.total_size())
        return history

    def export(self, metrics: list[GenerationMetrics]) -> None:
        """Export recorded metrics in configured formats."""
        self._write_status("export", target_dir=self.config.output_dir, metrics_steps=len(metrics))
        self._export_to_directory(
            metrics,
            self.config.output_dir,
            visual_output_dir=self.visualization_config.output_dir,
        )
        self._write_status("done", target_dir=self.config.output_dir, metrics_steps=len(metrics))

    def export_checkpoint(self, metrics: list[GenerationMetrics], step: int) -> None:
        """Export an intermediate checkpoint snapshot."""
        checkpoint_dir = f"{self.config.output_dir}/checkpoints/step_{step:05d}"
        self._write_status("checkpoint", step=step, checkpoint_dir=checkpoint_dir)
        print(
            f"Writing checkpoint for step {step} to {checkpoint_dir}..."
            " The program is still running and has not hung.",
            flush=True,
        )
        self._export_to_directory(metrics, checkpoint_dir, visual_output_dir=checkpoint_dir)
        print(f"Checkpoint written: {checkpoint_dir}", flush=True)

    def _export_to_directory(
        self,
        metrics: list[GenerationMetrics],
        output_dir: str,
        visual_output_dir: str | None = None,
    ) -> None:
        """Export recorded metrics in configured formats to a specific directory."""
        prepared_export = prepare_export_data(metrics)
        if self.config.export_csv and metrics:
            export_metrics_csv(metrics, f"{output_dir}/metrics.csv", prepared_export=prepared_export)
            export_population_breakdown_csv(
                metrics,
                f"{output_dir}/population_breakdown.csv",
                prepared_export=prepared_export,
            )
            export_final_population_summary_csv(
                metrics,
                f"{output_dir}/final_population_summary.csv",
                prepared_export=prepared_export,
            )
        if self.config.export_json:
            export_metrics_json(metrics, f"{output_dir}/metrics.json", prepared_export=prepared_export)
            export_population_breakdown_json(
                metrics,
                f"{output_dir}/population_breakdown.json",
                prepared_export=prepared_export,
            )
            export_final_population_summary_json(
                metrics,
                f"{output_dir}/final_population_summary.json",
                prepared_export=prepared_export,
            )
        if self.config.export_visuals and metrics:
            from cooperation_ga.visualization import export_visualizations

            export_visualizations(
                metrics,
                visual_output_dir or output_dir,
                self.visualization_config,
                prepared_export=prepared_export,
            )

    def _apply_scores(self, score_by_agent_id: dict[int, float]) -> None:
        """Add the current step's match scores to each agent."""
        for agent in self.population.agents:
            agent.score += score_by_agent_id.get(agent.id, 0.0)

    def _eliminate_lowest_scoring_agents(self) -> tuple[int, list[tuple[int, float]]]:
        """Remove the configured lowest-scoring fraction of agents, breaking ties randomly."""
        if not self.population.agents:
            return 0, []
        num_to_kill = floor(self.config.death_rate * self.population.total_size())
        shuffled = list(self.population.agents)
        self.rng.shuffle(shuffled)
        shuffled.sort(key=lambda agent: agent.score)
        victims = [(agent.id, agent.score) for agent in shuffled[:num_to_kill]]
        to_remove = {agent_id for agent_id, _score in victims}
        self.population.remove_agent_ids(to_remove)
        return len(to_remove), victims

    def _reproduce(self) -> tuple[int, int, int, list[str]]:
        """Run scheduled reproduction at the individual-agent level."""
        if len(self.population.agents) < 2:
            return 0, 0, 0, []
        available = [
            agent
            for agent in self.population.agents
            if agent.children_count < self.config.max_children_per_agent
        ]
        births = 0
        mutation_count = 0
        crossover_count = 0
        offspring_dnas: list[StrategyDNA] = []
        parent_ids_to_remove: set[int] = set()
        trace_lines: list[str] = []
        target_pairs = self._target_pair_count(len(available))
        for _ in range(target_pairs):
            parent_a = self._sample_parent(available)
            if parent_a is None:
                break
            available.remove(parent_a)
            parent_b = self._sample_parent(
                available,
                forbidden_dna=None if self.config.allow_self_pairing else parent_a.dna,
            )
            if parent_b is None:
                break
            available.remove(parent_b)
            remaining_capacity = min(
                self.config.max_children_per_agent - parent_a.children_count,
                self.config.max_children_per_agent - parent_b.children_count,
            )
            if remaining_capacity <= 0:
                if parent_a.children_count >= self.config.max_children_per_agent:
                    parent_ids_to_remove.add(parent_a.id)
                if parent_b.children_count >= self.config.max_children_per_agent:
                    parent_ids_to_remove.add(parent_b.id)
                continue
            pair_offspring = min(self.config.offspring_per_pair, remaining_capacity)
            for _child_index in range(pair_offspring):
                child_dna, did_crossover, child_mutation_count = self._create_valid_offspring(
                    parent_a.dna,
                    parent_b.dna,
                )
                crossover_count += int(did_crossover)
                mutation_count += child_mutation_count
                offspring_dnas.append(child_dna)
                births += 1
                parent_a.children_count += 1
                parent_b.children_count += 1
                if self.config.trace:
                    trace_lines.append(
                        "reproduction "
                        f"parents=({parent_a.id},{parent_b.id}) "
                        f"child_dna={child_dna.to_string()} "
                        f"crossover={did_crossover} mutations={child_mutation_count}"
                    )
            if parent_a.children_count >= self.config.max_children_per_agent:
                parent_ids_to_remove.add(parent_a.id)
            if parent_b.children_count >= self.config.max_children_per_agent:
                parent_ids_to_remove.add(parent_b.id)

        self.population.remove_agent_ids(parent_ids_to_remove)
        self.population.add_offspring(offspring_dnas)
        return births, mutation_count, crossover_count, trace_lines

    def _apply_population_cap(self) -> tuple[int, list[tuple[int, float]]]:
        """Cull agents when the configured max population size is reached or exceeded."""
        if self.config.max_population_size is None:
            return 0, []
        current_size = self.population.total_size()
        if current_size < self.config.max_population_size:
            return 0, []
        num_to_kill = ceil(self.config.overflow_cull_rate * current_size)
        if num_to_kill <= 0:
            return 0, []
        scored_agents = self._overflow_cull_order()
        victims = [(agent.id, agent.score) for agent in scored_agents[:num_to_kill]]
        to_remove = {agent_id for agent_id, _score in victims}
        self.population.remove_agent_ids(to_remove)
        return len(to_remove), victims

    def _overflow_cull_order(self) -> list[Agent]:
        """Order agents for overflow culling by blending random and low-score pressure."""
        shuffled = list(self.population.agents)
        self.rng.shuffle(shuffled)
        if self.config.overflow_cull_score_correlation <= 0.0:
            return shuffled
        ranked = sorted(shuffled, key=lambda agent: agent.score)
        if len(ranked) == 1 or self.config.overflow_cull_score_correlation >= 1.0:
            return ranked
        badness_by_id = {
            agent.id: index / (len(ranked) - 1)
            for index, agent in enumerate(ranked)
        }
        blended = sorted(
            shuffled,
            key=lambda agent: (
                self.config.overflow_cull_score_correlation * badness_by_id[agent.id]
                + (1.0 - self.config.overflow_cull_score_correlation) * self.rng.random()
            ),
            reverse=True,
        )
        return blended

    def _target_pair_count(self, available_population: int) -> int:
        """Return the configured number of parent pairs."""
        if self.config.pairing_mode == "fixed":
            return min(self.config.fixed_pairs_per_reproduction or 0, available_population // 2)
        return available_population // 2

    def _sample_parent(
        self,
        candidates: list[Agent],
        forbidden_dna: StrategyDNA | None = None,
    ) -> Agent | None:
        """Sample one parent with probability proportional to adjusted score."""
        eligible = [agent for agent in candidates if forbidden_dna is None or agent.dna != forbidden_dna]
        if not eligible:
            return None
        min_score = min(agent.score for agent in eligible)
        weights = [agent.score - min_score + self.config.selection_epsilon for agent in eligible]
        total = sum(weights)
        threshold = self.rng.random() * total
        cumulative = 0.0
        for agent, weight in zip(eligible, weights):
            cumulative += weight
            if threshold <= cumulative:
                return agent
        return eligible[-1]

    @staticmethod
    def _strategy_label(dna: str | None) -> str:
        """Return a compact human-readable strategy label for logs."""
        if dna is None:
            return "n/a"
        return baseline_name_by_dna_string().get(dna, dna)

    def _top_strategy_summary(self, metric: GenerationMetrics) -> str:
        """Return the top three strategy groups as a compact log string."""
        ordered = sorted(
            metric.population_count_per_dna.items(),
            key=lambda item: (-item[1], item[0]),
        )[:3]
        return ", ".join(
            f"{self._strategy_label(dna)}:{count}"
            for dna, count in ordered
        ) or "none"

    @staticmethod
    def _print_trace(
        step: int,
        interactions,
        low_score_victims: list[tuple[int, float]],
        overflow_victims: list[tuple[int, float]],
        reproduction_trace: list[str],
    ) -> None:
        """Print trace-level event details for a step."""
        for agent_a, agent_b, match in interactions.pairwise_scores:
            print(
                f"  trace step={step} match agents=({agent_a},{agent_b}) "
                f"scores=({match.score_a},{match.score_b}) "
                f"coop=({match.coop_a},{match.coop_b}) defect=({match.defect_a},{match.defect_b})"
            )
        if low_score_victims:
            print(
                f"  trace step={step} low_score_deaths="
                + ", ".join(f"{agent_id}:{score:.2f}" for agent_id, score in low_score_victims)
            )
        for line in reproduction_trace:
            print(f"  trace step={step} {line}")
        if overflow_victims:
            print(
                f"  trace step={step} overflow_cull="
                + ", ".join(f"{agent_id}:{score:.2f}" for agent_id, score in overflow_victims)
            )

    def _create_offspring(self, dna_a: StrategyDNA, dna_b: StrategyDNA) -> tuple[StrategyDNA, bool]:
        """Create one child DNA from two parents."""
        if self.rng.random() < self.config.new_random_strategy_rate:
            return StrategyDNA.random(self.config.memory_depth, self.rng), False
        if self.rng.random() < self.config.crossover_rate:
            return dna_a.crossover(dna_b, self.rng), True
        return (dna_a if self.rng.random() < 0.5 else dna_b), False

    def _create_valid_offspring(
        self,
        dna_a: StrategyDNA,
        dna_b: StrategyDNA,
    ) -> tuple[StrategyDNA, bool, int]:
        """Retry crossover and mutation until a valid child genome is produced."""
        for _ in range(1000):
            child_dna, did_crossover = self._create_offspring(dna_a, dna_b)
            per_gene_mutation = min(1.0, self.config.mutation_genes_per_step / len(child_dna.genes))
            try:
                mutated = child_dna.mutate(per_gene_mutation, self.rng)
            except ValueError:
                continue
            mutation_count = sum(1 for before, after in zip(child_dna.genes, mutated.genes) if before != after)
            return mutated, did_crossover, mutation_count
        raise RuntimeError("Unable to generate a valid child DNA after 1000 attempts.")
