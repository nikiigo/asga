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
        AxelrodStrategyMapping("AdaptorBrief", "ADAPTOR_BRIEF", "SCRIPTED", "exact", "Implemented as an exact stochastic state-update strategy with the Hauert short-interaction parameters."),
        AxelrodStrategyMapping("AdaptorLong", "ADAPTOR_LONG", "SCRIPTED", "exact", "Implemented as an exact stochastic state-update strategy with the Hauert long-interaction parameters."),
        AxelrodStrategyMapping("APavlov2006", "APAVLOV2006", "SCRIPTED", "exact", "Implemented as an exact scripted classifier strategy with six-turn reclassification."),
        AxelrodStrategyMapping("APavlov2011", "APAVLOV2011", "SCRIPTED", "exact", "Implemented as an exact scripted classifier strategy with six-turn reclassification."),
        AxelrodStrategyMapping("Champion", "CHAMPION", "SCRIPTED", "exact", "Implemented exactly as a phased scripted strategy with a stochastic post-turn-25 rule."),
        AxelrodStrategyMapping("Tullock", "TULLOCK", "SCRIPTED", "exact", "Implemented exactly as a ten-round-window stochastic strategy after the opening phase."),
        AxelrodStrategyMapping("ANN", None, "NN", "exact", "The NN family now encodes the Axelrod ANN architecture exactly: 17 features, one ReLU hidden layer, and a signed output score."),
        AxelrodStrategyMapping("EvolvedANN", "EVOLVED_ANN", "NN", "exact", "Exact pretrained ANN encoded directly as an NN genome."),
        AxelrodStrategyMapping("EvolvedANN5", "EVOLVED_ANN5", "NN", "exact", "Exact pretrained ANN with hidden size 5 encoded directly as an NN genome."),
        AxelrodStrategyMapping("EvolvedANNNoise05", "EVOLVED_ANN_NOISE05", "NN", "exact", "Exact pretrained ANN trained with noise 0.05 encoded directly as an NN genome."),
        AxelrodStrategyMapping("EvolvedAttention", None, "ATTENTION", "unsupported", "Transformer-like model weights and inference are not implemented."),
        AxelrodStrategyMapping("FirstByTidemanAndChieruzzi", "FIRST_BY_TIDEMAN_AND_CHIERUZZI", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with escalating punishment, fresh starts, and match-end defections."),
        AxelrodStrategyMapping("FirstByShubik", "SHUBIK", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with escalating retaliation length."),
        AxelrodStrategyMapping("FirstBySteinAndRapoport", "FIRST_BY_STEIN_AND_RAPOPORT", "SCRIPTED", "exact", "Implemented as an exact scripted strategy with periodic randomness checks and final-two-turn defections."),
        AxelrodStrategyMapping("SecondByChampion", "CHAMPION", "SCRIPTED", "exact", "Uses the same canonical implementation as Champion."),
        AxelrodStrategyMapping("SecondByGrofman", "SECOND_BY_GROFMAN", "SCRIPTED", "exact", "Implemented as an exact scripted three-phase strategy with the original seven-of-eight-round lookback rule."),
    ]
