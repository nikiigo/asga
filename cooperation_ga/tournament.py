"""Per-step interaction simulation for explicit agents."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from cooperation_ga.config import SimulationConfig
from cooperation_ga.game import MatchResult, PayoffMatrix, simulate_match
from cooperation_ga.population import Agent, Population
from cooperation_ga.strategy import DnaStrategy


@dataclass(frozen=True, slots=True)
class InteractionResult:
    """Aggregate result of one interaction step."""

    matches_played: int
    cooperation_rate: float
    defection_rate: float
    score_by_agent_id: dict[int, float]
    pairwise_scores: list[tuple[int, int, MatchResult]]


def run_interactions(
    population: Population,
    config: SimulationConfig,
    rng: Random,
) -> InteractionResult:
    """Pair agents randomly without replacement and run one match per paired agent."""
    payoff = PayoffMatrix(
        reward=config.payoff_R,
        temptation=config.payoff_T,
        punishment=config.payoff_P,
        sucker=config.payoff_S,
    )
    agents = list(population.agents)
    rng.shuffle(agents)
    total_coop = 0
    total_defect = 0
    score_by_agent_id = {agent.id: 0.0 for agent in population.agents}
    pairwise_scores: list[tuple[int, int, MatchResult]] = []
    matches_played = 0

    def record_match(agent_a: Agent, agent_b: Agent) -> None:
        nonlocal total_coop, total_defect, matches_played
        match = simulate_match(
            DnaStrategy(agent_a.dna),
            DnaStrategy(agent_b.dna),
            config.rounds_per_match,
            payoff,
            config.noise_rate,
            rng,
        )
        score_by_agent_id[agent_a.id] += match.score_a
        score_by_agent_id[agent_b.id] += match.score_b
        total_coop += match.coop_a + match.coop_b
        total_defect += match.defect_a + match.defect_b
        pairwise_scores.append((agent_a.id, agent_b.id, match))
        matches_played += 1

    if len(agents) == 1 and (config.self_play or config.odd_agent_mode == "self_play"):
        record_match(agents[0], agents[0])
    else:
        limit = len(agents) - 1
        for index in range(0, limit, 2):
            record_match(agents[index], agents[index + 1])
        if len(agents) % 2 == 1 and config.odd_agent_mode == "random_opponent" and len(agents) > 1:
            leftover = agents[-1]
            opponent = rng.choice(agents[:-1])
            record_match(leftover, opponent)

    total_actions = total_coop + total_defect
    return InteractionResult(
        matches_played=matches_played,
        cooperation_rate=(total_coop / total_actions if total_actions else 0.0),
        defection_rate=(total_defect / total_actions if total_actions else 0.0),
        score_by_agent_id=score_by_agent_id,
        pairwise_scores=pairwise_scores,
    )
