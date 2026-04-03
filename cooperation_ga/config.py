"""Configuration objects for the simulator and visualization."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Any, TypeVar

from cooperation_ga.dna import default_genome_length

ConfigT = TypeVar("ConfigT", bound=object)


def _load_json_object(path: str | Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration JSON must contain a top-level object.")
    return data


def _filter_dataclass_kwargs(data: dict[str, Any], cls: type[ConfigT]) -> dict[str, Any]:
    """Keep only keys accepted by the target dataclass."""
    allowed = {field.name for field in fields(cls)}
    return {key: value for key, value in data.items() if key in allowed}


@dataclass(slots=True)
class VisualizationConfig:
    """Presentation and report settings for exported visuals."""

    output_dir: str = "sample_output"
    top_strategies_to_plot: int = 10
    viz_palette: list[str] | None = None
    viz_bg_color: str = "#f6efe7"
    viz_panel_color: str = "#fffaf5"
    viz_ink_color: str = "#003d5b"
    viz_muted_color: str = "#5c5c5c"
    viz_accent_color: str = "#d1495b"
    viz_cooperation_color: str = "#00798c"
    viz_defection_color: str = "#d1495b"
    viz_unique_color: str = "#edae49"
    viz_entropy_color: str = "#30638e"
    viz_dominant_color: str = "#bc4749"
    viz_title_text: str = "Evolution of Cooperation"
    viz_subtitle_text: str = "Genetic algorithms in the repeated Prisoner's Dilemma"
    viz_behavior_title: str = "Behavioral balance over time"
    viz_structure_title: str = "Population structure"
    viz_leader_title: str = "Leading DNA at the finish"
    viz_report_title: str = "Evolution of Cooperation Report"
    viz_report_heading: str = "Evolution of Cooperation"
    viz_report_description: str = "Agent-based Prisoner's Dilemma simulation with per-step pairing, score-based selection pressure, scheduled reproduction, and long-run DNA dynamics."

    def __post_init__(self) -> None:
        """Validate visualization settings."""
        if self.top_strategies_to_plot <= 0:
            raise ValueError("top_strategies_to_plot must be positive.")
        if self.viz_palette is None:
            self.viz_palette = [
                "#d1495b",
                "#00798c",
                "#edae49",
                "#30638e",
                "#003d5b",
                "#66a182",
                "#9c6644",
                "#6d597a",
                "#bc4749",
                "#7f5539",
            ]
        if not self.viz_palette:
            raise ValueError("viz_palette must contain at least one color.")

    @classmethod
    def from_json(cls, path: str | Path) -> "VisualizationConfig":
        """Load visualization settings from a JSON file, ignoring simulation keys."""
        return cls(**_filter_dataclass_kwargs(_load_json_object(path), cls))

    @classmethod
    def from_simulation_config(cls, config: "SimulationConfig") -> "VisualizationConfig":
        """Build visualization settings from a simulation config for backward compatibility."""
        data = {
            field.name: getattr(config, field.name)
            for field in fields(cls)
            if hasattr(config, field.name)
        }
        return cls(**data)

    def to_json(self, path: str | Path) -> None:
        """Persist visualization settings to a JSON file."""
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


@dataclass(slots=True)
class SimulationConfig:
    """Configurable parameters for a simulation run."""

    memory_depth: int = 1
    rounds_per_match: int = 20
    num_generations: int = 50
    num_steps: int | None = None
    initial_population_size: int = 200
    initial_num_strategies: int = 8
    initial_population: dict[str, int] | None = None
    mutation_rate: float = 0.01
    mutation_genes_per_step: float | None = None
    crossover_rate: float = 0.7
    noise_rate: float = 0.0
    death_rate: float = 0.02
    max_population_size: int | None = None
    overflow_cull_rate: float = 0.3
    overflow_cull_score_correlation: float = 0.5
    selection_epsilon: float = 1e-9
    odd_agent_mode: str = "skip"
    self_play: bool = True
    payoff_R: int = 3
    payoff_T: int = 5
    payoff_P: int = 1
    payoff_S: int = 0
    random_seed: int | None = 7
    selection_mode: str = "fitness_proportional"
    elitism_count: int = 0
    new_random_strategy_rate: float = 0.0
    extinction_threshold: int = 0
    initialization_mode: str = "random"
    include_seeded_strategies: bool = True
    seed_strategies: list[str] | None = None
    seed_strategy_population: int = 50
    tft_forgiveness_probability: float = 0.1
    random_strategy_cooperation_probability: float = 0.5
    random_strategy_mix: int = 0
    sexual_reproduction_rate: float = 0.5
    reproduction_interval: int = 10
    offspring_per_pair: int = 1
    max_children_per_agent: int = 4
    allow_self_pairing: bool = True
    pairing_mode: str = "max_possible"
    fixed_pairs_per_reproduction: int | None = None
    rating_mode: str = "current_step"
    rating_window: int = 10
    reset_scores_after_reproduction: bool = True
    checkpoint_interval: int = 0
    verbose: bool = False
    debug: bool = False
    trace: bool = False
    output_dir: str = "sample_output"
    export_csv: bool = True
    export_json: bool = True
    export_visuals: bool = True

    def __post_init__(self) -> None:
        """Validate supported settings."""
        if self.memory_depth != 1:
            raise ValueError("Only memory_depth=1 is currently supported.")
        if self.num_steps is None:
            self.num_steps = self.num_generations
        if self.initial_population_size < 0:
            raise ValueError("initial_population_size must be non-negative.")
        if self.initial_num_strategies <= 0:
            raise ValueError("initial_num_strategies must be positive.")
        if self.seed_strategy_population <= 0:
            raise ValueError("seed_strategy_population must be positive.")
        for name in (
            "mutation_rate",
            "crossover_rate",
            "noise_rate",
            "death_rate",
            "overflow_cull_rate",
            "overflow_cull_score_correlation",
            "new_random_strategy_rate",
            "sexual_reproduction_rate",
            "tft_forgiveness_probability",
            "random_strategy_cooperation_probability",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1.")
        if self.mutation_genes_per_step is None:
            self.mutation_genes_per_step = self.mutation_rate * default_genome_length(self.memory_depth)
        if self.mutation_genes_per_step < 0:
            raise ValueError("mutation_genes_per_step must be non-negative.")
        if self.selection_mode != "fitness_proportional":
            raise ValueError("Only fitness_proportional selection is supported.")
        if self.initialization_mode not in {"random", "seeded"}:
            raise ValueError("initialization_mode must be 'random' or 'seeded'.")
        if self.selection_epsilon <= 0.0:
            raise ValueError("selection_epsilon must be positive.")
        if self.odd_agent_mode not in {"skip", "self_play"}:
            raise ValueError("odd_agent_mode must be 'skip' or 'self_play'.")
        if self.pairing_mode not in {"max_possible", "fixed"}:
            raise ValueError("pairing_mode must be 'max_possible' or 'fixed'.")
        if self.rating_mode not in {"current_step", "rolling_average"}:
            raise ValueError("rating_mode must be 'current_step' or 'rolling_average'.")
        if self.reproduction_interval <= 0:
            raise ValueError("reproduction_interval must be positive.")
        if self.checkpoint_interval < 0:
            raise ValueError("checkpoint_interval must be non-negative.")
        if self.offspring_per_pair <= 0:
            raise ValueError("offspring_per_pair must be positive.")
        if self.max_children_per_agent <= 0:
            raise ValueError("max_children_per_agent must be positive.")
        if self.rating_window <= 0:
            raise ValueError("rating_window must be positive.")
        if self.seed_strategies is None:
            self.seed_strategies = [
                "ALLC",
                "ALLD",
                "TFT",
                "TF2T",
                "PAVLOV",
                "JOSS",
                "GTFT",
                "NYDEGGER",
                "SHUBIK",
                "SUSPICIOUS_TFT",
                "SUSPICIOUS_PAVLOV",
                "ALTERNATOR",
                "FORGIVER",
                "DEFENSIVE",
                "TESTER",
            ]
        if self.max_population_size is not None and self.max_population_size <= 0:
            raise ValueError("max_population_size must be positive when provided.")
        if self.initial_population is not None and any(count < 0 for count in self.initial_population.values()):
            raise ValueError("initial_population counts must be non-negative.")

    @classmethod
    def from_json(cls, path: str | Path) -> "SimulationConfig":
        """Load simulation settings from a JSON file, ignoring visualization keys."""
        return cls(**_filter_dataclass_kwargs(_load_json_object(path), cls))

    def to_json(self, path: str | Path) -> None:
        """Persist configuration to a JSON file."""
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
