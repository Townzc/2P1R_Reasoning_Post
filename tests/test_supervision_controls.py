import copy
import unittest
from collections import Counter

from experiments.supervision_controls_v1.masks import make_control, strata
from experiments.supervision_controls_v1.analyze_existing import pattern_counts


def annotation(length=80):
    selected = list(range(3, length - 1, 10))
    return dict(L=length, K=len(selected), eligible_indices=list(range(length-1)),
                selected_indices=selected, mask=[i in selected for i in range(length)],
                full_logp=[-0.2 * (i % 13) for i in range(length)])


class MaskControls(unittest.TestCase):
    def test_random_preserves_count_and_boundary(self):
        a = annotation()
        for seed in range(30):
            r = make_control("p", a, "random", seed)
            self.assertEqual(sum(r["mask"]), a["K"])
            self.assertFalse(r["mask"][-1])
            self.assertTrue(set(r["selected_indices"]) <= set(a["eligible_indices"]))

    def test_joint_cell_counts_exact(self):
        a = annotation()
        cells, _ = strata(a)
        target = Counter(cells[i] for i in a["selected_indices"])
        for seed in range(30):
            r = make_control("p", a, "position_difficulty", seed)
            self.assertEqual(Counter(cells[i] for i in r["selected_indices"]), target)
            self.assertGreaterEqual(r["overlap_with_qdw"], r["forced_overlap_lower_bound"])

    def test_uniform_logp_ties_are_not_arbitrarily_split(self):
        a = annotation()
        a["full_logp"] = [-1.0] * a["L"]
        cells, _ = strata(a)
        self.assertEqual({cell[1] for cell in cells.values()}, {0})

    def test_zero_selection_retains_row(self):
        a = annotation()
        a.update(K=0, selected_indices=[], mask=[False]*a["L"])
        r = make_control("empty", a, "position_difficulty")
        self.assertEqual(r["K"], 0)
        self.assertIsNone(r["control_mean_nll"])
        self.assertFalse(r["changed_mask"])

    def test_all_selected_retains_forced_overlap(self):
        a = annotation()
        a.update(K=len(a["eligible_indices"]), selected_indices=a["eligible_indices"],
                 mask=[True]*(a["L"]-1)+[False])
        r = make_control("all", a, "position_difficulty")
        self.assertEqual(r["forced_overlap_lower_bound"], a["K"])
        self.assertFalse(r["changed_mask"])

    def test_determinism_order_independence_and_no_mutation(self):
        a = annotation()
        before = copy.deepcopy(a)
        r = make_control("p", a, "random")
        make_control("other", a, "random")
        self.assertEqual(r, make_control("p", a, "random"))
        self.assertEqual(a, before)

    def test_malformed_sources_fail_closed(self):
        for mutation in (dict(K=100), dict(selected_indices=[0]),
                         dict(eligible_indices=[1,1]), dict(full_logp=[float("nan")]*80)):
            a = annotation()
            a.update(mutation)
            with self.assertRaises(ValueError):
                make_control("p", a, "random")


class ScorePatterns(unittest.TestCase):
    def test_all_denominators_and_unresolved_bounds(self):
        rows = [[True]*8, [False]*8, [True]*7+[None], [False]*7+[None], [None]*8]
        result = pattern_counts(list(map(list, zip(*rows))))
        self.assertEqual(result["questions"], 5)
        self.assertEqual(result["all_eight_correct"], dict(lower=1, upper=3, denominator=5))
        self.assertEqual(result["any_correct"], dict(lower=2, upper=4, denominator=5))
        self.assertEqual(result["zero_correct"], dict(lower=1, upper=3, denominator=5))
        self.assertEqual(result["unresolved_outputs"], 10)

    def test_invalid_grade_and_incomplete_draws(self):
        with self.assertRaises(ValueError):
            pattern_counts([[True]] * 7)
        with self.assertRaises(ValueError):
            pattern_counts([[1]] * 8)


if __name__ == "__main__":
    unittest.main()
