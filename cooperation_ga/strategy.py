"""Strategy interfaces and baseline strategy implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Protocol, TypedDict

from cooperation_ga.dna import COOPERATE, DEFECT, RANDOM, STATE_INDEX, StrategyDNA


class IteratedStrategy(Protocol):
    """Common interface for all strategy implementations."""

    def initial_state(self) -> object | None:
        """Return the initial per-match runtime state."""

    def next_move(
        self,
        own_history: list[int],
        opp_history: list[int],
        rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Return the next action and updated state from history."""


@dataclass(slots=True)
class CounterTriggerState:
    """Explicit runtime state for counter-trigger strategies."""

    punishment_remaining: int = 0
    next_punishment_length: int = 1


@dataclass(slots=True)
class ScriptedState:
    """Generic scripted runtime state."""

    turns_played: int = 0
    retaliation_remaining: int = 0
    next_retaliation_length: int = 1


@dataclass(slots=True)
class APavlovState:
    """Runtime state for Adaptive Pavlov variants."""

    opponent_class: str | None = None


@dataclass(slots=True)
class AdaptiveState:
    """Runtime state for Adaptive."""

    score_c: int = 0
    score_d: int = 0


@dataclass(slots=True)
class AdaptorState:
    """Runtime state for Adaptor variants."""

    s: float = 0.0


@dataclass(slots=True)
class FsmState:
    """Explicit runtime state for finite state machine strategies."""

    current_state: int


class GrimTriggerState(TypedDict):
    """Explicit runtime state for Grim Trigger."""

    triggered: bool


@dataclass(slots=True)
class DnaStrategy:
    """Typed DNA interpreter dispatching behavior by family."""

    dna: StrategyDNA

    def initial_state(self) -> object | None:
        """Return the initial runtime state for the DNA family."""
        family = self.dna.family_name()
        if family in {"LOOKUP", "TRIGGER", "COUNT_BASED", "PROBABILISTIC_LOOKUP"}:
            return None
        if family == "FSM":
            return FsmState(current_state=self.dna.fsm_initial_state())
        if family == "SCRIPTED":
            if self.dna.script_name() == "SHUBIK":
                return ScriptedState(turns_played=0, retaliation_remaining=0, next_retaliation_length=1)
            if self.dna.script_name() in {"APAVLOV2006", "APAVLOV2011"}:
                return APavlovState()
            if self.dna.script_name() == "ADAPTIVE":
                return AdaptiveState()
            if self.dna.script_name() in {"ADAPTOR_BRIEF", "ADAPTOR_LONG"}:
                return AdaptorState()
            return ScriptedState()
        if family == "COUNTER_TRIGGER":
            base = max(1, self.dna.counter_trigger_base_punishment_length())
            return CounterTriggerState(punishment_remaining=0, next_punishment_length=base)
        raise ValueError(f"Unsupported DNA family: {family}")

    def next_move(
        self,
        own_history: list[int],
        opp_history: list[int],
        rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Return the next move and updated runtime state."""
        family = self.dna.family_name()
        if family == "LOOKUP":
            return (
                self._resolve_action(
                    self.dna.action_for_history(own_history, opp_history),
                    self.dna.lookup_random_action_probability(),
                    rng,
                ),
                state,
            )
        if family == "TRIGGER":
            return (
                self._resolve_action(
                    self._trigger_move(own_history, opp_history, rng),
                    self.dna.trigger_random_action_probability(),
                    rng,
                ),
                state,
            )
        if family == "COUNT_BASED":
            return (
                self._resolve_action(
                    self._count_based_move(opp_history),
                    self.dna.count_based_random_action_probability(),
                    rng,
                ),
                state,
            )
        if family == "PROBABILISTIC_LOOKUP":
            probability = self.dna.probability_for_history(own_history, opp_history)
            if not own_history:
                if probability <= 0.0:
                    return DEFECT, state
                if probability >= 1.0:
                    return COOPERATE, state
            return COOPERATE if rng.random() < probability else DEFECT, state
        if family == "FSM":
            action, new_state = self._fsm_move(opp_history, state)
            return self._resolve_action(action, self.dna.fsm_random_action_probability(), rng), new_state
        if family == "SCRIPTED":
            return self._scripted_move(own_history, opp_history, rng, state)
        if family == "COUNTER_TRIGGER":
            action, new_state = self._counter_trigger_move(own_history, opp_history, state)
            return (
                self._resolve_action(
                    action,
                    self.dna.counter_trigger_random_action_probability(),
                    rng,
                ),
                new_state,
            )
        raise ValueError(f"Unsupported DNA family: {family}")

    @staticmethod
    def _resolve_action(action_code: int, random_probability: float, rng: Random) -> int:
        """Resolve deterministic or random action codes into a move."""
        if action_code == RANDOM:
            return COOPERATE if rng.random() < random_probability else DEFECT
        return action_code

    def _trigger_move(self, own_history: list[int], opp_history: list[int], rng: Random) -> int:
        """Evaluate a trigger-style strategy against the full observed history."""
        if not own_history:
            return self.dna.trigger_init_action()
        trigger_states = self.dna.trigger_states()
        triggered = any(
            trigger_states[STATE_INDEX[state]]
            for state in zip(own_history, opp_history)
        )
        if not triggered:
            return self.dna.trigger_default_action()
        if rng.random() < self.dna.trigger_forgiveness_probability():
            return self.dna.trigger_default_action()
        return self.dna.trigger_triggered_action()

    def _count_based_move(self, opp_history: list[int]) -> int:
        """Evaluate a count-based strategy against opponent cooperation statistics."""
        if not opp_history:
            return self.dna.count_based_init_action()
        window = self.dna.count_based_window()
        relevant = opp_history if window == 0 else opp_history[-window:]
        cooperation_count = sum(move == COOPERATE for move in relevant)
        if self.dna.count_based_mode() == 0:
            condition = cooperation_count >= self.dna.count_based_threshold()
        else:
            ratio_byte = round((cooperation_count / len(relevant)) * 255) if relevant else 0
            condition = ratio_byte >= self.dna.count_based_threshold()
        if not self.dna.count_based_cooperate_if_ge():
            condition = not condition
        return COOPERATE if condition else DEFECT

    def _fsm_move(self, opp_history: list[int], state: object | None) -> tuple[int, object | None]:
        """Advance an FSM using explicit runtime state rather than replaying full history."""
        if not opp_history:
            current = state if isinstance(state, FsmState) else FsmState(current_state=self.dna.fsm_initial_state())
            return self.dna.fsm_init_action(), current
        transitions = self.dna.fsm_transitions()
        current_state = self.dna.fsm_initial_state()
        for prior_opponent_action in opp_history[:-1]:
            transition_index = current_state * 2 + (0 if prior_opponent_action == COOPERATE else 1)
            _action, current_state = transitions[transition_index]
        transition_index = current_state * 2 + (0 if opp_history[-1] == COOPERATE else 1)
        action, next_state = transitions[transition_index]
        return action, FsmState(current_state=next_state)

    def _scripted_move(
        self,
        own_history: list[int],
        opp_history: list[int],
        rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Dispatch exact scripted strategies."""
        script_name = self.dna.script_name()
        if script_name == "NYDEGGER":
            return self._nydegger_move(own_history, opp_history), state
        if script_name == "SHUBIK":
            current = state if isinstance(state, ScriptedState) else ScriptedState()
            action, new_state = self._shubik_move(own_history, opp_history, current)
            return action, new_state
        if script_name == "CHAMPION":
            return self._champion_move(opp_history, rng), state
        if script_name == "TULLOCK":
            return self._tullock_move(opp_history, rng), state
        if script_name == "CYCLER_CCCCCD":
            return self._cycler_cccccd_move(own_history), state
        if script_name == "PROBER":
            return self._prober_move(opp_history), state
        if script_name == "ADAPTIVE":
            current = state if isinstance(state, AdaptiveState) else AdaptiveState()
            action, new_state = self._adaptive_move(own_history, opp_history, current)
            return action, new_state
        if script_name == "APAVLOV2006":
            current = state if isinstance(state, APavlovState) else APavlovState()
            return self._apavlov2006_move(opp_history, current), current
        if script_name == "APAVLOV2011":
            current = state if isinstance(state, APavlovState) else APavlovState()
            return self._apavlov2011_move(opp_history, current), current
        if script_name == "SECOND_BY_GROFMAN":
            return self._second_by_grofman_move(own_history, opp_history), state
        if script_name == "ADAPTOR_BRIEF":
            current = state if isinstance(state, AdaptorState) else AdaptorState()
            return self._adaptor_move(own_history, opp_history, current, brief=True, rng=rng)
        if script_name == "ADAPTOR_LONG":
            current = state if isinstance(state, AdaptorState) else AdaptorState()
            return self._adaptor_move(own_history, opp_history, current, brief=False, rng=rng)
        raise ValueError(f"Unsupported scripted strategy: {script_name}")

    def _nydegger_move(self, own_history: list[int], opp_history: list[int]) -> int:
        """Implement Nydegger using the documented three-outcome formula."""
        if not own_history:
            return COOPERATE
        if len(opp_history) == 1:
            return opp_history[-1]
        if len(opp_history) == 2:
            if opp_history[0] == DEFECT and opp_history[1] == COOPERATE:
                return DEFECT
            return opp_history[-1]
        weights = (16, 4, 1)
        encoded = 0
        for weight, own_move, opp_move in zip(weights, reversed(own_history[-3:]), reversed(opp_history[-3:])):
            encoded += weight * self._nydegger_code(own_move, opp_move)
        defect_codes = {1, 6, 7, 17, 22, 23, 26, 29, 30, 31, 33, 38, 39, 45, 49, 54, 55, 58, 61}
        return DEFECT if encoded in defect_codes else COOPERATE

    @staticmethod
    def _nydegger_code(own_move: int, opp_move: int) -> int:
        """Map a round outcome to Nydegger's ternary code."""
        mapping = {
            (COOPERATE, COOPERATE): 0,
            (COOPERATE, DEFECT): 2,
            (DEFECT, COOPERATE): 1,
            (DEFECT, DEFECT): 3,
        }
        return mapping[(own_move, opp_move)]

    @staticmethod
    def _shubik_move(
        own_history: list[int],
        opp_history: list[int],
        state: ScriptedState,
    ) -> tuple[int, ScriptedState]:
        """Implement Shubik with explicit runtime state."""
        current = ScriptedState(
            turns_played=state.turns_played,
            retaliation_remaining=state.retaliation_remaining,
            next_retaliation_length=state.next_retaliation_length,
        )
        if not opp_history:
            current.turns_played += 1
            return COOPERATE, current
        if current.retaliation_remaining > 0:
            current.retaliation_remaining -= 1
            action = DEFECT
        elif opp_history[-1] == DEFECT and own_history[-1] == COOPERATE:
            current.retaliation_remaining = current.next_retaliation_length - 1
            current.next_retaliation_length += 1
            action = DEFECT
        else:
            action = COOPERATE
        current.turns_played += 1
        return action, current

    @staticmethod
    def _champion_move(opp_history: list[int], rng: Random) -> int:
        """Implement Champion exactly from the documented phase logic."""
        turn = len(opp_history) + 1
        if turn <= 10:
            return COOPERATE
        if turn <= 25:
            return COOPERATE if not opp_history or opp_history[-1] == COOPERATE else DEFECT
        opponent_defection_rate = sum(move == DEFECT for move in opp_history) / len(opp_history)
        if opp_history[-1] == DEFECT and opponent_defection_rate >= max(0.4, rng.random()):
            return DEFECT
        return COOPERATE

    @staticmethod
    def _tullock_move(opp_history: list[int], rng: Random) -> int:
        """Implement Tullock exactly from the documented ten-round window rule."""
        turn = len(opp_history) + 1
        if turn <= 11:
            return COOPERATE
        recent_window = opp_history[-10:]
        opponent_cooperation_rate = sum(move == COOPERATE for move in recent_window) / len(recent_window)
        cooperation_probability = max(0.0, min(1.0, opponent_cooperation_rate - 0.1))
        return COOPERATE if rng.random() < cooperation_probability else DEFECT

    @staticmethod
    def _cycler_cccccd_move(own_history: list[int]) -> int:
        """Implement the exact periodic sequence CCCCCD."""
        cycle = (COOPERATE, COOPERATE, COOPERATE, COOPERATE, COOPERATE, DEFECT)
        return cycle[len(own_history) % len(cycle)]

    @staticmethod
    def _prober_move(opp_history: list[int]) -> int:
        """Implement Prober exactly."""
        turn = len(opp_history)
        if turn == 0:
            return DEFECT
        if turn in {1, 2}:
            return COOPERATE
        if opp_history[1:3] == [COOPERATE, COOPERATE]:
            return DEFECT
        return DEFECT if opp_history[-1] == DEFECT else COOPERATE

    @staticmethod
    def _adaptive_move(
        own_history: list[int],
        opp_history: list[int],
        state: AdaptiveState,
    ) -> tuple[int, AdaptiveState]:
        """Implement Adaptive using the default payoff matrix scoring rule."""
        current = AdaptiveState(score_c=state.score_c, score_d=state.score_d)
        if own_history:
            own_last = own_history[-1]
            opp_last = opp_history[-1]
            if own_last == COOPERATE and opp_last == COOPERATE:
                current.score_c += 3
            elif own_last == COOPERATE and opp_last == DEFECT:
                current.score_c += 0
            elif own_last == DEFECT and opp_last == COOPERATE:
                current.score_d += 5
            else:
                current.score_d += 1
        opening = [COOPERATE] * 6 + [DEFECT] * 5
        if len(own_history) < len(opening):
            return opening[len(own_history)], current
        return (COOPERATE if current.score_c > current.score_d else DEFECT), current

    @staticmethod
    def _apavlov2006_move(opp_history: list[int], state: APavlovState) -> int:
        """Implement Adaptive Pavlov 2006 exactly."""
        turn = len(opp_history)
        if turn < 6:
            return DEFECT if opp_history[-1:] == [DEFECT] else COOPERATE
        if turn % 6 == 0:
            if opp_history[-6:] == [COOPERATE] * 6:
                state.opponent_class = "Cooperative"
            elif opp_history[-6:] == [DEFECT] * 6:
                state.opponent_class = "ALLD"
            elif opp_history[-6:] == [DEFECT, COOPERATE, DEFECT, COOPERATE, DEFECT, COOPERATE]:
                state.opponent_class = "STFT"
            elif opp_history[-6:] == [DEFECT, DEFECT, COOPERATE, DEFECT, DEFECT, COOPERATE]:
                state.opponent_class = "PavlovD"
            else:
                state.opponent_class = "Random"
        if state.opponent_class in {"Random", "ALLD"}:
            return DEFECT
        if state.opponent_class == "STFT":
            if turn % 6 in {0, 1}:
                return COOPERATE
            return DEFECT if opp_history[-1] == DEFECT else COOPERATE
        if state.opponent_class == "PavlovD":
            if turn % 6 == 0:
                return DEFECT
        if state.opponent_class == "Cooperative" and opp_history[-1:] == [DEFECT]:
            return DEFECT
        return COOPERATE

    @staticmethod
    def _apavlov2011_move(opp_history: list[int], state: APavlovState) -> int:
        """Implement Adaptive Pavlov 2011 exactly."""
        turn = len(opp_history)
        if turn < 6:
            return DEFECT if opp_history[-1:] == [DEFECT] else COOPERATE
        if turn % 6 == 0:
            recent = opp_history[-6:]
            if recent == [COOPERATE] * 6:
                state.opponent_class = "Cooperative"
            elif recent.count(DEFECT) >= 4:
                state.opponent_class = "ALLD"
            elif recent.count(DEFECT) == 3:
                state.opponent_class = "STFT"
            else:
                state.opponent_class = "Random"
        if state.opponent_class in {"Random", "ALLD"}:
            return DEFECT
        if state.opponent_class == "STFT":
            return DEFECT if opp_history[-2:] == [DEFECT, DEFECT] else COOPERATE
        return DEFECT if opp_history[-1:] == [DEFECT] else COOPERATE

    @staticmethod
    def _second_by_grofman_move(own_history: list[int], opp_history: list[int]) -> int:
        """Implement SecondByGrofman exactly."""
        turn = len(own_history)
        if turn < 2:
            return COOPERATE
        if 2 <= turn <= 6:
            return opp_history[-1]
        opponent_defections_last_window = opp_history[-8:-1].count(DEFECT)
        if own_history[-1] == COOPERATE and opponent_defections_last_window <= 2:
            return COOPERATE
        if own_history[-1] == DEFECT and opponent_defections_last_window <= 1:
            return COOPERATE
        return DEFECT

    @staticmethod
    def _adaptor_move(
        own_history: list[int],
        opp_history: list[int],
        state: AdaptorState,
        brief: bool,
        rng: Random,
    ) -> tuple[int, AdaptorState]:
        """Implement Adaptor variants exactly."""
        current = AdaptorState(s=state.s)
        if own_history:
            last_round = (own_history[-1], opp_history[-1])
            if brief:
                delta = {
                    (COOPERATE, COOPERATE): 0.0,
                    (COOPERATE, DEFECT): -1.001505,
                    (DEFECT, COOPERATE): 0.992107,
                    (DEFECT, DEFECT): -0.638734,
                }
            else:
                delta = {
                    (COOPERATE, COOPERATE): 0.0,
                    (COOPERATE, DEFECT): 1.888159,
                    (DEFECT, COOPERATE): 1.858883,
                    (DEFECT, DEFECT): -0.995703,
                }
            current.s += delta[last_round]
        perr = 0.01
        heaviside_plus = 1.0 if current.s >= -1 else 0.0
        heaviside_minus = 1.0 if current.s >= 1 else 0.0
        probability = perr + (1.0 - 2 * perr) * (heaviside_plus - heaviside_minus)
        return (COOPERATE if rng.random() < probability else DEFECT), current

    def _counter_trigger_move(
        self,
        own_history: list[int],
        opp_history: list[int],
        state: object | None,
    ) -> tuple[int, object | None]:
        """Evaluate a counter-trigger strategy with explicit punishment state."""
        current = state if isinstance(state, CounterTriggerState) else CounterTriggerState(
            punishment_remaining=0,
            next_punishment_length=max(1, self.dna.counter_trigger_base_punishment_length()),
        )
        if not own_history:
            return self.dna.counter_trigger_init_action(), current
        if current.punishment_remaining > 0:
            current.punishment_remaining -= 1
            action = self.dna.counter_trigger_triggered_action()
            if current.punishment_remaining == 0 and not self.dna.counter_trigger_forgive_after_serving():
                current.punishment_remaining = max(1, self.dna.counter_trigger_base_punishment_length())
            return action, current
        trigger_states = self.dna.counter_trigger_states()
        if trigger_states[STATE_INDEX[(own_history[-1], opp_history[-1])]]:
            punishment_length = min(
                current.next_punishment_length,
                max(1, self.dna.counter_trigger_max_punishment_length()),
            )
            current.punishment_remaining = max(0, punishment_length - 1)
            current.next_punishment_length = min(
                current.next_punishment_length + self.dna.counter_trigger_escalation_step(),
                max(1, self.dna.counter_trigger_max_punishment_length()),
            )
            return self.dna.counter_trigger_triggered_action(), current
        return self.dna.counter_trigger_default_action(), current


@dataclass(slots=True)
class AlwaysCooperateStrategy:
    """Always cooperate."""

    @staticmethod
    def initial_state() -> object | None:
        """Return no runtime state."""
        return None

    @staticmethod
    def next_move(
        _own_history: list[int],
        _opp_history: list[int],
        _rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Always cooperate."""
        return COOPERATE, state


@dataclass(slots=True)
class AlwaysDefectStrategy:
    """Always defect."""

    @staticmethod
    def initial_state() -> object | None:
        """Return no runtime state."""
        return None

    @staticmethod
    def next_move(
        _own_history: list[int],
        _opp_history: list[int],
        _rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Always defect."""
        return DEFECT, state


@dataclass(slots=True)
class TitForTatStrategy:
    """Start cooperative, then mirror the opponent's previous move."""

    @staticmethod
    def initial_state() -> object | None:
        """Return no runtime state."""
        return None

    @staticmethod
    def next_move(
        _own_history: list[int],
        opp_history: list[int],
        _rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Mirror the opponent's previous move."""
        return COOPERATE if not opp_history else opp_history[-1], state


@dataclass(slots=True)
class TitForTatForgivingStrategy:
    """Tit for Tat with stochastic forgiveness."""

    forgiveness_probability: float = 0.1

    @staticmethod
    def initial_state() -> object | None:
        """Return no runtime state."""
        return None

    def next_move(
        self,
        _own_history: list[int],
        opp_history: list[int],
        rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Mirror unless forgiving a previous defection."""
        if not opp_history or opp_history[-1] == COOPERATE:
            return COOPERATE, state
        return COOPERATE if rng.random() < self.forgiveness_probability else DEFECT, state


@dataclass(slots=True)
class RandomStrategy:
    """Independent Bernoulli action selection."""

    cooperation_probability: float = 0.5

    @staticmethod
    def initial_state() -> object | None:
        """Return no runtime state."""
        return None

    def next_move(
        self,
        _own_history: list[int],
        _opp_history: list[int],
        rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Sample a random action."""
        return COOPERATE if rng.random() < self.cooperation_probability else DEFECT, state


@dataclass(slots=True)
class GrimTriggerStrategy:
    """Cooperate until the opponent defects once, then defect forever."""

    @staticmethod
    def initial_state() -> object | None:
        """Return explicit trigger state."""
        return GrimTriggerState(triggered=False)

    @staticmethod
    def next_move(
        _own_history: list[int],
        opp_history: list[int],
        _rng: Random,
        state: object | None,
    ) -> tuple[int, object | None]:
        """Defect forever after any opponent defection."""
        current: GrimTriggerState = (
            state if isinstance(state, dict) and "triggered" in state else GrimTriggerState(triggered=False)
        )
        if not opp_history:
            return COOPERATE, current
        if DEFECT in opp_history:
            current["triggered"] = True
        return DEFECT if current["triggered"] else COOPERATE, current


@dataclass(slots=True)
class PavlovStrategy:
    """Win-Stay, Lose-Shift."""

    @staticmethod
    def initial_state() -> object | None:
        """Return no runtime state."""
        return None

    @staticmethod
    def next_move(
        own_history: list[int],
        opp_history: list[int],
        _rng: Random,
        _state: object | None,
    ) -> tuple[int, object | None]:
        """Repeat after good outcomes, switch after bad outcomes."""
        if not own_history:
            return COOPERATE, None
        last_round = (own_history[-1], opp_history[-1])
        table = {
            (COOPERATE, COOPERATE): COOPERATE,
            (COOPERATE, DEFECT): DEFECT,
            (DEFECT, COOPERATE): DEFECT,
            (DEFECT, DEFECT): COOPERATE,
        }
        return table[last_round], None


@dataclass(frozen=True, slots=True)
class ParticipantSpec:
    """Hashable participant descriptor used in population aggregation."""

    identifier: str
    dna: StrategyDNA | None = None
    parameters: tuple[tuple[str, float], ...] = field(default_factory=tuple)

    def label(self) -> str:
        """Render a compact label for reports."""
        if self.dna is not None:
            return self.dna.to_string()
        if not self.parameters:
            return self.identifier
        args = ",".join(f"{key}={value:.2f}" for key, value in self.parameters)
        return f"{self.identifier}({args})"

    @property
    def is_evolvable_dna(self) -> bool:
        """Return whether the participant uses DNA evolution operators."""
        return self.dna is not None


def make_strategy(spec: ParticipantSpec) -> IteratedStrategy:
    """Instantiate a runtime strategy from a participant spec."""
    if spec.dna is not None:
        return DnaStrategy(spec.dna)
    params = dict(spec.parameters)
    registry = {
        "ALLC": AlwaysCooperateStrategy,
        "ALLD": AlwaysDefectStrategy,
        "TFT": TitForTatStrategy,
        "TFT_F": lambda: TitForTatForgivingStrategy(
            forgiveness_probability=params.get("forgiveness_probability", 0.1)
        ),
        "RANDOM": lambda: RandomStrategy(
            cooperation_probability=params.get("cooperation_probability", 0.5)
        ),
        "GRIM": GrimTriggerStrategy,
        "PAVLOV": PavlovStrategy,
    }
    factory = registry.get(spec.identifier)
    if factory is None:
        raise ValueError(f"Unknown participant identifier: {spec.identifier}")
    return factory()


def apply_noise(action: int, noise_rate: float, rng: Random) -> int:
    """Flip an intended action with the configured probability."""
    if rng.random() < noise_rate:
        return DEFECT if action == COOPERATE else COOPERATE
    return action
