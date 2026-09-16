"""Audit completed measurements from an incomplete phase without a factorial table."""
import argparse
from collections import Counter
import json
from pathlib import Path

from experiments.thursday_probe.common import dump, jsonl
from experiments.thursday_probe_v2.analyze import audit_records, per_question
from experiments.thursday_probe_v2.config import RELEASE, evaluation_queue
from experiments.thursday_probe_v2.queue import load_inputs
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import read_jsonl, sha256_file


def measurement(records):
    questions=per_question(records)
    if not questions:
        raise ValueError('No empty measurement denominators')
    sizes={r['n'] for r in questions.values()}
    result=dict(questions=len(questions),generations=len(records),
        samples_per_question=next(iter(sizes)) if len(sizes)==1 else None,
        pass_at_1=sum(r['pass_at_1'] for r in questions.values())/len(questions),
        parse_fraction=sum(r['score']['parsed'] for r in records)/len(records),
        completed_fraction=sum(r['score']['completed'] for r in records)/len(records),
        failures=dict(Counter(r['score']['failure'] for r in records)),
        stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in records)),
        traces=dict(Counter(r['independent_trace_status'] for r in records)))
    if sizes=={4}:
        result['pass_at_4']=sum(r['pass_at_4'] for r in questions.values())/len(questions)
    return result


def incomplete_file(path):
    """Inventory the original bytes, retaining a torn final line as a limitation."""
    lines=path.read_bytes().splitlines();records=[];invalid=[]
    for index,line in enumerate(lines,1):
        try:
            record=json.loads(line)
            if not isinstance(record,dict):raise ValueError('Nonobject record')
            records.append(record)
        except (ValueError,UnicodeDecodeError):
            invalid.append(index)
    return dict(file=path.name,sha256=sha256_file(path),bytes=path.stat().st_size,
                valid_json_records=len(records),invalid_json_lines=invalid),records


def audit_batch_journal(prediction_path,records,rows,event,tokenizer,*,allow_missing=False):
    """Independent raw-batch/row correspondence; reusable by the full analyzer."""
    path=Path(prediction_path).with_suffix('.raw_batches.jsonl')
    if not path.exists():
        if not allow_missing:raise ValueError('Completed new evaluation has no raw batch journal')
        return dict(status='absent_legacy_stream',note='Legacy or reused calibration is verified from its original prediction hash and token audit; no journal is invented.')
    expected=[(r['problem_id'],sample) for r in rows for sample in range(event['samples'])]
    if [(r['problem_id'],r['sample_index']) for r in records]!=expected:
        raise ValueError('Journal comparison requires exact frozen sample order')
    batches=read_jsonl(path)
    if len(batches)!=(len(records)+7)//8:
        raise ValueError('Raw batch journal count differs')
    for index,raw in enumerate(batches):
        part=records[index*8:(index+1)*8]
        prompts=[r['prompt_ids'] for r in part];width=max(map(len,prompts))
        inputs=[[tokenizer.eos_token_id]*(width-len(ids))+ids for ids in prompts]
        masks=[[0]*(width-len(ids))+[1]*len(ids) for ids in prompts]
        wanted=dict(batch_index=index,start_index=index*8,padded_prompt_width=width,
            problem_ids=[r['problem_id'] for r in part],sample_indices=[r['sample_index'] for r in part],
            forced_prefixes=[r['forced_prefix'] for r in part],prompt_ids=prompts,
            input_ids=inputs,attention_mask=masks,
            output_ids=[ids+r['batch_output_ids'] for ids,r in zip(inputs,part)],
            stop_events=[r['stop'] for r in part])
        if any(raw.get(key)!=value for key,value in wanted.items()):
            raise ValueError('Raw batch tensor/event/sample mismatch: '+str(index))
        if any(r['batch_index']!=index or r['batch_seconds']!=raw.get('batch_seconds') for r in part):
            raise ValueError('Raw batch timing/index mismatch')
    return dict(status='verified_against_completed_predictions',sha256=sha256_file(path),
                batches=len(batches),generated_records=len(records))


def calibration_pairs(before,after,rows):
    before={r['problem_id']:r for r in before};after={r['problem_id']:r for r in after}
    if set(before)!=set(after) or set(before)!={r['problem_id'] for r in rows}:
        raise ValueError('Calibration paired identities differ')
    result={}
    for split in ('all','fit','check'):
        ids=[r['problem_id'] for r in rows if split=='all' or r['calibration_split']==split]
        pairs=[(before[pid],after[pid]) for pid in ids]
        result[split]=dict(questions=len(ids),
            both_correct=sum(bool(a['score']['correct']) and bool(b['score']['correct']) for a,b in pairs),
            gained_correct=sum(not a['score']['correct'] and bool(b['score']['correct']) for a,b in pairs),
            lost_correct=sum(bool(a['score']['correct']) and not b['score']['correct'] for a,b in pairs),
            neither_correct=sum(not a['score']['correct'] and not b['score']['correct'] for a,b in pairs))
        for label,records in (('before',[a for a,_ in pairs]),('after',[b for _,b in pairs])):
            result[split][label]=dict(correct=sum(bool(r['score']['correct']) for r in records),
                parsed=sum(bool(r['score']['parsed']) for r in records),
                length_caps=sum(r['stop']['stop_reason']=='length_cap' for r in records),
                native_eos=sum(r['stop']['stop_reason']=='native_eos' for r in records))
    return result


def audit(run_dir,tokenizer_dir):
    out=Path(run_dir);manifest_path=out/'run_manifest_final.json'
    manifest=json.loads(manifest_path.read_text())
    if manifest['status'] in ('completed','running','not_run'):
        raise ValueError('Partial audit requires a final incomplete phase manifest')
    audit_dir=out/'partial_independent_audit'
    if audit_dir.exists():raise FileExistsError('Never overwrite an independent audit')
    inputs,_,_,_,_=load_inputs();tokenizer,_=verified_tokenizer(Path(tokenizer_dir))
    if manifest['release_manifest_sha256']!=sha256_file(RELEASE/'manifest.json'):
        raise ValueError('Run and frozen analysis release differ')
    expected={event['name']:event for event in evaluation_queue()}
    completed={};hashes={};journals={};perq=[];failures=[];seen=set();reused=0
    for event in manifest['evaluations']:
        name=event['name']
        if name in seen or name not in expected:
            raise ValueError('Unknown or duplicated manifest evaluation')
        seen.add(name)
        if event['status']!='completed':continue
        if any(event.get(k)!=v for k,v in expected[name].items()):
            raise ValueError('Completed evaluation differs from the frozen recipe')
        key='discovery_problems' if event['view'].startswith('discovery_') else event['view']
        rows=inputs[key];path=out/(name+'.jsonl')
        if sha256_file(path)!=event['predictions_sha256']:
            raise ValueError('Completed prediction SHA mismatch: '+name)
        records=audit_records(path,rows,tokenizer)
        identities=[(r['problem_id'],sample) for r in rows for sample in range(event['samples'])]
        if (len(rows)!=event['questions'] or len(records)!=event['generations']
            or [(r['problem_id'],r['sample_index']) for r in records]!=identities):
            raise ValueError('Completed evaluation sample identity/denominator mismatch: '+name)
        questions=per_question(records)
        if len(questions)!=event['questions'] or any(r['n']!=event['samples'] for r in questions.values()):
            raise ValueError('Completed evaluation per-question denominator mismatch')
        if event.get('reused_from'):
            carry=manifest.get('continuation') or {}
            if name!='C0_calibration' or event['reused_from']!=carry.get('previous_attempt'):
                raise ValueError('Unexpected reused evaluation provenance')
            reused+=len(records)
        journals[name]=audit_batch_journal(path,records,rows,event,tokenizer,
            allow_missing=bool(event.get('reused_from')) or manifest.get('source_commit')=='a85d615fd7c2e7b4efe30fe248059ad195c16823')
        completed[name]=records;hashes[name]=sha256_file(path)
        perq.extend(dict(evaluation=name,state=event['state'],view=event['view'],
                         problem_id=pid,**r) for pid,r in questions.items())
        failures.append(dict(evaluation=name,state=event['state'],view=event['view'],**measurement(records)))

    incomplete=[]
    for name,event in expected.items():
        if name in completed:continue
        path=out/(name+'.jsonl');journal=out/(name+'.raw_batches.jsonl')
        if not path.exists() and not journal.exists():continue
        entry=dict(evaluation=name,status='incomplete_not_in_scientific_denominators',
            expected_generations=event['generations'],row_audit_status='not_claimed',
            note='Original partial streams remain unchanged; no complete-view accuracy is inferred.')
        if path.exists():entry['prediction_stream'],_=incomplete_file(path)
        if journal.exists():
            entry['raw_batch_journal'],batches=incomplete_file(journal)
            entry['journal_output_records']=sum(len(b['output_ids']) for b in batches
                if isinstance(b.get('output_ids'),list))
        else:
            entry['journal_output_records']=None
            entry['raw_output_limitation']='No raw batch journal; unpersisted output rows cannot be reconstructed.'
        incomplete.append(entry)

    carry=manifest.get('continuation') or {}
    fault=carry.get('fault_generations',0)
    if type(fault) is not int or fault<0:raise ValueError('Invalid continuation fault accounting')
    saved_fault=carry.get('incomplete_saved_records',0)
    if type(saved_fault) is not int or not 0<=saved_fault<=fault:
        raise ValueError('Invalid persisted continuation fault records')
    if reused>carry.get('completed_reused_generations',0):
        raise ValueError('Reused results exceed the preserved continuation allowance')
    visible=sum(len(records) for records in completed.values())
    ledger_path=out/'generation_ledger.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else None
    summary=dict(status='partial_completed_measurements_independently_verified',
        phase_status=manifest['status'],source_commit=manifest.get('source_commit'),
        final_manifest_sha256=sha256_file(manifest_path),
        frozen_release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),
        completed_evaluations=list(completed),completed_prediction_files_sha256=hashes,
        completed_batch_journal_audits=journals,continuation_provenance=carry,
        visible_independent_result_records=visible,reused_completed_records=reused,
        newly_generated_completed_records_in_this_attempt=visible-reused,
        continuation_fault_generations=fault,previous_fault_saved_records=saved_fault,
        previous_fault_unrecoverable_records=fault-saved_fault,
        previous_fault_limitation=('The previous attempt returned16 probe outputs but persisted only12 per-row token records. '
            'The remaining4 outputs have no recoverable token records and cannot be reconstructed.'
            if fault==16 and saved_fault==12 else 'Counts come from preserved continuation provenance; no missing output is reconstructed.'),
        completed_unique_results_plus_previous_fault_generations=visible+fault,
        generation_ledger_reserved_count=ledger['used'] if ledger else None,
        accounting_note='Completed results count reused calibration once. Prior fault outputs remain charged separately. '
            'Incomplete current streams are inventoried separately and excluded from completed-view metrics; '
            'a reservation is not proof that every reserved generation was invoked.',
        incomplete_evaluations=[r['evaluation'] for r in incomplete],
        training_status=manifest['runs'],
        interpretations_not_established=['prep manipulation','four-cell treatment effects','interaction','post-main sentinel effects'],
        reserved_test_contents_read=False)

    calibration={}
    for name,label in (('C0_calibration','before'),('calibration_calibration','after')):
        if name not in completed:continue
        records=completed[name]
        calibration[label]=dict(full=measurement(records),**{split:measurement([
            r for r in records if r['problem_id'] in {p['problem_id'] for p in inputs['calibration'] if p['calibration_split']==split}
        ]) for split in ('fit','check')})
    if 'C0_calibration' in completed and 'calibration_calibration' in completed:
        calibration['paired_transition_counts']=calibration_pairs(
            completed['C0_calibration'],completed['calibration_calibration'],inputs['calibration'])
    raw_nll={}
    for run in manifest['runs']:
        if run.get('state')!='calibration':continue
        run_id=Path(run['run_id'])
        if len(run_id.parts)!=1:raise ValueError('Invalid calibration run identity')
        for filename in ('reference_nll_before.json','reference_nll_after.json'):
            path=out/run_id/filename
            if path.exists():raw_nll[filename]=dict(source=str(path.relative_to(out)),sha256=sha256_file(path),record=json.loads(path.read_text()))
    if raw_nll:calibration['raw_reference_nll']=raw_nll
    recorded_calibration=out/'ARITH_CALIBRATION_RESULTS.json'
    if recorded_calibration.exists():
        calibration['original_results']=dict(sha256=sha256_file(recorded_calibration),record=json.loads(recorded_calibration.read_text()))
    if calibration:calibration['scope']='Engineering calibration with an independent small arithmetic adapter; never a scientific prep parent and not evidence of generalization.'

    probes=[]
    if 'C0_probes' in completed:
        for category in ('atomic','target','control'):
            records=[r for r in completed['C0_probes'] if r['category']==category]
            stats=measurement(records)
            if stats['questions']!=32 or stats['samples_per_question']!=4:
                raise ValueError('Unexpected complete C0 probe category support')
            probes.append(dict(state='C0',category=category,**stats))

    # All complete-stream checks happen before creating any audit artifact.
    audit_dir.mkdir()
    dump(audit_dir/'summary.json',summary)
    jsonl(audit_dir/'per_question.jsonl',perq)
    dump(audit_dir/'failure_breakdown.json',failures)
    dump(audit_dir/'incomplete_streams.json',incomplete)
    if probes:dump(audit_dir/'C0_PROBE_RESULTS.json',probes)
    if calibration:dump(audit_dir/'CALIBRATION_RESULTS.json',calibration)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    parser.add_argument('--tokenizer-dir',required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.run_dir,args.tokenizer_dir),indent=2))
