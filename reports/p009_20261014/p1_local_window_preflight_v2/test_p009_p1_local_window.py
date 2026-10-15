"""Synthetic local-window/authority checks; no symbolic or model calls."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import sha
from experiments.learning_regime_p009.p1_input_binding_extended import SOURCE_PATHS,GENERATION_TARGET,GENERATION_SPEC_SHA,OWNER_WINDOW_AMENDMENT_SHA256
from scripts import p009_p1_driver_extended as new
from scripts import p009_p1_driver as old


def put(p,x):p.write_text(json.dumps(x));return p
class Timer:
    def cancel(self):pass
class FinishedFakeJournal:
    def __init__(self,*args,**kwargs):
        self.position=100;self.completed=[(None,None,dict(rows=[]))]
    def __enter__(self):return self
    def __exit__(self,*args):pass

class WindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        report=self.root/'REPORT.md';report.write_text('SYNTHETIC ONLY; not an actual review.')
        self.source={n:sha(n) for n in SOURCE_PATHS}
        self.review=dict(scope=new.SCOPE,decision='PASS',report_commit='a'*40,
            local_report_path=str(report),report_sha256=sha(report),conditional_first100_authorized=True,
            first100_wall_seconds=1200,maximum_total_wall_seconds=129600,
            local_window_amendment_sha256=OWNER_WINDOW_AMENDMENT_SHA256,
            generation_target_commit=GENERATION_TARGET,generation_spec_sha256=GENERATION_SPEC_SHA,
            source_files=self.source)
    def tearDown(self):self.tmp.cleanup()
    def test_exact_owner_window_and_extended_source_accepted(self):
        p=put(self.root/'review.json',self.review);self.assertEqual(new.accepted(p),self.review)
        self.assertEqual(old.MAXIMUM_TOTAL_SCENARIO_SECONDS,21600)
        self.assertEqual(new.FIRST_WALL_SECONDS,old.FIRST_WALL_SECONDS)
    def test_old_scope_or_6h_or_missing_owner_rejected(self):
        for field,value in [('scope',old.SCOPE),('maximum_total_wall_seconds',21600),('local_window_amendment_sha256',None)]:
            changed=dict(self.review);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):new.accepted(put(self.root/'review.json',changed))
    def setup_remaining(self,approved,owner=OWNER_WINDOW_AMENDMENT_SHA256):
        rows=[dict(id=str(i),dataset='math_procurement') for i in range(100)]
        put(self.root/'ROWS.json',rows);put(self.root/'INPUT_BINDING.json',dict(source_files=self.source));put(self.root/'UNSUPPORTED_GOLD.json',[])
        put(self.root/'FROZEN.json',dict(rows_sha256=sha(self.root/'ROWS.json'),binding_sha256=sha(self.root/'INPUT_BINDING.json'),exclusions_sha256=sha(self.root/'UNSUPPORTED_GOLD.json')))
        put(self.root/'FIRST100_PROPOSAL.json',dict(serial_time_scenario_seconds=23000))
        put(self.root/'FIRST100_COMPLETED.json',dict(total_command_seconds=300))
        timing=dict(scope='p009-math-p1-first100-throughput',decision='PASS',report_commit='b'*40,
            local_report_path=self.review['local_report_path'],report_sha256=self.review['report_sha256'],
            proposal_sha256=sha(self.root/'FIRST100_PROPOSAL.json'),driver_source_files=self.source,
            local_window_amendment_sha256=owner,approved_total_wall_seconds=approved)
        path=put(self.root/'timing.json',timing)
        return SimpleNamespace(root=str(self.root),code_review='fixture',timing_review=str(path))
    def test_over6h_reviewed_window_subtracts_original_first_command(self):
        args=self.setup_remaining(24000);seen=[]
        with patch.object(new,'accepted',return_value=self.review),patch.object(new.importlib.metadata,'version',side_effect=lambda n:new.VERSIONS[n]),patch.object(new,'JournaledPool',FinishedFakeJournal),patch.object(new,'audit_samples',return_value={}),patch.object(new,'hard_timer',side_effect=lambda seconds:(seen.append(seconds) or Timer())):
            new.score(args,False)
        self.assertEqual(seen,[23700]);self.assertTrue((self.root/'REMAINDER_COMPLETED.json').exists())
    def test_over36h_is_rejected_before_any_attempt(self):
        args=self.setup_remaining(129601)
        with patch.object(new,'accepted',return_value=self.review),patch.object(new.importlib.metadata,'version',side_effect=lambda n:new.VERSIONS[n]),self.assertRaises(ValueError):new.score(args,False)
        self.assertFalse((self.root/'REMAINDER_STARTED.json').exists())
    def test_numeric_review_must_bind_same_owner_amendment(self):
        args=self.setup_remaining(24000,'wrong')
        with patch.object(new,'accepted',return_value=self.review),patch.object(new.importlib.metadata,'version',side_effect=lambda n:new.VERSIONS[n]),self.assertRaises(ValueError):new.score(args,False)
        self.assertFalse((self.root/'REMAINDER_STARTED.json').exists())

if __name__=='__main__':unittest.main()
