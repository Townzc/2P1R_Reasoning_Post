"""Independent regressions for progress across finite launcher slices."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from experiments.post_e037_goal_training import launcher
import tests.test_goal_training_launcher as fixture


class DurableReferenceProgressTests(unittest.TestCase):
    def test_committed_nll_counts_as_progress_but_intent_and_aggregate_do_not(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory);budget=SimpleNamespace(used=0)
            initial=launcher._work_state(output,budget)
            (output/'reference_H_before.intent.json').write_text('{"planned_forward_calls":512}\n')
            (output/'progress.json').write_text('{"reference_forward_calls":512}\n')
            self.assertEqual(launcher._work_state(output,budget),initial)
            result=output/'reference_H_before.json'
            result.write_text('{"forward_calls":512,"input_tokens":40000}\n')
            committed=launcher._work_state(output,budget)
            self.assertNotEqual(committed,initial)
            result.write_text(result.read_text())
            self.assertEqual(launcher._work_state(output,budget),committed)

    def test_only_committed_reference_progress_admits_one_more_slice(self):
        helper=fixture.GoalTrainingLauncherTests()
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def worker(command,environment,stream):
                calls.append(True)
                if len(calls)==1:
                    out=Path(environment['GOAL_TRAINING_OUTPUT'])/'goal_train_e038_r1'
                    out.mkdir()
                    (out/'reference_H_before.json').write_text(json.dumps(dict(
                        forward_calls=512,input_tokens=40000,forward_seconds=12.)))
                return 75
            code,output,_=helper.invoke(directory,worker)
            self.assertEqual(code,75)
            self.assertEqual(len(calls),2)
            self.assertEqual(len(launcher._receipts(output)),2)
            self.assertEqual(json.loads((output/'generation_ledger.json').read_text())['used'],0)


if __name__=='__main__':unittest.main()
