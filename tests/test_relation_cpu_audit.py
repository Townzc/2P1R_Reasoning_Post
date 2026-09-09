import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from src.relation_transport import make_world, allocation_schedule, views, render_prompt
from src.relation_audit import audit_world, audit_schedule
from src.relation_probes import features, fit_probes, predict, probe_statistics, NAMES
from scripts.run_relation_cpu_audit import write_archive, run
from scripts.verify_relation_cpu_audit import load_archive, check_record
from scripts.audit_family_matching import verified_tokenizer

TOKENIZER=Path('.local/hf-cache/hub/models--Qwen--Qwen2.5-1.5B/snapshots/8faed761d45a263340a0528343f099c05c9a4323')


class CPUAuditTest(unittest.TestCase):
    def test_archive_roundtrip_tamper_and_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'archive.json';rows=[{'x':i} for i in range(4)]
            write_archive(p,rows);self.assertEqual(load_archive(p),rows)
            with self.assertRaises(FileExistsError):write_archive(p,rows)
            data=json.loads(p.read_text());data['raw_sha256']='0'*64;p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):load_archive(p)
            with self.assertRaises(FileExistsError):run(Path(root),TOKENIZER)

    def test_null_test_and_detectable_planted_leak(self):
        labels=np.arange(2000)%5;null=np.zeros((2000,len(NAMES)),dtype=int)
        stats=probe_statistics(null,labels)
        self.assertFalse(any(r['flagged'] for r in stats.values()))
        leaked=np.tile(labels[:,None],(1,len(NAMES)))
        self.assertTrue(all(r['flagged'] for r in probe_statistics(leaked,labels).values()))

    def test_probe_features_are_finite_and_independent_of_gold_metadata(self):
        w=make_world(71001,0,split='fixture');before=features(w['prompt'])
        w['answer']=(w['answer']+1)%5;w['gold_endpoint_map']=[0]*5
        after=features(w['prompt'])
        for name in before:np.testing.assert_array_equal(before[name],after[name])
        for name,(q,_) in views(make_world(71001,1,split='fixture')).items():
            f=features(render_prompt(q))
            self.assertTrue(all(np.isfinite(v).all() for v in f.values()))

    def test_fixed_fit_predict_shapes_and_deterministic_ties(self):
        worlds=[make_world(71004,i,split='fixture') for i in range(16)]
        rows=[features(w['prompt']) for w in worlds]
        model=fit_probes(rows,[w['answer'] for w in worlds])
        a=predict(model,rows[:4]);b=predict(model,rows[:4])
        np.testing.assert_array_equal(a,b)
        self.assertEqual(a.shape,(4,8));self.assertTrue(((a>=0)&(a<5)).all())
        # The nearest-neighbor baseline must recover its exact stored fixture.
        self.assertEqual(list(a[:,NAMES.index('template_1nn')]),[w['answer'] for w in worlds[:4]])

    @unittest.skipUnless(TOKENIZER.exists(),'Pinned tokenizer unavailable')
    def test_full_serialization_independent_receipts_and_schedule(self):
        t,_=verified_tokenizer(TOKENIZER)
        worlds=[]
        for i in range(4):
            w=make_world(71002,i,split='fixture')
            w['audit']=audit_world(w,t,1536,metamorphic=True)
            self.assertEqual(w['audit']['failures'],[])
            check_record(w,t,1536)
            worlds.append(w)
        report=audit_schedule(worlds,allocation_schedule([w['world_id'] for w in worlds],71003))
        self.assertEqual(report['failures'],[])
        self.assertEqual(report['arms']['multi']['supervised'],report['arms']['repeat']['supervised'])
        self.assertEqual(report['arms']['multi']['processed'],report['arms']['repeat']['processed'])
        # Intentionally corrupt one target length: the gate must detect it.
        worlds[0]['audit']['tokens'][0]['n_supervised']+=1
        broken=audit_schedule(worlds,allocation_schedule([w['world_id'] for w in worlds],71003))
        self.assertTrue(broken['failures'])


if __name__=='__main__':unittest.main()
