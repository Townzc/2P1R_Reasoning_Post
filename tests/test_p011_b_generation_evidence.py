"""NEW read-only oracle checks with synthetic files; no old worker/test replay."""
from pathlib import Path
import json
import tempfile
import unittest

from experiments.p011 import b_generation_evidence as x
from experiments.p011.short_generation import b_requests
from experiments.sft_allocation_midpoint.common import digest, sha, read


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True))


class Evidence(unittest.TestCase):
    def fixture(self, root):
        ids = [f'synthetic-{i}' for i in range(400)]
        prompts = {p:[1,2] for p in ids}; rows = b_requests(ids, prompts)
        out = Path(root)/'body'; key = 'b'; claim = {'synthetic':True}
        roster = digest(rows)
        job = {'claim':claim,'roster_sha256':roster,'new_requests':6400,
               'temperature':1.,'new_training_updates':0,'new_symbolic_scores':0}
        records = {'b/claim':claim,'b/generation':job}
        write(out/'INTENT.json',job)
        cycles = [{'batch':i,'seconds':7.,'three_commits_and_remote_ack_included':True}
                  for i in range(25)]
        def forecast(left, times):return {'left':left,'times':times}
        def transport(raw):return {'raw_digest':digest(raw),'synthetic':True}
        for i in range(25):
            part=rows[i*256:(i+1)*256];directory=out/'batches'/f'{i:03d}'
            intent={'first':256*i,'requests':[r['request'] for r in part],
                    'sampling':[r['sampling'] for r in part],'roster_sha256':roster}
            raw=[{'candidate_id':r['request']['candidate_id'],
                  'problem_id':r['request']['problem_id'],'source_row_sha256':None,
                  'sampling':r['sampling'],'prompt_token_ids':[1,2],'output_count':1,
                  'token_ids':[5,151645],'backend_text':'synthetic',
                  'finish_reason':'stop','stop_reason':151645} for r in part]
            write(directory/'INTENT.json',intent);write(directory/'RAW.json',raw)
            write(directory/'TRANSPORT.json',[transport(v) for v in raw])
            write(directory/'FORECAST.json',forecast(25-i,[7.]*i))
            ack={'count':256,'first':256*i,'raw_file_sha256':sha(directory/'RAW.json'),
                 'transport_file_sha256':sha(directory/'TRANSPORT.json')}
            write(directory/'ACK.json',ack)
            records[f'b/batch/{i:03d}']=intent;records[f'b/batch_done/{i:03d}']=ack
        write(out/'COMPLETED.json',{'new_outputs':6400,'complete_batches':25,
            'roster_sha256':roster,'cycles':cycles,'original_P010_outputs_regenerated':0,
            'new_symbolic_scores':0,'selection_performed':False,'training_admitted':False,
            'final_summary_write_excluded_from_cycles':True})
        return dict(ordered400=ids,prompts=prompts,rows=rows,out=out,key=key,claim=claim,
                    records=records,verify_transport=transport,replay_forecast=forecast)

    def test_all6400_verified_without_file_writes(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d); before={str(p):sha(p) for p in kw['out'].rglob('*.json')}
            result=x.check_body(**kw)
            self.assertEqual((result['verified_new_outputs'],result['new_symbolic_scores']),(6400,0))
            self.assertEqual(before,{str(p):sha(p) for p in kw['out'].rglob('*.json')})

    def test_failed_partial_never_enters_complete_oracle(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d);write(kw['out']/'FAILED.json',{'preserved':True})
            kw['verify_transport']=lambda _:self.fail('must reject before transport')
            with self.assertRaisesRegex(ValueError,'partial oracle'):x.check_body(**kw)

    def test_foreign_parent_rejected_even_if_candidate_id_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d);p=kw['out']/'batches/000/RAW.json';v=read(p)
            v[0]['problem_id']='foreign';write(p,v)
            with self.assertRaisesRegex(ValueError,'Foreign'):x.check_body(**kw)

    def test_missing_remote_ack_is_unknown_not_complete(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d);del kw['records']['b/batch_done/024']
            with self.assertRaisesRegex(ValueError,'acknowledgments'):x.check_body(**kw)

    def test_forecast_uses_all_previous_full_cycles(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d);write(kw['out']/'batches/024/FORECAST.json',{'left':1,'times':[7.]})
            with self.assertRaisesRegex(ValueError,'forecast replay'):x.check_body(**kw)

    def test_transport_tampering_preserved_not_rescored(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d);p=kw['out']/'batches/000/TRANSPORT.json';v=read(p)
            v[0]['raw_digest']='changed';write(p,v)
            with self.assertRaisesRegex(ValueError,'transport differs'):x.check_body(**kw)

    def test_nonfinite_full_cycle_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            kw=self.fixture(d);p=kw['out']/'COMPLETED.json';v=read(p)
            v['cycles'][0]['seconds']=float('nan');write(p,v)
            with self.assertRaisesRegex(ValueError,'full-cycle'):x.check_body(**kw)


if __name__=='__main__':unittest.main()
