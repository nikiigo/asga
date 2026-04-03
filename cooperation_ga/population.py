"""Population storage and initialization for explicit agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from cooperation_ga.config import SimulationConfig
from cooperation_ga.dna import StrategyDNA, baseline_dna_library


@dataclass(slots=True)
class Agent:
    """One explicit individual in the population."""

    id: int
    dna: StrategyDNA
    score: float = 0.0
    age: int = 0
    children_count: int = 0


@dataclass(slots=True)
class Population:
    """Collection of explicit agents."""

    agents: list[Agent] = field(default_factory=list)
    next_agent_id: int = 0

    def total_size(self) -> int:
        """Return total population size."""
        return len(self.agents)

    def active_strategies(self) -> list[StrategyDNA]:
        """Return active DNA types."""
        return list(self.dna_counts().keys())

    def dna_counts(self) -> dict[StrategyDNA, int]:
        """Aggregate agents by DNA for reporting."""
        counts: dict[StrategyDNA, int] = {}
        for agent in self.agents:
            counts[agent.dna] = counts.get(agent.dna, 0) + 1
        return counts

    def remove_agent_ids(self, ids_to_remove: set[int]) -> None:
        """Remove agents by id."""
        self.agents = [agent for agent in self.agents if agent.id not in ids_to_remove]

    def reset_scores(self) -> None:
        """Reset all scores to zero."""
        for agent in self.agents:
            agent.score = 0.0

    def increment_age(self) -> None:
        """Increment age for all surviving agents."""
        for agent in self.agents:
            agent.age += 1

    def spawn_agent(
        self,
        dna: StrategyDNA,
        score: float = 0.0,
        age: int = 0,
        children_count: int = 0,
    ) -> Agent:
        """Create a new agent with a unique id."""
        agent = Agent(
            id=self.next_agent_id,
            dna=dna,
            score=score,
            age=age,
            children_count=children_count,
        )
        self.next_agent_id += 1
        return agent

    def add_offspring(self, dnas: list[StrategyDNA]) -> None:
        """Add newborn agents to the population."""
        for dna in dnas:
            self.agents.append(self.spawn_agent(dna=dna, score=0.0, age=0))

    def normalize_total(self, target_size: int, rng: Random, selection_epsilon: float) -> None:
        """Downsample or upsample the explicit population to a target size."""
        current_total = self.total_size()
        if target_size == current_total:
            return
        if target_size <= 0:
            self.agents = []
            return
        if current_total == 0:
            return
        if current_total > target_size:
            self.agents = _weighted_sample_without_replacement(
                self.agents,
                target_size,
                rng,
                selection_epsilon,
            )
            return
        dnas = [agent.dna for agent in self.agents]
        for _ in range(target_size - current_total):
            self.agents.append(self.spawn_agent(dna=rng.choice(dnas), score=0.0, age=0))

    @classmethod
    def random_initial(cls, config: SimulationConfig, rng: Random) -> "Population":
        """Create an initial population using random DNA."""
        if config.initial_population is not None:
            return cls.from_mapping(config.initial_population)
        strategies: list[StrategyDNA] = []
        seen: set[StrategyDNA] = set()
        while len(strategies) < config.initial_num_strategies:
            dna = StrategyDNA.random(config.memory_depth, rng)
            if dna not in seen:
                seen.add(dna)
                strategies.append(dna)
        population = cls()
        for _ in range(config.initial_population_size):
            population.agents.append(population.spawn_agent(rng.choice(strategies)))
        return population

    @classmethod
    def seeded_initial(cls, config: SimulationConfig, rng: Random) -> "Population":
        """Create an initial population from deterministic baseline DNA plus random DNA."""
        if config.initial_population is not None:
            return cls.from_mapping(config.initial_population)
        deterministic = baseline_dna_library()
        population = cls()
        seen: set[StrategyDNA] = set()
        if config.include_seeded_strategies:
            for name in config.seed_strategies:
                dna = deterministic[name]
                if dna in seen:
                    continue
                seen.add(dna)
                for _ in range(config.seed_strategy_population):
                    population.agents.append(population.spawn_agent(dna))
        target_unique = len(seen) + config.random_strategy_mix
        while len(seen) < target_unique:
            dna = StrategyDNA.random(config.memory_depth, rng)
            if dna in seen:
                continue
            seen.add(dna)
            for _ in range(config.seed_strategy_population):
                population.agents.append(population.spawn_agent(dna))
        return population

    @classmethod
    def from_mapping(
        cls,
        initial_population: dict[str, int],
    ) -> "Population":
        """Create a population from an explicit DNA-compatible mapping."""
        population = cls()
        for key, count in initial_population.items():
            dna = _parse_initial_population_key(key)
            for _ in range(count):
                population.agents.append(population.spawn_agent(dna))
        return population


def _parse_initial_population_key(key: str) -> StrategyDNA:
    """Parse an initial-population key into DNA."""
    deterministic = baseline_dna_library()
    if key in deterministic:
        return deterministic[key]
    dna_key = key.removeprefix("DNA:")
    if len(dna_key) == 5 and set(dna_key).issubset({"C", "D", "R"}):
        return StrategyDNA.from_action_string(dna_key)
    if set(dna_key).issubset({"0", "1"}):
        return StrategyDNA.from_string(dna_key)
    raise ValueError(f"Unsupported initial_population key for agent model: {key}")


def _weighted_sample_without_replacement(
    agents: list[Agent],
    k: int,
    rng: Random,
    selection_epsilon: float,
) -> list[Agent]:
    """Sample agents without replacement, biasing toward higher scores."""
    pool = list(agents)
    chosen: list[Agent] = []
    while pool and len(chosen) < k:
        min_score = min(agent.score for agent in pool)
        weights = [agent.score - min_score + selection_epsilon for agent in pool]
        total = sum(weights)
        threshold = rng.random() * total
        cumulative = 0.0
        index = len(pool) - 1
        for idx, weight in enumerate(weights):
            cumulative += weight
            if threshold <= cumulative:
                index = idx
                break
        chosen.append(pool.pop(index))
    return chosen
