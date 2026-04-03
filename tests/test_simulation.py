"""Unit and behavioral tests for the simulator."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from math import ceil
from pathlib import Path
from random import Random
import unittest

from cooperation_ga.config import SimulationConfig, VisualizationConfig
from cooperation_ga.axelrod_mapping import axelrod_strategy_mappings
from cooperation_ga.dna import (
    COOPERATE,
    COUNT_MODE_RATIO,
    DEFECT,
    RANDOM,
    StrategyDNA,
    baseline_dna_library,
    default_genome_length,
    explain_dna,
)
from cooperation_ga.evolution import EvolutionEngine
from cooperation_ga.game import PayoffMatrix, simulate_match
from cooperation_ga.metrics import GenerationMetrics, final_population_summary_rows, load_metrics_json, strategy_name_by_dna
from cooperation_ga.population import Population
from cooperation_ga.strategy import DnaStrategy, GrimTriggerStrategy, ParticipantSpec, RandomStrategy
from cooperation_ga.tournament import run_interactions


class DnaTests(unittest.TestCase):
    def test_mutation_preserves_genome_at_probability_zero(self) -> None:
        dna = StrategyDNA.from_action_string("CCDDD")
        mutated = dna.mutate(0.0, Random(0))
        self.assertEqual(mutated.to_string(), dna.to_string())

    def test_one_point_crossover_preserves_gene_length(self) -> None:
        dna_a = StrategyDNA.from_action_string("CCCCC")
        dna_b = StrategyDNA.from_action_string("DDDDD")
        child = dna_a.crossover(dna_b, Random(1))
        self.assertEqual(len(child.genes), default_genome_length())
        self.assertTrue(set(child.genes).issubset({0, 1}))

    def test_pavlov_dna_mapping_produces_correct_table(self) -> None:
        self.assertEqual(baseline_dna_library()["PAVLOV"].to_action_string(), "CCDDC")

    def test_invalid_mode_bits_are_rejected(self) -> None:
        invalid_bits = list(baseline_dna_library()["ALLC"].genes)
        invalid_bits[3:8] = [1, 1, 1, 1, 1]
        with self.assertRaises(ValueError):
            StrategyDNA(tuple(invalid_bits))

    def test_axelrod_mapping_contains_exact_and_unsupported_entries(self) -> None:
        mappings = axelrod_strategy_mappings()
        levels = {mapping.support_level for mapping in mappings}
        self.assertIn("exact", levels)
        self.assertIn("approximate", levels)
        self.assertIn("unsupported", levels)
        self.assertTrue(any(mapping.axelrod_name == "Tit For Tat" and mapping.support_level == "exact" for mapping in mappings))
        self.assertTrue(any(mapping.axelrod_name == "Cycler CCCCD" and mapping.support_level == "exact" for mapping in mappings))

    def test_baseline_library_has_unique_dna_per_name(self) -> None:
        library = baseline_dna_library()
        raw_dna = [dna.to_string() for dna in library.values()]
        self.assertEqual(len(raw_dna), len(set(raw_dna)))

    def test_explain_dna_decodes_lookup_strategy(self) -> None:
        dna = baseline_dna_library()["TFT"]
        explanation = explain_dna(dna.to_string())
        self.assertIn("TFT", explanation)
        self.assertIn("LOOKUP strategy", explanation)
        self.assertIn("CC->C", explanation)

    def test_explain_dna_decodes_scripted_strategy(self) -> None:
        dna = baseline_dna_library()["NYDEGGER"]
        explanation = explain_dna(dna.to_string())
        self.assertIn("NYDEGGER", explanation)
        self.assertIn("SCRIPTED strategy", explanation)

    def test_strategy_name_by_dna_assigns_hybrid_labels_to_novel_dna(self) -> None:
        tft = baseline_dna_library()["TFT"].to_string()
        hybrid = StrategyDNA.random(1, Random(11)).to_string()
        while hybrid == tft:
            hybrid = StrategyDNA.random(1, Random(12)).to_string()
        metrics = [
            GenerationMetrics(
                step=1,
                total_population_size=3,
                num_unique_strategies=2,
                population_count_per_dna={tft: 2, hybrid: 1},
                dominant_dna=tft,
                dominant_group_size=2,
                average_score=1.0,
                best_score=1.0,
                worst_score=1.0,
                score_distribution={"1": 3},
                overall_cooperation_rate=0.5,
                overall_defection_rate=0.5,
                diversity_entropy=1.0,
                dominant_strategy_share=2 / 3,
                matches_played=1,
                deaths_this_step=0,
                births_this_step=0,
                reproduction_step=False,
                mutation_count=0,
                crossover_count=0,
            )
        ]
        names = strategy_name_by_dna(metrics)
        self.assertIn("TFT", names[tft])
        self.assertEqual(names[hybrid], "Hybrid1")

    def test_final_population_summary_rows_include_names_counts_and_explanations(self) -> None:
        allc = baseline_dna_library()["ALLC"].to_string()
        hybrid = StrategyDNA.random(1, Random(21)).to_string()
        while hybrid == allc:
            hybrid = StrategyDNA.random(1, Random(22)).to_string()
        rows = final_population_summary_rows(
            [
                GenerationMetrics(
                    step=2,
                    total_population_size=7,
                    num_unique_strategies=2,
                    population_count_per_dna={hybrid: 4, allc: 3},
                    dominant_dna=hybrid,
                    dominant_group_size=4,
                    average_score=1.0,
                    best_score=1.0,
                    worst_score=1.0,
                    score_distribution={"1": 7},
                    overall_cooperation_rate=0.5,
                    overall_defection_rate=0.5,
                    diversity_entropy=1.0,
                    dominant_strategy_share=4 / 7,
                    matches_played=3,
                    deaths_this_step=0,
                    births_this_step=0,
                    reproduction_step=False,
                    mutation_count=0,
                    crossover_count=0,
                )
            ]
        )
        self.assertEqual(rows[0]["strategy_name"], "Hybrid1")
        self.assertEqual(rows[0]["population"], 4)
        self.assertEqual(rows[1]["strategy_name"], "ALLC")
        self.assertIn("strategy", str(rows[0]["strategy_explanation"]).lower())

    def test_metrics_json_roundtrip_loads_generation_metrics(self) -> None:
        metric = GenerationMetrics(
            step=1,
            total_population_size=3,
            num_unique_strategies=1,
            population_count_per_dna={baseline_dna_library()["ALLC"].to_string(): 3},
            dominant_dna=baseline_dna_library()["ALLC"].to_string(),
            dominant_group_size=3,
            average_score=1.0,
            best_score=1.0,
            worst_score=1.0,
            score_distribution={"1": 3},
            overall_cooperation_rate=1.0,
            overall_defection_rate=0.0,
            diversity_entropy=0.0,
            dominant_strategy_share=1.0,
            matches_played=1,
            deaths_this_step=0,
            births_this_step=0,
            reproduction_step=False,
            mutation_count=0,
            crossover_count=0,
        )
        path = Path("test_output_visuals/metrics_roundtrip.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '[{"step": 1, "total_population_size": 3, "num_unique_strategies": 1, '
            f'"population_count_per_dna": {{"{metric.dominant_dna}": 3}}, '
            f'"dominant_dna": "{metric.dominant_dna}", '
            '"dominant_group_size": 3, "average_score": 1.0, "best_score": 1.0, "worst_score": 1.0, '
            '"score_distribution": {"1": 3}, "overall_cooperation_rate": 1.0, "overall_defection_rate": 0.0, '
            '"diversity_entropy": 0.0, "dominant_strategy_share": 1.0, "matches_played": 1, '
            '"deaths_this_step": 0, "births_this_step": 0, "reproduction_step": false, '
            '"mutation_count": 0, "crossover_count": 0}]',
            encoding="utf-8",
        )
        loaded = load_metrics_json(path)
        self.assertEqual(loaded, [metric])

    def test_simulation_and_visualization_configs_can_load_same_json(self) -> None:
        path = Path("test_output_visuals/config_split_roundtrip.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            """{
  "num_steps": 3,
  "output_dir": "demo_output",
  "export_visuals": true,
  "top_strategies_to_plot": 7,
  "viz_title_text": "Demo"
}""",
            encoding="utf-8",
        )
        simulation = SimulationConfig.from_json(path)
        visualization = VisualizationConfig.from_json(path)
        self.assertEqual(simulation.num_steps, 3)
        self.assertEqual(simulation.output_dir, "demo_output")
        self.assertEqual(visualization.output_dir, "demo_output")
        self.assertEqual(visualization.top_strategies_to_plot, 7)
        self.assertEqual(visualization.viz_title_text, "Demo")


class StrategyTests(unittest.TestCase):
    def test_decision_lookup_uses_previous_round_state(self) -> None:
        dna = StrategyDNA.from_action_string("CDDCC")
        strategy = DnaStrategy(dna)
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(strategy.next_move([COOPERATE], [DEFECT], Random(0), strategy.initial_state())[0], DEFECT)

    def test_trigger_dna_defects_after_betrayal(self) -> None:
        dna = StrategyDNA.trigger(
            init_action=COOPERATE,
            default_action=COOPERATE,
            triggered_action=DEFECT,
            trigger_states=(False, True, False, True),
        )
        strategy = DnaStrategy(dna)
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(strategy.next_move([COOPERATE], [COOPERATE], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(
            strategy.next_move([COOPERATE, COOPERATE], [COOPERATE, DEFECT], Random(0), strategy.initial_state())[0],
            DEFECT,
        )

    def test_probabilistic_lookup_uses_encoded_probability(self) -> None:
        dna = StrategyDNA.probabilistic_lookup(0.75, 1, (0.75, 0.75, 0.75, 0.75))
        strategy = DnaStrategy(dna)
        rng = Random(3)
        coop = sum(strategy.next_move([], [], rng, strategy.initial_state())[0] == COOPERATE for _ in range(1000))
        self.assertGreater(coop / 1000, 0.7)
        self.assertLess(coop / 1000, 0.8)

    def test_count_based_strategy_uses_recent_opponent_ratio(self) -> None:
        dna = StrategyDNA.count_based(
            init_action=COOPERATE,
            window=4,
            threshold=128,
            comparison_mode=COUNT_MODE_RATIO,
            cooperate_if_ge=True,
        )
        strategy = DnaStrategy(dna)
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(
            strategy.next_move(
                [COOPERATE, COOPERATE, COOPERATE, COOPERATE],
                [COOPERATE, COOPERATE, DEFECT, DEFECT],
                Random(0),
                strategy.initial_state(),
            )[0],
            COOPERATE,
        )
        self.assertEqual(
            strategy.next_move(
                [COOPERATE, COOPERATE, COOPERATE, COOPERATE],
                [DEFECT, DEFECT, DEFECT, DEFECT],
                Random(0),
                strategy.initial_state(),
            )[0],
            DEFECT,
        )

    def test_fsm_strategy_can_alternate(self) -> None:
        dna = baseline_dna_library()["ALTERNATOR"]
        strategy = DnaStrategy(dna)
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(strategy.next_move([COOPERATE], [COOPERATE], Random(0), strategy.initial_state())[0], DEFECT)
        self.assertEqual(
            strategy.next_move([COOPERATE, DEFECT], [COOPERATE, COOPERATE], Random(0), strategy.initial_state())[0],
            COOPERATE,
        )

    def test_tf2t_defects_only_after_two_consecutive_defections(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["TF2T"])
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(
            strategy.next_move([COOPERATE, COOPERATE], [COOPERATE, DEFECT], Random(0), strategy.initial_state())[0],
            COOPERATE,
        )
        self.assertEqual(
            strategy.next_move(
                [COOPERATE, COOPERATE, COOPERATE],
                [COOPERATE, DEFECT, DEFECT],
                Random(0),
                strategy.initial_state(),
            )[0],
            DEFECT,
        )

    def test_suspicious_tft_starts_with_defection_then_mirrors(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["SUSPICIOUS_TFT"])
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], DEFECT)
        self.assertEqual(
            strategy.next_move([DEFECT], [COOPERATE], Random(0), strategy.initial_state())[0],
            COOPERATE,
        )
        self.assertEqual(
            strategy.next_move([DEFECT, COOPERATE], [COOPERATE, DEFECT], Random(0), strategy.initial_state())[0],
            DEFECT,
        )

    def test_joss_is_probabilistic_after_opponent_cooperation(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["JOSS"])
        rng = Random(9)
        coop = sum(
            strategy.next_move([COOPERATE], [COOPERATE], rng, strategy.initial_state())[0] == COOPERATE
            for _ in range(2000)
        )
        self.assertGreater(coop / 2000, 0.85)
        self.assertLess(coop / 2000, 0.95)
        self.assertEqual(strategy.next_move([COOPERATE], [DEFECT], Random(0), strategy.initial_state())[0], DEFECT)

    def test_gtft_is_more_forgiving_than_joss_after_defection(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["GTFT"])
        rng = Random(11)
        coop = sum(
            strategy.next_move([COOPERATE], [DEFECT], rng, strategy.initial_state())[0] == COOPERATE
            for _ in range(2000)
        )
        self.assertGreater(coop / 2000, 0.28)
        self.assertLess(coop / 2000, 0.38)

    def test_nydegger_uses_documented_third_move_exception(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["NYDEGGER"])
        self.assertEqual(strategy.next_move([], [], Random(0), strategy.initial_state())[0], COOPERATE)
        self.assertEqual(strategy.next_move([COOPERATE], [DEFECT], Random(0), strategy.initial_state())[0], DEFECT)
        self.assertEqual(
            strategy.next_move([COOPERATE, DEFECT], [DEFECT, COOPERATE], Random(0), strategy.initial_state())[0],
            DEFECT,
        )

    def test_shubik_escalates_retaliation_length(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["SHUBIK"])
        state = strategy.initial_state()
        action, state = strategy.next_move([], [], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE], [DEFECT], Random(0), state)
        self.assertEqual(action, DEFECT)
        action, state = strategy.next_move([COOPERATE, DEFECT], [DEFECT, COOPERATE], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE, DEFECT, COOPERATE], [DEFECT, COOPERATE, DEFECT], Random(0), state)
        self.assertEqual(action, DEFECT)
        self.assertEqual(
            strategy.next_move(
                [COOPERATE, DEFECT, COOPERATE, DEFECT],
                [DEFECT, COOPERATE, DEFECT, COOPERATE],
                Random(0),
                state,
            )[0],
            DEFECT,
        )

    def test_counter_trigger_uses_explicit_punishment_state(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["SHUBIK_COUNTER"])
        state = strategy.initial_state()
        action, state = strategy.next_move([], [], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE], [DEFECT], Random(0), state)
        self.assertEqual(action, DEFECT)
        action, state = strategy.next_move([COOPERATE, DEFECT], [DEFECT, COOPERATE], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE, DEFECT, COOPERATE], [DEFECT, COOPERATE, DEFECT], Random(0), state)
        self.assertEqual(action, DEFECT)

    def test_counter_trigger_with_random_coded_actions_resolves_to_concrete_moves(self) -> None:
        dna = StrategyDNA.counter_trigger(
            init_action=RANDOM,
            default_action=RANDOM,
            triggered_action=RANDOM,
            trigger_states=(False, True, False, True),
            base_punishment_length=1,
        )
        strategy = DnaStrategy(dna)
        result = simulate_match(strategy, strategy, 8, PayoffMatrix(), 0.0, Random(5))
        self.assertEqual(result.rounds, 8)
        self.assertEqual(result.coop_a + result.defect_a, 8)
        self.assertEqual(result.coop_b + result.defect_b, 8)

    def test_champion_uses_opening_tft_and_late_rule(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["CHAMPION"])
        state = strategy.initial_state()
        for turn in range(1, 11):
            action, state = strategy.next_move([COOPERATE] * (turn - 1), [DEFECT] * (turn - 1), Random(0), state)
            self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE] * 10, [DEFECT] * 10, Random(0), state)
        self.assertEqual(action, DEFECT)
        opp_history = [DEFECT] * 26
        action, state = strategy.next_move([COOPERATE] * 26, opp_history, Random(1), state)
        self.assertEqual(action, DEFECT)

    def test_tullock_uses_recent_ten_round_rate_minus_ten_percent(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["TULLOCK"])
        state = strategy.initial_state()
        for turn in range(1, 12):
            action, state = strategy.next_move([COOPERATE] * (turn - 1), [DEFECT] * (turn - 1), Random(0), state)
            self.assertEqual(action, COOPERATE)
        opp_history = [DEFECT] + [COOPERATE] * 8 + [DEFECT] * 2
        rng = Random(2)
        coop = sum(
            strategy.next_move([COOPERATE] * 11, opp_history, rng, state)[0] == COOPERATE
            for _ in range(2000)
        )
        self.assertGreater(coop / 2000, 0.65)
        self.assertLess(coop / 2000, 0.75)

    def test_appeaser_switches_only_after_opponent_defection(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["APPEASER"])
        state = strategy.initial_state()
        action, state = strategy.next_move([], [], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE], [COOPERATE], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE, COOPERATE], [COOPERATE, DEFECT], Random(0), state)
        self.assertEqual(action, DEFECT)
        action, state = strategy.next_move([COOPERATE, COOPERATE, DEFECT], [COOPERATE, DEFECT, COOPERATE], Random(0), state)
        self.assertEqual(action, DEFECT)
        action, state = strategy.next_move(
            [COOPERATE, COOPERATE, DEFECT, DEFECT],
            [COOPERATE, DEFECT, COOPERATE, DEFECT],
            Random(0),
            state,
        )
        self.assertEqual(action, COOPERATE)

    def test_go_by_majority_and_hard_variant_handle_ties_differently(self) -> None:
        soft = DnaStrategy(baseline_dna_library()["GO_BY_MAJORITY"])
        hard = DnaStrategy(baseline_dna_library()["HARD_GO_BY_MAJORITY"])
        own = [COOPERATE, COOPERATE, COOPERATE, COOPERATE]
        opp = [COOPERATE, COOPERATE, DEFECT, DEFECT]
        self.assertEqual(soft.next_move(own, opp, Random(0), soft.initial_state())[0], COOPERATE)
        self.assertEqual(hard.next_move(own, opp, Random(0), hard.initial_state())[0], DEFECT)

    def test_cycler_ccccd_repeats_five_turn_pattern(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["CYCLER_CCCCD"])
        state = strategy.initial_state()
        own_history: list[int] = []
        opp_history: list[int] = []
        actions: list[int] = []
        for _ in range(10):
            action, state = strategy.next_move(own_history, opp_history, Random(0), state)
            actions.append(action)
            own_history.append(action)
            opp_history.append(COOPERATE)
        self.assertEqual(actions, [COOPERATE, COOPERATE, COOPERATE, COOPERATE, DEFECT] * 2)

    def test_cycler_ccd_repeats_three_turn_pattern(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["CYCLER_CCD"])
        state = strategy.initial_state()
        own_history: list[int] = []
        opp_history: list[int] = []
        actions: list[int] = []
        for _ in range(9):
            action, state = strategy.next_move(own_history, opp_history, Random(0), state)
            actions.append(action)
            own_history.append(action)
            opp_history.append(COOPERATE)
        self.assertEqual(actions, [COOPERATE, COOPERATE, DEFECT] * 3)

    def test_cycler_cccd_repeats_four_turn_pattern(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["CYCLER_CCCD"])
        state = strategy.initial_state()
        own_history: list[int] = []
        opp_history: list[int] = []
        actions: list[int] = []
        for _ in range(8):
            action, state = strategy.next_move(own_history, opp_history, Random(0), state)
            actions.append(action)
            own_history.append(action)
            opp_history.append(COOPERATE)
        self.assertEqual(actions, [COOPERATE, COOPERATE, COOPERATE, DEFECT] * 2)

    def test_random_baseline_dna_cooperates_at_half_rate(self) -> None:
        strategy = DnaStrategy(baseline_dna_library()["RANDOM"])
        rng = Random(13)
        coop = sum(strategy.next_move([], [], rng, strategy.initial_state())[0] == COOPERATE for _ in range(4000))
        self.assertGreater(coop / 4000, 0.45)
        self.assertLess(coop / 4000, 0.55)

    def test_random_strategy_produces_expected_cooperation_rate(self) -> None:
        strategy = RandomStrategy(cooperation_probability=0.7)
        rng = Random(5)
        coop = sum(strategy.next_move([], [], rng, strategy.initial_state())[0] == COOPERATE for _ in range(2000))
        self.assertGreater(coop / 2000, 0.65)
        self.assertLess(coop / 2000, 0.75)

    def test_grim_defects_forever_after_betrayal(self) -> None:
        strategy = GrimTriggerStrategy()
        state = strategy.initial_state()
        action, state = strategy.next_move([], [], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE], [COOPERATE], Random(0), state)
        self.assertEqual(action, COOPERATE)
        action, state = strategy.next_move([COOPERATE, COOPERATE], [COOPERATE, DEFECT], Random(0), state)
        self.assertEqual(action, DEFECT)
        action, state = strategy.next_move([COOPERATE, COOPERATE, DEFECT], [COOPERATE, DEFECT, COOPERATE], Random(0), state)
        self.assertEqual(action, DEFECT)


class GameTests(unittest.TestCase):
    def test_payoff_calculation_correctness(self) -> None:
        payoff = PayoffMatrix()
        self.assertEqual(payoff.payoff(COOPERATE, COOPERATE), (3, 3))
        self.assertEqual(payoff.payoff(DEFECT, COOPERATE), (5, 0))
        self.assertEqual(payoff.payoff(COOPERATE, DEFECT), (0, 5))
        self.assertEqual(payoff.payoff(DEFECT, DEFECT), (1, 1))

    def test_tft_vs_tft_stable_cooperation(self) -> None:
        tft = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["TFT"])
        result = simulate_match(tft, tft, 10, PayoffMatrix(), 0.0, Random(0))
        self.assertEqual(result.coop_a, 10)
        self.assertEqual(result.coop_b, 10)

    def test_alld_vs_allc_alld_dominates(self) -> None:
        alld = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["ALLD"])
        allc = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["ALLC"])
        result = simulate_match(alld, allc, 10, PayoffMatrix(), 0.0, Random(0))
        self.assertEqual(result.score_a, 50)
        self.assertEqual(result.score_b, 0)

    def test_alld_vs_alld_mutual_defection(self) -> None:
        alld = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["ALLD"])
        result = simulate_match(alld, alld, 10, PayoffMatrix(), 0.0, Random(0))
        self.assertEqual(result.defect_a, 10)
        self.assertEqual(result.defect_b, 10)
        self.assertEqual(result.score_a, 10)

    def test_grim_vs_allc_stable_cooperation_without_betrayal(self) -> None:
        grim = ParticipantSpec(identifier="GRIM")
        allc = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["ALLC"])
        result = simulate_match(grim, allc, 8, PayoffMatrix(), 0.0, Random(0))
        self.assertEqual(result.coop_a, 8)
        self.assertEqual(result.coop_b, 8)

    def test_grudger_vs_alld_switches_to_permanent_defection(self) -> None:
        grudger = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["GRUDGER"])
        alld = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["ALLD"])
        result = simulate_match(grudger, alld, 5, PayoffMatrix(), 0.0, Random(0))
        self.assertEqual(result.coop_a, 1)
        self.assertEqual(result.defect_a, 4)

    def test_pavlov_vs_pavlov_recovers_from_mistake(self) -> None:
        pavlov = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["PAVLOV"])
        result = simulate_match(pavlov, pavlov, 20, PayoffMatrix(), 0.05, Random(1))
        self.assertGreaterEqual(result.coop_a, 10)
        self.assertGreaterEqual(result.coop_b, 10)

    def test_tf2t_vs_alld_is_forgiving_once_then_retaliatory(self) -> None:
        tf2t = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["TF2T"])
        alld = ParticipantSpec(identifier="DNA", dna=baseline_dna_library()["ALLD"])
        result = simulate_match(tf2t, alld, 5, PayoffMatrix(), 0.0, Random(0))
        self.assertEqual(result.coop_a, 2)
        self.assertEqual(result.defect_a, 3)


class PopulationTests(unittest.TestCase):
    def test_population_normalization(self) -> None:
        population = Population.from_mapping({"CCCCC": 2, "DDDDD": 1})
        population.normalize_total(12, Random(0), 1e-9)
        self.assertEqual(population.total_size(), 12)

    def test_explicit_initial_population_creates_individual_agents(self) -> None:
        population = Population.from_mapping({"ALLC": 3, "ALLD": 2})
        counts = {dna.to_string(): count for dna, count in population.dna_counts().items()}
        allc = baseline_dna_library()["ALLC"].to_string()
        alld = baseline_dna_library()["ALLD"].to_string()
        self.assertEqual(population.total_size(), 5)
        self.assertEqual(counts[allc], 3)
        self.assertEqual(counts[alld], 2)
        self.assertEqual(len({agent.id for agent in population.agents}), 5)


class InteractionTests(unittest.TestCase):
    @staticmethod
    def _interaction_config(**overrides: object) -> SimulationConfig:
        return SimulationConfig(
            export_csv=False,
            export_json=False,
            export_visuals=False,
            **overrides,
        )

    def test_each_agent_plays_at_most_one_match_per_step(self) -> None:
        config = self._interaction_config(initial_population={"ALLC": 4})
        population = Population.from_mapping(config.initial_population)
        result = run_interactions(population, config, Random(0))
        self.assertEqual(result.matches_played, 2)
        touched = {agent_id for pair in result.pairwise_scores for agent_id in pair[:2]}
        self.assertEqual(len(touched), 4)

    def test_odd_agent_mode_random_opponent_plays_leftover_agent(self) -> None:
        config = self._interaction_config(
            initial_population={"ALLC": 5},
            odd_agent_mode="random_opponent",
        )
        population = Population.from_mapping(config.initial_population)
        result = run_interactions(population, config, Random(0))
        self.assertEqual(result.matches_played, 3)


class EngineTests(unittest.TestCase):
    @staticmethod
    def _engine_config(**overrides: object) -> SimulationConfig:
        config_kwargs: dict[str, object] = {
            "export_csv": False,
            "export_json": False,
            "export_visuals": False,
        }
        config_kwargs.update(overrides)
        return SimulationConfig(**config_kwargs)

    def _make_engine(self, **overrides: object) -> EvolutionEngine:
        return EvolutionEngine.from_config(self._engine_config(**overrides))

    def _assert_valid_offspring(
        self,
        parent_a: StrategyDNA,
        parent_b: StrategyDNA,
        *,
        expected_family: str | None = None,
        expected_parent_fallback: bool = False,
    ) -> None:
        engine = self._make_engine(
            mutation_genes_per_step=0.0,
            crossover_rate=1.0,
        )
        child, did_crossover, mutation_count = engine._create_valid_offspring(parent_a, parent_b, 0.0)
        self.assertTrue(isinstance(child, StrategyDNA))
        if expected_family is not None:
            self.assertEqual(child.family_name(), expected_family)
        if expected_parent_fallback:
            self.assertIn(child.to_string(), {parent_a.to_string(), parent_b.to_string()})
        self.assertTrue(did_crossover)
        self.assertEqual(mutation_count, 0)

    def test_deterministic_reproducibility_with_fixed_seed(self) -> None:
        config = self._engine_config(
            num_steps=5,
            initial_population_size=50,
            initial_num_strategies=5,
            random_seed=123,
        )
        self.assertEqual(EvolutionEngine.from_config(config).run(), EvolutionEngine.from_config(config).run())

    def test_visual_exports_are_generated(self) -> None:
        output_dir = Path("test_output_visuals")
        config = SimulationConfig(
            num_steps=2,
            initial_population_size=20,
            initial_num_strategies=4,
            random_seed=10,
            output_dir=str(output_dir),
            export_csv=True,
            export_json=True,
            export_visuals=True,
        )
        engine = EvolutionEngine.from_config(
            config,
            VisualizationConfig(output_dir=str(output_dir), top_strategies_to_plot=5),
        )
        metrics = engine.run()
        engine.export(metrics)
        self.assertTrue((output_dir / "summary_infographic.png").exists())
        self.assertTrue((output_dir / "report.html").exists())
        self.assertTrue((output_dir / "population_breakdown.csv").exists())
        self.assertTrue((output_dir / "population_breakdown.json").exists())
        self.assertTrue((output_dir / "final_population_summary.csv").exists())
        self.assertTrue((output_dir / "final_population_summary.json").exists())
        self.assertIn("strategy_explanation", (output_dir / "population_breakdown.csv").read_text(encoding="utf-8"))
        self.assertIn("strategy_name", (output_dir / "final_population_summary.csv").read_text(encoding="utf-8"))
        self.assertNotIn("Winning DNA", (output_dir / "report.html").read_text(encoding="utf-8"))

    def test_explicit_initial_population_is_respected(self) -> None:
        config = self._engine_config(
            initial_population={"TFT": 100, "ALLD": 60, "ALLC": 40},
        )
        engine = EvolutionEngine.from_config(config)
        counts = {dna.to_string(): count for dna, count in engine.population.dna_counts().items()}
        tft = baseline_dna_library()["TFT"].to_string()
        alld = baseline_dna_library()["ALLD"].to_string()
        allc = baseline_dna_library()["ALLC"].to_string()
        self.assertEqual(engine.population.total_size(), 200)
        self.assertEqual(counts[tft], 100)
        self.assertEqual(counts[alld], 60)
        self.assertEqual(counts[allc], 40)

    def test_default_seeded_setup_uses_fifteen_strategies_with_fifty_agents_each(self) -> None:
        config = self._engine_config(
            initialization_mode="seeded",
            initial_population=None,
            random_strategy_mix=0,
        )
        engine = EvolutionEngine.from_config(config)
        self.assertEqual(engine.population.total_size(), 15 * 50)
        self.assertEqual(len(engine.population.dna_counts()), 15)
        self.assertTrue(all(count == 50 for count in engine.population.dna_counts().values()))

    def test_metrics_report_dominant_dna_by_group_size(self) -> None:
        config = self._engine_config(
            num_steps=1,
            initial_population={"TFT": 5, "ALLD": 3, "ALLC": 2},
        )
        engine = EvolutionEngine.from_config(config)
        metric = engine.run_step(1)
        tft = baseline_dna_library()["TFT"].to_string()
        alld = baseline_dna_library()["ALLD"].to_string()
        allc = baseline_dna_library()["ALLC"].to_string()
        self.assertEqual(metric.population_count_per_dna[tft], 5)
        self.assertEqual(metric.population_count_per_dna[alld], 3)
        self.assertEqual(metric.population_count_per_dna[allc], 1)
        self.assertEqual(metric.dominant_dna, tft)
        self.assertEqual(metric.dominant_group_size, 5)
        self.assertAlmostEqual(metric.dominant_strategy_share, 5 / 9)

    def test_death_removes_bottom_half_percent_each_step(self) -> None:
        config = self._engine_config(
            num_steps=1,
            initial_population={"ALLC": 200},
        )
        engine = EvolutionEngine.from_config(config)
        metric = engine.run_step(1)
        self.assertEqual(metric.deaths_this_step, ceil(config.death_rate * 200))
        self.assertEqual(engine.population.total_size(), 200 - ceil(config.death_rate * 200))

    def test_non_reproduction_step_updates_scores_and_ages(self) -> None:
        config = self._engine_config(
            num_steps=1,
            reproduction_interval=10,
            initial_population={"ALLC": 4},
        )
        engine = EvolutionEngine.from_config(config)
        metric = engine.run_step(1)
        self.assertFalse(metric.reproduction_step)
        self.assertEqual(metric.matches_played, 2)
        self.assertTrue(all(agent.age == 1 for agent in engine.population.agents))
        self.assertTrue(all(agent.score > 0 for agent in engine.population.agents))

    def test_reproduction_step_produces_one_offspring_per_pair(self) -> None:
        config = self._engine_config(
            num_steps=1,
            reproduction_interval=1,
            initial_population={"ALLC": 4},
            mutation_genes_per_step=0.0,
            crossover_rate=1.0,
        )
        engine = EvolutionEngine.from_config(config)
        original_ids = {agent.id for agent in engine.population.agents}
        metric = engine.run_step(1)
        self.assertTrue(metric.reproduction_step)
        self.assertEqual(metric.births_this_step, 1)
        self.assertEqual(metric.deaths_this_step, ceil(config.death_rate * 4))
        self.assertEqual(engine.population.total_size(), 4 - ceil(config.death_rate * 4) + 1)
        surviving_original_ids = {agent.id for agent in engine.population.agents} & original_ids
        self.assertGreaterEqual(len(surviving_original_ids), 1)
        parent_survivors = [
            agent for agent in engine.population.agents
            if agent.id in surviving_original_ids and agent.children_count == 1
        ]
        self.assertEqual(len(parent_survivors), 2)

    def test_parent_dies_after_four_children_total(self) -> None:
        config = self._engine_config(
            num_steps=1,
            reproduction_interval=1,
            initial_population={"ALLC": 2},
            death_rate=0.0,
            pairing_mode="fixed",
            fixed_pairs_per_reproduction=1,
            mutation_genes_per_step=0.0,
        )
        engine = EvolutionEngine.from_config(config)
        parent_ids = [agent.id for agent in engine.population.agents]
        for agent in engine.population.agents:
            agent.children_count = 3
        metric = engine.run_step(1)
        self.assertEqual(metric.births_this_step, 1)
        self.assertEqual(engine.population.total_size(), 1)
        self.assertTrue(all(agent.id not in parent_ids for agent in engine.population.agents))

    def test_scores_reset_after_reproduction(self) -> None:
        config = self._engine_config(
            num_steps=1,
            reproduction_interval=1,
            initial_population={"ALLC": 4},
            mutation_genes_per_step=0.0,
            reset_scores_after_reproduction=True,
        )
        engine = EvolutionEngine.from_config(config)
        engine.run_step(1)
        self.assertTrue(all(agent.score == 0.0 for agent in engine.population.agents))

    def test_reproduction_step_metrics_preserve_pre_reset_scores(self) -> None:
        config = self._engine_config(
            num_steps=1,
            reproduction_interval=1,
            initial_population={"ALLC": 4},
            mutation_genes_per_step=0.0,
            reset_scores_after_reproduction=True,
        )
        engine = EvolutionEngine.from_config(config)
        metric = engine.run_step(1)
        self.assertGreater(metric.average_score, 0.0)
        self.assertGreater(metric.best_score, 0.0)
        self.assertGreaterEqual(metric.best_score, metric.average_score)

    def test_verbose_run_prints_step_progress(self) -> None:
        config = self._engine_config(
            num_steps=1,
            initial_population={"ALLC": 4},
            verbose=True,
        )
        engine = EvolutionEngine.from_config(config)
        output = StringIO()
        with redirect_stdout(output):
            engine.run()
        rendered = output.getvalue()
        self.assertIn("Step 1/1:", rendered)
        self.assertIn("matches=2", rendered)
        self.assertIn("start_population=4", rendered)
        self.assertIn("start_unique_strategies=1", rendered)

    def test_debug_run_prints_detailed_step_progress(self) -> None:
        config = self._engine_config(
            num_steps=1,
            initial_population={"ALLC": 4},
            debug=True,
        )
        engine = EvolutionEngine.from_config(config)
        output = StringIO()
        with redirect_stdout(output):
            engine.run()
        rendered = output.getvalue()
        self.assertIn("Step 1/1:", rendered)
        self.assertIn("reproduction=False", rendered)
        self.assertIn("births=0", rendered)
        self.assertIn("deaths=", rendered)
        self.assertIn("end_population=", rendered)
        self.assertIn("dominant=", rendered)
        self.assertIn("top_strategies=", rendered)
        self.assertIn("avg_score=", rendered)

    def test_trace_run_prints_event_lines(self) -> None:
        config = self._engine_config(
            num_steps=1,
            initial_population={"ALLC": 4},
            trace=True,
        )
        engine = EvolutionEngine.from_config(config)
        output = StringIO()
        with redirect_stdout(output):
            engine.run()
        rendered = output.getvalue()
        self.assertIn("Step 1/1:", rendered)
        self.assertIn("trace step=1 match agents=", rendered)
        self.assertIn("trace step=1 low_score_deaths=", rendered)

    def test_checkpoint_interval_writes_periodic_exports(self) -> None:
        output_dir = Path("test_output_visuals/checkpoints_case")
        config = self._engine_config(
            num_steps=2,
            initial_population={"ALLC": 4},
            checkpoint_interval=1,
            output_dir=str(output_dir),
            export_csv=True,
            export_json=True,
            export_visuals=False,
        )
        engine = EvolutionEngine.from_config(config)
        engine.run()
        self.assertTrue((output_dir / "checkpoints" / "step_00001" / "metrics.json").exists())
        self.assertTrue((output_dir / "checkpoints" / "step_00002" / "metrics.csv").exists())

    def test_checkpoint_interval_prints_progress_even_without_verbose(self) -> None:
        output_dir = Path("test_output_visuals/checkpoints_logging_case")
        config = self._engine_config(
            num_steps=1,
            initial_population={"ALLC": 4},
            checkpoint_interval=1,
            output_dir=str(output_dir),
            export_csv=True,
            export_json=False,
            export_visuals=False,
        )
        engine = EvolutionEngine.from_config(config)
        output = StringIO()
        with redirect_stdout(output):
            engine.run()
        rendered = output.getvalue()
        self.assertIn("Writing checkpoint for step 1", rendered)
        self.assertIn("Checkpoint written:", rendered)

    def test_population_cap_randomly_culls_after_reaching_max_size(self) -> None:
        config = self._engine_config(
            num_steps=1,
            reproduction_interval=1,
            initial_population={"ALLC": 20},
            death_rate=0.0,
            pairing_mode="fixed",
            fixed_pairs_per_reproduction=1,
            mutation_genes_per_step=0.0,
            max_population_size=20,
            overflow_cull_rate=0.3,
        )
        engine = EvolutionEngine.from_config(config)
        metric = engine.run_step(1)
        self.assertEqual(metric.births_this_step, 1)
        self.assertEqual(metric.deaths_this_step, ceil(0.3 * 21))
        self.assertEqual(engine.population.total_size(), 21 - ceil(0.3 * 21))

    def test_population_cap_with_full_score_correlation_kills_lowest_scores(self) -> None:
        config = self._engine_config(
            max_population_size=4,
            overflow_cull_rate=0.3,
            overflow_cull_score_correlation=1.0,
            initial_population={"ALLC": 4},
        )
        engine = EvolutionEngine.from_config(config)
        scores = [10.0, 1.0, 5.0, 2.0]
        for agent, score in zip(engine.population.agents, scores):
            agent.score = score
        deaths, _victims = engine._apply_population_cap()
        self.assertEqual(deaths, 2)
        self.assertEqual(sorted(agent.score for agent in engine.population.agents), [5.0, 10.0])

    def test_offspring_from_same_family_same_length_parents_is_valid(self) -> None:
        parent_a = baseline_dna_library()["TFT"]
        parent_b = baseline_dna_library()["PAVLOV"]
        self._assert_valid_offspring(parent_a, parent_b, expected_family="LOOKUP")

    def test_offspring_from_cross_family_different_length_parents_is_valid(self) -> None:
        parent_a = baseline_dna_library()["TFT"]
        parent_b = baseline_dna_library()["NYDEGGER"]
        self._assert_valid_offspring(parent_a, parent_b, expected_parent_fallback=True)

    def test_offspring_from_same_family_different_length_lookup_parents_is_valid(self) -> None:
        parent_a = baseline_dna_library()["TFT"]
        parent_b = baseline_dna_library()["TF2T"]
        self._assert_valid_offspring(parent_a, parent_b, expected_parent_fallback=True)

    def test_offspring_from_same_family_same_shape_probabilistic_parents_is_valid(self) -> None:
        parent_a = baseline_dna_library()["JOSS"]
        parent_b = baseline_dna_library()["GTFT"]
        self._assert_valid_offspring(parent_a, parent_b, expected_family="PROBABILISTIC_LOOKUP")

    def test_offspring_mutation_can_change_child_bits(self) -> None:
        config = self._engine_config(
            mutation_genes_per_step=0.0,
            crossover_rate=0.0,
        )
        engine = EvolutionEngine.from_config(config)
        parent_a = baseline_dna_library()["TFT"]
        parent_b = baseline_dna_library()["TFT"]
        child, did_crossover, mutation_count = engine._create_valid_offspring(parent_a, parent_b, 1.0 / len(parent_a.genes))
        self.assertTrue(isinstance(child, StrategyDNA))
        self.assertFalse(did_crossover)
        self.assertGreaterEqual(mutation_count, 0)
        self.assertNotEqual(child.to_string(), parent_a.to_string())
        self.assertEqual(mutation_count, sum(1 for before, after in zip(parent_a.genes, child.genes) if before != after))


if __name__ == "__main__":
    unittest.main()
