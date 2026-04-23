import unittest

from borg.core.checkpoint_comms import (
    Confidence,
    CostModel,
    Phase,
    build_checkpoint_receipt,
    estimate_savings,
    mechanism_mode_for_risk_level,
    render_telegram_checkpoint,
)


class TestCheckpointComms(unittest.TestCase):
    def test_estimate_savings_defaults(self):
        estimate = estimate_savings(tool_calls_avoided=4, token_savings=50000)
        self.assertEqual(estimate.tool_calls_avoided, 4)
        self.assertEqual(estimate.seconds_saved, 100.0)
        self.assertEqual(estimate.token_savings, 50000)
        self.assertAlmostEqual(estimate.usd_low, 0.15)
        self.assertAlmostEqual(estimate.usd_high, 0.75)

    def test_estimate_savings_rejects_negative(self):
        with self.assertRaises(ValueError):
            estimate_savings(tool_calls_avoided=-1)
        with self.assertRaises(ValueError):
            estimate_savings(token_savings=-5)

    def test_build_checkpoint_receipt_validates_inputs(self):
        with self.assertRaises(ValueError):
            build_checkpoint_receipt(
                phase=Phase.DECIDE,
                borg_used=True,
                source="invalid",
                confidence=Confidence.HIGH,
                what_changed="Used prior trace",
                next_step="Run verification",
            )

    def test_render_checkpoint_format(self):
        receipt = build_checkpoint_receipt(
            phase=Phase.EXECUTE,
            borg_used=True,
            source="borg",
            confidence=Confidence.HIGH,
            what_changed="Skipped dead-end retry strategy",
            next_step="Run tests",
            tool_calls_avoided=3,
            token_savings=12000,
        )
        rendered = render_telegram_checkpoint(receipt)
        self.assertIn("[borg checkpoint]", rendered)
        self.assertIn("phase: execute", rendered)
        self.assertIn("borg used: yes (source: borg, confidence: high)", rendered)
        self.assertIn("what changed: Skipped dead-end retry strategy", rendered)
        self.assertIn("next step: Run tests", rendered)

    def test_mechanism_mode_selection(self):
        self.assertEqual(mechanism_mode_for_risk_level("low"), 1)
        self.assertEqual(mechanism_mode_for_risk_level("medium"), 2)
        self.assertEqual(mechanism_mode_for_risk_level("high"), 4)
        with self.assertRaises(ValueError):
            mechanism_mode_for_risk_level("unknown")

    def test_custom_cost_model(self):
        model = CostModel(avg_seconds_per_tool_call=30, usd_per_million_tokens_low=2, usd_per_million_tokens_high=10)
        receipt = build_checkpoint_receipt(
            phase=Phase.VERIFY,
            borg_used=False,
            source="none",
            confidence=Confidence.LOW,
            what_changed="No Borg lookup used for this phase",
            next_step="Proceed with baseline checks",
            tool_calls_avoided=2,
            token_savings=100000,
            model=model,
        )
        self.assertEqual(receipt.estimate.seconds_saved, 60.0)
        self.assertAlmostEqual(receipt.estimate.usd_low, 0.2)
        self.assertAlmostEqual(receipt.estimate.usd_high, 1.0)


if __name__ == "__main__":
    unittest.main()
