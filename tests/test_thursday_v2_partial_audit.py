"""Partial-report contracts; token replay itself is covered by existing audits."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.thursday_probe_v2 import partial_audit as p
from experiments.thursday_probe_v2.config import RELEASE, evaluation_queue
from src.sft_data import read_jsonl, sha256_file


def write(path,obj):path.write_text(json.dumps(obj))
def write_rows(path,rows):path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


class PartialAuditTests(unittest.TestCase):
    def fixture(self,out):
        calibration=[dict(problem_id=f'c{i}',category='target',calibration_split='fit' if i<32 else 'check') for i in range(48)]
        probes=[dict(problem_id=f'p{i}',category=('atomic','target','control')[i//32]) for i in range(96)]
        inputs=dict(calibration=calibration,probes=probes)
        events={e['name']:e for e in evaluation_queue()};completed=[];self.records={}
        for name,rows in (('C0_calibration',calibration),('C0_probes',probes)):
            event=events[name];rs=[]
            for row in rows:
                for sample in range(event['samples']):
                    rs.append(dict(problem_id=row['problem_id'],sample_index=sample,category=row['category'],
                        forced_prefix='',prompt_ids=[1],batch_output_ids=[2,0],generated_ids=[2,0],
                        batch_index=len(rs)//8,batch_seconds=1.,stop={'stop_reason':'native_eos'},
                        score=dict(correct=True,parsed=True,completed=True,failure='none'),
                        independent_trace_status='verified',reference_program_class='unknown'))
            path=out/(name+'.jsonl');write_rows(path,rs);self.records[name]=rs
            completed.append(dict(event,status='completed',predictions_sha256=sha256_file(path),
                reused_from='runs/thursday_arithmetic_v2_r1' if name=='C0_calibration' else None))
            if name=='C0_probes':
                batches=[]
                for index,start in enumerate(range(0,len(rs),8)):
                    part=rs[start:start+8]
                    batches.append(dict(batch_index=index,start_index=start,padded_prompt_width=1,
                        problem_ids=[r['problem_id'] for r in part],sample_indices=[r['sample_index'] for r in part],
                        forced_prefixes=['']*len(part),prompt_ids=[[1]]*len(part),input_ids=[[1]]*len(part),
                        attention_mask=[[1]]*len(part),output_ids=[[1,2,0]]*len(part),
                        stop_events=[r['stop'] for r in part],batch_seconds=1.))
                write_rows(out/(name+'.raw_batches.jsonl'),batches)
        manifest=dict(status='failed_hard_or_resource',source_commit='new-runtime',evaluations=completed,
            release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),
            continuation=dict(previous_attempt='runs/thursday_arithmetic_v2_r1',fault_generations=16,
                incomplete_saved_records=12,completed_reused_generations=48,previous_export_manifest_sha256='preserved'),
            runs=[dict(state='calibration',run_id='thu_v2_e030_r1',status='not_run')])
        write(out/'run_manifest_final.json',manifest)
        write_rows(out/'C0_discovery_greedy.jsonl',[{'partial':1},{'partial':2}])
        write(out/'generation_ledger.json',{'used':544})
        return inputs,manifest

    def mocked_token_audit(self,inputs):
        context=ExitStack()
        context.enter_context(patch.object(p,'load_inputs',return_value=(inputs,None,None,None,None)))
        context.enter_context(patch.object(p,'verified_tokenizer',return_value=(SimpleNamespace(eos_token_id=0),{})))
        context.enter_context(patch.object(p,'audit_records',side_effect=lambda path,rows,tok:read_jsonl(path)))
        return context

    def test_partial_outputs_count_reuse_faults_and_exclude_incomplete_view(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);inputs,_=self.fixture(out)
            with self.mocked_token_audit(inputs):summary=p.audit(out,'unused-tokenizer')
            self.assertEqual((summary['visible_independent_result_records'],summary['reused_completed_records'],
                summary['newly_generated_completed_records_in_this_attempt']),(432,48,384))
            self.assertEqual(summary['previous_fault_unrecoverable_records'],4)
            self.assertEqual(summary['completed_unique_results_plus_previous_fault_generations'],448)
            self.assertEqual(summary['generation_ledger_reserved_count'],544)
            self.assertEqual(summary['incomplete_evaluations'],['C0_discovery_greedy'])
            audit=out/'partial_independent_audit'
            self.assertEqual(len(json.loads((audit/'C0_PROBE_RESULTS.json').read_text())),3)
            cal=json.loads((audit/'CALIBRATION_RESULTS.json').read_text())
            self.assertEqual((cal['before']['fit']['questions'],cal['before']['check']['questions']),(32,16))
            self.assertNotIn('after',cal)
            self.assertFalse(any('FOUR_CELL' in f.name or 'PREP_MANIPULATION' in f.name or 'POST_SENTINEL' in f.name for f in out.rglob('*')))
            with self.assertRaises(FileExistsError):p.audit(out,'unused-tokenizer')

    def test_completed_phase_and_changed_prediction_refused_before_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);inputs,manifest=self.fixture(out)
            manifest['status']='completed';write(out/'run_manifest_final.json',manifest)
            with self.assertRaisesRegex(ValueError,'final incomplete'):p.audit(out,'unused-tokenizer')
            manifest['status']='failed_hard_or_resource';write(out/'run_manifest_final.json',manifest)
            with (out/'C0_calibration.jsonl').open('a') as stream:stream.write('\n')
            with self.mocked_token_audit(inputs),self.assertRaisesRegex(ValueError,'SHA mismatch'):p.audit(out,'unused-tokenizer')
            self.assertFalse((out/'partial_independent_audit').exists())

    def test_journal_tensor_and_sample_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);inputs,_=self.fixture(out)
            event=next(e for e in evaluation_queue() if e['name']=='C0_probes')
            path=out/'C0_probes.jsonl';journal=path.with_suffix('.raw_batches.jsonl')
            batches=read_jsonl(journal);batches[0]['output_ids'][0][-1]=9;write_rows(journal,batches)
            with self.assertRaisesRegex(ValueError,'tensor/event/sample mismatch'):
                p.audit_batch_journal(path,self.records['C0_probes'],inputs['probes'],event,SimpleNamespace(eos_token_id=0))

    def test_calibration_paired_transitions_and_stop_counts(self):
        rows=[{'problem_id':str(i),'calibration_split':'fit' if i<2 else 'check'} for i in range(4)]
        before=[dict(problem_id=str(i),score=dict(correct=i<2,parsed=i!=2),
                     stop={'stop_reason':'length_cap' if i==2 else 'native_eos'}) for i in range(4)]
        after=[dict(problem_id=str(i),score=dict(correct=i%2==0,parsed=True),
                    stop={'stop_reason':'native_eos'}) for i in range(4)]
        result=p.calibration_pairs(before,after,rows)
        self.assertEqual([result['all'][k] for k in ('both_correct','gained_correct','lost_correct','neither_correct')],[1,1,1,1])
        self.assertEqual(result['fit']['lost_correct'],1)
        self.assertEqual(result['check']['gained_correct'],1)
        self.assertEqual(result['all']['before'],dict(correct=2,parsed=3,length_caps=1,native_eos=3))
        self.assertEqual(result['all']['after'],dict(correct=2,parsed=4,length_caps=0,native_eos=4))


if __name__=='__main__':unittest.main()
