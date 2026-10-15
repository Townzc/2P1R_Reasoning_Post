# Prepared preclaim guard-intent repair; original sources retained.
# New physical/campaign/spec binding; full science oracle body retained.
"""One complete NC state/dose/raw oracle; never runs training or inference."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from analyses.completion_contract import first_stop, completion_score
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_p008.block_journal import POLICY, verify_training_blocks
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.stage1_nc_guard_repair_binding import (
    CAMPAIGN, validate, intent, marker, dispatch_key, logical_key)
from experiments.learning_regime_p009.stage1_nc_replacement_contract import forecast, transport_checked
from experiments.learning_regime_p009.stage1_training_core import checked_recipe
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, validate_observed_engine
from src.sft_data import encode_row, read_jsonl


def check_state(state, identity, plan, targets, processed):
    import torch
    if (state['identity'] != identity or state['step'] != 1024 or state['cursor'] != 1024
            or state['schedule'] != plan['updates'] or state['lrs'] != plan['lrs']
            or state['supervised_tokens'] != targets or state['processed_tokens'] != processed):
        raise ValueError('Full checkpoint trajectory/dose differs')
    names = state['trainable_names']; adapter = state['adapter']; optimizer = state['optimizer']
    if (not names or len(names) != len(set(names)) or set(names) != set(adapter)
            or any('lora_' not in n for n in names)):
        raise ValueError('Complete original adapter names required')
    params = [i for g in optimizer['param_groups'] for i in g['params']]
    if len(params) != len(names) or len(set(params)) != len(params) or set(optimizer['state']) != set(params):
        raise ValueError('All optimizer states must map to all trainable tensors')
    for n, i in zip(names, params):
        a = adapter[n]; s = optimizer['state'][i]
        if (not isinstance(a,torch.Tensor) or a.dtype != torch.float32 or not torch.isfinite(a).all()
                or set(s) != {'step','exp_avg','exp_avg_sq'} or float(s['step']) != 1024):
            raise ValueError('Adapter or AdamW state is incomplete/nonfinite')
        for k in ('exp_avg','exp_avg_sq'):
            if s[k].shape != a.shape or s[k].dtype != a.dtype or not torch.isfinite(s[k]).all():
                raise ValueError('Optimizer tensor shape/dtype/finite mismatch')
    rng = state['rng']
    if (set(rng) != {'python','numpy','torch','cuda'} or not rng['python']
            or len(rng['numpy']) != 5 or len(rng['numpy'][1]) != 624
            or not isinstance(rng['torch'],torch.Tensor) or rng['torch'].dtype != torch.uint8
            or rng['torch'].numel() == 0 or len(rng['cuda']) != 1
            or not isinstance(rng['cuda'][0],torch.Tensor) or rng['cuda'][0].dtype != torch.uint8
            or rng['cuda'][0].numel() == 0):
        raise ValueError('Complete original Python/NumPy/Torch/CUDA RNG is required')


def audit(args):
    from transformers import AutoTokenizer
    root=Path(args.root); inputs=Path(args.inputs); spec=read(args.admission)
    env=read(args.receipt); db=read(args.ledger); provider=read(args.provider)
    sent=read(root/'intent.json'); run=sent['run_id']; cap=validate(spec,sent['plan'],run,sent['release'])
    if sent['spec'] != spec or run != args.run:
        raise ValueError('Actual sent spec/run differs')
    for p,h in spec['source_files'].items():
        if sha(p)!=h:raise ValueError('Exact reviewed source changed')
    pre='midpoint/'+CAMPAIGN+'/'; claim=db[pre+'claim/'+run]; terminal=db[pre+'terminal/'+run]
    if (terminal!=env['receipt'] or terminal['status']!='completed'
            or claim['run_id']!=run or terminal['run_id']!=run
            or claim['reserved_cents']!=cap['reserved_cents']
            or terminal['actual_cost_cents']!=cap['reserved_cents']
            or terminal['attempt_id']!=claim['attempt_id']
            or db[pre+'attempt/'+run+'/'+claim['attempt_id']]!=claim
            or terminal['claim_sha256']!=digest(claim)
            or terminal['evidence_sha256']!=digest(env['artifact_manifest'])
            or db[pre+'intent/'+run]!=intent(spec,run)
            or claim['intent_sha256']!=digest(intent(spec,run))
            or claim['plan_sha256']!=digest(sent['plan'])):
        raise ValueError('Original complete receipt/claim/intent differs')
    expected=marker(spec,run,sent['release'])
    if expected['provider_app_id']!=args.app_id or any(db.get(k)!=expected for k in (dispatch_key(run),logical_key(run))):
        raise ValueError('Permanent original physical/logical dispatch fence differs')
    for k,v in spec['required_records'].items():
        if db.get(k)!=v:raise ValueError('Original scientific dependency changed')
    apps=spec['required_stopped_app_ids']+[args.app_id]
    if provider['app_ids']!=apps or provider['state']!='stopped' or provider['owned_container_ids']:
        raise ValueError('All required original apps must be STOPPED0')
    validate_stopped_apps(apps,provider['original_app_info'],provider['owned_containers'])
    if (abs(sent['hard_deadline_epoch']-sent['worker_started_epoch']-cap['worker_seconds'])>.001
            or terminal['finished_epoch']>sent['hard_deadline_epoch']):
        raise ValueError('Original whole-worker timer including pack was exceeded')
    files=read(root/'artifact_manifest.json')
    if files!=env['artifact_manifest']:raise ValueError('Original manifest differs')
    verify(root,files);verify(inputs,spec['inputs'])
    if {n for n in files if n.endswith('.pt')}!={'checkpoint_1024/state.pt'}:
        raise ValueError('Only the complete terminal1024 state is permitted')
    result=read(root/'result.json')
    if result!=env['result'] or any(result[k]!=v for k,v in dict(new_outputs=1319,updates=1024,targets=2097148,reserved_cents=cap['reserved_cents']).items()):
        raise ValueError('Original full result/dose differs')
    stem=f'nc17_n{cap["n"]}'
    rows,encoded,plan,cfg=[read(inputs/(stem+'_'+k+'.json')) for k in ('rows','encoded','plan','config')]
    checked_recipe(cfg,encoded,plan)
    tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,use_fast=True)
    for n,v in spec['base']['files'].items():
        if n in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','config.json'):
            if sha(Path(args.tokenizer)/n)!=v['sha256']:raise ValueError('Original tokenizer/model config differs')
    if [encode_row(x,tok,2048) for x in rows]!=encoded:raise ValueError('Independent full-answer encoding differs')
    recipe=read(root/'recipe.json'); identity=recipe['identity']
    expected_identity=dict(campaign=CAMPAIGN,run_id=run,config=cfg,spec_sha256=digest(spec),
        source_files=spec['source_files'],base_files=spec['base']['files'],input_files=spec['inputs'],
        config_sha256=digest(cfg),actual_NC_G0_report_sha256=spec['G0_report_sha256'],
        input_review_report_sha256=spec['input_report_sha256'])
    if identity!=expected_identity or recipe['schedule']!=plan['updates'] or recipe['lrs']!=plan['lrs']:
        raise ValueError('Original recipe identity/trajectory differs')
    attempts={p.stem:read(p) for p in (root/'intents').glob('*.json')}
    done={p.stem:read(p) for p in (root/'completed').glob('*.json')}
    if set(attempts)!=set(done):raise ValueError('Incomplete/unknown attempts')
    blocks=verify_training_blocks(attempts,done,db,pre+run+'/',1024)
    expected_units={f'update_{i:04d}' for i in range(1,1025)}|blocks|{'terminal_merge'}|{f'endpoint_{i:05d}' for i in range(0,1319,256)}
    if set(done)!=expected_units:raise ValueError('Extra/missing scientific units')
    targets=processed=0
    for step,indices in enumerate(plan['updates'],1):
        wanted=dict(step=step,indices=indices,lr=plan['lrs'][step-1],
            supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),
            processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
        name=f'update_{step:04d}';targets+=wanted['supervised_tokens'];processed+=wanted['processed_tokens']
        if attempts[name]!=wanted or any(done[name].get(k)!=v for k,v in wanted.items()) or done[name]['cumulative_targets']!=targets or done[name]['cumulative_processed']!=processed:
            raise ValueError('Actual per-update complete-answer dose differs')
    if targets!=2097148:raise ValueError('Total normalized targets differ')
    state=ck.load(root/'checkpoint_1024',identity);check_state(state,identity,plan,targets,processed)
    trained=result['training']; train_seconds=trained['full_block_intervals_seconds']
    merge=read(root/'MERGE_PROOF.json'); joined=read(root/'TRAINING_PROCESS_EXITED.json')
    if (read(root/'TRAINING_CHILD_RESULT.json')!=trained or trained['checkpoint']!=read(root/'checkpoint_1024/manifest.json')
            or trained['identity_sha256']!=digest(identity) or len(train_seconds)!=64
            or not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in train_seconds)
            or merge['checkpoint']!=trained['checkpoint'] or merge['merge_dtype']!='float32'
            or merge['saved_dtype']!='bfloat16' or merge['optimizer_updates_after_terminal_save']!=0
            or done['terminal_merge']['proof_sha256']!=digest(merge)
            or joined['exitcode']!=0 or joined['joined_before_endpoint'] is not True):
        raise ValueError('Complete state, original merge or process-exit proof differs')
    actual_env=read(root/'training_environment.json'); process_info=read(root/'TRAINING_PROCESS.json')
    if (process_info['threads']!=4 or process_info['CUBLAS_WORKSPACE_CONFIG']!=':4096:8'
            or 'H100' not in process_info['gpu'] or process_info['tokenizer_is_verified_base'] is not True
            or actual_env['deterministic_algorithms'] is not True or actual_env['allow_tf32'] is not False):
        raise ValueError('Original deterministic training environment differs')
    metrics=read(root/'block_journal_metrics.json')
    if any(metrics[k]!=v for k,v in dict(policy=POLICY,completed_blocks=64,completed_local_updates=1024,configured_updates=1024,block_boundary_calls=128).items()):
        raise ValueError('Original full block journal metrics differ')
    prior=spec['timing']; stage=spec['stage_remaining_before_cents'][run]
    before=read(root/'BEFORE_TRAINING_FORECAST.json')
    if before!=forecast(before['elapsed_worker_seconds'],64,6,prior['training_block_seconds'],prior['endpoint_batch_seconds'],stage) or not before['admitted']:
        raise ValueError('Original pretraining forecast failed')
    for index in range(64):
        f=read(root/'training_forecasts'/f'{index:03d}.json')
        if f!=forecast(f['elapsed_worker_seconds'],64-index,6,prior['training_block_seconds']+train_seconds[:index],prior['endpoint_batch_seconds'],stage) or not f['admitted']:
            raise ValueError('Training block forecast differs')
        t=read(root/'training_timings'/f'{index:03d}.json')
        if not 0<t['through_original_block_commit_seconds']<=train_seconds[index]:raise ValueError('Full block timing is incomplete')
    endpoint=read(inputs/'NC_ENDPOINT.json');durations=result['endpoint']['full_batch_intervals_seconds']
    environment=read(root/'endpoint/environment.json');validate_observed_engine(environment['actual_engine'])
    if (environment['requested_engine']!=engine_kwargs() or environment['training_process_exit']!=joined
            or environment['endpoint_rows_sha256']!=digest(endpoint) or len(durations)!=6):
        raise ValueError('Original endpoint engine/process/batch roster differs')
    gold_path=Path(args.gold)
    if sha(gold_path)!=spec['gold_file_sha256']:raise ValueError('Frozen local-only gold differs')
    gold={x['problem_id']:x for x in read_jsonl(gold_path)}
    if set(gold)!={x['problem_id'] for x in endpoint}:raise ValueError('Full frozen endpoint IDs required')
    vocab=set(tok.get_vocab().values());special=tuple(tok.all_special_ids);scores={};stops=Counter();decoded=[]
    if {p.name for p in (root/'endpoint/raw').glob('*.json')}!={f'{i:05d}.json' for i in range(0,1319,256)}:
        raise ValueError('Extra/missing raw batches')
    for index,offset in enumerate(range(0,1319,256)):
        f=read(root/'endpoint_forecasts'/f'{index:03d}.json')
        if f!=forecast(f['elapsed_worker_seconds'],0,6-index,prior['training_block_seconds']+train_seconds,prior['endpoint_batch_seconds']+durations[:index],stage) or not f['admitted']:
            raise ValueError('Endpoint forecast differs')
        part=endpoint[offset:offset+256];p=root/'endpoint/raw'/f'{offset:05d}.json';raw=read(p)
        transport_checked(endpoint,part,raw);unit=f'endpoint_{offset:05d}';a=attempts[unit];d=done[unit]
        if (a['request_sha256']!=digest(part) or a['offset']!=offset or a['count']!=len(part)
                or a['candidate_ids']!=[x['candidate_id'] for x in part] or a['measurement_exception'] is not False
                or a['preceding_full_batch_seconds']!=durations[:index] or d['raw_sha256']!=sha(p)
                or d['request_sha256']!=a['request_sha256'] or d['count']!=len(part)
                or d['candidate_ids']!=a['candidate_ids']
                or not joined['observed_exited_epoch']<=a['started_epoch']<=d['finished_epoch']<=terminal['finished_epoch']):
            raise ValueError('Original endpoint attempt/ack/timing differs')
        for row,item in zip(part,raw):
            ids=item['token_ids']
            if any(t not in vocab for t in ids):raise ValueError('Unknown token is not a score zero')
            event=first_stop(ids,lambda x:tok.decode(x,skip_special_tokens=False,clean_up_tokenization_spaces=False),151643,512,special)
            score=completion_score(gold[row['problem_id']],event)
            scores[row['problem_id']]=score['task_answer_correct'];stops[event['stop_reason']]+=1
            decoded.append(dict(problem_id=row['problem_id'],raw_file=str(p.relative_to(root)),
                raw_file_sha256=d['raw_sha256'],stop=event,score=score,backend_finish_reason=item['finish_reason'],backend_stop_reason=item['stop_reason']))
    if len(scores)!=1319 or any(type(x)is not bool for x in scores.values()):raise ValueError('Complete Boolean endpoint required')
    return dict(schema='p009_stage1_NC_guard_repair_full_oracle_v1',passed=True,run_id=run,updates_verified=1024,
        targets_verified=targets,processed_tokens_verified=processed,outputs_rescored=1319,
        state_sha256=sha(root/'checkpoint_1024/state.pt'),artifact_digest=digest(files),
        correct=sum(scores.values()),total=1319,question_correct=scores,logical_stops=dict(stops),
        technical_unknown=0,decoded=decoded,scientific_NC_gate='Separate registered paired analysis required',
        utc=datetime.now(timezone.utc).isoformat(),new_model_calls=0,external_A4_pending=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('root','inputs','admission','run','receipt','ledger','provider','app-id','tokenizer','gold','out'):
        p.add_argument('--'+k,required=True)
    a=p.parse_args();value=audit(a);dump(a.out,value)
    print(json.dumps({k:v for k,v in value.items() if k not in ('decoded','question_correct')}))
