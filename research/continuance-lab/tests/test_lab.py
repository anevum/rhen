import unittest
import numpy as np
from lab import autoregressive_matrix, design_matrix, evaluate, make_stream


class ContinuanceLabTests(unittest.TestCase):
    def test_deterministic_and_finite_stream(self):
        a, y_a = make_stream(seed=27)
        b, y_b = make_stream(seed=27)
        self.assertTrue(np.array_equal(a, b))
        self.assertTrue(np.array_equal(y_a, y_b))
        self.assertTrue(np.isfinite(y_a).all())

    def test_no_future_feature_leakage(self):
        u, y = make_stream(seed=7)
        a = design_matrix(u[:200], y[:200], units=16, seed=99)
        other_u = u[:200].copy()
        other_y = y[:200].copy()
        other_u[150:] = 0.0
        other_y[150:] = 0.0
        b = design_matrix(other_u, other_y, units=16, seed=99)
        np.testing.assert_allclose(a[:150], b[:150], rtol=0, atol=0)

    def test_linear_baseline_is_causal(self):
        u, y = make_stream(seed=11)
        a = autoregressive_matrix(u[:200], y[:200])
        changed = u[:200].copy()
        changed[150:] = 0.0
        b = autoregressive_matrix(changed, y[:200])
        np.testing.assert_array_equal(a[:150], b[:150])

    def test_metrics_and_online_adaptation_are_reproducible(self):
        a, rows_a = evaluate(units=24, seed=29)
        b, rows_b = evaluate(units=24, seed=29)
        self.assertEqual(a, b)
        self.assertEqual(len(rows_a), len(rows_b))
        self.assertGreater(a['metrics']['post_change_late']['samples'], 0)
        self.assertTrue(np.isfinite(a['metrics']['post_change_all']['online_reservoir']['rmse']))


if __name__ == '__main__':
    unittest.main()
