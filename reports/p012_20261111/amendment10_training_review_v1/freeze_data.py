"""CPU-only A10 selected-data freezing; requires completed S1, never launches jobs."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

PUBLIC = Path(__file__).parent
LOCAL = Path('.local/p012_20261111/amendment10_v1')
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    state = read(LOCAL/'RECOVERY_QUEUE.json')
    assert state['status'] == 'generation_complete_data_and_training_review_required'
    assert state['qualified_rows'] >= 4096
    manifest = read('reports/p012_20261111/amendment10_s1_v1/MANIFEST.json')
    assert sha(LOCAL/'ALL_INPUTS_PRIVATE.json') == manifest['private_input_sha256']
    inputs = read(LOCAL/'ALL_INPUTS_PRIVATE.json')
    identities = {x['id']:x for x in inputs}
    parents=[]; selected={}; counts={}; evidence=[]
    for batch in state['completed_batches']:
        directory=Path(batch['private_directory']); public=Path(batch['public_directory'])
        result=read(directory/'RESULTS.json')
        assert not result['overlength_training_samples']
        assert result['raw_sha256'] == sha(directory/'result/raw.jsonl') == batch['raw_sha256']
        qualified=read(directory/'QUALIFIED.json')
        records=read(directory/'SELECTED_PRIVATE.json')
        assert len(records) == len(qualified)*4
        for q in qualified:
            ident=q['id']; assert ident not in selected
            group=[r for r in records if r['parent_id']==ident]
            assert len(group)==4 and [r['draw'] for r in group]==[x['draw'] for x in q['selected']]
            assert len({' '.join(r['solution'].split()) for r in group})==4
            for r,s in zip(group,q['selected'],strict=True):
                assert r['problem'] == identities[ident]['prompt']
                assert hashlib.sha256(r['solution'].encode()).hexdigest()==s['solution_sha256']==r['solution_hash']
                assert s['full_sequence_tokens']<=4096
            parents.append(q);selected[ident]=group;counts[ident]=q['selected']
        evidence.append({'public_directory':str(public),'archive_sha256':sha(public/'evidence.zip'),
            'qualified_sha256':sha(directory/'QUALIFIED.json'),'raw_sha256':result['raw_sha256'],
            'labels_sha256':result['labels_sha256']})
    assert len(parents)==state['qualified_rows']
    assert [q['row_index'] for q in parents] == sorted(q['row_index'] for q in parents)
    destination=LOCAL/'training_data';destination.mkdir(exist_ok=False)
    pub=PUBLIC/'data';pub.mkdir(exist_ok=False)
    datasets={}
    for p,k in [(512,1),(4096,1),(2048,2),(1024,4),(512,4)]:
        name=f'p{p}_k{k}';records=[];safe=[];supervised=0;training_tokens=0
        for q in parents[:p]:
            for r,c in zip(selected[q['id']][:k],counts[q['id']][:k],strict=True):
                line=json.dumps(r,ensure_ascii=False)+'\n';records.append(line)
                safe.append({'parent_id':r['parent_id'],'draw':r['draw'],'solution_hash':r['solution_hash'],
                    'line_sha256':hashlib.sha256(line.encode()).hexdigest(),**c})
                supervised+=c['supervised_target_tokens'];training_tokens+=c['training_input_tokens']
        target=destination/(name+'.jsonl');target.write_text(''.join(records));target.chmod(0o600)
        assert len(records)==p*k and len({r['parent_id'] for r in safe})==p
        (pub/(name+'_identities.json')).write_text(json.dumps(safe,indent=2)+'\n')
        datasets[name]={'private_path':str(target),'sha256':sha(target),'parents':p,'paths_per_parent':k,
            'rows':p*k,'supervised_tokens_one_epoch':supervised,'training_input_tokens_one_epoch':training_tokens,
            'public_identities':str(pub/(name+'_identities.json')),'public_identities_sha256':sha(pub/(name+'_identities.json'))}
    parent_ids=[q['id'] for q in parents]
    arms={'L':(512,1,2),'P':(4096,1,2),'S2':(2048,2,2),'S4':(1024,4,2),
          'R':(512,1,16),'K4s':(512,4,2),'R8':(512,1,8)}
    order=[(x,17) for x in ['L','P','R','S2','S4','K4s','R8']]+[(x,29) for x in ['P','R','L','S2','S4']]
    cells=[]
    for arm,seed in order:
        p,k,e=arms[arm];dataset=datasets[f'p{p}_k{k}']
        cells.append({'arm':arm,'seed':seed,'P':p,'K':k,'E':e,'updates':p*k*e//8,
            'dataset_sha256':dataset['sha256'],'supervised_tokens':dataset['supervised_tokens_one_epoch']*e,
            'training_input_tokens':dataset['training_input_tokens_one_epoch']*e})
    result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authority_commit':manifest['authority_commit'],
        'status':'data_ready_for_combined_pretraining_review','original_text_public':False,
        'datasets':datasets,'cells':cells,'source_batches':evidence,
        'qualified_pool_rows':len(parents),'selected_first4096_ids':parent_ids[:4096],
        'pool_correct_of8':dict(collections.Counter(q['correct_of8'] for q in parents)),
        'first4096_correct_of8':dict(collections.Counter(q['correct_of8'] for q in parents[:4096])),
        'nesting':'FirstP qualified parents in frozen shuffle order; firstK distinct correct solutions by draw',
        'private_JSONL_serialization':'json.dumps(record,ensure_ascii=False) plus newline; fields parent_id,problem,solution,solution_hash,draw',
        'freeze_script_sha256':sha(__file__),'training_started':False}
    (PUBLIC/'DATA_MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pool':len(parents),'datasets':len(datasets),'training_arms':len(cells),'training_started':False}))


if __name__=='__main__':
    main()
