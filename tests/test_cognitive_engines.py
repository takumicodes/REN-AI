"""
Comprehensive Test Suite for Phases 8-13: Cognitive Architecture, Learning Pipeline,
Model Evolution, and Automatic Safe Upgrades.
"""

import unittest
from ren.cognitive.curiosity import CuriosityEngine
from ren.cognitive.dream_lab import DreamLab
from ren.cognitive.transfer import TransferEngine
from ren.cognitive.prediction import PredictionEngine
from ren.cognitive.self_evaluation import SelfEvaluationEngine
from ren.cognitive.learning_pipeline import LearningPipeline
from ren.cognitive.evolution import EvolutionEngine, EvolutionState
from ren.system.upgrade_manager import UpgradeManager, UpgradeItem
from ren.dream.daemon import DreamDaemon


class TestCognitiveArchitecture(unittest.TestCase):

    def test_curiosity_engine_objective_lifecycle(self):
        engine = CuriosityEngine()
        obj = engine.generate_objective(
            topic="Async WebSocket streaming optimization",
            reason="Latency spike observed in high-concurrency turns",
            category="knowledge_gap",
            priority=0.85
        )
        self.assertTrue(obj.id.startswith("cur_"))
        self.assertFalse(obj.resolved)
        self.assertEqual(obj.priority, 0.85)

        # Resolve objective
        resolved = engine.resolve_objective(obj.id, resolution="Implemented non-blocking queue poll")
        self.assertTrue(resolved)
        active = engine.list_active_objectives()
        self.assertNotIn(obj.id, [o.id for o in active])

    def test_dream_lab_trial_and_decision(self):
        lab = DreamLab()

        # Trial 1: Candidate is better than baseline -> KEEP
        res_keep = lab.run_experiment(
            hypothesis="Parallel AST parse is faster than sequential",
            domain="planning",
            baseline_fn=lambda: (True, 0.60),
            candidate_fn=lambda: (True, 0.85),
            min_improvement_margin=0.10
        )
        self.assertEqual(res_keep.decision, "KEEP")
        self.assertAlmostEqual(res_keep.metrics["delta"], 0.25)

        # Trial 2: Candidate is worse than baseline -> DISCARD
        res_discard = lab.run_experiment(
            hypothesis="Greedy regex search reduces token usage",
            domain="tool_selection",
            baseline_fn=lambda: (True, 0.70),
            candidate_fn=lambda: (True, 0.65),
            min_improvement_margin=0.05
        )
        self.assertEqual(res_discard.decision, "DISCARD")

    def test_transfer_engine_abstraction(self):
        engine = TransferEngine()
        ab = engine.extract_abstraction(
            concept="Finite State Action Verification",
            source_context="minecraft_bot",
            rule="Always wait for action_done confirmation event before scheduling next goal",
            confidence=0.92,
            target_domains=["robotics", "device_management"]
        )
        self.assertTrue(ab.id.startswith("abs_"))
        self.assertEqual(ab.confidence, 0.92)

        all_abs = engine.list_abstractions()
        self.assertTrue(any(a["id"] == ab.id for a in all_abs))

    def test_prediction_and_calibration(self):
        pred_engine = PredictionEngine()
        p_id = pred_engine.record_prediction(
            domain="tool_execution",
            statement="Read file will find settings.py",
            expected_outcome="Success",
            confidence=0.90
        )

        rec = pred_engine.record_observation(p_id, actual_outcome="Success", was_accurate=True)
        self.assertIsNotNone(rec)
        self.assertTrue(rec.was_accurate)
        self.assertAlmostEqual(rec.error_delta, 0.10)

        stats = pred_engine.get_calibration_stats(domain="tool_execution")
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["accuracy"], 1.0)

    def test_self_evaluation_weak_area_detection(self):
        eval_engine = SelfEvaluationEngine()
        # Simulate failing tool
        eval_engine.record_tool_call("buggy_tool", False)
        eval_engine.record_tool_call("buggy_tool", False)
        eval_engine.record_tool_call("buggy_tool", False)

        flagged = eval_engine.evaluate_and_generate_improvement_objectives()
        self.assertTrue(any("buggy_tool" in msg for msg in flagged))

    def test_learning_pipeline_repeated_confirmation(self):
        pipeline = LearningPipeline()
        lesson = pipeline.propose_candidate_lesson(
            experience="Cloudflare tunnel restarted with new URL",
            lesson="Preserve persistent device identity across tunnel endpoint rotations",
            source="user_interaction",
            initial_confidence=0.60
        )
        self.assertEqual(lesson.status, "candidate")
        self.assertFalse(lesson.training_candidate)

        # Confirm 3 times to achieve validation threshold
        pipeline.record_evidence(lesson.id, confirmed=True)
        pipeline.record_evidence(lesson.id, confirmed=True)
        updated = pipeline.record_evidence(lesson.id, confirmed=True)

        self.assertEqual(updated.status, "validated")
        self.assertTrue(updated.training_candidate)
        self.assertGreaterEqual(updated.confidence, 0.80)

    def test_model_evolution_benchmark_and_promotion(self):
        evo = EvolutionEngine()
        curr = evo.get_current_version()

        # Create candidate
        cand = evo.create_candidate_version(changes_summary="Upgraded retrieval calibration rules.")
        self.assertIsNotNone(cand)
        self.assertEqual(cand.state, EvolutionState.CANDIDATE)

        # Benchmark superior candidate
        promoted, msg = evo.benchmark_and_evaluate(
            cand.version_id,
            benchmark_fn=lambda: curr.benchmark_score + 0.05
        )
        self.assertTrue(promoted)
        self.assertEqual(evo.get_current_version().version_id, cand.version_id)

        # Rollback test
        rolled_back = evo.rollback_to(curr.version_id)
        self.assertTrue(rolled_back)
        self.assertEqual(evo.get_current_version().version_id, curr.version_id)

    def test_upgrade_manager_checkpoint_and_rollback(self):
        mgr = UpgradeManager()
        item = UpgradeItem(
            item_id="test_upgrade_01",
            component="skills",
            version="1.0.1",
            risk_level="LOW",
            description="Patch verification test"
        )

        # Successful upgrade flow
        success, msg = mgr.execute_upgrade_flow(
            upgrade=item,
            install_action=lambda: True,
            regression_test_fn=lambda: True
        )
        self.assertTrue(success)
        self.assertEqual(item.status, "verified")

        # Failing upgrade flow triggers safe rollback
        item_fail = UpgradeItem(
            item_id="test_upgrade_fail",
            component="system",
            version="2.1.0",
            risk_level="MEDIUM",
            description="Broken patch"
        )
        success_fail, msg_fail = mgr.execute_upgrade_flow(
            upgrade=item_fail,
            install_action=lambda: True,
            regression_test_fn=lambda: False  # Regression test fails!
        )
        self.assertFalse(success_fail)
        self.assertEqual(item_fail.status, "rolled_back")

    def test_dream_daemon_resource_checks(self):
        daemon = DreamDaemon()
        healthy, reason = daemon.check_resource_limits()
        self.assertIsInstance(healthy, bool)
        self.assertIsInstance(reason, str)


if __name__ == "__main__":
    unittest.main()
