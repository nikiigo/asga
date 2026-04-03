"""Configuration objects for the simulator and visualization."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Any, TypeVar

from cooperation_ga.dna import baseline_dna_library, default_genome_length, StrategyDNA


def _max_random_lookup_strategies(memory_depth: int) -> int:
    """Return the maximum number of unique random lookup DNAs the generator can produce."""
    effective_memory = max(1, memory_depth)
    return 2 ** (1 + 4**effective_memory)


def _random_lookup_space(memory_depth: int) -> set[str]:
    """Return the set of raw DNA strings reachable by the random lookup generator."""
    effective_memory = max(1, memory_depth)
    states = 4**effective_memory
    random_space: set[str] = set()
    for init_mask in range(2):
        for table_mask in range(2**states):
            actions = [
                "C" if (table_mask >> (states - 1 - index)) & 1 else "D"
                for index in range(states)
            ]
            shorthand = ("C" if init_mask else "D") + "".join(actions)
            random_space.add(StrategyDNA.from_action_string(shorthand).to_string())
    return random_space

ConfigT = TypeVar("ConfigT", bound=object)
SIMULATION_JSON_KEYS = frozenset(
    {
        "memory_depth",
        "rounds_per_match",
        "num_generations",
        "num_steps",
        "initial_population_size",
        "initial_num_strategies",
        "initial_population",
        "mutation_rate",
        "mutation_genes_per_step",
        "crossover_rate",
        "noise_rate",
        "death_rate",
        "max_population_size",
        "overflow_cull_rate",
        "overflow_cull_score_correlation",
        "selection_epsilon",
        "payoff_R",
        "payoff_T",
        "payoff_P",
        "payoff_S",
        "random_seed",
        "selection_mode",
        "elitism_count",
        "new_random_strategy_rate",
        "extinction_threshold",
        "initialization_mode",
        "include_seeded_strategies",
        "seed_strategies",
        "seed_strategy_population",
        "tft_forgiveness_probability",
        "random_strategy_cooperation_probability",
        "random_strategy_mix",
        "sexual_reproduction_rate",
        "reproduction_interval",
        "offspring_per_pair",
        "max_children_per_agent",
        "allow_same_dna_pairing",
        "allow_self_pairing",
        "pairing_mode",
        "fixed_pairs_per_reproduction",
        "reset_scores_after_reproduction",
        "checkpoint_interval",
        "verbose",
        "debug",
        "trace",
        "export_csv",
        "export_json",
        "export_visuals",
    }
)
VISUALIZATION_JSON_KEYS = frozenset(
    {
        "top_strategies_to_plot",
        "viz_palette",
        "viz_bg_color",
        "viz_panel_color",
        "viz_ink_color",
        "viz_muted_color",
        "viz_accent_color",
        "viz_cooperation_color",
        "viz_defection_color",
        "viz_unique_color",
        "viz_entropy_color",
        "viz_dominant_color",
        "viz_title_text",
        "viz_subtitle_text",
        "viz_behavior_title",
        "viz_structure_title",
        "viz_leader_title",
        "viz_report_title",
        "viz_report_heading",
        "viz_report_description",
    }
)


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


def _require_config_keys(
    data: dict[str, Any],
    required_any: frozenset[str],
    config_kind: str,
) -> None:
    """Require at least one distinguishing key for the expected config type."""
    if any(key in data for key in required_any):
        return
    kind_label = config_kind.removesuffix("Config").lower()
    raise ValueError(
        f"{config_kind} JSON must include at least one {kind_label}-specific setting."
    )


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
        """Load visualization settings from a visualization JSON file."""
        data = _load_json_object(path)
        _require_config_keys(data, VISUALIZATION_JSON_KEYS, "VisualizationConfig")
        return cls(**_filter_dataclass_kwargs(data, cls))

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
    allow_same_dna_pairing: bool = True
    allow_self_pairing: bool | None = None
    pairing_mode: str = "max_possible"
    fixed_pairs_per_reproduction: int | None = None
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
        if self.num_generations <= 0:
            raise ValueError("num_generations must be positive.")
        if self.num_steps <= 0:
            raise ValueError("num_steps must be positive.")
        if self.initial_population_size < 0:
            raise ValueError("initial_population_size must be non-negative.")
        if self.initial_population_size == 0 and self.initial_population is None and self.initialization_mode == "random":
            raise ValueError("random initialization requires initial_population_size to be positive.")
        max_random_strategies = _max_random_lookup_strategies(self.memory_depth)
        if self.initial_population is None:
            if self.initial_num_strategies <= 0:
                raise ValueError("initial_num_strategies must be positive.")
            if (
                self.initialization_mode == "random"
                and self.initial_num_strategies > self.initial_population_size
            ):
                raise ValueError(
                    "initial_num_strategies cannot exceed initial_population_size for random initialization."
                )
            if self.initial_num_strategies > max_random_strategies:
                raise ValueError(
                    f"initial_num_strategies exceeds the supported random DNA space ({max_random_strategies})."
                )
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
        if self.pairing_mode not in {"max_possible", "fixed"}:
            raise ValueError("pairing_mode must be 'max_possible' or 'fixed'.")
        if self.reproduction_interval <= 0:
            raise ValueError("reproduction_interval must be positive.")
        if self.checkpoint_interval < 0:
            raise ValueError("checkpoint_interval must be non-negative.")
        if self.offspring_per_pair <= 0:
            raise ValueError("offspring_per_pair must be positive.")
        if self.max_children_per_agent <= 0:
            raise ValueError("max_children_per_agent must be positive.")
        if self.allow_self_pairing is not None:
            self.allow_same_dna_pairing = self.allow_self_pairing
        if self.pairing_mode == "fixed":
            if self.fixed_pairs_per_reproduction is None:
                raise ValueError("fixed_pairs_per_reproduction must be set when pairing_mode is 'fixed'.")
            if self.fixed_pairs_per_reproduction <= 0:
                raise ValueError("fixed_pairs_per_reproduction must be positive when pairing_mode is 'fixed'.")
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
        if self.initial_population is not None:
            if any(count < 0 for count in self.initial_population.values()):
                raise ValueError("initial_population counts must be non-negative.")
            if sum(self.initial_population.values()) <= 0:
                raise ValueError("initial_population must contain at least one agent.")
        elif self.initialization_mode == "seeded":
            seeded_population = 0
            occupied_random_slots = 0
            if self.include_seeded_strategies:
                deterministic = baseline_dna_library()
                seeded_dnas = {
                    deterministic[name].to_string()
                    for name in self.seed_strategies
                }
                seeded_population += len(seeded_dnas) * self.seed_strategy_population
                occupied_random_slots = len(seeded_dnas & _random_lookup_space(self.memory_depth))
            seeded_population += self.random_strategy_mix * self.seed_strategy_population
            if seeded_population <= 0:
                raise ValueError(
                    "seeded initialization must produce at least one agent. "
                    "Enable seeded strategies or set random_strategy_mix > 0."
                )
            available_random_slots = max(0, max_random_strategies - occupied_random_slots)
            if self.random_strategy_mix > available_random_slots:
                raise ValueError(
                    "random_strategy_mix exceeds the remaining supported random DNA space "
                    f"({available_random_slots})."
                )

    @classmethod
    def from_json(cls, path: str | Path) -> "SimulationConfig":
        """Load simulation settings from a simulation JSON file."""
        data = _load_json_object(path)
        _require_config_keys(data, SIMULATION_JSON_KEYS, "SimulationConfig")
        return cls(**_filter_dataclass_kwargs(data, cls))

    def to_json(self, path: str | Path) -> None:
        """Persist configuration to a JSON file."""
        data = asdict(self)
        data.pop("allow_self_pairing", None)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
