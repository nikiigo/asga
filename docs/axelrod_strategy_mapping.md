# Axelrod Strategy Mapping

This file maps selected strategies from the Axelrod library to the DNA families implemented in this project.

Important scope note:

- this file is not a complete list of every baseline strategy implemented in the codebase
- it covers Axelrod-referenced strategies and their relationship to our implementation
- several project-local helper baselines in `baseline_dna_library()` are not Axelrod mapping rows

Simulation rule:

- only strategies with `Support = exact` are eligible to be used directly as seeded/evolving DNA strategies in this simulator
- `approximate` and `unsupported` rows are kept for roadmap/comparison purposes only

Support levels:

- `exact`: the current DNA family can encode the strategy without losing intended behavior
- `approximate`: the current DNA family is close, but some behavior is simplified or missing
- `unsupported`: the current DNA families cannot encode the strategy faithfully
- when a family allows `RANDOM` as an action gene, that genome also carries a random-action cooperation probability used at runtime
- some `exact` rows are exact only under the simulator's default payoff matrix; those cases are called out explicitly in the notes column

Reference source: [Axelrod strategy index](https://axelrod.readthedocs.io/en/stable/reference/strategy_index.html)

## Mapping

| Axelrod strategy | Shortname | DNA family | Support | Raw DNA | Notes |
| --- | --- | --- | --- | --- | --- |
| Cooperator | `ALLC` | `LOOKUP` | exact | `001000000001010000011000000000000000` | Deterministic always-cooperate table. |
| Defector | `ALLD` | `LOOKUP` | exact | `001000000001010001011000000001010101` | Deterministic always-defect table. |
| Tit For Tat | `TFT` | `LOOKUP` | exact | `001000000001010000011000000000010001` | Deterministic memory-1 table. |
| Suspicious Tit For Tat | `SUSPICIOUS_TFT` | `LOOKUP` | exact | `001000000001010001011000000000010001` | Implemented and validated as a lookup-table variant of Tit For Tat. |
| Win-Stay Lose-Shift | `PAVLOV` | `LOOKUP` | exact | `001000000001010000011000000000010100` | Pavlov is deterministic memory-1. |
| Grudger | `GRUDGER` | `TRIGGER` | exact | `001000010001101000000101010000000010000000` | Binary trigger state is enough. |
| Grim Trigger | `GRUDGER` | `TRIGGER` | exact | `001000010001101000000101010000000010000000` | Uses the same canonical trigger implementation as Grudger. |
| Random | `RANDOM` | `PROBABILISTIC_LOOKUP` | exact | `0010001100101010100000000110000000100000001000000010000000` | Implemented and validated as a constant probabilistic lookup. |
| Joss | `JOSS` | `PROBABILISTIC_LOOKUP` | exact | `0010001100101010111111110111100110000000001110011000000000` | Memory-1 stochastic response. |
| Generous Tit For Tat | `GTFT` | `PROBABILISTIC_LOOKUP` | exact | `0010001100101010111111110111111111010101011111111101010101` | Exact for the default payoff matrix `(R=3, P=1, S=0, T=5)`; Axelrod's reference implementation derives `p` from the active game payoffs. |
| Tit For 2 Tats | `TF2T` | `LOOKUP` | exact | `001000000010110000101000000000000000000100010000000000010001` | Lookup with memory depth 2. |
| Alternator | `ALTERNATOR` | `FSM` | exact | `0010010000100100000010001000000001001010010000000000` | Two-state finite state machine. |
| Cycler CCD | `CYCLER_CCD` | `FSM` | exact | `00100100001011100001000010000000000010000101010010100000000000` | Implemented and validated as a three-state periodic FSM. |
| Cycler CCCD | `CYCLER_CCCD` | `FSM` | exact | `001001000011100000011000100000000000100001000100001001011010110000000000` | Implemented and validated as a four-state periodic FSM. |
| Cycler CCCCCD | `CYCLER_CCCCCD` | `SCRIPTED` | exact | `001001010010000000000100000000000000000000000000` | Implemented and validated as an exact periodic scripted strategy. |
| Go By Majority | `GO_BY_MAJORITY` | `COUNT_BASED` | exact | `0010001000011110000000000010000000011010000000` | Count-based full-history threshold. |
| Hard Go By Majority | `HARD_GO_BY_MAJORITY` | `COUNT_BASED` | exact | `0010001000011110000000000010000001011010000000` | Count-based full-history threshold. |
| Soft Go By Majority | `GO_BY_MAJORITY` | `COUNT_BASED` | exact | `0010001000011110000000000010000000011010000000` | Uses the same canonical majority implementation as Go By Majority. |
| Appeaser | `APPEASER` | `FSM` | exact | `0010010000100100000010001000000000000010010100100000` | Toggle-on-defection behavior fits a small FSM. |
| Prober | `PROBER` | `SCRIPTED` | exact | `001001010010000000000101000000000000000000000000` | Implemented exactly as a D,C,C opening with contingent forever-defect or TFT behavior. |
| Nydegger | `NYDEGGER` | `SCRIPTED` | exact | `001001010010000000000000000000000000000000000000` | Implemented exactly from the documented three-outcome formula. |
| Shubik | `SHUBIK` | `SCRIPTED` | exact | `001001010010000000000001000000000000000000000000` | Implemented exactly with escalating retaliation length. |
| Adaptive | `ADAPTIVE` | `SCRIPTED` | exact | `001001010010000000000110000000000000000000000000` | Exact under the default payoff matrix `(R=3, P=1, S=0, T=5)`; the reference implementation scores outcomes from the active game object. |
| Adaptor |  | `SCRIPTED` | approximate |  | Axelrod exposes `AdaptorBrief` and `AdaptorLong` as exact variants; there is no single exact canonical `Adaptor` class to map here. |
| AdaptorBrief | `ADAPTOR_BRIEF` | `SCRIPTED` | exact | `001001010010000000001010000000000000000000000000` | Exact stochastic state-update strategy with the short-interaction parameters. |
| AdaptorLong | `ADAPTOR_LONG` | `SCRIPTED` | exact | `001001010010000000001011000000000000000000000000` | Exact stochastic state-update strategy with the long-interaction parameters. |
| APavlov2006 | `APAVLOV2006` | `SCRIPTED` | exact | `001001010010000000000111000000000000000000000000` | Exact six-turn classifier strategy. |
| APavlov2011 | `APAVLOV2011` | `SCRIPTED` | exact | `001001010010000000001000000000000000000000000000` | Exact six-turn classifier strategy with TFTT response for STFT-like opponents. |
| Champion | `CHAMPION` | `SCRIPTED` | exact | `001001010010000000000010000000000000000000000000` | Implemented exactly as a phased scripted strategy with a stochastic post-turn-25 rule. |
| Tullock | `TULLOCK` | `SCRIPTED` | exact | `001001010010000000000011000000000000000000000000` | Implemented exactly as a ten-round-window stochastic strategy after the opening phase. |
| ANN |  | `NN` | unsupported |  | Neural-network weights are not represented. |
| EvolvedANN |  | `NN` | unsupported |  | Neural-network weights are not represented. |
| EvolvedANN5 |  | `NN` | unsupported |  | Neural-network weights are not represented. |
| EvolvedANNNoise05 |  | `NN` | unsupported |  | Neural-network weights are not represented. |
| EvolvedAttention |  | `ATTENTION` | unsupported |  | Attention-model weights are not represented. |
| FirstByTidemanAndChieruzzi |  | `SCRIPTED` | unsupported |  | Complex phased control flow is not implemented. |
| FirstByShubik | `SHUBIK` | `SCRIPTED` | exact | `001001010010000000000001000000000000000000000000` | Implemented exactly with escalating punishment length. |
| FirstBySteinAndRapoport |  | `SCRIPTED` | unsupported |  | Periodic statistical tests and endgame logic are not represented. |
| SecondByChampion |  | `SCRIPTED` | unsupported |  | Multi-phase scripted logic is not implemented. |
| SecondByGrofman | `SECOND_BY_GROFMAN` | `SCRIPTED` | exact | `001001010010000000001001000000000000000000000000` | Exact three-phase strategy using the original seven-of-eight-round lookback rule. |

## Strategy To DNA

Exact strategies currently usable in the simulator:

| Strategy | DNA family | Raw DNA |
| --- | --- | --- |
| `Cooperator` | `LOOKUP`, shorthand `CCCCC` | `001000000001010000011000000000000000` |
| `Defector` | `LOOKUP`, shorthand `DDDDD` | `001000000001010001011000000001010101` |
| `Tit For Tat` | `LOOKUP`, shorthand `CCDCD` | `001000000001010000011000000000010001` |
| `Suspicious Tit For Tat` | `LOOKUP`, shorthand `DCDCD` | `001000000001010001011000000000010001` |
| `Tit For 2 Tats` | `LOOKUP`, memory depth `2` | `001000000010110000101000000000000000000100010000000000010001` |
| `Win-Stay Lose-Shift` | `LOOKUP`, shorthand `CCDDC` | `001000000001010000011000000000010100` |
| `Random` | `PROBABILISTIC_LOOKUP`, constant `p(C)=0.5` | `0010001100101010100000000110000000100000001000000010000000` |
| `Joss` | `PROBABILISTIC_LOOKUP`, memory depth `1` | `0010001100101010111111110111100110000000001110011000000000` |
| `Generous Tit For Tat` | `PROBABILISTIC_LOOKUP`, memory depth `1` | `0010001100101010111111110111111111010101011111111101010101` |
| `Grudger` | `TRIGGER` | `001000010001101000000101010000000010000000` |
| `Alternator` | `FSM` | `0010010000100100000010001000000001001010010000000000` |
| `Cycler CCD` | `FSM` | `00100100001011100001000010000000000010000101010010100000000000` |
| `Cycler CCCD` | `FSM` | `001001000011100000011000100000000000100001000100001001011010110000000000` |
| `Cycler CCCCCD` | `SCRIPTED[CYCLER_CCCCCD]` | `001001010010000000000100000000000000000000000000` |
| `Prober` | `SCRIPTED[PROBER]` | `001001010010000000000101000000000000000000000000` |
| `Adaptive` | `SCRIPTED[ADAPTIVE]` | `001001010010000000000110000000000000000000000000` |
| `APavlov2006` | `SCRIPTED[APAVLOV2006]` | `001001010010000000000111000000000000000000000000` |
| `APavlov2011` | `SCRIPTED[APAVLOV2011]` | `001001010010000000001000000000000000000000000000` |
| `SecondByGrofman` | `SCRIPTED[SECOND_BY_GROFMAN]` | `001001010010000000001001000000000000000000000000` |
| `AdaptorBrief` | `SCRIPTED[ADAPTOR_BRIEF]` | `001001010010000000001010000000000000000000000000` |
| `AdaptorLong` | `SCRIPTED[ADAPTOR_LONG]` | `001001010010000000001011000000000000000000000000` |
| `Appeaser` | `FSM` | `0010010000100100000010001000000000000010010100100000` |
| `Go By Majority` | `COUNT_BASED` | `0010001000011110000000000010000000011010000000` |
| `Hard Go By Majority` | `COUNT_BASED` | `0010001000011110000000000010000001011010000000` |
| `Nydegger` | `SCRIPTED[NYDEGGER]` | `001001010010000000000000000000000000000000000000` |
| `Shubik` | `SCRIPTED[SHUBIK]` | `001001010010000000000001000000000000000000000000` |
| `Champion` | `SCRIPTED[CHAMPION]` | `001001010010000000000010000000000000000000000000` |
| `Tullock` | `SCRIPTED[TULLOCK]` | `001001010010000000000011000000000000000000000000` |

## Project-Local Implemented Baselines

These strategies are implemented in `baseline_dna_library()` and usable by the simulator, but they are not primary Axelrod mapping rows.

They are project-specific helper baselines for experiments.

| Shortname | DNA family | Raw DNA | Notes |
| --- | --- | --- | --- |
| `SUSPICIOUS_PAVLOV` | `LOOKUP` | `001000000001010001011000000000010100` | Pavlov variant that defects on the first move. |
| `SHUBIK_COUNTER` | `COUNTER_TRIGGER` | `001001100010110000000101010000000100000001111111111010000000` | Explicit counter-trigger variant of Shubik-style escalation. |
| `REVERSE_TFT` | `LOOKUP` | `001000000001010000011000000001010001` | Inverts Tit For Tat’s usual reciprocity pattern. |
| `CYCLER_CCCCD` | `FSM` | `0010010001000010001000001000000000001000010001000010000110001101100011000000000000` | Project-local five-turn cycle: cooperate four times, then defect once. |
| `SUSPICIOUS_ALTERNATOR` | `FSM` | `0010010000100100010010001000000000001000010100001000` | Alternator variant that opens with defection. |
| `GO_BY_MAJORITY_5` | `COUNT_BASED` | `0010001000011110000000010110000000011010000000` | Windowed majority rule over the last 5 rounds. |
| `GO_BY_MAJORITY_10` | `COUNT_BASED` | `0010001000011110000000101010000000011010000000` | Windowed majority rule over the last 10 rounds. |
| `GO_BY_MAJORITY_20` | `COUNT_BASED` | `0010001000011110000001010010000000011010000000` | Windowed majority rule over the last 20 rounds. |
| `GO_BY_MAJORITY_40` | `COUNT_BASED` | `0010001000011110000010100010000000011010000000` | Windowed majority rule over the last 40 rounds. |
| `HARD_GO_BY_MAJORITY_5` | `COUNT_BASED` | `0010001000011110000000010110000001011010000000` | Hard majority rule over the last 5 rounds. |
| `HARD_GO_BY_MAJORITY_10` | `COUNT_BASED` | `0010001000011110000000101010000001011010000000` | Hard majority rule over the last 10 rounds. |
| `HARD_GO_BY_MAJORITY_20` | `COUNT_BASED` | `0010001000011110000001010010000001011010000000` | Hard majority rule over the last 20 rounds. |
| `HARD_GO_BY_MAJORITY_40` | `COUNT_BASED` | `0010001000011110000010100010000001011010000000` | Hard majority rule over the last 40 rounds. |
| `FORGIVER` | `LOOKUP` | `001000000001010000011000000000000001` | Cooperates in all memory-1 states except persistent `DD`. |
| `DEFENSIVE` | `LOOKUP` | `001000000001010001011000000001010100` | Defects by default but cooperates after mutual defection. |
| `PROBER_LIKE` | `FSM` | `0010010000100100010010001000000000001000010000100001` | Project-local prober-style finite-state heuristic. |
| `HARD_REVENGER` | `LOOKUP` | `001000000001010000011000000001010101` | Opens cooperatively, then defects forever after any memory-1 punishment state. |
| `TESTER` | `LOOKUP` | `001000000001010001011000000000000100` | Project-local probe-and-recover deterministic heuristic. |

## DNA Structure

All genomes share the same bit-level header:

| Field | Bits | Meaning |
| --- | --- | --- |
| `VERSION` | 3 | DNA format version |
| `FAMILY` | 5 | Strategy family identifier |
| `PAYLOAD_LENGTH` | 8 | Number of payload bits |
| `PAYLOAD` | variable | Family-specific parameters |

Family payloads:

| Family | Payload meaning |
| --- | --- |
| `LOOKUP` | initial action, memory depth, random-action probability, action table |
| `TRIGGER` | initial/default/triggered actions, trigger-state mask, forgiveness, random-action probability |
| `COUNT_BASED` | initial action, history window, threshold, comparison mode, random-action probability |
| `PROBABILISTIC_LOOKUP` | initial cooperation probability, memory depth, probability table |
| `FSM` | initial action, state count, initial state, random-action probability, transitions |
| `SCRIPTED` | exact named algorithm id and parameters |
| `COUNTER_TRIGGER` | trigger-state mask, punishment-length parameters, random-action probability |

## Current DNA Families

- `LOOKUP`: deterministic table lookup for memory depth `1..3`
- `TRIGGER`: binary persistent trigger logic
- `COUNT_BASED`: threshold/count or ratio logic over opponent cooperation history
- `PROBABILISTIC_LOOKUP`: stochastic lookup table by recent history
- `FSM`: finite state machine with up to 8 states
- `SCRIPTED`: exact named algorithms with family-specific replay logic
- `COUNTER_TRIGGER`: trigger logic with explicit punishment counters and escalation parameters

## Next Gaps

The biggest missing families for broader Axelrod coverage are:

- `NN` for ANN-based strategies
- `SCRIPTED` for tournament-submitted multi-phase hand-coded strategies
- richer `FSM` payloads with more states and explicit opening scripts

## Canonical Naming

The baseline registry now uses canonical names only:

- one raw DNA maps to one baseline name
- behaviorally equivalent Axelrod names, such as `Grim Trigger`, map to the canonical internal shortname shown in the table above
