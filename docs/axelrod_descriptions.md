# Axelrod Descriptions

This document lines up the Axelrod strategy names with the local implementation names used in this project, and describes them in plain language.

Scope:

- the `Axelrod description` column is a short plain-language summary of the reference strategy
- the `Local description` column says how the same behavior is represented in this project
- only one mapped strategy is still unsupported: `EvolvedAttention`

Reference:

- compatibility map: [axelrod_strategy_mapping.md](axelrod_strategy_mapping.md)
- local strategy catalog: [implemented_strategies.md](implemented_strategies.md)

## Deterministic Lookup

| Axelrod strategy | Local shortname | Axelrod description | Local description |
| --- | --- | --- | --- |
| `Cooperator` | `ALLC` | Always cooperates. | Exact lookup-table DNA that always returns cooperation. |
| `Defector` | `ALLD` | Always defects. | Exact lookup-table DNA that always returns defection. |
| `Tit For Tat` | `TFT` | Starts with cooperation, then copies the opponent's previous move. | Exact memory-1 lookup-table DNA with shorthand `CCDCD`. |
| `Suspicious Tit For Tat` | `SUSPICIOUS_TFT` | Like Tit For Tat, but opens with defection. | Exact memory-1 lookup-table DNA with a suspicious first move. |
| `Tit For 2 Tats` | `TF2T` | Cooperates until the opponent defects twice in a row. | Exact memory-2 lookup-table DNA. |
| `Win-Stay Lose-Shift` | `PAVLOV` | Repeats the last move after a good result and switches after a bad result. | Exact memory-1 lookup-table DNA with shorthand `CCDDC`. |

## Probabilistic Lookup

| Axelrod strategy | Local shortname | Axelrod description | Local description |
| --- | --- | --- | --- |
| `Random` | `RANDOM` | Chooses cooperation or defection randomly with a fixed probability. | Exact probabilistic lookup DNA with constant `p(C) = 0.5`. |
| `Joss` | `JOSS` | Mostly behaves like Tit For Tat, but occasionally defects after cooperation. | Exact probabilistic lookup DNA with the Axelrod `Joss` probabilities. |
| `Generous Tit For Tat` | `GTFT` | Like Tit For Tat, but sometimes forgives a defection instead of retaliating. | Exact probabilistic lookup DNA for the default payoff matrix `(R=3, P=1, S=0, T=5)`. |

## Trigger And Count-Based

| Axelrod strategy | Local shortname | Axelrod description | Local description |
| --- | --- | --- | --- |
| `Grudger` | `GRUDGER` | Cooperates until the opponent defects once, then defects forever. | Exact trigger DNA. |
| `Grim Trigger` | `GRUDGER` | Same basic behavior as Grudger: one betrayal triggers permanent defection. | Uses the same canonical trigger DNA as `GRUDGER`. |
| `Go By Majority` | `GO_BY_MAJORITY` | Cooperates if the opponent has cooperated often enough in the observed history. | Exact count-based DNA using a majority threshold. |
| `Soft Go By Majority` | `GO_BY_MAJORITY` | The softer majority-rule version. | Uses the same canonical local implementation as `GO_BY_MAJORITY`. |
| `Hard Go By Majority` | `HARD_GO_BY_MAJORITY` | Requires a stricter cooperation record before it cooperates. | Exact count-based DNA with the hard-threshold rule. |

## Finite State Machine

| Axelrod strategy | Local shortname | Axelrod description | Local description |
| --- | --- | --- | --- |
| `Alternator` | `ALTERNATOR` | Alternates between cooperation and defection each turn. | Exact 2-state FSM DNA. |
| `Cycler CCD` | `CYCLER_CCD` | Repeats the pattern cooperate, cooperate, defect. | Exact 3-state FSM DNA. |
| `Cycler CCCD` | `CYCLER_CCCD` | Repeats the pattern cooperate, cooperate, cooperate, defect. | Exact 4-state FSM DNA. |
| `Appeaser` | `APPEASER` | Cooperates while things are calm, punishes after defection, then settles back. | Exact FSM DNA with a short punitive phase. |

## Scripted Exact Strategies

| Axelrod strategy | Local shortname | Axelrod description | Local description |
| --- | --- | --- | --- |
| `Cycler CCCCCD` | `CYCLER_CCCCCD` | Repeats five cooperations followed by one defection. | Exact scripted periodic strategy. |
| `Prober` | `PROBER` | Opens with `D,C,C`, then either exploits naive cooperators or falls back to Tit For Tat. | Exact scripted strategy with the same opening and branch logic. |
| `Nydegger` | `NYDEGGER` | Uses a specific coded formula over recent outcomes to decide retaliation. | Exact scripted implementation of that formula. |
| `Shubik` | `SHUBIK` | Uses retaliation runs that grow longer after repeated betrayals. | Exact scripted escalating-punishment strategy. |
| `FirstByShubik` | `SHUBIK` | Axelrod first-tournament naming for Shubik's strategy. | Uses the same canonical `SHUBIK` implementation. |
| `Adaptive` | `ADAPTIVE` | Tries both cooperation and defection, tracks which has scored better, then prefers the better-performing action. | Exact scripted strategy under the default payoff matrix. |
| `AdaptorBrief` | `ADAPTOR_BRIEF` | Maintains a continuous internal state and converts it to a cooperation probability for short interactions. | Exact scripted stochastic state-update strategy with the short-run parameters. |
| `AdaptorLong` | `ADAPTOR_LONG` | Same idea as `AdaptorBrief`, but tuned for long interactions. | Exact scripted stochastic state-update strategy with the long-run parameters. |
| `APavlov2006` | `APAVLOV2006` | Classifies opponents over six-turn blocks, then changes policy based on the detected class. | Exact scripted classifier strategy. |
| `APavlov2011` | `APAVLOV2011` | Updated Adaptive Pavlov classifier with a slightly different response policy. | Exact scripted classifier strategy. |
| `Champion` | `CHAMPION` | Uses phased behavior, then later switches into a stochastic rule. | Exact scripted phased strategy. |
| `SecondByChampion` | `CHAMPION` | Axelrod second-tournament naming for Champion's strategy. | Uses the same canonical `CHAMPION` implementation. |
| `Tullock` | `TULLOCK` | Starts cooperatively, then reacts to the opponent's recent cooperation rate over a window. | Exact scripted ten-round-window stochastic strategy. |
| `SecondByGrofman` | `SECOND_BY_GROFMAN` | Uses a phased rule and then a conditional decision based on the earlier seven of the last eight rounds. | Exact scripted three-phase strategy. |
| `FirstBySteinAndRapoport` | `FIRST_BY_STEIN_AND_RAPOPORT` | Starts cooperatively, plays TFT, periodically checks whether the opponent looks random, and defects at the end of the match. | Exact scripted implementation with the same randomness checks and final-two-turn defections. |
| `FirstByTidemanAndChieruzzi` | `FIRST_BY_TIDEMAN_AND_CHIERUZZI` | Escalates punishment, tracks score advantage, may grant a fresh start, and defects in the final two turns. | Exact scripted implementation of the same logic. |

## Neural Strategies

| Axelrod strategy | Local shortname | Axelrod description | Local description |
| --- | --- | --- | --- |
| `ANN` |  | Neural-network strategy using the Axelrod ANN architecture. | Supported by the local `NN` DNA family architecture. |
| `EvolvedANN` | `EVOLVED_ANN` | Pretrained ANN-based strategy from the Axelrod library. | Exact NN genome loaded from bundled Axelrod ANN weights. |
| `EvolvedANN5` | `EVOLVED_ANN5` | Pretrained ANN variant with hidden size 5. | Exact NN genome loaded from bundled Axelrod ANN weights. |
| `EvolvedANNNoise05` | `EVOLVED_ANN_NOISE05` | Pretrained ANN variant evolved under 0.05 noise. | Exact NN genome loaded from bundled Axelrod ANN weights. |
| `EvolvedAttention` |  | Attention-based sequence model strategy. | Unsupported; the project does not yet have an `ATTENTION` DNA family. |
