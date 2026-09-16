import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.thursday_probe_v2 import continuation as c, queue as q
from experiments.thursday_probe_v2.config import LIMITS, RELEASE, DATA, evaluation_queue
from experiments.thursday_probe_v2.runtime import GenerationBudget


class ContinuationTests(unittest.TestCase):
    def test_shared_process_and_original_whole_window_bounds(self):
        self.assertEqual(c.continuation_cap(1000,478),7922)
        self.assertEqual(c.continuation_cap(2000,478),7285)
        for age,charged in ((9285,478),(-1,478),(float('nan'),478),(0,-1),(0,8400),(0,True)):
            with self.subTest(age=age,charged=charged),self.assertRaises(ValueError):
                c.continuation_cap(age,charged)

    def test_faults_charged_and_reused_calibration_counted_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ledger.json';budget=GenerationBudget(path,fault_generations=16)
            for event in evaluation_queue():budget.reserve(event['name']+'.jsonl',event['generations'])
            self.assertEqual(budget.used,4720)
            self.assertEqual(LIMITS['generation_cap']-budget.used,144)
            with self.assertRaises(ValueError):budget.reserve('C0_calibration.jsonl',48)
            with self.assertRaises(ValueError):budget.reserve('overflow',145)
            with self.assertRaises(FileExistsError):GenerationBudget(path,fault_generations=16)
            for bad in (-1,4865,1.5,True):
                with self.subTest(bad=bad),self.assertRaises(ValueError):
                    GenerationBudget(Path(folder)/'bad.json',fault_generations=bad)

    def previous_fixture(self):
        root=Path('runs/thursday_arithmetic_v2_r1')
        calibration=[dict(problem_id=f'c{i}',sample_index=0,batch_index=i//8) for i in range(48)]
        probes=[dict(problem_id=f'p{i//4}',sample_index=i%4,batch_index=i//8) for i in range(12)]
        manifest=dict(source_commit='a85d615fd7c2e7b4efe30fe248059ad195c16823',
            release_manifest_sha256='hash',runs=[{'status':'not_run'} for _ in range(7)],
            evaluations=[dict(evaluation_queue()[0],predictions_sha256='hash',adapter={'sha256':'adapter'})])
        files={'resource_receipt.json':dict(charged_seconds=478,status='failed',historical_ledger_unchanged=True),
            'run_manifest_final.json':manifest,'generation_ledger.json':dict(cap=4864,used=432,
                events=[dict(name='C0_calibration.jsonl',reserved=48),dict(name='C0_probes.jsonl',reserved=384)]),
            'preflight.json':{'power_on_at_utc':'2026-09-16T20:11:00Z'},
            'C0_calibration.jsonl':None,'C0_calibration.generation.json':{},'C0_probes.jsonl':None}
        export={'files':{name:{'sha256':'hash','bytes':1} for name in files}}
        files['export_manifest_final.json']=export
        rows={root/'C0_calibration.jsonl':calibration,root/'C0_probes.jsonl':probes,
              RELEASE/'calibration.jsonl':[{'problem_id':f'c{i}'} for i in range(48)],
              DATA/'probes.jsonl':[{'problem_id':f'p{i}'} for i in range(96)]}
        return root,files,rows

    def test_previous_attempt_identity_and_batch_accounting(self):
        root,files,rows=self.previous_fixture()
        with patch.object(Path,'read_text',lambda p:json.dumps(files[p.name])),\
             patch.object(Path,'stat',lambda p:SimpleNamespace(st_size=1)),\
             patch.object(c,'sha256_file',return_value='hash'),patch.object(c,'read_jsonl',side_effect=lambda p:rows[p]):
            carry=c.validate_previous(root)
            self.assertEqual((carry['completed_reused_generations'],carry['fault_generations'],carry['cancelled_uninvoked_reservation']),(48,16,368))
            self.assertEqual(carry['power_on_at_utc'],'2026-09-16T20:11:00Z')
            rows[root/'C0_probes.jsonl'][8]['batch_index']=0
            with self.assertRaisesRegex(ValueError,'identities/batches'):c.validate_previous(root)
            rows[root/'C0_probes.jsonl'][8]['batch_index']=1
            files['run_manifest_final.json']['runs'][0]['status']='completed'
            with self.assertRaisesRegex(ValueError,'before any training'):c.validate_previous(root)

    def test_continuation_cannot_reset_power_on_timestamp(self):
        carry={'charged_seconds':478,'power_on_at_utc':'2026-09-16T20:11:00Z'}
        prior={'closed':True,'total_charged_seconds_across_phases':7372,'reservations':0}
        with patch.object(q,'source'),patch.object(q,'dry_run'),patch.object(q,'validate_previous',return_value=carry),\
             patch.object(q,'OUT',Path('runs/thursday_arithmetic_v2_r2')),patch.object(q,'sha256_file',return_value=q.OLD_LEDGER_HASH),\
             patch.object(Path,'read_text',return_value=json.dumps(prior)),patch.object(Path,'exists',return_value=False),\
             patch.object(q,'server_preflight') as server:
            with self.assertRaisesRegex(ValueError,'original powered-on window'):
                q.launch('unused','unused','2026-09-16T20:32:00Z',7.98,'runs/thursday_arithmetic_v2_r1')
            server.assert_not_called()


if __name__=='__main__':unittest.main()
