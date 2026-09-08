"""Synthetic checks for the independent auditor; no study inputs are read."""

import math
import unittest

from audit_correction import (
    AuditError, finite, payment, scores, select_from_published, transitions, verify_weight,
)


class AuditArithmeticTests(unittest.TestCase):
    def test_binary_interior_weight(self):
        samples = [{"model": [0.9, 0.1], "market": [0.5, 0.5], "outcome": int(i >= 14)} for i in range(20)]
        self.assertAlmostEqual(verify_weight(samples, "ou25", 0.5)["weight"], 0.5)
        with self.assertRaises(AuditError):
            verify_weight(samples, "ou25", 0.6)

    def test_zero_denominator_and_clamped_multiclass(self):
        identical = [{"model": [0.5, 0.5], "market": [0.5, 0.5], "outcome": 0}] * 20
        self.assertEqual(verify_weight(identical, "btts", 0)["weight"], 0)
        multiclass = [{"model": [0.8, 0.1, 0.1], "market": [0.4, 0.3, 0.3], "outcome": 0}] * 20
        self.assertEqual(verify_weight(multiclass, "1x2", 1)["weight"], 1)

    def test_scores_have_distinct_binary_and_multiclass_scales(self):
        self.assertEqual(scores([0.5, 0.25, 0.25], 0, "1x2"), (0.375, math.log(2)))
        brier, _ = scores([0.6, 0.4], 0, "btts")
        self.assertAlmostEqual(brier, 0.16)

    def test_boolean_and_infinity_are_not_numbers(self):
        for invalid in (True, False, math.inf, math.nan, "0.5"):
            with self.assertRaises(AuditError):
                finite(invalid)

    def test_fixed_selection_and_payment_cost_on_loss(self):
        selected = select_from_published({"p_1x2": [0.57, 0.23, 0.2], "p_over25": 0.5, "p_btts": 0.5},
                                         {"1x2": [2, 3, 4], "ou25": [1.9, 1.9], "btts": [1.9, 1.9]})
        self.assertEqual((selected["market"], selected["side"]), ("1x2", "home"))
        self.assertEqual(payment(selected, 2, 0)["net_profit_units"], 0.98)
        self.assertEqual(payment(selected, 0, 1)["net_profit_units"], -1.02)
        self.assertEqual(payment(None, 0, 0)["stake_units"], 0)

    def test_removed_winners_and_avoided_losses_are_separate(self):
        candidate = {"market": "1x2", "side": "home", "side_index": 0, "odd": 2}
        old = {"a": {"candidate": candidate, "payment": payment(candidate, 2, 0)},
               "b": {"candidate": candidate, "payment": payment(candidate, 0, 1)}}
        new = {key: {"candidate": None, "payment": payment(None, 0, 0)} for key in old}
        result = transitions(old, new)
        self.assertEqual(result["removed_winner"]["n"], 1)
        self.assertEqual(result["avoided_loser"]["n"], 1)
        self.assertAlmostEqual(sum(value["difference"] for value in result.values()), 0.04)


if __name__ == "__main__":
    unittest.main()
