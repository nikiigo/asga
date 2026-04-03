"""Repeated Prisoner's Dilemma game logic."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from cooperation_ga.dna import COOPERATE, DEFECT
from cooperation_ga.strategy import IteratedStrategy, ParticipantSpec, apply_noise, make_strategy


@dataclass(frozen=True, slots=True)
class PayoffMatrix:
    """Payoff values for the Prisoner's Dilemma."""

    reward: int = 3
    temptation: int = 5
    punishment: int = 1
    sucker: int = 0

    def payoff(self, move_a: int, move_b: int) -> tuple[int, int]:
        """Return the payoff pair for a simultaneous action pair."""
        if move_a == COOPERATE and move_b == COOPERATE:
            return self.reward, self.reward
        if move_a == DEFECT and move_b == COOPERATE:
            return self.temptation, self.sucker
        if move_a == COOPERATE and move_b == DEFECT:
            return self.sucker, self.temptation
        return self.punishment, self.punishment


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Aggregate result of a repeated match."""

    score_a: int
    score_b: int
    coop_a: int
    coop_b: int
    defect_a: int
    defect_b: int
    rounds: int


def simulate_match(
    player_a: ParticipantSpec | IteratedStrategy,
    player_b: ParticipantSpec | IteratedStrategy,
    rounds: int,
    payoff_matrix: PayoffMatrix,
    noise_rate: float,
    rng: Random,
) -> MatchResult:
    """Simulate an iterated match between two strategies."""
    strategy_a = _coerce_strategy(player_a)
    strategy_b = _coerce_strategy(player_b)
    if hasattr(strategy_a, "configure_match"):
        strategy_a.configure_match(rounds, payoff_matrix)  # type: ignore[attr-defined]
    if hasattr(strategy_b, "configure_match"):
        strategy_b.configure_match(rounds, payoff_matrix)  # type: ignore[attr-defined]
    history_a: list[int] = []
    history_b: list[int] = []
    state_a = strategy_a.initial_state()
    state_b = strategy_b.initial_state()
    score_a = 0
    score_b = 0
    coop_a = 0
    coop_b = 0
    defect_a = 0
    defect_b = 0
    for _ in range(rounds):
        intended_a, state_a = strategy_a.next_move(history_a, history_b, rng, state_a)
        intended_b, state_b = strategy_b.next_move(history_b, history_a, rng, state_b)
        move_a = apply_noise(intended_a, noise_rate, rng)
        move_b = apply_noise(intended_b, noise_rate, rng)
        round_score_a, round_score_b = payoff_matrix.payoff(move_a, move_b)
        score_a += round_score_a
        score_b += round_score_b
        if move_a == COOPERATE:
            coop_a += 1
        else:
            defect_a += 1
        if move_b == COOPERATE:
            coop_b += 1
        else:
            defect_b += 1
        history_a.append(move_a)
        history_b.append(move_b)
    return MatchResult(score_a, score_b, coop_a, coop_b, defect_a, defect_b, rounds)


def _coerce_strategy(player: ParticipantSpec | IteratedStrategy) -> IteratedStrategy:
    """Instantiate a strategy if a participant spec is supplied."""
    return make_strategy(player) if isinstance(player, ParticipantSpec) else player
