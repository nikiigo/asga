# Implemented Strategies

This document describes every baseline strategy currently implemented in the project in plain language.

Scope:

- these are the strategies defined in `baseline_dna_library()`
- all of them are encoded as DNA and can be used directly in simulations
- the baseline registry uses canonical names only: one raw DNA maps to one strategy name
- when an action gene is `RANDOM`, the relevant DNA family also stores a random-action cooperation probability used to resolve that gene at runtime

Reference:

- code source: [dna.py](../cooperation_ga/dna.py)
- Axelrod compatibility map: [axelrod_strategy_mapping.md](axelrod_strategy_mapping.md)

## Deterministic Lookup Strategies

These strategies choose their action from a fixed response table.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `ALLC` | `LOOKUP` | Yes | `00100000000000000001010000011000000000000000` | Always cooperates. It starts with cooperation and keeps cooperating no matter what the opponent does. |
| `ALLD` | `LOOKUP` | Yes | `00100000000000000001010001011000000001010101` | Always defects. It starts by defecting and never switches to cooperation. |
| `TFT` | `LOOKUP` | Yes | `00100000000000000001010000011000000000010001` | Tit For Tat. It starts by cooperating, then copies the opponent's last move. |
| `TF2T` | `LOOKUP` | Yes | `00100000000000000010110000101000000000000000000100010000000000010001` | Tit For 2 Tats. It starts cooperatively and defects only after two consecutive opponent defections, making it more forgiving than TFT. |
| `PAVLOV` | `LOOKUP` | Yes | `00100000000000000001010000011000000000010100` | Win-Stay Lose-Shift. It repeats behavior after a good outcome and switches after a bad one, so it can recover from accidental mutual defection. |
| `SUSPICIOUS_TFT` | `LOOKUP` | Yes | `00100000000000000001010001011000000000010001` | A suspicious Tit For Tat variant. It opens with defection, then mirrors the opponent after that. |
| `SUSPICIOUS_PAVLOV` | `LOOKUP` | Yes | `00100000000000000001010001011000000000010100` | Pavlov with a suspicious opening. It starts by defecting, then follows the Pavlov response rule afterward. |
| `REVERSE_TFT` | `LOOKUP` | No | `00100000000000000001010000011000000001010001` | Reverse Tit For Tat. It tends to do the opposite of the cooperative part of TFT, punishing even cooperative situations. |
| `FORGIVER` | `LOOKUP` | Yes | `00100000000000000001010000011000000000000001` | Mostly cooperative. It cooperates in every memory-1 state except persistent mutual defection, where it defects. |
| `DEFENSIVE` | `LOOKUP` | Yes | `00100000000000000001010001011000000001010100` | Mostly defensive. It defects by default and only softens after mutual defection. |
| `HARD_REVENGER` | `LOOKUP` | No | `00100000000000000001010000011000000001010101` | Starts cooperatively but defects in every remembered state after that. It is effectively a harsh one-step revenger. |
| `TESTER` | `LOOKUP` | Yes | `00100000000000000001010001011000000000000100` | A probe-like heuristic. It opens with defection, then tries to cooperate in some cases to see whether cooperation can be restored. |

## Probabilistic Lookup Strategies

These strategies use encoded cooperation probabilities rather than fully deterministic responses.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `RANDOM` | `PROBABILISTIC_LOOKUP` | No | `001000110000000000101010100000000110000000100000001000000010000000` | Pure random play with about a 50% chance to cooperate on every move, regardless of history. |
| `JOSS` | `PROBABILISTIC_LOOKUP` | Yes | `001000110000000000101010111111110111100110000000001110011000000000` | Joss behaves like Tit For Tat most of the time, but sometimes defects even after opponent cooperation. |
| `GTFT` | `PROBABILISTIC_LOOKUP` | Yes | `001000110000000000101010111111110111111111010101011111111101010101` | Generous Tit For Tat. It starts cooperatively and often forgives defections instead of retaliating every time. |

## Trigger Strategies

These strategies cooperate until a trigger condition is met, then switch into punishment behavior.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `GRUDGER` | `TRIGGER` | No | `00100001000000000001101000000101010000000010000000` | Cooperates until the opponent defects, then defects forever. This is also the canonical implementation used for Grim Trigger behavior. |
| `SHUBIK_COUNTER` | `COUNTER_TRIGGER` | No | `00100110000000000010110000000101010000000100000001111111111010000000` | A counter-based trigger strategy. It cooperates until betrayed, then retaliates for a punish period that can grow over time. |

## Finite State Machine Strategies

These strategies carry an internal state and transition between states based on the opponent's last move.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `ALTERNATOR` | `FSM` | Yes | `001001000000000000100100000010001000000001001010010000000000` | Alternates between cooperation and defection every turn. |
| `CYCLER_CCD` | `FSM` | No | `0010010000000000001011100001000010000000000010000101010010100000000000` | Repeats a three-turn pattern: cooperate, cooperate, defect. |
| `CYCLER_CCCD` | `FSM` | No | `00100100000000000011100000011000100000000000100001000100001001011010110000000000` | Repeats a four-turn pattern: cooperate, cooperate, cooperate, defect. |
| `CYCLER_CCCCD` | `FSM` | No | `001001000000000001000010001000001000000000001000010001000010000110001101100011000000000000` | Repeats a five-turn pattern: cooperate, cooperate, cooperate, cooperate, defect. |
| `SUSPICIOUS_ALTERNATOR` | `FSM` | No | `001001000000000000100100010010001000000000001000010100001000` | Alternator with a suspicious first move. It opens by defecting and then alternates. |
| `APPEASER` | `FSM` | No | `001001000000000000100100000010001000000000000010010100100000` | Cooperates while things are peaceful. After being hit by a defection it moves into a punitive phase, then returns to cooperation. |
| `PROBER_LIKE` | `FSM` | No | `001001000000000000100100010010001000000000001000010000100001` | A project-local finite-state probing strategy. It starts suspiciously and then settles into a cooperative state after probing. |

## Count-Based Strategies

These strategies summarize recent opponent behavior and compare it to a threshold.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `GO_BY_MAJORITY` | `COUNT_BASED` | No | `001000100000000000011110000000000010000000011010000000` | Cooperates when the opponent has cooperated at least about half the time over the full history. This is also the canonical implementation used for Soft Go By Majority behavior. |
| `HARD_GO_BY_MAJORITY` | `COUNT_BASED` | No | `001000100000000000011110010000000010000001011010000000` | Requires a stricter-than-half cooperation rate before it cooperates. |
| `GO_BY_MAJORITY_5` | `COUNT_BASED` | No | `001000100000000000011110000000010110000000011010000000` | Majority rule over the last 5 rounds instead of full history. |
| `GO_BY_MAJORITY_10` | `COUNT_BASED` | No | `001000100000000000011110000000101010000000011010000000` | Majority rule over the last 10 rounds. |
| `GO_BY_MAJORITY_20` | `COUNT_BASED` | No | `001000100000000000011110000001010010000000011010000000` | Majority rule over the last 20 rounds. |
| `GO_BY_MAJORITY_40` | `COUNT_BASED` | No | `001000100000000000011110000010100010000000011010000000` | Majority rule over the last 40 rounds. |
| `HARD_GO_BY_MAJORITY_5` | `COUNT_BASED` | No | `001000100000000000011110010000010110000001011010000000` | Hard majority rule over the last 5 rounds. |
| `HARD_GO_BY_MAJORITY_10` | `COUNT_BASED` | No | `001000100000000000011110010000101010000001011010000000` | Hard majority rule over the last 10 rounds. |
| `HARD_GO_BY_MAJORITY_20` | `COUNT_BASED` | No | `001000100000000000011110010001010010000001011010000000` | Hard majority rule over the last 20 rounds. |
| `HARD_GO_BY_MAJORITY_40` | `COUNT_BASED` | No | `001000100000000000011110010010100010000001011010000000` | Hard majority rule over the last 40 rounds. |

## Scripted Exact Strategies

These use named algorithm implementations rather than only a direct lookup table.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `NYDEGGER` | `SCRIPTED` | Yes | `00100101000000000010000000000000000000000000000000000000` | Exact Nydegger strategy. It uses a specific documented formula over recent outcomes to decide when to retaliate. |
| `SHUBIK` | `SCRIPTED` | Yes | `00100101000000000010000000000001000000000000000000000000` | Exact Shubik strategy. It escalates retaliation length after repeated betrayals. |
| `CHAMPION` | `SCRIPTED` | No | `00100101000000000010000000000010000000000000000000000000` | Exact Champion strategy. It follows a phased decision process and later mixes in stochastic behavior. |
| `TULLOCK` | `SCRIPTED` | No | `00100101000000000010000000000011000000000000000000000000` | Exact Tullock strategy. It starts cooperatively, then adapts based on the opponent's recent cooperation rate. |
| `CYCLER_CCCCCD` | `SCRIPTED` | No | `00100101000000000010000000000100000000000000000000000000` | Exact periodic cycle: cooperate five times, then defect once, and repeat. |
| `PROBER` | `SCRIPTED` | No | `00100101000000000010000000000101000000000000000000000000` | Exact Prober strategy. It opens with D,C,C, then either defects forever against naive opponents or falls back to Tit For Tat. |
| `ADAPTIVE` | `SCRIPTED` | No | `00100101000000000010000000000110000000000000000000000000` | Exact Adaptive strategy under the default payoff matrix. It plays a fixed opening, tracks how well cooperation and defection have scored, and then chooses the better-performing action. |
| `APAVLOV2006` | `SCRIPTED` | No | `00100101000000000010000000000111000000000000000000000000` | Exact Adaptive Pavlov 2006. It classifies the opponent in six-turn blocks and then switches to a response policy tailored to that class. |
| `APAVLOV2011` | `SCRIPTED` | No | `00100101000000000010000000001000000000000000000000000000` | Exact Adaptive Pavlov 2011. It classifies opponents in six-turn blocks and then uses TFT, TFTT, or pure defection depending on the detected class. |
| `SECOND_BY_GROFMAN` | `SCRIPTED` | No | `00100101000000000010000000001001000000000000000000000000` | Exact SecondByGrofman. It cooperates twice, mirrors for several rounds, then uses a conditional rule over the earlier seven of the last eight opponent moves. |
| `ADAPTOR_BRIEF` | `SCRIPTED` | No | `00100101000000000010000000001010000000000000000000000000` | Exact AdaptorBrief. It updates a continuous internal state after each round and converts that state into a stochastic cooperation probability tuned for short interactions. |
| `ADAPTOR_LONG` | `SCRIPTED` | No | `00100101000000000010000000001011000000000000000000000000` | Exact AdaptorLong. It uses the same state-update design as AdaptorBrief but with parameters tuned for long interactions. |
| `FIRST_BY_STEIN_AND_RAPOPORT` | `SCRIPTED` | No | `00100101000000000010000000001100000000000000000000000000` | Exact FirstBySteinAndRapoport. It opens cooperatively, plays TFT, periodically tests whether the opponent looks random, and defects on the final two turns. |
| `FIRST_BY_TIDEMAN_AND_CHIERUZZI` | `SCRIPTED` | No | `00100101000000000010000000001101000000000000000000000000` | Exact FirstByTidemanAndChieruzzi. It escalates punishment runs, tracks score advantage, can grant a fresh start under strict conditions, and defects on the final two turns. |

## Neural Strategies

These strategies use encoded neural-network weights rather than rule tables or scripted control flow.

| Shortname | DNA family | Default seeded setup | Raw DNA | Human explanation |
| --- | --- | --- | --- | --- |
| `EVOLVED_ANN` | `NN` | No | `loaded from bundled Axelrod ANN weights` | Exact neural-network strategy using the bundled Axelrod EvolvedANN weights and the same fixed feature extractor as the reference implementation. |
| `EVOLVED_ANN5` | `NN` | No | `loaded from bundled Axelrod ANN weights` | Exact neural-network strategy using the bundled Axelrod EvolvedANN5 weights. |
| `EVOLVED_ANN_NOISE05` | `NN` | No | `loaded from bundled Axelrod ANN weights` | Exact neural-network strategy using the bundled Axelrod EvolvedANNNoise05 weights. |

## Canonical Naming

The baseline registry is canonical:

- one raw DNA maps to one baseline name
- equivalent external names such as `Grim Trigger` or `Soft Go By Majority` are documented in the Axelrod mapping, but not duplicated in the internal baseline registry
