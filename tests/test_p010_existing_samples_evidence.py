"""New complete-sample verification cases, no original state or symbolic scorer."""
import tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch
from experiments.p010.common import dump,read,digest
from experiments.p010.existing_student_samples import rows_checked,sampling,forecast
from experiments.p010.existing_samples_evidence import verify_samples,record_keys

class EvidenceTests(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);base=Path(tmp.name);root=base/'payload'
        run='s1_s17_n400';key='existing_s1_samples/'+run
        endpoint=[dict(problem_id=f'synthetic/{i}',input_ids=[21,22]) for i in range(500)]
        rows=rows_checked(endpoint);files={'model.safetensors':dict(bytes=7,sha256='synthetic')}
        parent=dict(proof=dict(checkpoint=dict(sha256='state',identity_sha256='identity'),merged_files=files))
        spec=dict(parents={run:parent},batch_observations_seconds=[11.55])
        proof=dict(original_state_sha256='state',original_identity_sha256='identity',actual_merged_files=files,original_merged_files=files,
            original_greedy_model_bytes_reproduced=True,merge_dtype='float32',saved_dtype='bfloat16',new_training_updates=0,
            new_optimizer_instances=0,optimizer_rng_preserved_not_restored=True,state_loads_for_this_new_inference=1,old_full_state_oracle_repeated=False)
        dump(root/'ORIGINAL_MODEL_PROOF.json',parent['proof']);dump(root/'restore/COMPLETED.json',proof)
        dump(root/'RESTORE_PROCESS_EXIT.json',dict(exitcode=0,joined_before_vllm=True,new_training_updates=0))
        dump(root/'ENGINE.json',{'synthetic':True})
        for name in ('BEFORE_RESTORE_FORECAST.json','BEFORE_EVAL_FORECAST.json'):dump(root/name,forecast(0,0,[],[11.55],'31.24'))
        times=[1.]*8;ledger={}
        for index,offset in enumerate(range(0,2000,256)):
            part=rows[offset:offset+256];unit=f'{offset:04d}'
            raw=[dict(candidate_id=r['candidate_id'],problem_id=r['problem_id'],source_row_sha256=r['source_row_sha256'],
                prompt_token_ids=r['input_ids'],sampling=sampling(r['sampling_seed']),output_count=1,token_ids=[31,151643],
                backend_text=r'\boxed{1}',finish_reason='stop',stop_reason=151643) for r in part]
            intent=dict(rows=part,sampling=[sampling(r['sampling_seed']) for r in part],epoch=0)
            ack=dict(count=len(part),raw_sha256=digest(raw),seconds=1.)
            for folder,value in [('raw',raw),('sample_intents',intent),('sample_acks',ack),('sample_forecasts',forecast(index,index,times[:index],[11.55],'31.24'))]:dump(root/folder/(unit+'.json'),value)
            ledger[key+'/sample/'+unit]=intent;ledger[key+'/sample_done/'+unit]=ack
        dump(root/'RESULT.json',dict(run=run,raw_sample_outputs=2000,greedy_outputs_generated=0,new_training_updates=0,
            original_training_updates=1024,original_targets=2097148,sampling_seeds=list(range(4)),original_merged_model_reproduced=True,sample_batch_seconds=times))
        tok=type('Tokenizer',(),{'all_special_ids':[151643],'get_vocab':lambda self:{'one':31,'eos':151643},'decode':lambda self,ids,**kw:r'\boxed{1}'})()
        gold={r['problem_id']:{'problem_id':r['problem_id'],'answer':'1'} for r in endpoint}
        return root,endpoint,spec,run,ledger,tok,gold,'31.24',base/'out'

    def execute(self,args):
        with patch('experiments.p010.existing_samples_evidence.validate_observed_engine'):
            return verify_samples(*args)

    def test_full_four_passes_cross_batch_boundaries_without_greedy_or_state_load(self):
        args=self.fixture();out=self.execute(args)
        self.assertEqual(len(out['decoded']),2000);self.assertEqual(len(out['scoring']),2000)
        self.assertEqual([r['evaluation'] for r in out['scoring'][::500]],['sample0','sample1','sample2','sample3'])
        self.assertTrue(all(row['gold']=='1' for row in out['scoring']))
        self.assertFalse(out['symbolic_scoring_performed']);self.assertEqual(out['repeated_local_binary_loads'],0)
        self.assertEqual(len(record_keys(args[3])),18)

    def test_partial_sample_set_is_rejected_before_decode(self):
        args=self.fixture();(args[0]/'raw/1792.json').unlink()
        with self.assertRaisesRegex(ValueError,'Partial'):self.execute(args)

    def test_failed_process_or_changed_original_merge_cannot_be_accepted(self):
        args=self.fixture();p=args[0]/'RESTORE_PROCESS_EXIT.json';x=read(p);x['exitcode']=1;p.write_text(__import__('json').dumps(x))
        with self.assertRaisesRegex(ValueError,'reconstruction'):self.execute(args)

    def test_changed_ack_or_seed_cannot_be_scored_as_zero(self):
        args=self.fixture();args[4]['existing_s1_samples/'+args[3]+'/sample_done/0000']['raw_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'binding'):self.execute(args)

if __name__=='__main__':unittest.main()
