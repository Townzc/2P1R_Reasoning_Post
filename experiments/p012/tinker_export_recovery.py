"""Export a sampler from a completed training state; never update model weights.

This infrastructure path is gated on explicit owner permission and a one-time
code review. It writes to a new directory and preserves the failed attempt.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_training(request, losses, order, state, partial, expected_state):
    require(request['run_id']=='a6_3_tinker_lora_4b_math_e8_s17_20261113_v1', 'Wrong run')
    require(request['mode']=='train' and request['model']=='Qwen/Qwen3.5-4B' and
            request['cell']=='E8' and request['seed']==17 and request['rank']==32, 'Wrong identity')
    require(request['dose']['expected_updates']==1024 and
            [x['step'] for x in losses]==list(range(1,1025)), 'Incomplete training')
    require([i for row in losses for i in row['row_indices']]==order and
            sorted(order)==sorted(list(range(1024))*8), 'Row order or dose mismatch')
    require(state['path']==expected_state and '/weights/' in expected_state, 'Wrong state')
    require(partial['training_input_tokens']==request['cpu_counts']['full_training_input_tokens']
            and partial['sampling'] is None, 'Usage mismatch')


def preflight(plan):
    require(plan['model_updates']==0 and plan['sampling_calls']==0, 'Export only')
    values={}
    for name,spec in plan['files'].items():
        require(digest(spec['path'])==spec['sha256'], 'Changed evidence: '+name)
        values[name]=Path(spec['path'])
    req=read(values['request']);losses=[json.loads(x) for x in values['losses'].open()]
    validate_training(req,losses,read(values['order']),read(values['state']),
                      read(values['partial_usage']),plan['expected_state_path'])
    require(not Path(plan['output']).exists(), 'Output already exists; no replay')
    return req


def export(plan, approval):
    req=preflight(plan)
    require(approval.get('owner_approved_export_only') is True, 'Owner export approval required')
    review=approval.get('accepted_recovery_review_commit','')
    require(len(review)==40 and all(c in '0123456789abcdef' for c in review), 'Recovery review required')
    require(approval.get('plan_sha256')==plan['_plan_sha256'], 'Approval belongs to another plan')
    require(approval.get('export_source_sha256')==digest(__file__), 'Source not approved')
    require(approval.get('storage_available') is True, 'Storage disposition required')
    import tinker
    rest=tinker.RestClient()
    info=rest.get_weights_info_by_tinker_path(plan['expected_state_path']).result().model_dump(mode='json')
    require(info['base_model']==req['model'] and info['is_lora'] and info['lora_rank']==32,
            'Remote checkpoint identity mismatch')
    for flag in ['train_mlp','train_attn','train_unembed']:
        require(info[flag] is True, 'Remote target layers changed')
    out=Path(plan['output']);out.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        with (out/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    write('PLAN.json',plan);write('APPROVAL.json',approval);write('WEIGHTS_INFO.json',info)
    service=tinker.ServiceClient(display_name='P012 E8 completed-state sampler export')
    try:
        client=service.create_training_client_from_state(plan['expected_state_path']).result()
        saved=client.save_weights_for_sampler('final_export_recovery',ttl_seconds=60*86400).result()
        write('SAMPLER.json',saved.model_dump(mode='json'))
        write('COMPLETE.json',{'success':True,'operation':'export_only','started_utc':started,
              'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_state_path':plan['expected_state_path'],'new_training_updates':0,
              'new_forward_calls':0,'new_sampling_calls':0,'original_request_sha256':plan['files']['request']['sha256']})
        service.close(status='success').result()
    except BaseException:
        write('FAILED.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            'automatic_retry':False,'new_training_updates':0})
        service.close(status='errored').result()
        raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--approval',type=Path);args=parser.parse_args()
    plan=read(args.plan);plan['_plan_sha256']=digest(args.plan)
    if args.approval is None:
        preflight(plan);print('CPU preflight passed; no remote call')
    else:
        export(plan,read(args.approval))


if __name__=='__main__':
    main()
