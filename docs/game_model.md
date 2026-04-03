# Game Model

This document explains the simulation rules in plain language.

## Overview

The project simulates an evolving population of agents that repeatedly play the Iterated Prisoner's Dilemma.

Each agent:

- has its own DNA-encoded strategy
- plays repeated matches against other agents
- accumulates score from those matches
- may die if it performs poorly
- may reproduce if it performs well enough

The simulation is agent-based, not just strategy-count-based. That means every individual agent exists explicitly in the population.

## One Match

When two agents meet, they play a repeated Prisoner's Dilemma match.

Each round, both agents choose one action:

- `C` = cooperate
- `D` = defect

They choose simultaneously, based on their strategy logic and the match history so far.

### Payoff Matrix

The default payoff matrix is:

| Agent A | Agent B | Score A | Score B |
| --- | --- | --- | --- |
| `C` | `C` | `3` | `3` |
| `D` | `C` | `5` | `0` |
| `C` | `D` | `0` | `5` |
| `D` | `D` | `1` | `1` |

Meaning:

- mutual cooperation gives both agents a solid reward
- defecting against a cooperator gives the highest one-round payoff
- mutual defection is worse than mutual cooperation
- cooperating against a defector gives the worst payoff

### Match History

Strategies can use the history of the current match:

- their own previous moves
- the opponent's previous moves
- any explicit internal runtime state used by the DNA family

The match lasts for a configurable number of rounds.

In configuration, this is controlled by:

- `rounds_per_match`

The current sample/default setup uses:

- `rounds_per_match = 20`

## One Simulation Step

The simulation runs in discrete steps.

On each step:

1. Agents are paired randomly.
2. Each paired agent plays exactly one repeated match.
3. Match scores are added to each agent's accumulated score.
4. The lowest-scoring fraction of the population is removed.
5. Surviving agents age by one step.
6. If the step is a reproduction step, reproduction happens.

## Pairing

Pairing is random.

The usual flow is:

- shuffle the agent list
- pair agents in order

This gives each agent at most one match on a step.

If the population size is odd, behavior depends on configuration:

- skip the leftover agent
- match the leftover agent with a random opponent
- allow self-play if configured

If the leftover agent is skipped on that step:

- it does not play a match
- it gets no new score from interaction on that step
- its existing accumulated score is kept
- it can still be eliminated later in the step if its score is low enough
- it can still be selected for reproduction later if its accumulated score is high enough
- if it survives, its age still increases normally

## Score Accumulation

Each agent stores its own score.

Scores are accumulated across steps until a reproduction reset happens.

This score is used for:

- elimination
- reproduction selection

Important distinction:

- `fitness` in the simulation is individual score
- `success` in the reports is strategy spread by DNA group size

## Death / Selection Pressure

On every step, the weakest-performing part of the population is removed.

The configured rule is:

- remove `ceil(death_rate * population_size)` agents

By default the project has used low percentages such as 0.5% or 2%, depending on configuration.

Agents are ordered by score from lowest to highest.

If several agents tie near the cutoff, random shuffling breaks ties before removal.

## Reproduction

Reproduction happens only on scheduled reproduction steps.

The interval is configurable, for example:

- every 10 steps

### Parent Selection

Parents are selected probabilistically from the living agents.

Agents with higher scores get higher probability of being selected.

To avoid zero-weight problems, the engine shifts scores by the current minimum and adds a small epsilon.

### Current Parent/Child Rule

In the current implementation:

- one selected parent pair produces one child per reproductive event
- each parent tracks how many children it has produced over its lifetime
- once an agent reaches `max_children_per_agent`, it dies

This means parent death is based on lifetime reproduction count, not immediate death after every birth.

## Crossover and Mutation

Each child is created from parent DNA.

### Crossover

If crossover is selected:

- same-length genomes can use one-point crossover
- compatible typed genomes can also mix payload bits
- if crossover would create invalid DNA, the engine falls back to a safe valid parent-derived child

In other words, the engine prefers a real hybrid, but it never accepts invalid DNA just to force crossover.

### Worked Example

Two same-family lookup parents:

- `TFT` = `CCDCD` = `00100000000000000001010000011000000000010001`
- `PAVLOV` = `CCDDC` = `00100000000000000001010000011000000000010100`

One valid child from those parents is:

- `CCDDD` = `00100000000000000001010000011000000000010101`

That child means:

- initial move `C`
- after `CC` -> `C`
- after `CD` -> `D`
- after `DC` -> `D`
- after `DD` -> `D`

So the child is a real mixed lookup-table strategy rather than a pure copy of either parent.

Cross-family pairs behave differently:

- compatible same-family pairs often produce true hybrids
- cross-family pairs such as `LOOKUP x SCRIPTED` often fall back to one parent genome, because most direct mixes would be invalid
- mutation is then what usually creates novelty in those cross-family cases

### Mutation

After crossover or inheritance, mutation is applied.

Mutation flips bits in the child DNA:

- `0 -> 1`
- `1 -> 0`

The mutation setting is interpreted as an expected number of mutated genes per offspring genome, then converted to a per-bit probability.

Invalid mutated DNA is rejected and the engine retries child creation until it gets a valid genome.

So the final child after reproduction can be:

- a mixed hybrid DNA
- a copied parent DNA
- either of those plus valid mutation

## DNA and Strategy Execution

Every agent stores its own raw DNA bitstring.

The DNA is decoded into one of the supported strategy families, such as:

- `LOOKUP`
- `TRIGGER`
- `COUNT_BASED`
- `PROBABILISTIC_LOOKUP`
- `FSM`
- `SCRIPTED`
- `COUNTER_TRIGGER`
- `NN`

### What "Gene" Means Here

The simulator mutates DNA at the bit level, but the meaningful unit is a behavior field inside the family payload.

So, depending on the family, mutation or crossover can change things like:

- a lookup-table response after a specific history
- a trigger condition or forgiveness probability
- a count threshold or lookback window
- a probabilistic response rate
- an FSM transition or current-machine layout
- a scripted strategy id or script parameter
- a punishment-length or escalation flag
- a neural-network weight or bias

That is why "gene" is family-specific in this project. It does not always mean "one table cell" or "one action". In some families it means a rule parameter, and in `NN` it means part of the encoded network.
- `PROBABILISTIC_LOOKUP`
- `FSM`
- `SCRIPTED`
- `COUNTER_TRIGGER`

During a match, the strategy executor uses:

- DNA
- match history
- runtime state

to decide the next move.

## Strategy Grouping and Dominance

After each step, living agents are grouped by identical DNA.

For each DNA group, the simulator records:

- number of living agents
- share of the whole population

The dominant strategy is defined as:

- the DNA group with the largest number of living agents

So the winning strategy is not the one with the single highest-scoring individual.

It is the one that spreads the most through the population.

## Outputs

The simulator exports per-step and final summaries, including:

- total population
- DNA counts
- dominant DNA
- cooperation rate
- births and deaths
- final ordered strategy list

Novel DNA that does not match a named baseline is labeled in outputs as:

- `Hybrid1`
- `Hybrid2`
- and so on

Those hybrid strategies also get human-readable explanations decoded from their raw DNA.
