"""Verify only the new four sample passes; never reload original model state."""
from collections import Counter
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest
from experiments.p010.existing_student_samples import RUNS,rows_checked,sampling,forecast
from experiments.p010.student_evidence import decode_record,positive,GOLD_SHA256,SCORER_SHA256
from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine


def record_keys(run):
    if run not in RUNS:raise ValueError('Original two completed S1 models only')
    key='existing_s1_samples/'+run
    return sorted([key+'/claim',key+'/terminal']+
        [key+'/'+kind+f'/{offset:04d}' for offset in range(0,2000,256) for kind in ('sample','sample_done')])


def restore_proof(root,parent):
    root=Path(root);proof=read(root/'restore/COMPLETED.json');joined=read(root/'RESTORE_PROCESS_EXIT.json')
    if (read(root/'ORIGINAL_MODEL_PROOF.json')!=parent['proof']
            or proof['original_state_sha256']!=parent['proof']['checkpoint']['sha256']
            or proof['original_identity_sha256']!=parent['proof']['checkpoint']['identity_sha256']
            or proof['actual_merged_files']!=parent['proof']['merged_files']
            or proof['original_merged_files']!=parent['proof']['merged_files']
            or proof['original_greedy_model_bytes_reproduced'] is not True
            or proof['merge_dtype']!='float32' or proof['saved_dtype']!='bfloat16'
            or proof['new_training_updates']!=0 or proof['new_optimizer_instances']!=0
            or proof['optimizer_rng_preserved_not_restored'] is not True
            or proof['state_loads_for_this_new_inference']!=1 or proof['old_full_state_oracle_repeated'] is not False
            or joined['exitcode']!=0 or joined['joined_before_vllm'] is not True or joined['new_training_updates']!=0):
        raise ValueError('Original final model reconstruction or owned process exit differs')
    return proof


def verify_samples(root,endpoint,spec,run,ledger,tokenizer,gold,prior,out):
    root,out=Path(root),Path(out);rows=rows_checked(endpoint);key='existing_s1_samples/'+run
    if set(gold)!={r['problem_id'] for r in endpoint}:raise ValueError('Exact original500 gold roster required')
    validate_observed_engine(read(root/'ENGINE.json'))
    proof=restore_proof(root,spec['parents'][run]);result=read(root/'RESULT.json')
    if (result['run']!=run or result['raw_sample_outputs']!=2000 or result['greedy_outputs_generated']!=0
            or result['new_training_updates']!=0 or result['original_training_updates']!=1024
            or result['original_targets']!=2097148 or result['sampling_seeds']!=list(range(4))
            or result['original_merged_model_reproduced'] is not True):
        raise ValueError('Only complete original four new sample passes are permitted')
    times=positive(result['sample_batch_seconds'],8)
    expected={f'{offset:04d}.json' for offset in range(0,2000,256)}
    for folder in ('raw','sample_intents','sample_acks','sample_forecasts'):
        if {p.name for p in (root/folder).glob('*.json')}!=expected:raise ValueError('Partial/extra sample batch')
    for name in ('BEFORE_RESTORE_FORECAST.json','BEFORE_EVAL_FORECAST.json'):
        value=read(root/name)
        if value!=forecast(value['elapsed_seconds'],0,[],spec['batch_observations_seconds'],prior):
            raise ValueError('Original complete preflight timing scenario differs')
    mapped=set(tokenizer.get_vocab().values());special=tuple(tokenizer.all_special_ids)
    decoded=[];score_rows=[];stops={f'sample{i}':Counter() for i in range(4)};unknown=0
    for index,offset in enumerate(range(0,2000,256)):
        unit=f'{offset:04d}';part=rows[offset:offset+256];raw=read(root/'raw'/(unit+'.json'))
        intent=read(root/'sample_intents'/(unit+'.json'));ack=read(root/'sample_acks'/(unit+'.json'))
        f=read(root/'sample_forecasts'/(unit+'.json'))
        if (intent['rows']!=part or intent['sampling']!=[sampling(r['sampling_seed']) for r in part]
                or len(raw)!=len(part) or ledger[key+'/sample/'+unit]!=intent or ledger[key+'/sample_done/'+unit]!=ack
                or ack!=dict(count=len(part),raw_sha256=digest(raw),seconds=times[index])
                or f!=forecast(f['elapsed_seconds'],index,times[:index],spec['batch_observations_seconds'],prior)):
            raise ValueError('Original raw/intent/ack/all-time forecast binding differs')
        batch=[];scoring=[]
        for row,item in zip(part,raw):
            seed=row['sampling_seed'];label=f'sample{seed}'
            stop,unmapped=decode_record(row,item,(label,seed,.6,.95),tokenizer,mapped,special,151936)
            # Original decode preserves model-vocabulary padding IDs only in a
            # true length-cap stream; they remain counted and cannot be unknown zeros.
            unknown+=len(unmapped);stops[label][stop['stop_reason']]+=1
            original=gold[row['problem_id']]
            answer=original['answer']
            if not isinstance(answer,str) or not answer.strip():raise ValueError('Unsupported gold cannot be zero')
            entry=dict(id=label+'::'+row['problem_id'],problem_id=row['problem_id'],evaluation=label,
                raw_file='raw/'+unit+'.json',raw_record_sha256=digest(item),stop=stop,
                backend_finish_reason=item['finish_reason'],backend_stop_reason=item['stop_reason'],unmapped_ids=unmapped)
            scoring.append(dict(id=entry['id'],problem_id=row['problem_id'],evaluation=label,
                gold=answer,answer_segment=stop['answer_segment'],stop_reason=stop['stop_reason'],
                original_gold_row_sha256=digest(original),original_decoded_record_sha256=digest(entry)))
            batch.append(entry)
        dump(out/'confirmed_batches'/(unit+'.json'),dict(decoded=batch,scoring=scoring))
        decoded.extend(batch);score_rows.extend(scoring)
    if len(decoded)!=2000 or len({r['id'] for r in decoded})!=2000:raise ValueError('Incomplete sample roster')
    return dict(decoded=decoded,scoring=score_rows,outputs_decoded=2000,unique_questions=500,
        logical_stops={k:dict(v) for k,v in stops.items()},unmapped_token_occurrences=unknown,
        technical_unknown=0,new_training_updates=0,greedy_outputs_generated=0,
        original_state_sha256=proof['original_state_sha256'],repeated_local_binary_loads=0,
        symbolic_scoring_performed=False)
