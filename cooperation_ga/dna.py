"""Typed bit-array DNA representation and genetic operators."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Final


DEFECT = 0
COOPERATE = 1
RANDOM = 2

ACTION_TO_TEXT: Final[dict[int, str]] = {COOPERATE: "C", DEFECT: "D", RANDOM: "R"}
TEXT_TO_ACTION: Final[dict[str, int]] = {value: key for key, value in ACTION_TO_TEXT.items()}

VERSION_BITS = 3
FAMILY_BITS = 5
PAYLOAD_LENGTH_BITS = 8
HEADER_BITS = VERSION_BITS + FAMILY_BITS + PAYLOAD_LENGTH_BITS
SUPPORTED_VERSION = 1

MAX_MEMORY = 3
MAX_FSM_STATES = 8

FAMILY_TO_CODE: Final[dict[str, int]] = {
    "LOOKUP": 0,
    "TRIGGER": 1,
    "COUNT_BASED": 2,
    "PROBABILISTIC_LOOKUP": 3,
    "FSM": 4,
    "SCRIPTED": 5,
    "COUNTER_TRIGGER": 6,
}
CODE_TO_FAMILY: Final[dict[int, str]] = {code: name for name, code in FAMILY_TO_CODE.items()}

LOOKUP_BITS = 2 + 2 + 8
TRIGGER_BITS = 2 + 2 + 2 + 4 + 8 + 8
COUNT_BASED_BITS = 2 + 8 + 8 + 2 + 1 + 1 + 8
PROB_LOOKUP_BITS = 8 + 2
FSM_BITS = 2 + 3 + 3 + 8
FSM_TRANSITION_BITS = 5
SCRIPTED_BITS = 8 + 24
COUNTER_TRIGGER_BITS = 2 + 2 + 2 + 4 + 8 + 8 + 8 + 1 + 1 + 8

STATE_ORDER: Final[list[tuple[int, int]]] = [
    (COOPERATE, COOPERATE),
    (COOPERATE, DEFECT),
    (DEFECT, COOPERATE),
    (DEFECT, DEFECT),
]
STATE_INDEX: Final[dict[tuple[int, int], int]] = {state: index for index, state in enumerate(STATE_ORDER)}

COUNT_MODE_ABSOLUTE = 0
COUNT_MODE_RATIO = 1

SCRIPT_ID_TO_NAME: Final[dict[int, str]] = {
    0: "NYDEGGER",
    1: "SHUBIK",
    2: "CHAMPION",
    3: "TULLOCK",
    4: "CYCLER_CCCCCD",
    5: "PROBER",
    6: "ADAPTIVE",
    7: "APAVLOV2006",
    8: "APAVLOV2011",
    9: "SECOND_BY_GROFMAN",
    10: "ADAPTOR_BRIEF",
    11: "ADAPTOR_LONG",
}
SCRIPT_NAME_TO_ID: Final[dict[str, int]] = {name: script_id for script_id, name in SCRIPT_ID_TO_NAME.items()}


@dataclass(frozen=True, slots=True)
class StrategyDNA:
    """Hashable validated bit-array strategy genome with typed payloads."""

    bits: tuple[int, ...]

    def __post_init__(self) -> None:
        """Validate binary bits, typed header fields, and payload shape."""
        if len(self.bits) < HEADER_BITS:
            raise ValueError("DNA bit array is shorter than the required header.")
        if any(bit not in (0, 1) for bit in self.bits):
            raise ValueError("DNA bits must be binary.")
        if self.version() != SUPPORTED_VERSION:
            raise ValueError(f"Unsupported DNA version: {self.version()}")
        if self.family_code() not in CODE_TO_FAMILY:
            raise ValueError("DNA family code is invalid.")
        if self.payload_length() != len(self.payload_bits()):
            raise ValueError("DNA payload length field does not match the stored bit array.")
        self._validate_payload()

    @property
    def genes(self) -> tuple[int, ...]:
        """Backward-compatible alias for the bit sequence."""
        return self.bits

    def version(self) -> int:
        """Return the encoded DNA format version."""
        return _bits_to_int(self.bits[:VERSION_BITS])

    def family_code(self) -> int:
        """Return the numeric family code."""
        start = VERSION_BITS
        end = start + FAMILY_BITS
        return _bits_to_int(self.bits[start:end])

    def family_name(self) -> str:
        """Return the symbolic family name."""
        return CODE_TO_FAMILY[self.family_code()]

    def payload_length(self) -> int:
        """Return the payload length encoded in the header."""
        start = VERSION_BITS + FAMILY_BITS
        end = start + PAYLOAD_LENGTH_BITS
        return _bits_to_int(self.bits[start:end])

    def payload_bits(self) -> tuple[int, ...]:
        """Return the payload bit slice."""
        return self.bits[HEADER_BITS:]

    def mutate(self, probability: float, rng: Random) -> "StrategyDNA":
        """Flip each bit independently with the given probability."""
        mutated = tuple((1 - bit) if rng.random() < probability else bit for bit in self.bits)
        return StrategyDNA(mutated)

    def crossover(self, other: "StrategyDNA", rng: Random) -> "StrategyDNA":
        """Perform safe crossover, falling back to parental inheritance when needed."""
        if len(self.bits) == len(other.bits):
            split = rng.randint(1, len(self.bits) - 1)
            try:
                return StrategyDNA(self.bits[:split] + other.bits[split:])
            except ValueError:
                pass
        if self.family_name() == other.family_name() and self.payload_length() == other.payload_length():
            mixed_payload = tuple(
                left if rng.random() < 0.5 else right
                for left, right in zip(self.payload_bits(), other.payload_bits())
            )
            try:
                return StrategyDNA(self.bits[:HEADER_BITS] + mixed_payload)
            except ValueError:
                pass
        return self if rng.random() < 0.5 else other

    @classmethod
    def random(cls, memory_depth: int, rng: Random) -> "StrategyDNA":
        """Generate a valid random DNA using the lookup-table family."""
        effective_memory = max(1, min(memory_depth, MAX_MEMORY))
        table = tuple(rng.choice((COOPERATE, DEFECT)) for _ in range(4**effective_memory))
        return cls.lookup_table(
            init_action=rng.choice((COOPERATE, DEFECT)),
            memory_depth=effective_memory,
            table_actions=table,
        )

    @classmethod
    def from_string(cls, bits: str) -> "StrategyDNA":
        """Create a genome from a raw bit string."""
        return cls(tuple(int(bit) for bit in bits))

    @classmethod
    def from_action_string(cls, actions: str) -> "StrategyDNA":
        """Create a deterministic memory-1 lookup-table genome from C/D/R shorthand."""
        if len(actions) != 5:
            raise ValueError("Action shorthand must contain INIT plus four state responses.")
        return cls.lookup_table(
            init_action=TEXT_TO_ACTION[actions[0]],
            memory_depth=1,
            table_actions=tuple(TEXT_TO_ACTION[action] for action in actions[1:]),
        )

    @classmethod
    def lookup_table(
        cls,
        init_action: int,
        memory_depth: int,
        table_actions: tuple[int, ...] | list[int],
        random_action_probability: float = 0.5,
    ) -> "StrategyDNA":
        """Create a lookup-table genome."""
        effective_memory = max(1, min(memory_depth, MAX_MEMORY))
        expected_entries = 4**effective_memory
        if len(table_actions) != expected_entries:
            raise ValueError(f"Lookup table requires {expected_entries} actions.")
        payload = (
            action_to_bits(init_action)
            + _int_to_bits(effective_memory, 2)
            + _int_to_bits(_probability_to_byte(random_action_probability), 8)
            + tuple(bit for action in table_actions for bit in action_to_bits(action))
        )
        return cls(_build_header("LOOKUP", len(payload)) + payload)

    @classmethod
    def trigger(
        cls,
        init_action: int,
        default_action: int,
        triggered_action: int,
        trigger_states: tuple[bool, bool, bool, bool],
        forgiveness_probability: float = 0.0,
        random_action_probability: float = 0.5,
    ) -> "StrategyDNA":
        """Create a trigger-based genome with persistent historical activation."""
        payload = (
            action_to_bits(init_action)
            + action_to_bits(default_action)
            + action_to_bits(triggered_action)
            + tuple(int(flag) for flag in trigger_states)
            + _int_to_bits(_probability_to_byte(forgiveness_probability), 8)
            + _int_to_bits(_probability_to_byte(random_action_probability), 8)
        )
        return cls(_build_header("TRIGGER", len(payload)) + payload)

    @classmethod
    def count_based(
        cls,
        init_action: int,
        window: int,
        threshold: int,
        comparison_mode: int = COUNT_MODE_ABSOLUTE,
        cooperate_if_ge: bool = True,
        random_action_probability: float = 0.5,
    ) -> "StrategyDNA":
        """Create a count-based genome that reacts to opponent cooperation statistics."""
        if comparison_mode not in {COUNT_MODE_ABSOLUTE, COUNT_MODE_RATIO}:
            raise ValueError("Unsupported count-based comparison mode.")
        payload = (
            action_to_bits(init_action)
            + _int_to_bits(window, 8)
            + _int_to_bits(threshold, 8)
            + _int_to_bits(comparison_mode, 2)
            + (int(cooperate_if_ge), 0)
            + _int_to_bits(_probability_to_byte(random_action_probability), 8)
        )
        return cls(_build_header("COUNT_BASED", len(payload)) + payload)

    @classmethod
    def probabilistic_lookup(
        cls,
        init_probability: float,
        memory_depth: int,
        table_probabilities: tuple[float, ...] | list[float],
    ) -> "StrategyDNA":
        """Create a probabilistic lookup-table genome."""
        effective_memory = max(1, min(memory_depth, MAX_MEMORY))
        expected_entries = 4**effective_memory
        if len(table_probabilities) != expected_entries:
            raise ValueError(f"Probabilistic lookup table requires {expected_entries} probabilities.")
        payload = (
            _int_to_bits(_probability_to_byte(init_probability), 8)
            + _int_to_bits(effective_memory, 2)
            + tuple(
                bit
                for probability in table_probabilities
                for bit in _int_to_bits(_probability_to_byte(probability), 8)
            )
        )
        return cls(_build_header("PROBABILISTIC_LOOKUP", len(payload)) + payload)

    @classmethod
    def fsm(
        cls,
        init_action: int,
        initial_state: int,
        transitions: tuple[tuple[int, int], ...] | list[tuple[int, int]],
        random_action_probability: float = 0.5,
    ) -> "StrategyDNA":
        """Create a finite-state-machine genome keyed by opponent last action."""
        state_count = len(transitions) // 2
        if state_count <= 0 or state_count > MAX_FSM_STATES:
            raise ValueError(f"FSM must use between 1 and {MAX_FSM_STATES} states.")
        if len(transitions) != state_count * 2:
            raise ValueError("FSM requires exactly two transitions per state.")
        if not 0 <= initial_state < state_count:
            raise ValueError("FSM initial_state is out of range.")
        payload = (
            action_to_bits(init_action)
            + _int_to_bits(state_count - 1, 3)
            + _int_to_bits(initial_state, 3)
            + _int_to_bits(_probability_to_byte(random_action_probability), 8)
            + tuple(
                bit
                for action, next_state in transitions
                for bit in (action_to_bits(action) + _int_to_bits(next_state, 3))
            )
        )
        return cls(_build_header("FSM", len(payload)) + payload)

    @classmethod
    def scripted(
        cls,
        script_name: str,
        parameter_a: int = 0,
        parameter_b: int = 0,
        parameter_c: int = 0,
    ) -> "StrategyDNA":
        """Create a scripted exact-strategy genome."""
        if script_name not in SCRIPT_NAME_TO_ID:
            raise ValueError(f"Unsupported scripted strategy: {script_name}")
        payload = (
            _int_to_bits(SCRIPT_NAME_TO_ID[script_name], 8)
            + _int_to_bits(parameter_a, 8)
            + _int_to_bits(parameter_b, 8)
            + _int_to_bits(parameter_c, 8)
        )
        return cls(_build_header("SCRIPTED", len(payload)) + payload)

    @classmethod
    def counter_trigger(
        cls,
        init_action: int,
        default_action: int,
        triggered_action: int,
        trigger_states: tuple[bool, bool, bool, bool],
        base_punishment_length: int,
        escalation_step: int = 1,
        max_punishment_length: int = 255,
        forgive_after_serving: bool = True,
        random_action_probability: float = 0.5,
    ) -> "StrategyDNA":
        """Create a trigger genome with explicit punishment counter semantics."""
        payload = (
            action_to_bits(init_action)
            + action_to_bits(default_action)
            + action_to_bits(triggered_action)
            + tuple(int(flag) for flag in trigger_states)
            + _int_to_bits(base_punishment_length, 8)
            + _int_to_bits(escalation_step, 8)
            + _int_to_bits(max_punishment_length, 8)
            + (int(forgive_after_serving), 0)
            + _int_to_bits(_probability_to_byte(random_action_probability), 8)
        )
        return cls(_build_header("COUNTER_TRIGGER", len(payload)) + payload)

    def to_string(self) -> str:
        """Render the raw genome as a bit string."""
        return "".join(str(bit) for bit in self.bits)

    def explain(self) -> str:
        """Return a human-readable explanation of the strategy encoded by this DNA."""
        family = self.family_name()
        names = baseline_name_by_dna_string().get(self.to_string())
        prefix = f"{names}: " if names else ""
        if family == "LOOKUP":
            memory = self.lookup_memory_depth()
            actions = self.lookup_table_actions()
            if memory == 1:
                state_table = ", ".join(
                    f"{_state_to_text(state)}->{ACTION_TO_TEXT[action]}"
                    for state, action in zip(STATE_ORDER, actions)
                )
                return (
                    f"{prefix}LOOKUP strategy with memory depth 1. "
                    f"Initial move {ACTION_TO_TEXT[self.lookup_init_action()]}; "
                    f"responses {state_table}. "
                    f"RANDOM actions cooperate with probability {self.lookup_random_action_probability():.3f}."
                )
            return (
                f"{prefix}LOOKUP strategy with memory depth {memory}. "
                f"Initial move {ACTION_TO_TEXT[self.lookup_init_action()]}; "
                f"table contains {len(actions)} action entries. "
                f"RANDOM actions cooperate with probability {self.lookup_random_action_probability():.3f}."
            )
        if family == "TRIGGER":
            trigger_states = ", ".join(
                _state_to_text(state)
                for state, active in zip(STATE_ORDER, self.trigger_states())
                if active
            ) or "none"
            return (
                f"{prefix}TRIGGER strategy. Initial move {ACTION_TO_TEXT[self.trigger_init_action()]}; "
                f"default action {ACTION_TO_TEXT[self.trigger_default_action()]}; "
                f"once triggered by states [{trigger_states}], plays "
                f"{ACTION_TO_TEXT[self.trigger_triggered_action()]}. "
                f"Forgiveness probability {self.trigger_forgiveness_probability():.3f}. "
                f"RANDOM actions cooperate with probability {self.trigger_random_action_probability():.3f}."
            )
        if family == "COUNT_BASED":
            mode = "absolute count" if self.count_based_mode() == COUNT_MODE_ABSOLUTE else "cooperation ratio"
            comparator = "cooperate" if self.count_based_cooperate_if_ge() else "defect"
            return (
                f"{prefix}COUNT_BASED strategy. Initial move {ACTION_TO_TEXT[self.count_based_init_action()]}; "
                f"uses {mode} over a window of "
                f"{'full history' if self.count_based_window() == 0 else self.count_based_window()} "
                f"with threshold {self.count_based_threshold()}; if the threshold is met, it will {comparator}. "
                f"RANDOM initial actions cooperate with probability {self.count_based_random_action_probability():.3f}."
            )
        if family == "PROBABILISTIC_LOOKUP":
            memory = self.prob_lookup_memory_depth()
            probabilities = self.prob_lookup_probabilities()
            if memory == 1:
                state_table = ", ".join(
                    f"{_state_to_text(state)}->{probability:.3f}"
                    for state, probability in zip(STATE_ORDER, probabilities)
                )
                return (
                    f"{prefix}PROBABILISTIC_LOOKUP strategy with memory depth 1. "
                    f"Initial cooperation probability {self.prob_lookup_init_probability():.3f}; "
                    f"per-state cooperation probabilities {state_table}."
                )
            return (
                f"{prefix}PROBABILISTIC_LOOKUP strategy with memory depth {memory}. "
                f"Initial cooperation probability {self.prob_lookup_init_probability():.3f}; "
                f"table contains {len(probabilities)} state probabilities."
            )
        if family == "FSM":
            transition_descriptions = []
            transitions = self.fsm_transitions()
            for state in range(self.fsm_state_count()):
                cooperate_action, cooperate_next = transitions[state * 2]
                defect_action, defect_next = transitions[state * 2 + 1]
                transition_descriptions.append(
                    f"S{state}: on C -> {ACTION_TO_TEXT[cooperate_action]}/S{cooperate_next}, "
                    f"on D -> {ACTION_TO_TEXT[defect_action]}/S{defect_next}"
                )
            return (
                f"{prefix}FSM strategy with {self.fsm_state_count()} states. "
                f"Initial move {ACTION_TO_TEXT[self.fsm_init_action()]}; "
                f"initial state S{self.fsm_initial_state()}. "
                f"RANDOM actions cooperate with probability {self.fsm_random_action_probability():.3f}. "
                + " ".join(transition_descriptions)
            )
        if family == "SCRIPTED":
            return (
                f"{prefix}SCRIPTED strategy `{self.script_name()}` with parameters "
                f"{self.script_parameters()}."
            )
        if family == "COUNTER_TRIGGER":
            trigger_states = ", ".join(
                _state_to_text(state)
                for state, active in zip(STATE_ORDER, self.counter_trigger_states())
                if active
            ) or "none"
            return (
                f"{prefix}COUNTER_TRIGGER strategy. Initial move {ACTION_TO_TEXT[self.counter_trigger_init_action()]}; "
                f"default action {ACTION_TO_TEXT[self.counter_trigger_default_action()]}; "
                f"triggered action {ACTION_TO_TEXT[self.counter_trigger_triggered_action()]}; "
                f"trigger states [{trigger_states}]; base punishment length "
                f"{self.counter_trigger_base_punishment_length()}, escalation "
                f"{self.counter_trigger_escalation_step()}, cap "
                f"{self.counter_trigger_max_punishment_length()}, forgive_after_serving="
                f"{self.counter_trigger_forgive_after_serving()}. "
                f"RANDOM actions cooperate with probability {self.counter_trigger_random_action_probability():.3f}."
            )
        return f"{prefix}{family} strategy."

    def to_action_string(self) -> str:
        """Render deterministic memory-1 lookup/trigger DNA as action shorthand when possible."""
        family = self.family_name()
        if family == "LOOKUP" and self.lookup_memory_depth() == 1:
            return ACTION_TO_TEXT[self.lookup_init_action()] + "".join(
                ACTION_TO_TEXT[action] for action in self.lookup_table_actions()
            )
        if family == "TRIGGER":
            return f"TRIGGER[{ACTION_TO_TEXT[self.trigger_init_action()]}]"
        if family == "COUNT_BASED":
            return f"COUNT[{ACTION_TO_TEXT[self.count_based_init_action()]}]"
        if family == "PROBABILISTIC_LOOKUP" and self.prob_lookup_memory_depth() == 1:
            probabilities = ",".join(f"{prob:.2f}" for prob in self.prob_lookup_probabilities())
            return f"PLOOKUP[{self.prob_lookup_init_probability():.2f};{probabilities}]"
        if family == "FSM":
            return f"FSM[{ACTION_TO_TEXT[self.fsm_init_action()]}]"
        if family == "SCRIPTED":
            return f"SCRIPTED[{self.script_name()}]"
        if family == "COUNTER_TRIGGER":
            return f"CTRIGGER[{ACTION_TO_TEXT[self.counter_trigger_init_action()]}]"
        return self.to_string()

    def lookup_init_action(self) -> int:
        """Return the lookup-family initial action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[:2])

    def lookup_memory_depth(self) -> int:
        """Return the decoded lookup-memory depth."""
        payload = self.payload_bits()
        return max(1, min(_bits_to_int(payload[2:4]), MAX_MEMORY))

    def lookup_random_action_probability(self) -> float:
        """Return the lookup-family probability used for RANDOM action genes."""
        payload = self.payload_bits()
        return _bits_to_int(payload[4:12]) / 255.0

    def lookup_table_actions(self) -> tuple[int, ...]:
        """Return the decoded lookup table."""
        payload = self.payload_bits()
        actions = payload[12:]
        return tuple(_action_from_bits(actions[index : index + 2]) for index in range(0, len(actions), 2))

    def action_for_history(self, own_history: list[int], opp_history: list[int]) -> int:
        """Return the lookup-family action for the observed history."""
        memory = self.lookup_memory_depth()
        if len(own_history) < memory or len(opp_history) < memory:
            return self.lookup_init_action()
        index = 0
        for own_move, opp_move in zip(own_history[-memory:], opp_history[-memory:]):
            index = index * 4 + STATE_INDEX[(own_move, opp_move)]
        return self.lookup_table_actions()[index]

    def trigger_init_action(self) -> int:
        """Return the trigger-family initial action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[:2])

    def trigger_default_action(self) -> int:
        """Return the pre-trigger action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[2:4])

    def trigger_triggered_action(self) -> int:
        """Return the post-trigger action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[4:6])

    def trigger_states(self) -> tuple[bool, bool, bool, bool]:
        """Return the state mask that activates the trigger."""
        payload = self.payload_bits()
        return tuple(bool(bit) for bit in payload[6:10])  # type: ignore[return-value]

    def trigger_forgiveness_probability(self) -> float:
        """Return the trigger-family forgiveness probability."""
        payload = self.payload_bits()
        return _bits_to_int(payload[10:18]) / 255.0

    def trigger_random_action_probability(self) -> float:
        """Return the trigger-family probability used for RANDOM action genes."""
        payload = self.payload_bits()
        return _bits_to_int(payload[18:26]) / 255.0

    def count_based_init_action(self) -> int:
        """Return the count-based initial action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[:2])

    def count_based_window(self) -> int:
        """Return the count-based lookback window, with zero meaning full history."""
        payload = self.payload_bits()
        return _bits_to_int(payload[2:10])

    def count_based_threshold(self) -> int:
        """Return the count threshold or ratio byte."""
        payload = self.payload_bits()
        return _bits_to_int(payload[10:18])

    def count_based_mode(self) -> int:
        """Return the count-based comparison mode."""
        payload = self.payload_bits()
        return _bits_to_int(payload[18:20])

    def count_based_cooperate_if_ge(self) -> bool:
        """Return whether the strategy cooperates when the threshold condition is met."""
        payload = self.payload_bits()
        return bool(payload[20])

    def count_based_random_action_probability(self) -> float:
        """Return the count-based probability used for RANDOM initial actions."""
        payload = self.payload_bits()
        return _bits_to_int(payload[22:30]) / 255.0

    def prob_lookup_init_probability(self) -> float:
        """Return the initial cooperation probability."""
        payload = self.payload_bits()
        return _bits_to_int(payload[:8]) / 255.0

    def prob_lookup_memory_depth(self) -> int:
        """Return the probabilistic lookup memory depth."""
        payload = self.payload_bits()
        return max(1, min(_bits_to_int(payload[8:10]), MAX_MEMORY))

    def prob_lookup_probabilities(self) -> tuple[float, ...]:
        """Return the state probabilities for probabilistic lookup."""
        payload = self.payload_bits()[10:]
        return tuple(_bits_to_int(payload[index : index + 8]) / 255.0 for index in range(0, len(payload), 8))

    def probability_for_history(self, own_history: list[int], opp_history: list[int]) -> float:
        """Return the cooperation probability for the observed history."""
        memory = self.prob_lookup_memory_depth()
        if len(own_history) < memory or len(opp_history) < memory:
            return self.prob_lookup_init_probability()
        index = 0
        for own_move, opp_move in zip(own_history[-memory:], opp_history[-memory:]):
            index = index * 4 + STATE_INDEX[(own_move, opp_move)]
        return self.prob_lookup_probabilities()[index]

    def fsm_init_action(self) -> int:
        """Return the FSM initial action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[:2])

    def fsm_state_count(self) -> int:
        """Return the FSM number of states."""
        payload = self.payload_bits()
        return _bits_to_int(payload[2:5]) + 1

    def fsm_initial_state(self) -> int:
        """Return the initial FSM state."""
        payload = self.payload_bits()
        return _bits_to_int(payload[5:8])

    def fsm_random_action_probability(self) -> float:
        """Return the FSM-family probability used for RANDOM action genes."""
        payload = self.payload_bits()
        return _bits_to_int(payload[8:16]) / 255.0

    def fsm_transitions(self) -> tuple[tuple[int, int], ...]:
        """Return FSM transitions as (action, next_state) pairs."""
        payload = self.payload_bits()[16:]
        transitions = []
        for index in range(0, len(payload), FSM_TRANSITION_BITS):
            action = _action_from_bits(payload[index : index + 2])
            next_state = _bits_to_int(payload[index + 2 : index + 5])
            transitions.append((action, next_state))
        return tuple(transitions)

    def fsm_action_for_history(self, opp_history: list[int]) -> int:
        """Return the FSM action determined by replaying the opponent history."""
        if not opp_history:
            return self.fsm_init_action()
        state = self.fsm_initial_state()
        action = self.fsm_init_action()
        transitions = self.fsm_transitions()
        for opponent_action in opp_history:
            transition_index = state * 2 + (0 if opponent_action == COOPERATE else 1)
            action, state = transitions[transition_index]
        return action

    def script_name(self) -> str:
        """Return the scripted strategy identifier."""
        payload = self.payload_bits()
        script_id = _bits_to_int(payload[:8])
        if script_id not in SCRIPT_ID_TO_NAME:
            raise ValueError("Scripted DNA contains an invalid script id.")
        return SCRIPT_ID_TO_NAME[script_id]

    def script_parameters(self) -> tuple[int, int, int]:
        """Return the three script parameter bytes."""
        payload = self.payload_bits()
        return (
            _bits_to_int(payload[8:16]),
            _bits_to_int(payload[16:24]),
            _bits_to_int(payload[24:32]),
        )

    def counter_trigger_init_action(self) -> int:
        """Return the counter-trigger initial action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[:2])

    def counter_trigger_default_action(self) -> int:
        """Return the counter-trigger default action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[2:4])

    def counter_trigger_triggered_action(self) -> int:
        """Return the counter-trigger punishment action."""
        payload = self.payload_bits()
        return _action_from_bits(payload[4:6])

    def counter_trigger_states(self) -> tuple[bool, bool, bool, bool]:
        """Return the trigger states for the counter-trigger family."""
        payload = self.payload_bits()
        return tuple(bool(bit) for bit in payload[6:10])  # type: ignore[return-value]

    def counter_trigger_base_punishment_length(self) -> int:
        """Return the base punishment length."""
        payload = self.payload_bits()
        return _bits_to_int(payload[10:18])

    def counter_trigger_escalation_step(self) -> int:
        """Return the punishment escalation step."""
        payload = self.payload_bits()
        return _bits_to_int(payload[18:26])

    def counter_trigger_max_punishment_length(self) -> int:
        """Return the punishment length cap."""
        payload = self.payload_bits()
        return _bits_to_int(payload[26:34])

    def counter_trigger_forgive_after_serving(self) -> bool:
        """Return whether the strategy resumes default behavior after punishment."""
        payload = self.payload_bits()
        return bool(payload[34])

    def counter_trigger_random_action_probability(self) -> float:
        """Return the counter-trigger probability used for RANDOM action genes."""
        payload = self.payload_bits()
        return _bits_to_int(payload[36:44]) / 255.0

    def _validate_payload(self) -> None:
        """Validate the family-specific payload layout."""
        family = self.family_name()
        payload = self.payload_bits()
        if family == "LOOKUP":
            if len(payload) < LOOKUP_BITS:
                raise ValueError("Lookup payload is too short.")
            memory = max(1, min(_bits_to_int(payload[2:4]), MAX_MEMORY))
            expected = LOOKUP_BITS + 2 * (4**memory)
            if len(payload) != expected:
                raise ValueError("Lookup payload length is inconsistent with memory depth.")
            _validate_action_bits(payload[:2])
            for index in range(12, len(payload), 2):
                _validate_action_bits(payload[index : index + 2])
            return
        if family == "TRIGGER":
            if len(payload) != TRIGGER_BITS:
                raise ValueError("Trigger payload has invalid length.")
            _validate_action_bits(payload[:2])
            _validate_action_bits(payload[2:4])
            _validate_action_bits(payload[4:6])
            return
        if family == "COUNT_BASED":
            if len(payload) != COUNT_BASED_BITS:
                raise ValueError("Count-based payload has invalid length.")
            _validate_action_bits(payload[:2])
            if _bits_to_int(payload[18:20]) not in {COUNT_MODE_ABSOLUTE, COUNT_MODE_RATIO}:
                raise ValueError("Count-based comparison mode is invalid.")
            return
        if family == "PROBABILISTIC_LOOKUP":
            if len(payload) < PROB_LOOKUP_BITS:
                raise ValueError("Probabilistic lookup payload is too short.")
            memory = max(1, min(_bits_to_int(payload[8:10]), MAX_MEMORY))
            expected = PROB_LOOKUP_BITS + 8 * (4**memory)
            if len(payload) != expected:
                raise ValueError("Probabilistic lookup payload length is inconsistent with memory depth.")
            return
        if family == "FSM":
            if len(payload) < FSM_BITS:
                raise ValueError("FSM payload is too short.")
            state_count = _bits_to_int(payload[2:5]) + 1
            initial_state = _bits_to_int(payload[5:8])
            expected = FSM_BITS + FSM_TRANSITION_BITS * state_count * 2
            if len(payload) != expected:
                raise ValueError("FSM payload has invalid length.")
            if initial_state >= state_count:
                raise ValueError("FSM initial_state exceeds state count.")
            _validate_action_bits(payload[:2])
            for index in range(16, len(payload), FSM_TRANSITION_BITS):
                _validate_action_bits(payload[index : index + 2])
                next_state = _bits_to_int(payload[index + 2 : index + 5])
                if next_state >= state_count:
                    raise ValueError("FSM transition points to an invalid state.")
            return
        if family == "SCRIPTED":
            if len(payload) != SCRIPTED_BITS:
                raise ValueError("Scripted payload has invalid length.")
            if _bits_to_int(payload[:8]) not in SCRIPT_ID_TO_NAME:
                raise ValueError("Scripted payload contains an invalid script id.")
            return
        if family == "COUNTER_TRIGGER":
            if len(payload) != COUNTER_TRIGGER_BITS:
                raise ValueError("Counter-trigger payload has invalid length.")
            _validate_action_bits(payload[:2])
            _validate_action_bits(payload[2:4])
            _validate_action_bits(payload[4:6])
            return
        raise ValueError(f"Unsupported DNA family: {family}")


def baseline_dna_library() -> dict[str, StrategyDNA]:
    """Return predefined baseline strategies encoded as typed DNA."""
    return {
        "ALLC": StrategyDNA.lookup_table(COOPERATE, 1, (COOPERATE, COOPERATE, COOPERATE, COOPERATE)),
        "ALLD": StrategyDNA.lookup_table(DEFECT, 1, (DEFECT, DEFECT, DEFECT, DEFECT)),
        "TFT": StrategyDNA.lookup_table(COOPERATE, 1, (COOPERATE, DEFECT, COOPERATE, DEFECT)),
        "TF2T": StrategyDNA.lookup_table(
            COOPERATE,
            2,
            tuple(
                DEFECT if states[-1] in {1, 3} and states[-2] in {1, 3} else COOPERATE
                for states in (
                    ((index // 4) % 4, index % 4) for index in range(16)
                )
            ),
        ),
        "PAVLOV": StrategyDNA.lookup_table(COOPERATE, 1, (COOPERATE, DEFECT, DEFECT, COOPERATE)),
        "RANDOM": StrategyDNA.probabilistic_lookup(0.5, 1, (0.5, 0.5, 0.5, 0.5)),
        "JOSS": StrategyDNA.probabilistic_lookup(1.0, 1, (0.9, 0.0, 0.9, 0.0)),
        "GTFT": StrategyDNA.probabilistic_lookup(1.0, 1, (1.0, 1 / 3, 1.0, 1 / 3)),
        "SUSPICIOUS_TFT": StrategyDNA.lookup_table(DEFECT, 1, (COOPERATE, DEFECT, COOPERATE, DEFECT)),
        "SUSPICIOUS_PAVLOV": StrategyDNA.lookup_table(DEFECT, 1, (COOPERATE, DEFECT, DEFECT, COOPERATE)),
        "GRUDGER": StrategyDNA.trigger(
            init_action=COOPERATE,
            default_action=COOPERATE,
            triggered_action=DEFECT,
            trigger_states=(False, True, False, True),
        ),
        "NYDEGGER": StrategyDNA.scripted("NYDEGGER"),
        "SHUBIK": StrategyDNA.scripted("SHUBIK"),
        "CHAMPION": StrategyDNA.scripted("CHAMPION"),
        "TULLOCK": StrategyDNA.scripted("TULLOCK"),
        "PROBER": StrategyDNA.scripted("PROBER"),
        "ADAPTIVE": StrategyDNA.scripted("ADAPTIVE"),
        "APAVLOV2006": StrategyDNA.scripted("APAVLOV2006"),
        "APAVLOV2011": StrategyDNA.scripted("APAVLOV2011"),
        "SECOND_BY_GROFMAN": StrategyDNA.scripted("SECOND_BY_GROFMAN"),
        "ADAPTOR_BRIEF": StrategyDNA.scripted("ADAPTOR_BRIEF"),
        "ADAPTOR_LONG": StrategyDNA.scripted("ADAPTOR_LONG"),
        "SHUBIK_COUNTER": StrategyDNA.counter_trigger(
            init_action=COOPERATE,
            default_action=COOPERATE,
            triggered_action=DEFECT,
            trigger_states=(False, True, False, True),
            base_punishment_length=1,
            escalation_step=1,
            max_punishment_length=255,
            forgive_after_serving=True,
        ),
        "REVERSE_TFT": StrategyDNA.lookup_table(COOPERATE, 1, (DEFECT, DEFECT, COOPERATE, DEFECT)),
        "ALTERNATOR": StrategyDNA.fsm(
            init_action=COOPERATE,
            initial_state=0,
            transitions=((DEFECT, 1), (DEFECT, 1), (COOPERATE, 0), (COOPERATE, 0)),
        ),
        "CYCLER_CCD": StrategyDNA.fsm(
            init_action=COOPERATE,
            initial_state=0,
            transitions=(
                (COOPERATE, 1), (COOPERATE, 1),
                (DEFECT, 2), (DEFECT, 2),
                (COOPERATE, 0), (COOPERATE, 0),
            ),
        ),
        "CYCLER_CCCD": StrategyDNA.fsm(
            init_action=COOPERATE,
            initial_state=0,
            transitions=(
                (COOPERATE, 1), (COOPERATE, 1),
                (COOPERATE, 2), (COOPERATE, 2),
                (DEFECT, 3), (DEFECT, 3),
                (COOPERATE, 0), (COOPERATE, 0),
            ),
        ),
        "CYCLER_CCCCD": StrategyDNA.fsm(
            init_action=COOPERATE,
            initial_state=0,
            transitions=(
                (COOPERATE, 1), (COOPERATE, 1),
                (COOPERATE, 2), (COOPERATE, 2),
                (COOPERATE, 3), (COOPERATE, 3),
                (DEFECT, 4), (DEFECT, 4),
                (COOPERATE, 0), (COOPERATE, 0),
            ),
        ),
        "CYCLER_CCCCCD": StrategyDNA.scripted("CYCLER_CCCCCD"),
        "SUSPICIOUS_ALTERNATOR": StrategyDNA.fsm(
            init_action=DEFECT,
            initial_state=0,
            transitions=((COOPERATE, 1), (COOPERATE, 1), (DEFECT, 0), (DEFECT, 0)),
        ),
        "APPEASER": StrategyDNA.fsm(
            init_action=COOPERATE,
            initial_state=0,
            transitions=((COOPERATE, 0), (DEFECT, 1), (DEFECT, 1), (COOPERATE, 0)),
        ),
        "GO_BY_MAJORITY": StrategyDNA.count_based(
            init_action=COOPERATE,
            window=0,
            threshold=128,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "HARD_GO_BY_MAJORITY": StrategyDNA.count_based(
            init_action=DEFECT,
            window=0,
            threshold=129,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "GO_BY_MAJORITY_5": StrategyDNA.count_based(
            init_action=COOPERATE,
            window=5,
            threshold=128,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "GO_BY_MAJORITY_10": StrategyDNA.count_based(
            init_action=COOPERATE,
            window=10,
            threshold=128,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "GO_BY_MAJORITY_20": StrategyDNA.count_based(
            init_action=COOPERATE,
            window=20,
            threshold=128,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "GO_BY_MAJORITY_40": StrategyDNA.count_based(
            init_action=COOPERATE,
            window=40,
            threshold=128,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "HARD_GO_BY_MAJORITY_5": StrategyDNA.count_based(
            init_action=DEFECT,
            window=5,
            threshold=129,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "HARD_GO_BY_MAJORITY_10": StrategyDNA.count_based(
            init_action=DEFECT,
            window=10,
            threshold=129,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "HARD_GO_BY_MAJORITY_20": StrategyDNA.count_based(
            init_action=DEFECT,
            window=20,
            threshold=129,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "HARD_GO_BY_MAJORITY_40": StrategyDNA.count_based(
            init_action=DEFECT,
            window=40,
            threshold=129,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        ),
        "FORGIVER": StrategyDNA.lookup_table(COOPERATE, 1, (COOPERATE, COOPERATE, COOPERATE, DEFECT)),
        "DEFENSIVE": StrategyDNA.lookup_table(DEFECT, 1, (DEFECT, DEFECT, DEFECT, COOPERATE)),
        "PROBER_LIKE": StrategyDNA.fsm(
            init_action=DEFECT,
            initial_state=0,
            transitions=((COOPERATE, 1), (COOPERATE, 1), (COOPERATE, 1), (COOPERATE, 1)),
        ),
        "HARD_REVENGER": StrategyDNA.lookup_table(COOPERATE, 1, (DEFECT, DEFECT, DEFECT, DEFECT)),
        "TESTER": StrategyDNA.lookup_table(DEFECT, 1, (COOPERATE, COOPERATE, DEFECT, COOPERATE)),
    }


def baseline_name_by_dna_string() -> dict[str, str]:
    """Return a reverse mapping from raw DNA bit strings to baseline names."""
    return {dna.to_string(): name for name, dna in baseline_dna_library().items()}


def default_genome_length(memory_depth: int = 1) -> int:
    """Return the default random-lookup genome length for configuration defaults."""
    return HEADER_BITS + LOOKUP_BITS + 2 * (4**max(1, min(memory_depth, MAX_MEMORY)))


def explain_dna(raw_dna: str) -> str:
    """Decode a raw DNA bit string into a human-readable explanation."""
    return StrategyDNA.from_string(raw_dna).explain()


def _build_header(family_name: str, payload_length: int) -> tuple[int, ...]:
    """Build a common DNA header."""
    return (
        _int_to_bits(SUPPORTED_VERSION, VERSION_BITS)
        + _int_to_bits(FAMILY_TO_CODE[family_name], FAMILY_BITS)
        + _int_to_bits(payload_length, PAYLOAD_LENGTH_BITS)
    )


def _int_to_bits(value: int, width: int) -> tuple[int, ...]:
    """Encode an integer into a fixed-width bit tuple."""
    if not 0 <= value < 2**width:
        raise ValueError(f"Value {value} does not fit in {width} bits.")
    return tuple((value >> shift) & 1 for shift in range(width - 1, -1, -1))


def _bits_to_int(bits: tuple[int, ...] | list[int]) -> int:
    """Decode a bit sequence into an integer."""
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def _probability_to_byte(value: float) -> int:
    """Quantize a probability into one byte."""
    if not 0.0 <= value <= 1.0:
        raise ValueError("Probability must be between 0 and 1.")
    return round(value * 255)


def action_to_bits(action: int) -> tuple[int, int]:
    """Encode an action code into two bits."""
    mapping: dict[int, tuple[int, int]] = {
        COOPERATE: (0, 0),
        DEFECT: (0, 1),
        RANDOM: (1, 0),
    }
    if action not in mapping:
        raise ValueError(f"Unsupported action code: {action}")
    return mapping[action]


def _action_from_bits(bits: tuple[int, ...] | list[int]) -> int:
    """Decode two bits into an action code."""
    mapping: dict[tuple[int, int], int] = {
        (0, 0): COOPERATE,
        (0, 1): DEFECT,
        (1, 0): RANDOM,
    }
    if len(bits) != 2:
        raise ValueError("Action bits must contain exactly two bits.")
    key: tuple[int, int] = (bits[0], bits[1])
    if key not in mapping:
        raise ValueError("Action bits contain a prohibited encoding.")
    return mapping[key]


def _validate_action_bits(bits: tuple[int, ...] | list[int]) -> None:
    """Validate a two-bit action encoding."""
    _action_from_bits(bits)


def _state_to_text(state: tuple[int, int]) -> str:
    """Render a state tuple as CC/CD/DC/DD shorthand."""
    return f"{ACTION_TO_TEXT[state[0]]}{ACTION_TO_TEXT[state[1]]}"
