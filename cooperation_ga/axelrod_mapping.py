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
        AxelrodStrategyMapping("Generous Tit For Tat", "GTFT", "PROBABILISTIC_LOOKUP", "exact", "Implemented and validated as the standard memory-one generous Tit For Tat variant."),
        AxelrodStrategyMapping("Two Tits For Tat", "TF2T", "LOOKUP", "exact", "A deterministic lookup table with memory depth 2."),
        AxelrodStrategyMapping("Alternator", "ALTERNATOR", "FSM", "exact", "Two-state alternating behavior is a finite state machine."),
        AxelrodStrategyMapping("Cycler CCD", "CYCLER_CCD", "FSM", "exact", "Implemented and validated as a three-state periodic FSM."),
        AxelrodStrategyMapping("Cycler CCCD", "CYCLER_CCCD", "FSM", "exact", "Implemented and validated as a four-state periodic FSM."),
        AxelrodStrategyMapping("Cycler CCCCD", "CYCLER_CCCCD", "FSM", "exact", "Five-state periodic cycle fits within the current 8-state FSM family."),
        AxelrodStrategyMapping("Go By Majority", "GO_BY_MAJORITY", "COUNT_BASED", "exact", "Decision depends on opponent cooperation/defection counts."),
        AxelrodStrategyMapping("Hard Go By Majority", "HARD_GO_BY_MAJORITY", "COUNT_BASED", "exact", "Count-based full-history threshold rule."),
        AxelrodStrategyMapping("Soft Go By Majority", "GO_BY_MAJORITY", "COUNT_BASED", "exact", "Uses the same canonical majority implementation as Go By Majority."),
        AxelrodStrategyMapping("Appeaser", "APPEASER", "FSM", "exact", "Toggle-on-defection behavior is representable as a small FSM."),
        AxelrodStrategyMapping("Prober", None, "FSM", "approximate", "Opening probe plus contingent mode switch needs richer scripted phases than current FSM payload."),
        AxelrodStrategyMapping("Nydegger", "NYDEGGER", "SCRIPTED", "exact", "Implemented as an exact scripted strategy using the documented three-outcome formula."),
        AxelrodStrategyMapping("Shubik", "SHUBIK", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with escalating retaliation length."),
        AxelrodStrategyMapping("Adaptive", None, "COUNT_BASED", "approximate", "Adaptive score-tracking behavior exceeds the current count-based payload."),
        AxelrodStrategyMapping("Adaptor", None, "PROBABILISTIC_LOOKUP", "approximate", "Internal floating state updates are richer than current fixed probabilistic lookup."),
        AxelrodStrategyMapping("APavlov2006", None, "FSM", "approximate", "Opponent classification and multi-mode switching need a richer state payload."),
        AxelrodStrategyMapping("APavlov2011", None, "FSM", "approximate", "Opponent classification and multi-mode switching need a richer state payload."),
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
        AxelrodStrategyMapping("SecondByGrofman", None, "COUNT_BASED", "approximate", "Windowed counting is close, but the exact three-phase logic is not fully encoded."),
    ]
