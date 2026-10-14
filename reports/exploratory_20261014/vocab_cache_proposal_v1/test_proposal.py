"""New isolated proposal checks; no live worker import or cloud submission."""
import unittest
from scripts.exploratory_reference_vocab_cache_proposal import reference_event_cached


class FrozenTokenizer:
    eos_token_id = 7
    all_special_ids = [7, 8, 9]

    def __init__(self):
        self.length_reads = 0

    def __len__(self):
        self.length_reads += 1
        return 32

    def decode(self, ids, **kwargs):
        return ''.join({1: 'reason', 2: '\nProblem', 3: ':', 7: '', 8: '', 9: ''}.get(i, 'x') for i in ids)


class CacheProposalTests(unittest.TestCase):
    def test_native_alternate_eos_preserves_first_terminal(self):
        tok = FrozenTokenizer()
        result = reference_event_cached([1, 8, 7, 7], tok, [7, 8])
        self.assertEqual((result['stop_reason'], result['retained_tokens']), ('native_eos', 2))
        self.assertEqual(result['answer_segment'], 'reason')
        self.assertEqual(tok.length_reads, 1)

    def test_boundary_still_precedes_later_eos(self):
        tok = FrozenTokenizer()
        result = reference_event_cached([1, 2, 3, 7], tok, [7, 8])
        self.assertEqual((result['stop_reason'], result['retained_tokens']), ('new_problem_boundary', 3))
        self.assertEqual(tok.length_reads, 1)

    def test_out_of_vocabulary_remains_invalid(self):
        tok = FrozenTokenizer()
        result = reference_event_cached([1, 999, 7], tok, [7, 8])
        self.assertEqual((result['stop_reason'], result['retained_tokens']), ('invalid_special_token', 2))
        self.assertEqual(tok.length_reads, 1)

    def test_full_cap_is_not_a_completion_and_lookup_count_is_constant(self):
        tok = FrozenTokenizer()
        result = reference_event_cached([1] * 512, tok, [7])
        self.assertEqual((result['stop_reason'], result['retained_tokens']), ('length_cap', 512))
        self.assertFalse(result['actual_eos_at_stop'])
        self.assertEqual(tok.length_reads, 1)


if __name__ == '__main__':
    unittest.main()
