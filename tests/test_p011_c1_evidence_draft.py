"""New C1 IO/journal synthetic fixtures; no original data or model loaded."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.p011 import c1_evidence as e


class Journal(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.out=Path(self.temp.name)/'out';self.basis={'fixture_only':True}
        self.tasks={}
        for i in range(35):
            ids=[i+1,151643];labels=[-100,151643];key=e.digest({'input_ids':ids,'labels':labels})
            self.tasks[key]={'sequence_sha256':key,'input_ids':ids,'labels':labels,
                             'target_positions':[1],'supervised_tokens':1}
        self.members={'fixture':[{'sequence_sha256':k,'unverified_fallback':False}
                                 for k in self.tasks]}

    @staticmethod
    def forward(model,task):
        return {'sequence_sha256':task['sequence_sha256'],'target_positions':[1],
                'supervised_tokens':1,'token_nll':[.5],'nll_sum':.5,'mean_nll':.5}

    def run_once(self):
        with patch.object(e.c1_nll,'forward_one',side_effect=self.forward) as f:
            summary=e.run_confirmed_forward(None,self.tasks,self.members,self.out,self.basis,time.time()+60)
            self.assertEqual(f.call_count,35)
        return summary

    def test_complete_two_chunks_then_readonly_verification(self):
        self.assertEqual(self.run_once()['unique_forward_sequences'],35)
        with patch.object(e.c1_nll,'forward_one') as f,patch.object(e.c1_nll,'descriptive_summary') as s:
            proof=e.check_confirmed_evidence(self.out,self.tasks,self.members,self.basis)
            self.assertTrue(proof['complete']);f.assert_not_called();s.assert_not_called()
        self.assertEqual(len(list((self.out/'chunks').iterdir())),2)

    def test_interrupted_chunk_retains_attempt_and_never_retries(self):
        calls=[]
        def interrupted(model,task):
            calls.append(task)
            if len(calls)==2:raise TimeoutError('synthetic interruption')
            return self.forward(model,task)
        with patch.object(e.c1_nll,'forward_one',side_effect=interrupted):
            with self.assertRaises(TimeoutError):
                e.run_confirmed_forward(None,self.tasks,self.members,self.out,self.basis,time.time()+60)
        chunk=self.out/'chunks'/'00000'
        self.assertEqual(len(list(chunk.glob('*.ATTEMPT.json'))),2)
        self.assertEqual(len(list(chunk.glob('*.RESULT.json'))),1)
        self.assertFalse((chunk/'CONFIRMED.json').exists())
        self.assertFalse((self.out/'DESCRIPTIVE_SUMMARY.json').exists())
        self.assertTrue((self.out/'FAILED.json').exists())
        with patch.object(e.c1_nll,'forward_one') as f:
            with self.assertRaises(FileExistsError):
                e.run_confirmed_forward(None,self.tasks,self.members,self.out,self.basis,time.time()+60)
            f.assert_not_called()

    def test_nonfinite_result_blocks_confirmation_and_aggregation(self):
        def corrupt(model,task):
            x=self.forward(model,task);x['token_nll']=[float('nan')];return x
        with patch.object(e.c1_nll,'forward_one',side_effect=corrupt):
            with self.assertRaisesRegex(ValueError,'finite'):
                e.run_confirmed_forward(None,self.tasks,self.members,self.out,self.basis,time.time()+60)
        self.assertFalse((self.out/'ALL_CONFIRMED.json').exists())

    def test_changed_saved_vector_or_basis_rejected_without_forward(self):
        self.run_once()
        with self.assertRaisesRegex(ValueError,'exact'):
            e.check_confirmed_evidence(self.out,self.tasks,self.members,{'other':True})
        p=next((self.out/'chunks'/'00000').glob('*.RESULT.json'));p.write_text('{}')
        with self.assertRaisesRegex(ValueError,'bytes changed'):
            e.check_confirmed_evidence(self.out,self.tasks,self.members,self.basis)

    def test_missing_final_chunk_confirmation_is_not_completed(self):
        self.run_once();(self.out/'chunks'/'00001'/'CONFIRMED.json').unlink()
        with self.assertRaises(FileNotFoundError):
            e.check_confirmed_evidence(self.out,self.tasks,self.members,self.basis)

    def test_expired_window_or_changed_token_mask_stops_before_forward(self):
        with patch.object(e.c1_nll,'forward_one') as f:
            with self.assertRaisesRegex(ValueError,'window'):
                e.run_confirmed_forward(None,self.tasks,self.members,self.out,self.basis,time.time()-1)
            self.assertFalse(self.out.exists())
            next(iter(self.tasks.values()))['input_ids'][0]+=1
            with self.assertRaisesRegex(ValueError,'identity'):
                e.run_confirmed_forward(None,self.tasks,self.members,self.out,self.basis,time.time()+60)
            f.assert_not_called()


class OriginalPaths(unittest.TestCase):
    def test_six_source_bindings_and_foreign_or_changed_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);roots={t:str(root/t) for t in ('t15','t7','t72')}
            binding={}
            with patch.object(e,'ORIGINAL_ROOTS',roots):
                for teacher in roots:
                    folder=Path(roots[teacher]);folder.mkdir();manifest={}
                    for n in (400,3200):
                        names=e.original_names(teacher,n)
                        for k,name in names.items():
                            p=folder/name;p.parent.mkdir(exist_ok=True)
                            p.write_text(json.dumps({'synthetic':True} if k=='config' else []))
                            manifest[name]={'bytes':p.stat().st_size,'sha256':e.sha(p)}
                        binding[f'{teacher}_n{n}']={'root':str(folder),'filenames':names,
                                                  'files':{f:manifest[f] for f in names.values()}}
                    (folder/'MANIFEST.json').write_text(json.dumps(manifest))
                    for n in (400,3200):
                        binding[f'{teacher}_n{n}']['original_manifest_sha256']=e.sha(folder/'MANIFEST.json')
                groups=e.load_original_groups(binding);self.assertEqual(len(groups),6)
                binding['t7_n400']['root']=str(root/'foreign')
                with self.assertRaisesRegex(ValueError,'writer paths'):e.load_original_groups(binding)
                binding['t7_n400']['root']=roots['t7']
                (Path(roots['t72'])/'t72_s17_n3200_k1'/'encoded.json').write_text('[1]')
                with self.assertRaisesRegex(ValueError,'Artifact differs'):e.load_original_groups(binding)


if __name__=='__main__':unittest.main()
