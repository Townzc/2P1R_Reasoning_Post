"""CPU, real-autograd contracts; no pretrained model or network is required."""
import math
import unittest

import torch

from experiments.public_math_pilot_v1.losses import (
    ARMS, causal_gold_log_probs, compute_loss, final_boxed_boundary,
    qdw_token_weights, select_qdw_tokens, validate_response_alignment,
)


class PublicMathLossTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_manual_loss_and_detached_gradients_all_four_formulas(self):
        # Gold is respectively unique top1, not top1, tied top1. Position 3 is
        # the supervised ending, so the last vocabulary row must remain unused.
        values = torch.tensor([[[3., 1., -2.], [4., 1., -1.], [0., 2., 2.],
                                [90., -90., 0.]]])
        labels = torch.tensor([[-100, 0, 1, 2]])
        mask = torch.tensor([[False, True, False, False]])
        denominator = 9  # Other microbatches in this optimizer update own six.
        for arm in ARMS:
            with self.subTest(arm=arm):
                logits = values.clone().requires_grad_()
                loss, audit = compute_loss(logits, labels, arm, denominator,
                    qdw_mask=mask if arm == "QDW_v0" else None)
                loss.backward()
                expected_loss = 0.
                expected_gradient = torch.zeros_like(values)
                for t, gold in enumerate((0, 1, 2)):
                    v = values[0, t].tolist()
                    total = sum(math.exp(x) for x in v)
                    p = math.exp(v[gold]) / total
                    ce = -math.log(p)
                    if arm == "DFT":
                        weight = p
                    elif arm == "TrimSFT":
                        gap = v[gold] - max(x for j, x in enumerate(v) if j != gold)
                        weight = math.exp(-((gap - 1.5) ** 2) / (2 * .8 ** 2))
                    elif arm == "QDW_v0":
                        weight = 3 * (5 if t == 0 else 1) / 7
                    else:
                        weight = 1.
                    expected_loss += weight * ce / denominator
                    for j, x in enumerate(v):
                        expected_gradient[0, t, j] = weight * (math.exp(x) / total - (j == gold)) / denominator
                self.assertAlmostEqual(loss.item(), expected_loss, places=6)
                torch.testing.assert_close(logits.grad, expected_gradient, atol=3e-8, rtol=3e-6)
                self.assertTrue(audit["weights_detached"])
                self.assertEqual(audit["microbatch_supervised_tokens"], 3)
                self.assertEqual(audit["update_denominator"], 9)
                if arm == "TrimSFT":
                    self.assertEqual(audit["gap_min"], -3.)
                    self.assertEqual(audit["gap_max"], 2.)

    def test_dft_gradient_excludes_probability_derivative(self):
        labels = torch.tensor([[-100, 1]])
        actual = torch.tensor([[[2., 1., 0.], [0., 0., 0.]]], requires_grad=True)
        wrong = actual.detach().clone().requires_grad_()
        loss, _ = compute_loss(actual, labels, "DFT", 1)
        loss.backward()
        ce = torch.logsumexp(wrong[0, 0], 0) - wrong[0, 0, 1]
        (torch.exp(-ce) * ce).backward()
        self.assertFalse(torch.allclose(actual.grad, wrong.grad))

    def test_causal_shift_prompt_padding_and_eos_are_actual_gradient_positions(self):
        logits = torch.arange(36, dtype=torch.float32).reshape(1, 6, 6).requires_grad_()
        labels = torch.tensor([[-100, -100, 2, 4, 5, -100]])  # id 5 is EOS.
        attention = torch.tensor([[1, 1, 1, 1, 1, 0]])
        loss, audit = compute_loss(logits, labels, "SFT", 3, attention_mask=attention)
        loss.backward()
        self.assertEqual(audit["microbatch_supervised_tokens"], 3)
        self.assertEqual((logits.grad.abs().sum(-1) > 0).nonzero().tolist(), [[0, 1], [0, 2], [0, 3]])
        logs, valid = causal_gold_log_probs(logits.detach(), labels, attention_mask=attention)
        self.assertEqual(valid.tolist(), [[False, True, True, True, False]])
        expected = logits.detach()[0, 1:4].log_softmax(-1).gather(1, torch.tensor([[2], [4], [5]])).flatten()
        torch.testing.assert_close(logs[valid], expected)

    def test_future_suffix_truncation_preserves_existing_causal_logit_mapping(self):
        # Tests the loss/indexing boundary only. It is not a test of a pretrained
        # model's causal attention; the runtime must separately audit that model.
        torch.manual_seed(8)
        logits = torch.randn(1, 7, 9)
        labels = torch.tensor([[-100, -100, 1, 2, 3, 4, 8]])
        full, _ = causal_gold_log_probs(logits, labels)
        prefix, _ = causal_gold_log_probs(logits[:, :5], labels[:, :5])
        self.assertTrue(torch.equal(full[:, :4], prefix))
        changed = logits.clone()
        changed[:, 4:] += torch.randn_like(changed[:, 4:]) * 10
        other, _ = causal_gold_log_probs(changed, labels)
        self.assertTrue(torch.equal(other[:, :4], prefix))

    def test_qdw_mass_and_ending_background_weight(self):
        labels = torch.tensor([[-100, 1, 2, 3, 4, -100], [-100, -100, 1, 2, 4, -100]])
        mask = torch.tensor([[False, True, False, True, False, False],
                             [False, False, False, False, False, False]])
        weights = qdw_token_weights(labels, mask)
        torch.testing.assert_close(weights[0], torch.tensor([0., 20/12, 4/12, 20/12, 4/12, 0.]))
        torch.testing.assert_close(weights.sum(1), torch.tensor([4., 3.]))
        self.assertAlmostEqual(weights[0, 4].item(), 1/3, places=6)  # EOS, not 1.
        self.assertEqual(weights[1, 4].item(), 1.)

    def test_qdw_zero_mask_and_lambda_one_exact_sft_loss_and_gradient(self):
        torch.manual_seed(9)
        values = torch.randn(2, 6, 7)
        labels = torch.tensor([[-100, -100, 2, 4, 6, -100], [-100, 3, 5, 6, -100, -100]])
        base = values.clone().requires_grad_()
        expected, _ = compute_loss(base, labels, "SFT", 6)
        expected.backward()
        for multiplier, any_selected in ((5., False), (1., True)):
            x = values.clone().requires_grad_()
            mask = torch.zeros_like(labels, dtype=torch.bool)
            if any_selected:
                mask[0, 2] = True
            loss, _ = compute_loss(x, labels, "QDW_v0", 6, qdw_mask=mask, qdw_lambda=multiplier)
            loss.backward()
            self.assertTrue(torch.equal(loss, expected))
            self.assertTrue(torch.equal(x.grad, base.grad))

    def test_whole_32_sample_denominator_invariant_to_16_microbatches(self):
        torch.manual_seed(10)
        features = torch.randn(32, 8, 4)
        initial = torch.randn(4, 11) * .3
        labels = torch.full((32, 8), -100, dtype=torch.long)
        mask = torch.zeros_like(labels, dtype=torch.bool)
        for i in range(32):
            length = 2 + i % 6
            labels[i, 1:length+1] = (torch.arange(length) + i) % 10
            labels[i, length] = 10  # One EOS per response, never extra-weighted.
            mask[i, 1] = i % 3 != 0
        denominator = int((labels != -100).sum())
        for arm in ARMS:
            with self.subTest(arm=arm):
                full = initial.clone().requires_grad_()
                full_loss, _ = compute_loss(features @ full, labels, arm, denominator,
                    qdw_mask=mask if arm == "QDW_v0" else None)
                full_loss.backward()
                micro = initial.clone().requires_grad_()
                total_loss = 0.
                counts = 0
                for start in range(0, 32, 2):
                    loss, audit = compute_loss(features[start:start+2] @ micro, labels[start:start+2], arm,
                        denominator, qdw_mask=mask[start:start+2] if arm == "QDW_v0" else None)
                    loss.backward()
                    total_loss += loss.item()
                    counts += audit["microbatch_supervised_tokens"]
                self.assertEqual(counts, denominator)
                self.assertAlmostEqual(total_loss, full_loss.item(), places=6)
                torch.testing.assert_close(micro.grad, full.grad, atol=8e-8, rtol=3e-5)

    def test_trim_no_floor_underflow_and_gold_excluded_with_ties(self):
        values = torch.tensor([[[2000., -2000., 0.], [2., 2., 1.], [0., 0., 0.]]], requires_grad=True)
        labels = torch.tensor([[-100, 0, 1]])
        loss, audit = compute_loss(values, labels, "TrimSFT", 2)
        loss.backward()
        self.assertEqual(audit["zero_weight_tokens"], 1)
        self.assertEqual(audit["weight_min"], 0.)
        self.assertEqual(audit["gap_max"], 2000.)
        self.assertEqual(audit["gap_min"], 0.)
        self.assertTrue(torch.equal(values.grad[0, 0], torch.zeros(3)))
        self.assertGreater(values.grad[0, 1].abs().sum().item(), 0)

    def test_bfloat16_input_fp32_calculation(self):
        torch.manual_seed(11)
        for arm in ARMS:
            x = torch.randn(1, 4, 5, dtype=torch.bfloat16).requires_grad_()
            labels = torch.tensor([[-100, 2, 3, 4]])
            mask = torch.tensor([[False, True, False, False]])
            loss, audit = compute_loss(x, labels, arm, 3, qdw_mask=mask if arm == "QDW_v0" else None)
            self.assertEqual(loss.dtype, torch.float32)
            self.assertEqual(audit["calculation_dtype"], "float32")
            loss.backward()
            self.assertTrue(torch.isfinite(x.grad).all())

    def test_invalid_denominator_masks_padding_and_nonfinite_fail_closed(self):
        x = torch.zeros(1, 4, 5)
        labels = torch.tensor([[-100, -100, 2, 4]])
        for denominator in (0, -1, 1, 2.5, True):
            with self.assertRaises(ValueError):
                compute_loss(x, labels, "SFT", denominator)
        with self.assertRaises(ValueError):
            compute_loss(x, labels, "SFT", 2, attention_mask=torch.tensor([[1, 1, 1, 0]]))
        with self.assertRaises(ValueError):
            compute_loss(x, labels, "QDW_v0", 2, qdw_mask=torch.tensor([[True, False, False, False]]))
        with self.assertRaises(ValueError):
            compute_loss(x, labels, "QDW_v0", 2, qdw_mask=torch.zeros_like(labels).float())
        with self.assertRaises(ValueError):
            compute_loss(x, torch.full_like(labels, -100), "SFT", 2)
        for value in (float("nan"), float("inf"), -float("inf")):
            bad = x.clone()
            bad[0, 3, 0] = value  # Even unused tail nonfinite is an implementation hard stop.
            with self.assertRaises(FloatingPointError):
                compute_loss(bad, labels, "SFT", 2)


class QdwSelectionTests(unittest.TestCase):
    @staticmethod
    def characters(text, scores=None, **overrides):
        ids = list(range(10, 10 + len(text))) + [99999]
        offsets = [(i, i+1) for i in range(len(text))] + [(0, 0)]
        # An EOS has highest score but must be excluded from selection.
        values = list(scores if scores is not None else [.5] * len(text)) + [1.]
        kw = dict(blank_response_ids=ids.copy(), special_ids=[99999],
                  full_prefix_length=17, blank_prefix_length=9)
        kw.update(overrides)
        return select_qdw_tokens(text, ids, offsets, [-2. + s for s in values], [-2.] * len(ids), **kw)

    def test_last_balanced_fraction_box_line_not_box_start(self):
        text = "Earlier \\boxed{1}.\nreason 2+2\nThus, \\boxed{\\frac{1}{2}} done\n\\boxed{broken"
        boundary = final_boxed_boundary(text)
        self.assertEqual(boundary["boxed_text"], r"\boxed{\frac{1}{2}}")
        self.assertEqual(boundary["line_start"], text.index("Thus,"))
        result = self.characters(text)
        self.assertTrue(all(i < text.index("Thus,") for i in result["eligible_indices"]))
        self.assertTrue(all(not text[i].isspace() for i in result["eligible_indices"]))
        self.assertFalse(result["mask"][-1])
        self.assertEqual(result["full_prefix_length"], 17)
        self.assertEqual(result["blank_prefix_length"], 9)

    def test_stable_ties_rank_quota_and_only_positive_scores(self):
        text = "abcdefghijklmnopqrstu\n\\boxed{0}"  # 21 eligible => ceil(2.1) = 3.
        result = self.characters(text)
        self.assertEqual(result["eligible_count"], 21)
        self.assertEqual(result["quota"], 3)
        self.assertEqual(result["selected_indices"], [0, 1, 2])
        scores = [-.5] * len(text)
        scores[4] = .1
        scores[17] = .2
        result = self.characters(text, scores)
        self.assertEqual(result["positive_count"], 2)
        self.assertEqual(result["selection_order"], [17, 4])
        self.assertEqual(result["selected_indices"], [4, 17])

    def test_threshold_zero_and_no_boundary_fallbacks_keep_every_token(self):
        for text, reason in (("No final box", "no_parseable_boxed_boundary"),
                             (" \\boxed{0}", "empty_eligible_region"),
                             ("\n \t\n\\boxed{0}", "empty_eligible_region")):
            result = self.characters(text)
            self.assertEqual(result["status"], reason)
            self.assertEqual(result["K"], 0)
            self.assertEqual(len(result["response_ids"]), len(text) + 1)
        text = "abc\n\\boxed{0}"
        result = self.characters(text, [0.] * len(text))
        self.assertEqual(result["status"], "no_positive_scores")
        # Build exact FP32 threshold without cancellation at -2.
        ids = list(range(len(text)))
        scores = torch.zeros(len(text))
        scores[0] = 1e-6
        scores[1] = torch.nextafter(scores[0], torch.tensor(float("inf")))
        result = select_qdw_tokens(text, ids, [(i, i+1) for i in ids], torch.zeros(len(text)),
                                   -scores, blank_response_ids=ids, special_ids=[])
        self.assertEqual(result["positive_indices"], [1])
        self.assertEqual(result["selected_indices"], [1])

    def test_nested_escaped_braces_literal_command_and_line_separators(self):
        self.assertIsNone(final_boxed_boundary(r"Escaped \\boxed{1}"))
        text = "reason\r\nanswer " + r"\boxed{\{x\} + {1}}"
        self.assertEqual(final_boxed_boundary(text)["boxed_text"], r"\boxed{\{x\} + {1}}")
        self.assertEqual(final_boxed_boundary(text)["line_start"], len("reason\r\n"))
        for separator in ("\r", "\n", "\u2028", "\u2029"):
            self.assertEqual(final_boxed_boundary("why" + separator + r"\boxed{0}")["line_start"], 4)
        self.assertEqual(final_boxed_boundary(r"\boxed{}")['content_start'],
                         final_boxed_boundary(r"\boxed{}")['content_end'])

    def test_whole_token_boundary_whitespace_special_and_ending(self):
        text = "ab \nAnswer \\boxed{1/2}"
        # Token1 straddles the line start: its pre-answer characters do not
        # justify applying extra weight to the answer-line characters.
        ids = [10, 11, 12, 13, 99, 98]
        offsets = [(0, 1), (1, 6), (2, 4), (0, 1), (0, 0), (len(text), len(text)+10)]
        result = select_qdw_tokens(text, ids, offsets, [-1.] * 6, [-2.] * 6,
                                  blank_response_ids=ids, special_ids=[13, 99, 98])
        self.assertEqual(result["eligible_indices"], [0])
        self.assertEqual(result["selected_indices"], [0])

    def test_exact_full_blank_alignment_and_selector_rejection(self):
        response = [3, 4, 99]
        record = validate_response_alignment([1, 2] + response, [2] + response, 2, 1, response)
        self.assertEqual(record["response_ids"], response)
        for blank in ([2, 3, 5, 99], [2, 3, 4], [2, 3, 4, 99, 99]):
            with self.assertRaises(ValueError):
                validate_response_alignment([1, 2] + response, blank, 2, 1, response)
        with self.assertRaises(ValueError):
            select_qdw_tokens("a\n\\boxed{0}", [1, 2], [(0, 1), (0, 0)], [-1., -1.], [-2., -2.],
                              blank_response_ids=[1, 3], special_ids=[2])
        with self.assertRaises(ValueError):
            select_qdw_tokens("x", [1], [(0, 1)], torch.tensor([-1.], requires_grad=True), [-2.],
                              blank_response_ids=[1], special_ids=[])
        for logp, exception in (([float("nan")], FloatingPointError), ([.1], ValueError)):
            with self.assertRaises(exception):
                select_qdw_tokens("x", [1], [(0, 1)], logp, [-2.], blank_response_ids=[1], special_ids=[])


if __name__ == "__main__":
    unittest.main()
