# Evolution of Cooperation via Genetic Algorithms

Python simulation of evolving populations in the iterated Prisoner's Dilemma using an explicit individual-agent model. Each agent carries validated bit-array DNA, plays one opponent per step, accumulates score, faces score-based elimination, and reproduces on a configurable schedule.

Important constraint:

- the simulation only uses strategies that can be encoded exactly by the implemented DNA families
- strategies marked `approximate` or `unsupported` in the Axelrod mapping are documented for comparison, but they are not used as evolving seeded strategies unless they are later implemented exactly

Action encoding follows the project spec:

- `1 = Cooperate`
- `0 = Defect`

## Structure

- `cooperation_ga/`: simulation package
- `main.py`: CLI entrypoint
- `sample_config.json`: example simulation configuration
- `sample_render_config.json`: example visualization configuration
- `tests/`: unit and behavioral tests
- `sample_output/`: generated metrics artifacts

## Requirements

- Python 3.10+ acceptable
- Python 3.11+ preferred

## Usage

Run the sample experiment:

```bash
.venv/bin/python main.py --config sample_config.json
```

Run the sample experiment with a separate visualization config:

```bash
.venv/bin/python main.py --config sample_config.json --render-config sample_render_config.json
```

Run with per-step progress output:

```bash
.venv/bin/python main.py --config sample_config.json --verbose
```

Run with detailed plain-text debug logging:

```bash
.venv/bin/python main.py --config sample_config.json --debug
```

Run with trace-level plain-text event logging:

```bash
.venv/bin/python main.py --config sample_config.json --trace
```

During long runs, the CLI prints an explicit message when the simulation loop has finished and the program is writing results to disk. That export phase can take noticeable time on large runs, so this message confirms the process is still active and has not hung.

Run tests with the standard library runner:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Implemented Features

- Hashable typed bit-array DNA strategies with mutation, one-point crossover, validation, and random generation
- Family-aware DNA execution supporting lookup-table, trigger, count-based, probabilistic lookup, FSM, and scripted exact strategies
- Deterministic baseline DNA mappings, including 15 predefined seeded strategies
- Seeded-default initialization with 15 predefined DNA strategies and 50 agents per strategy
- Explicit `initial_population` mapping support for baseline names and DNA strings
- Repeated Prisoner's Dilemma match simulation with configurable payoffs, configurable `rounds_per_match`, and optional action noise
- Explicit individual-agent population with unique ids, scores, and ages
- Random pair matching without replacement so each agent plays at most one match per step
- Bottom `death_rate` score-based death each step, defaulting to 2%
- Step-based lifecycle with reproduction every `reproduction_interval` steps
- Individual-based parent selection weighted by adjusted score
- Pair-based reproduction with one child per parent pair by default
- Parents remain alive until they have produced `max_children_per_agent` children, then die
- Mutation interpreted as expected mutated genes per offspring genome
- Configurable maximum population cap with random overflow culling after reproduction
- Per-step metrics with CSV and JSON export, including `DNA -> count`, dominant DNA, dominant group size, and dominant share
- Static infographic PNG and HTML report export
- Seeded initialization using deterministic baseline DNA plus random DNA

## Baseline Configuration

`sample_config.json` includes a seeded setup with:

- `seed_strategies`
- `seed_strategy_population`
- `rounds_per_match = 20`
- `max_population_size = 500`
- `overflow_cull_rate = 0.3`
- `overflow_cull_score_correlation = 0.5`

Some deterministic baselines still have a simple decoded action-table view:

- `ALLC -> CCCCC`
- `ALLD -> DDDDD`
- `TFT -> CCDCD`
- `PAVLOV -> CCDDC`

Internally, DNA now uses a typed header plus family-specific payload:

- `VERSION | FAMILY | PAYLOAD_LENGTH | PAYLOAD`

## DNA Structure

Every genome is stored as a raw bit string. The common header is:

| Field | Bits | Meaning |
| --- | --- | --- |
| `VERSION` | 3 | DNA format version |
| `FAMILY` | 5 | Strategy family identifier |
| `PAYLOAD_LENGTH` | 8 | Length of the family-specific payload |
| `PAYLOAD` | variable | Parameters for the selected strategy family |

Implemented DNA families and payload meaning:

| Family | Purpose | Payload summary |
| --- | --- | --- |
| `LOOKUP` | Deterministic history table | initial action, memory depth, action table |
| `TRIGGER` | Binary trigger strategies | initial/default/triggered actions, trigger states, forgiveness |
| `COUNT_BASED` | Majority/count thresholds | initial action, window, threshold, mode |
| `PROBABILISTIC_LOOKUP` | Stochastic memory-k strategies | initial probability, memory depth, probability table |
| `FSM` | Finite state machines | initial action, state count, initial state, transitions |
| `SCRIPTED` | Exact named algorithms | script id plus family-specific parameters |
| `COUNTER_TRIGGER` | Escalating punishment rules | trigger states plus punishment-length parameters |

Implemented DNA families:

- `LOOKUP`
- `TRIGGER`
- `COUNT_BASED`
- `PROBABILISTIC_LOOKUP`
- `FSM`
- `SCRIPTED`
- `COUNTER_TRIGGER`

The exported `dna` field is the raw bit string. When a DNA matches a known baseline, exports also include the corresponding `strategy_name`.

## How Children Are Formed

Children are created from raw bit-array DNA, but the outcome depends on whether the parent genomes are structurally compatible.

Current crossover order:

1. if both parents have the same total bit length, try one-point crossover on the full bitstring
2. if that fails, and both parents have the same DNA family and the same payload length, mix payload bits 50/50
3. if that also fails, inherit one whole parent genome unchanged
4. apply mutation to the resulting child
5. if the mutated child is invalid, retry until a valid DNA is produced

That means the child DNA is always one of these:

- a true mixed hybrid bitstring
- a same-family payload mix
- a copied parent genome
- any of the above plus mutation

### Worked Example

Same-family deterministic lookup parents:

- `TFT` = `CCDCD` = `0010000000001100000100010001`
- `PAVLOV` = `CCDDC` = `0010000000001100000100010100`

One valid child produced from those parents is:

- `CCDDD` = `0010000000001100000100010101`

Human meaning of that child:

- first move: cooperate
- after `CC`: cooperate
- after `CD`: defect
- after `DC`: defect
- after `DD`: defect

So the child keeps part of the `TFT` behavior and part of the `PAVLOV` behavior, but it is neither parent exactly.

### Same-Family vs Cross-Family Pairs

- `LOOKUP x LOOKUP`, `FSM x FSM`, `TRIGGER x TRIGGER`, `COUNT_BASED x COUNT_BASED`, and other same-shape pairs can often produce true mixed children
- cross-family pairs such as `TFT x NYDEGGER` usually do not produce rich hybrids directly, because mixing incompatible headers and payloads often creates invalid DNA
- in those cross-family cases, the engine usually falls back to inheriting one parent genome and then relies on mutation to create novelty

So in practice:

- same compatible family: children are often real hybrids
- different family: children are usually parent-like first, then potentially changed by mutation

## Strategy To DNA

The simulator uses only strategies that have an exact DNA encoding. The table below shows the current exact strategy set and how each one is encoded.

| Strategy | DNA family | Raw DNA |
| --- | --- | --- |
| `ALLC` | `LOOKUP`, shorthand `CCCCC` | `0010000000001100000100000000` |
| `ALLD` | `LOOKUP`, shorthand `DDDDD` | `0010000000001100010101010101` |
| `TFT` | `LOOKUP`, shorthand `CCDCD` | `0010000000001100000100010001` |
| `SUSPICIOUS_TFT` | `LOOKUP`, shorthand `DCDCD` | `0010000000001100010100010001` |
| `TF2T` | `LOOKUP`, memory depth `2` | `0010000000100100001000000000000100010000000000010001` |
| `PAVLOV` | `LOOKUP`, shorthand `CCDDC` | `0010000000001100000100010100` |
| `JOSS` | `PROBABILISTIC_LOOKUP`, memory depth `1` | `0010001100101010111111110111100110000000001110011000000000` |
| `GTFT` | `PROBABILISTIC_LOOKUP`, memory depth `1` | `0010001100101010111111110111111111010101011111111101010101` |
| `RANDOM` | `PROBABILISTIC_LOOKUP`, constant `p(C)=0.5` | `0010001100101010100000000110000000100000001000000010000000` |
| `GRUDGER` | `TRIGGER` | `0010000100010010000001010100000000` |
| `NYDEGGER` | `SCRIPTED[NYDEGGER]` | `001001010010000000000000000000000000000000000000` |
| `SHUBIK` | `SCRIPTED[SHUBIK]` | `001001010010000000000001000000000000000000000000` |
| `CHAMPION` | `SCRIPTED[CHAMPION]` | `001001010010000000000010000000000000000000000000` |
| `TULLOCK` | `SCRIPTED[TULLOCK]` | `001001010010000000000011000000000000000000000000` |
| `ALTERNATOR` | `FSM` | `00100100000111000000100001001010010000000000` |
| `CYCLER_CCD` | `FSM` | `001001000010011000010000000010000101010010100000000000` |
| `CYCLER_CCCD` | `FSM` | `0010010000110000000110000000100001000100001001011010110000000000` |
| `CYCLER_CCCCD` | `FSM` | `00100100001110100010000000001000010001000010000110001101100011000000000000` |
| `APPEASER` | `FSM` | `00100100000111000000100000000010010100100000` |
| `GO_BY_MAJORITY` | `COUNT_BASED` | `00100010000101100000000000100000000110` |
| `HARD_GO_BY_MAJORITY` | `COUNT_BASED` | `00100010000101100000000000100000010110` |
| `GO_BY_MAJORITY_5/10/20/40` | `COUNT_BASED` with explicit window | family variants with distinct raw DNA |
| `HARD_GO_BY_MAJORITY_5/10/20/40` | `COUNT_BASED` with explicit window | family variants with distinct raw DNA |

The default seeded strategy list is:

- `ALLC`
- `ALLD`
- `TFT`
- `TF2T`
- `PAVLOV`
- `JOSS`
- `GTFT`
- `NYDEGGER`
- `SHUBIK`
- `SUSPICIOUS_TFT`
- `SUSPICIOUS_PAVLOV`
- `ALTERNATOR`
- `FORGIVER`
- `DEFENSIVE`
- `TESTER`

## Simulation Configuration

`SimulationConfig` covers the experiment and lifecycle model:

- `initial_population`
- `rounds_per_match`
- `death_rate`
- `max_population_size`
- `overflow_cull_rate`
- `overflow_cull_score_correlation`
- `selection_epsilon`
- `odd_agent_mode`
- `reproduction_interval`
- `checkpoint_interval`
- `offspring_per_pair`
- `mutation_genes_per_step`
- `allow_self_pairing`
- `pairing_mode`
- `fixed_pairs_per_reproduction`
- `reset_scores_after_reproduction`
- `verbose`
- `debug`
- `trace`

Checkpoint behavior:

- `checkpoint_interval = 0` disables checkpoints
- any positive value writes checkpoint exports every N steps
- checkpoints are written under `output_dir/checkpoints/step_XXXXX/`

## Visualization Configuration

`VisualizationConfig` covers rendering only. It can live in a separate JSON file passed through `--render-config`.

Visualization settings are:

- `viz_palette`
- `viz_bg_color`
- `viz_panel_color`
- `viz_ink_color`
- `viz_muted_color`
- `viz_accent_color`
- `viz_cooperation_color`
- `viz_defection_color`
- `viz_unique_color`
- `viz_entropy_color`
- `viz_dominant_color`
- `viz_title_text`
- `viz_subtitle_text`
- `viz_behavior_title`
- `viz_structure_title`
- `viz_leader_title`
- `viz_report_title`
- `viz_report_heading`
- `viz_report_description`
- `top_strategies_to_plot`

## Output

The simulator exports:

- `sample_output/metrics.csv`
- `sample_output/metrics.json`
- `sample_output/population_breakdown.csv`
- `sample_output/population_breakdown.json`
- `sample_output/final_population_summary.csv`
- `sample_output/final_population_summary.json`
- `sample_output/summary_infographic.png`
- `sample_output/report.html`

These files are visualization-ready and include:

- per-step population breakdowns ordered by descending DNA group size
- human-readable strategy explanations decoded from raw DNA
- stable output names for non-baseline DNA, labeled as `Hybrid1`, `Hybrid2`, and so on
- a final-step ordered strategy summary with strategy name, raw DNA, population, and explanation
- an interactive Plotly report in `report.html`, with the PNG kept as a static export

The primary success criterion is population spread: the winning strategy is the DNA group with the largest number of living agents at the final step.

For long runs, a practical workflow is:

1. run a fast config with `export_visuals: false`
2. render visuals afterward from the saved metrics JSON

Config naming convention:

- `*_fast.json`: simulation-only run, metrics/CSV/JSON exports enabled, visual export disabled
- regular simulation config: simulation run with normal visual export enabled
- `*_render_static.json`: visualization-only config used with `--render-from-metrics`

Example:

```bash
.venv/bin/python main.py --config config_1000_steps_all_strategies_20_fast.json
.venv/bin/python main.py --config config_1000_steps_all_strategies_20_fast.json --render-config config_1000_steps_all_strategies_20_render_static.json --render-from-metrics sample_output_1000_all_strategies_20_fast/metrics.json
```

For very long runs, render the infographic and HTML report afterward from saved metrics:

```bash
.venv/bin/python main.py --config config_1000_steps_all_strategies_20_fast.json --render-config config_1000_steps_all_strategies_20_render_static.json --render-from-metrics sample_output_1000_all_strategies_20_fast/metrics.json
```

Equivalent 10,000-step configs are also available:

```bash
.venv/bin/python main.py --config config_10000_steps_all_strategies_20_fast.json
.venv/bin/python main.py --config config_10000_steps_all_strategies_20_fast.json --render-config config_10000_steps_all_strategies_20_render_static.json --render-from-metrics sample_output_10000_all_strategies_20_fast/metrics.json
```

## Axelrod Mapping

A compatibility map for selected Axelrod-library strategies is maintained in [docs/axelrod_strategy_mapping.md](docs/axelrod_strategy_mapping.md). It marks each mapped strategy as `exact`, `approximate`, or `unsupported` against the currently implemented DNA families.

That mapping file also contains a separate `Project-Local Implemented Baselines` section for strategies that exist in `baseline_dna_library()` but are not primary Axelrod mapping rows.

A plain-language inventory of every implemented baseline strategy is maintained in [docs/implemented_strategies.md](docs/implemented_strategies.md).

A plain-language explanation of the simulation lifecycle and match rules is maintained in [docs/game_model.md](docs/game_model.md).
