"""CPU artifact fixtures exercise real verifier failure and partial boundaries."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
import torch

from experiments.thursday_probe_v2 import resume_verify as rv


def write(path,value,lines=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in value) if lines else json.dumps(value))


def rng(generation=False):
    py=random.Random(17).getstate();n=np.random.RandomState(17).get_state()
    cpu=torch.Generator(device='cpu').manual_seed(2026091603).get_state()
    if generation:
        return dict(python=[py[0],list(py[1]),py[2]],numpy=[n[0],n[1].tolist(),n[2],n[3],n[4]],
            torch=cpu.tolist(),cuda=[[0]*16])
    return dict(python=py,numpy=dict(kind=n[0],keys=n[1].tolist(),position=n[2],has_gauss=n[3],cached_gaussian=n[4]),
        torch=cpu,cuda=[torch.zeros(16,dtype=torch.uint8)])


class ResumeVerifyTests(unittest.TestCase):
    def test_jsonl_uses_physical_lines_and_preserves_unicode_separators(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'literal_unicode.jsonl'
            rows=[dict(text='Answer: 1\u2028continuation\u2029paragraph\u0085next',index=0),dict(text='second',index=1)]
            path.write_bytes(('\r\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\r\n').encode('utf-8'))
            self.assertEqual(len(rv.physical_lines(path)),2)
            self.assertEqual(rv.jsonl(path),rows)
            # A physically torn final JSON record must still fail parsing.
            path.write_bytes(path.read_bytes()+b'{"text":')
            with self.assertRaises(json.JSONDecodeError):rv.jsonl(path)

    def test_frozen_per_update_schedule_lr_tokens_and_journal_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);schedule=[[0,1],[1,0]];lrs=[5e-5,1e-5]
            dose=dict(per_update=[dict(supervised_tokens=8,processed_tokens=12)]*2,
                supervised_response_tokens=16,processed_nonpadding_tokens=24)
            history=[dict(step=i+1,row_indices=indices,learning_rate=lrs[i],supervised_tokens=8,
                processed_tokens=12,seconds=1.,gradient_norm=2.,response_nll=.3,
                segment_file='segment_fixture.jsonl',segment_line=i) for i,indices in enumerate(schedule)]
            write(root/'segments/segment_fixture.jsonl',history,True)
            self.assertEqual(rv.verify_history(history,schedule,lrs,dose,root)['updates'],2)
            for field,value,match in [('row_indices',[0,1],'schedule'),('learning_rate',2e-5,'learning-rate'),
                    ('supervised_tokens',9,'token dose'),('segment_line',0,'Duplicate')]:
                changed=copy.deepcopy(history);changed[1][field]=value
                with self.subTest(field=field),self.assertRaisesRegex(ValueError,match):
                    rv.verify_history(changed,schedule,lrs,dose,root)
            changed=copy.deepcopy(history);changed[1]['response_nll']=.4
            with self.assertRaisesRegex(ValueError,'journal differs'):rv.verify_history(changed,schedule,lrs,dose,root)

    def test_optimizer_state_count_absolute_step_and_moments(self):
        adapter={'a':torch.zeros(2,3),'b':torch.zeros(3,2)}
        group=dict(params=[0,1],lr=1e-5,betas=(.9,.999),eps=1e-8,weight_decay=0,
            foreach=False,amsgrad=False,maximize=False,fused=None,capturable=False,differentiable=False)
        states={i:dict(step=torch.tensor(2.),exp_avg=torch.zeros_like(t),exp_avg_sq=torch.ones_like(t))
                for i,t in enumerate(adapter.values())}
        optimizer=dict(param_groups=[group],state=states)
        self.assertEqual(rv.verify_optimizer(optimizer,adapter,2,[5e-5,1e-5])['parameter_states'],2)
        changed=copy.deepcopy(optimizer);changed['state'][0]['step']=torch.tensor(1.)
        with self.assertRaisesRegex(ValueError,'absolute step'):rv.verify_optimizer(changed,adapter,2,[5e-5,1e-5])
        changed=copy.deepcopy(optimizer);changed['state'].pop(1)
        with self.assertRaisesRegex(ValueError,'state count'):rv.verify_optimizer(changed,adapter,2,[5e-5,1e-5])
        changed=copy.deepcopy(optimizer);changed['state'][0]['exp_avg_sq'][0,0]=-1
        with self.assertRaisesRegex(ValueError,'second moment'):rv.verify_optimizer(changed,adapter,2,[5e-5,1e-5])

    def test_four_rng_domains_validated_without_touching_callers(self):
        before=(random.getstate(),np.random.get_state(),torch.get_rng_state().clone())
        self.assertEqual(rv.rng_identity(rng())['sha256'],rv.rng_identity(rng(True),generation=True)['sha256'])
        self.assertEqual(random.getstate(),before[0]);self.assertTrue(np.array_equal(np.random.get_state()[1],before[1][1]))
        self.assertTrue(torch.equal(torch.get_rng_state(),before[2]))
        changed=rng();changed.pop('numpy')
        with self.assertRaisesRegex(ValueError,'Incomplete RNG'):rv.rng_identity(changed)
        changed=rng(True);changed['cuda'][0][0]=-1
        with self.assertRaisesRegex(ValueError,'byte RNG'):rv.rng_identity(changed,generation=True)

    def test_full_and_partial_ledger_require_explicit_fault_charge(self):
        reservations={f'batch_{i}':8 for i in range(524)}
        record=dict(cap=4864,historical_consumed=592,used=4784,
            events=[dict(name=k,reserved=v) for k,v in reservations.items()])
        self.assertEqual(rv.verify_ledger(record,reservations,complete=True)['actual_charged'],4784)
        record['events'].append(dict(name='interrupted_batch',reserved=8));record['used']+=8
        with self.assertRaisesRegex(ValueError,'explicit fault'):rv.verify_ledger(record,reservations,complete=True)
        partial=rv.verify_ledger(record,reservations,complete=False)
        self.assertEqual(partial['charged_without_exported_raw_or_fault'],8)
        fault=dict(request_key='interrupted_batch',generations=8,reason='Generation interrupted before raw commit',evidence_sha256='a'*64)
        self.assertEqual(rv.verify_ledger(record,reservations,complete=True,faults=[fault])['new_explicit_fault'],8)
        changed=copy.deepcopy(record);changed['events'].append(changed['events'][0]);changed['used']+=8
        with self.assertRaisesRegex(ValueError,'Duplicate'):rv.verify_ledger(changed,reservations,complete=False)
        changed=copy.deepcopy(record);changed['events'][-1]['reserved']=-8;changed['used']-=16
        with self.assertRaisesRegex(ValueError,'Invalid generation'):rv.verify_ledger(changed,reservations,complete=False)

    def evaluation_fixture(self,root):
        event=dict(name='C_probes',state='C',view='probes',questions=2,samples=4,sampling=True,generations=8)
        rows=[dict(problem_id=f'q{i}',task='compute',category='atomic',prompt='Compute 1+1.') for i in range(2)]
        split=root/'split.jsonl';write(split,rows,True)
        config=dict(do_sample=True,num_beams=1,max_new_tokens=512,eos_token_id=151643,pad_token_id=151643,
            use_cache=True,seed=2026091603,samples=4,batch_size=8,temperature=.7,top_p=.95,top_k=0)
        sources=('src/sft_data.py','analyses/e017_stopping.py','analyses/completion_contract.py','experiments/thursday_probe/arithmetic_eval.py')
        protocol=dict(generation=config,scientific_source_sha256={n:rv.file_hash(rv.PROJECT/n) for n in sources})
        descriptor=rv.expected_evaluation(event,rows,split,'a'*64,protocol);ids=descriptor['request_ids']
        folder=root/'C_probes.resume';batch_dir=folder/'batches';initial=rng(True)
        write(folder/'manifest.json',dict(descriptor=descriptor,initial_rng=initial))
        write(root/'C_probes.generation.json',config)
        identity=dict(evaluation_hash=rv.digest(descriptor),batch_index=0,request_key='eval_batch_'+rv.digest(ids),request_ids=ids,generations=8)
        pids=[r['problem_id'] for r in rows for s in range(4)];samples=list(range(4))*2
        stop=dict(retained_tokens=2,reason='native_eos')
        raw=dict(batch_index=0,start_index=0,batch_seconds=1.,padded_prompt_width=2,problem_ids=pids,sample_indices=samples,
            forced_prefixes=['']*8,prompt_ids=[[5,6]]*8,input_ids=[[5,6]]*8,attention_mask=[[1,1]]*8,
            output_ids=[[5,6,7,151643]]*8,stop_events=[stop]*8)
        bundle=dict(identity=identity,rng_before=initial,rng_after=initial,raw=raw)
        write(batch_dir/'000000.intent.json',dict(identity=identity,rng_before=initial))
        write(batch_dir/'000000.reserved.json',identity);write(batch_dir/'000000.raw.json',bundle)
        records=[dict(problem_id=pid,sample_index=s,task='compute',category='atomic',batch_index=0,batch_seconds=1.,
            stop=stop,batch_output_ids=[7,151643],generated_ids=[7,151643],prompt_ids=[5,6],forced_prefix='',score={})
            for pid,s in zip(pids,samples)]
        scored=dict(identity=identity,raw_sha256=rv.file_hash(batch_dir/'000000.raw.json'),records_sha256=rv.digest(records),records=records)
        write(batch_dir/'000000.scored.json',scored);write(root/'C_probes.jsonl',records,True)
        write(root/'C_probes.raw_batches.jsonl',[raw],True)
        summary=dict(**event,adapter=dict(sha256='a'*64),status='completed',completed_records=8,
            predictions_sha256=rv.file_hash(root/'C_probes.jsonl'))
        write(root/'C_probes.summary.json',summary)
        ledger={identity['request_key']:dict(reserved=8)}
        return event,rows,split,ledger

    def test_model_bound_raw_and_scored_fixture_with_stale_partial_views(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);event,rows,split,ledger=self.evaluation_fixture(root)
            def verify(model='a'*64):return rv.verify_evaluation(root,event,rows,split,model,ledger)
            self.assertEqual(verify()['status'],'completed')
            with self.assertRaisesRegex(ValueError,'Model/split/request'):verify('b'*64)
            # A crash after immutable score commit can leave derived views behind.
            write(root/'C_probes.jsonl',[],True);write(root/'C_probes.raw_batches.jsonl',[],True)
            summary=rv.read(root/'C_probes.summary.json');summary.update(status='partial',completed_records=0,
                predictions_sha256=rv.file_hash(root/'C_probes.jsonl'));write(root/'C_probes.summary.json',summary)
            result=verify();self.assertEqual((result['status'],result['scored_records'],result['published_records']),('partial',8,0))
            path=root/'C_probes.resume/batches/000000.scored.json';scored=rv.read(path)
            scored['records'][0]['sample_index']=2;write(path,scored)
            with self.assertRaisesRegex(ValueError,'records SHA'):verify()

    def test_raw_rng_chain_corruption_is_failed_not_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);event,rows,split,ledger=self.evaluation_fixture(root)
            path=root/'C_probes.resume/batches/000000.raw.json';bundle=rv.read(path)
            bundle['rng_before']['torch'][0]^=1;write(path,bundle)
            with self.assertRaisesRegex(ValueError,'RNG chain'):
                rv.verify_evaluation(root,event,rows,split,'a'*64,ledger)

    def test_stale_partial_summary_sha_must_match_its_actual_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);event,rows,split,ledger=self.evaluation_fixture(root)
            path=root/'C_probes.summary.json';summary=rv.read(path)
            # The current published file has eight rows; the old summary bound
            # the empty committed prefix before the first scored batch.
            summary.update(status='partial',completed_records=0,
                predictions_sha256=__import__('hashlib').sha256(b'').hexdigest())
            write(path,summary)
            self.assertEqual(rv.verify_evaluation(root,event,rows,split,'a'*64,ledger)['status'],'partial')
            summary['predictions_sha256']='0'*64;write(path,summary)
            with self.assertRaisesRegex(ValueError,'immutable scored prefix'):
                rv.verify_evaluation(root,event,rows,split,'a'*64,ledger)


if __name__=='__main__':unittest.main()
