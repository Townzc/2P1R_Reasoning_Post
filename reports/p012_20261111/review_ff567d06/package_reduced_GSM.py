"""Freeze only new reduced-GSM endpoints; no model calls, re-scoring or bootstrap."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, sys, zipfile
sys.path.insert(0,'reports/p012_20261111/review_46e98da5')
from current_budget import accounting
from a7_ops import lock
P=Path('reports/p012_20261111');L=Path('.local/p012_20261111')
OUT=P/'results_afterb0d31d3a_A8_gsm_v1'
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,x:Path(p).write_text(json.dumps(x,indent=2)+'\n')


def main():
    q=read(L/'gsm_reduction_20261114_v1/QUEUE.json');assert q['status']=='complete'
    names=sorted({e['run_id'] for e in q['events'] if e['stage']=='published'})
    assert 4<=len(names)<=7
    assert not OUT.exists();OUT.mkdir();(OUT/'inputs').mkdir()
    entries=[];table=[]
    def bind(spec):
        original=Path(spec['path']);assert sha(original)==spec['sha256']
        existing=P/'results_aftere9f0ebdd_v1/inputs'/(spec['sha256'][:16]+'_'+original.name)
        if existing.exists():assert sha(existing)==spec['sha256'];return {'path':str(existing),'sha256':spec['sha256']}
        target=OUT/'inputs'/(spec['sha256'][:16]+'_'+original.name)
        if not target.exists():shutil.copyfile(original,target)
        return {'path':str(target),'sha256':sha(target)}
    for name in names:
        folder=P/name.replace('_20261114','');assert not (folder/'AUDIT_STATUS.json').exists()
        result=read(folder/'RESULTS.json');metrics=result['GSM8K']
        for path in [folder/'RESULTS.json',folder/'evidence.zip']:
            assert subprocess.check_output(['git','hash-object',str(path)],text=True).strip()==subprocess.check_output(['git','rev-parse','HEAD:'+str(path)],text=True).strip()
        with zipfile.ZipFile(folder/'evidence.zip') as z:
            assert z.testzip() is None
            raw_path=next(n for n in z.namelist() if n.endswith('/generation/raw.jsonl'))
            labels_path=next(n for n in z.namelist() if n.endswith('/labels.jsonl'))
            eval_path=raw_path.split('/generation/')[0]+'/REQUEST.json'
            evaluation=json.loads(z.read(eval_path));training=json.loads(z.read('training/REQUEST.json'))
            rb=z.read(raw_path);lb=z.read(labels_path)
            assert digest(rb)==result['raw_sha256'] and digest(lb)==result['labels_sha256']
            raw=[json.loads(x) for x in rb.splitlines()];labels=[json.loads(x) for x in lb.splitlines()]
            assert len(raw)==len(labels)==1319 and len({x['id'] for x in raw})==1319
            assert {(x['id'],x['draw']) for x in raw}=={(x['id'],x['draw']) for x in labels}
            assert sum(x['correct'] for x in labels)==metrics['correct']
            assert metrics['accuracy']==metrics['correct']/1319
            assert training['model']==evaluation['model']==result['model']
            assert training['seed']==evaluation['seed']==result['seed']==17
            assert training['cell']==result['cell'] and training['dose']==result['dose']
            assert training['dataset']['sha256']==result['dataset_sha256']
            assert training['source_sha256']==evaluation['source_sha256']==sha(Path('experiments/p012/tinker_lora.py'))
            sampler=json.loads(z.read('training/SAMPLER.json'));assert evaluation['sampler_path']==sampler['path']
            inp=bind(evaluation['evaluation']);train=bind(training['dataset'])
            assert {x['id'] for x in raw}=={json.loads(x)['id'] for x in Path(inp['path']).read_text().splitlines()}
            pred=result['prediction_before_score'];assert pred['prediction_commit']=='8bbf06a7ef19f56ace1b23dde4607b02bc10b389'
            evidence={role:{'archive':str(folder/'evidence.zip'),'archive_sha256':sha(folder/'evidence.zip'),'member':member,'sha256':digest(z.read(member))}
                for role,member in {'raw':raw_path,'labels':labels_path,'evaluation_request':eval_path,
                'training_request':'training/REQUEST.json','sampler':'training/SAMPLER.json','state':'training/STATE.json'}.items()}
        entry={'run_id':name,'result':{'path':str(folder/'RESULTS.json'),'sha256':sha(folder/'RESULTS.json')},
            'model':result['model'],'cell':result['cell'],'seed':17,'dose':result['dose'],'metrics':metrics,
            'evaluation_input':inp,'training_input':train,'evidence':evidence,'prediction_before_score':pred,
            'independent_result_audit':'pending','exploratory':True,'excluded_from_H0_H3':True}
        if result['model']=='Qwen/Qwen3.5-4B':
            policy=P/'review_46e98da5/T_GSM_INTERPRETATION.json'
            entry['interpretation_policy']={'path':str(policy),'sha256':sha(policy)}
            entry['pretraining_reference']='4-shot1216/1319; 0-shot543/1319 answer-only; holdout pass1/pass8 not capability'
        entries.append(entry)
        table.append(f"| {result['model']} {result['cell']} | {metrics['correct']}/1319 | {100*metrics['accuracy']:.3f}% | {100*metrics['length_cap_rate']:.2f}% | {metrics['loop_count']} | {metrics['normally_terminated_correct']}/{metrics['normally_terminated_count']} |")
    for f in ['POLICY.json','K8_GATES.json','COMPLETION.json']:(OUT/f).write_bytes((P/'amendment8_gsm_reduction_v1'/f).read_bytes())
    (OUT/'PRED_T_TRACK_AND_BRIDGE_v1.md').write_bytes((P/'review_b0d31d3a/PRED_T_TRACK_AND_BRIDGE_v1.md').read_bytes())
    old=read(P/'review_b0d31d3a/NEXT_REVIEW_SCOPE.json')['already_accepted_training_runs']
    existing=[]
    for name in old:
        f=P/name.replace('_20261114','')/'RESULTS.json'
        existing.append({'path':str(f),'sha256':sha(f),'accepted_review_commit':'b0d31d3a6793aff81735d1ca636f113f27e5af2d'})
    write(OUT/'ENDPOINTS.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_endpoints':entries,
        'new_endpoint_count':len(entries),'new_outputs':len(entries)*1319,'previous_accepted_reference_only':existing,
        'G1':'not assessed; K4 cancelled by owner after seeing5/27 results','G2_G3':'Independent review requested; preserve original8bb predictions and46e baseline restriction',
        'new_model_calls_or_rescoring':0,'new_bootstrap_runs':0})
    with lock('BUDGET_ADMISSION.lock'):write(OUT/'BUDGET_SNAPSHOT.json',accounting())
    (OUT/'README.md').write_text('# Reduced Tinker GSM8K: new endpoints after b0d31d3a\n\n'
        f'The owner-reduced queue is complete. This packet requests independent review of {len(entries)} new endpoints / {len(entries)*1319} outputs. The five accepted training endpoints are reference-only. All runs use Tinker LoRA, seed17, unchanged frozen data and scoring; exploratory outsideH0–H3.\n\n'
        '| Endpoint | Correct | Accuracy | Capped | Loops | Normal correct/n |\n|---|---:|---:|---:|---:|---:|\n'+'\n'.join(table)+'\n\n'
        'Please verify the new raw outputs, training/input/sampler bindings and frozen G2–G3 predictions from8bbf06a7. G1 is not judged because K4 was cancelled. POLICY preserves the decision time,5/27 exposure and owner reason; K8_GATES records the prospective per-model P−R>=3pp decision before launch. Cancellation and unused reservations are reconciled in COMPLETION and BUDGET_SNAPSHOT.\n\n'
        'For4B use4-shot1216/1319 as the training-before reference. The0-shot baseline had543/1319 answer-only outputs; holdout pass1/pass8 are descriptive only and are not capability measures. Labels remain the existing Codex labels under the accepted percentage-normalization rule. No re-score or bootstrap was introduced.\n')
    (OUT/'build_packet.py').write_bytes(Path(__file__).read_bytes())
    print(OUT)


if __name__=='__main__':main()
