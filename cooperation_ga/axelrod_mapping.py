"""Compatibility mapping between Axelrod strategies and local DNA families."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AxelrodStrategyMapping:
    """Describe how an Axelrod strategy relates to the local DNA families."""

    axelrod_name: str
    shortname: str | None
    dna_family: str
    support_level: str
    rationale: str


def axelrod_strategy_mappings() -> list[AxelrodStrategyMapping]:
    """Return the current compatibility map for selected Axelrod strategies."""
    return [
        AxelrodStrategyMapping("Cooperator", "ALLC", "LOOKUP", "exact", "Always cooperate is a deterministic lookup rule."),
        AxelrodStrategyMapping("Defector", "ALLD", "LOOKUP", "exact", "Always defect is a deterministic lookup rule."),
        AxelrodStrategyMapping("Tit For Tat", "TFT", "LOOKUP", "exact", "Memory-1 deterministic response table."),
        AxelrodStrategyMapping("Suspicious Tit For Tat", "SUSPICIOUS_TFT", "LOOKUP", "exact", "Implemented and validated as a lookup-table variant of Tit For Tat."),
        AxelrodStrategyMapping("Win-Stay Lose-Shift", "PAVLOV", "LOOKUP", "exact", "Pavlov is a memory-1 deterministic lookup strategy."),
        AxelrodStrategyMapping("Grudger", "GRUDGER", "TRIGGER", "exact", "Grudger is a trigger rule: cooperate until any opponent defection, then defect forever."),
        AxelrodStrategyMapping("Grim Trigger", "GRUDGER", "TRIGGER", "exact", "Uses the same canonical trigger implementation as Grudger."),
        AxelrodStrategyMapping("Random", "RANDOM", "PROBABILISTIC_LOOKUP", "exact", "Implemented and validated as a constant probabilistic lookup."),
        AxelrodStrategyMapping("Joss", "JOSS", "PROBABILISTIC_LOOKUP", "exact", "Memory-1 probabilistic lookup with C after C at p=0.9 and D after D."),
        AxelrodStrategyMapping("Generous Tit For Tat", "GTFT", "PROBABILISTIC_LOOKUP", "exact", "Exact for the default payoff matrix (R=3, P=1, S=0, T=5); Axelrod's reference implementation derives p from the active game payoffs."),
        AxelrodStrategyMapping("Tit For 2 Tats", "TF2T", "LOOKUP", "exact", "A deterministic lookup table with memory depth 2."),
        AxelrodStrategyMapping("Alternator", "ALTERNATOR", "FSM", "exact", "Two-state alternating behavior is a finite state machine."),
        AxelrodStrategyMapping("Cycler CCD", "CYCLER_CCD", "FSM", "exact", "Implemented and validated as a three-state periodic FSM."),
        AxelrodStrategyMapping("Cycler CCCD", "CYCLER_CCCD", "FSM", "exact", "Implemented and validated as a four-state periodic FSM."),
        AxelrodStrategyMapping("Cycler CCCCCD", "CYCLER_CCCCCD", "SCRIPTED", "exact", "Implemented and validated as an exact periodic scripted strategy."),
        AxelrodStrategyMapping("Go By Majority", "GO_BY_MAJORITY", "COUNT_BASED", "exact", "Decision depends on opponent cooperation/defection counts."),
        AxelrodStrategyMapping("Hard Go By Majority", "HARD_GO_BY_MAJORITY", "COUNT_BASED", "exact", "Count-based full-history threshold rule."),
        AxelrodStrategyMapping("Soft Go By Majority", "GO_BY_MAJORITY", "COUNT_BASED", "exact", "Uses the same canonical majority implementation as Go By Majority."),
        AxelrodStrategyMapping("Appeaser", "APPEASER", "FSM", "exact", "Toggle-on-defection behavior is representable as a small FSM."),
        AxelrodStrategyMapping("Prober", "PROBER", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with the D,C,C opening and contingent forever-defect/TFT mode switch."),
        AxelrodStrategyMapping("Nydegger", "NYDEGGER", "SCRIPTED", "exact", "Implemented as an exact scripted strategy using the documented three-outcome formula."),
        AxelrodStrategyMapping("Shubik", "SHUBIK", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with escalating retaliation length."),
        AxelrodStrategyMapping("Adaptive", "ADAPTIVE", "SCRIPTED", "exact", "Exact under the default payoff matrix (R=3, P=1, S=0, T=5); the reference implementation scores outcomes from the active game object."),
        AxelrodStrategyMapping("Adaptor", None, "SCRIPTED", "approximate", "Axelrod exposes AdaptorBrief and AdaptorLong as exact variants; there is no single exact canonical Adaptor class to map here."),
        AxelrodStrategyMapping("AdaptorBrief", "ADAPTOR_BRIEF", "SCRIPTED", "exact", "Implemented as an exact stochastic state-update strategy with the Hauert short-interaction parameters."),
        AxelrodStrategyMapping("AdaptorLong", "ADAPTOR_LONG", "SCRIPTED", "exact", "Implemented as an exact stochastic state-update strategy with the Hauert long-interaction parameters."),
        AxelrodStrategyMapping("APavlov2006", "APAVLOV2006", "SCRIPTED", "exact", "Implemented as an exact scripted classifier strategy with six-turn reclassification."),
        AxelrodStrategyMapping("APavlov2011", "APAVLOV2011", "SCRIPTED", "exact", "Implemented as an exact scripted classifier strategy with six-turn reclassification."),
        AxelrodStrategyMapping("Champion", "CHAMPION", "SCRIPTED", "exact", "Implemented exactly as a phased scripted strategy with a stochastic post-turn-25 rule."),
        AxelrodStrategyMapping("Tullock", "TULLOCK", "SCRIPTED", "exact", "Implemented exactly as a ten-round-window stochastic strategy after the opening phase."),
        AxelrodStrategyMapping("ANN", None, "NN", "unsupported", "Neural-network weights and feature extraction are outside the current DNA families."),
        AxelrodStrategyMapping("EvolvedANN", None, "NN", "unsupported", "Neural-network genome family is not implemented."),
        AxelrodStrategyMapping("EvolvedANN5", None, "NN", "unsupported", "Neural-network genome family is not implemented."),
        AxelrodStrategyMapping("EvolvedANNNoise05", None, "NN", "unsupported", "Neural-network genome family is not implemented."),
        AxelrodStrategyMapping("EvolvedAttention", None, "ATTENTION", "unsupported", "Transformer-like model weights and inference are not implemented."),
        AxelrodStrategyMapping("FirstByTidemanAndChieruzzi", None, "SCRIPTED", "unsupported", "Complex phased control flow and tournament-end logic are not implemented."),
        AxelrodStrategyMapping("FirstByShubik", "SHUBIK", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with escalating retaliation length."),
        AxelrodStrategyMapping("FirstBySteinAndRapoport", None, "SCRIPTED", "unsupported", "Periodic statistical tests and endgame logic exceed current DNA families."),
        AxelrodStrategyMapping("SecondByChampion", None, "SCRIPTED", "unsupported", "Phased scripted openings plus conditional random behavior are not yet encoded."),
        AxelrodStrategyMapping("SecondByGrofman", "SECOND_BY_GROFMAN", "SCRIPTED", "exact", "Implemented as an exact scripted three-phase strategy with the original seven-of-eight-round lookback rule."),
    ]
