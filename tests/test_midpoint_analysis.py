"""Artificial fixtures only: test paired estimands and refusal of missing outcomes."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.summarize_midpoint_grid import analyze


class AnalysisTests(unittest.TestCase):
    def fixtures(self,folder):
        for arm in ('repeat','solutions','mixed','breadth'):
            for seed in (17,23):
                values={f'fixture/{i:03d}':arm!='repeat' for i in range(431)}
                result=dict(status='completed',arm=arm,seed=seed,committed_updates=256,supervised_tokens=524288,
                    endpoint=dict(n=431,correct=sum(values.values()),parsed=431,stop_reasons={},question_correct=values),
                    train_seconds=1,wall_seconds=1,runtime_rate_estimate_usd=0)
                (folder/f'{arm}_{seed}_result.json').write_text(json.dumps({'result':result}))
    def test_constant_paired_effect_is_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixtures(folder);r=analyze(folder)
            self.assertEqual(r['primary_contrasts'][0]['mean_difference_pp'],100.)
            self.assertEqual(r['primary_contrasts'][0]['conditional_question_interval_pp'],[100.,100.])
            self.assertEqual(r['primary_contrasts'][1]['mean_difference_pp'],0.)
    def test_unknown_not_silently_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.fixtures(folder);p=folder/'repeat_17_result.json'
            r=json.loads(p.read_text());r['result']['endpoint']['question_correct']['fixture/000']=None;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):analyze(folder)


if __name__=='__main__':unittest.main()
