import unittest
from experiments.p010.cue_selection import propose, select


class CueSelection(unittest.TestCase):
    def setUp(self):
        self.ids = [str(i) for i in range(30)]
        self.cues = [[]]+[[i] for i in range(20)]

    def observations(self):
        return [dict(candidate=c, problem_id=p, rollout=k, answer_key='same')
                for c in range(21) for p in self.ids for k in range(16)]

    def test_probability_mass_and_two_depths(self):
        def probs(prefix):
            if prefix:
                return [[.99]+[.01/20]*20 for _ in self.ids]
            return [[.4,.001]+[.599/19]*19 if i < 15 else [.001,.2]+[.799/19]*19
                    for i in range(30)]
        result = propose(probs, self.ids, range(21), 21)
        self.assertEqual(result['depths'][0]['beam'][0]['token_ids'], [0])
        self.assertAlmostEqual(result['depths'][0]['beam'][0]['mean_probability'], .2005)
        self.assertTrue(any(len(x['token_ids']) == 2 for x in result['candidates']))
        self.assertEqual(len(result['candidates']), 20)

    def test_silence_exact_boundary_and_no_cue(self):
        rows = self.observations()
        for row in rows:
            offset = int(row['problem_id'])*16+row['rollout']
            if row['candidate'] == 1 and offset < 48: row['answer_key'] = None
            if row['candidate'] == 2 and offset < 49: row['answer_key'] = None
        result = select(self.cues, self.ids, rows)
        self.assertTrue(result['candidates'][1]['eligible'])
        self.assertFalse(result['candidates'][2]['eligible'])
        self.assertEqual(result['selected_candidate'], 0)

    def test_low_entropy_with_complete_roster(self):
        rows = self.observations()
        for row in rows:
            if row['candidate'] != 7: row['answer_key'] = str(row['rollout'])
        result = select(self.cues, self.ids, rows)
        self.assertEqual(result['selected_candidate'], 7)
        self.assertAlmostEqual(result['candidates'][0]['mean_entropy_bits'], 4.)

    def test_partial_duplicate_gold_rejected(self):
        rows = self.observations()
        for altered in [rows[:-1], rows+[rows[0]], [dict(rows[0], gold='1')]+rows[1:]]:
            with self.assertRaises(ValueError): select(self.cues, self.ids, altered)

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            propose(lambda _: [[.1]*20 for _ in self.ids], self.ids, range(20), 20)


if __name__ == '__main__':
    unittest.main()
