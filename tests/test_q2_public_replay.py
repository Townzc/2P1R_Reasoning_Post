import json
from pathlib import Path
import tempfile
import unittest
from experiments.q2_supervision_migration.reanalyze_public_rollouts import load_joined, grouped, summarize


def fixture():
    rows=[]
    for i in range(16):
        base=i<8 or i%2==0
        rows.append(dict(kind='roll', uid=f'1-0-{i}', seed=0, arm='leaky', run_gen=1,
                         call=0,gstep=0,task_id='a' if i<8 else 'b',base=base,plus=None,code=''))
        if base:
            rows.append(dict(kind='plus',uid=f'1-0-{i}',seed=0,arm='leaky',run_gen=1,plus=i<4))
    return rows


class ReplayTests(unittest.TestCase):
    def read(self, rows):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            return load_joined(p,0)[0]

    def test_mixed_transitions_and_signs(self):
        rows=self.read(fixture()); out=summarize(rows,grouped(rows))
        self.assertEqual(out['reward_flips'],8)
        self.assertEqual(out['union_pass'],4)
        self.assertEqual(out['groups_centered_reward_sign_changed'],2)
        self.assertEqual(out['group_transition_counts'],{'all_pass -> mixed':1,'mixed -> all_fail':1})

    def test_missing_positive_extra_is_not_zero(self):
        rows=fixture();rows.pop(1)
        with self.assertRaises(ValueError):self.read(rows)

    def test_duplicate_and_orphan_rejected(self):
        rows=fixture()
        with self.assertRaises(ValueError):self.read(rows+[rows[0]])
        with self.assertRaises(ValueError):self.read(rows+[dict(kind='plus',uid='orphan',seed=0,arm='leaky',run_gen=1,plus=False)])

    def test_scorer_error_rejected(self):
        rows=fixture();rows[0]['scoring_error']=True
        with self.assertRaises(ValueError):self.read(rows)

    def test_incomplete_group_rejected(self):
        rows=self.read(fixture())[:-1]
        with self.assertRaises(ValueError):grouped(rows)

    def test_all_pass_to_all_fail_no_centered_signal(self):
        rows=fixture()
        for r in rows:
            if r['kind']=='plus':r['plus']=False
        joined=self.read(rows);out=summarize(joined,grouped(joined))
        self.assertEqual(out['groups_reward_vector_changed'],2)
        self.assertEqual(out['groups_centered_reward_sign_changed'],1)

if __name__=='__main__':unittest.main()
