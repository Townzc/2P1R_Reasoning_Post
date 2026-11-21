"""Bind completed S1/data/candidate evidence; CPU only, no external messages."""
import datetime
import hashlib
import json
import re
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
LOCAL = Path('.local/p012_20261111/amendment10_v1')
PUBLIC = Path('reports/p012_20261111')
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    state=read(LOCAL/'RECOVERY_QUEUE.json')
    assert state['status']=='generation_complete_data_and_training_review_required'
    assert state['active_batch'] is None and state['qualified_rows']>=4096
    data=read(HERE/'DATA_MANIFEST.json');budget=read(HERE/'PROSPECTIVE_BUDGET.json')
    assert data['qualified_pool_rows']==state['qualified_rows']
    assert data['training_started'] is False and budget['admitted'] is False
    assert len(data['cells'])==12 and len(list((HERE/'request_templates').glob('*.json')))==14
    bindings=[];summaries=[];total_outputs=0
    def bind(path,role,member=None):
        path=Path(path)
        if member is None:
            value=path.read_bytes()
            entry={'path':str(path),'sha256':sha(path),'bytes':len(value),'role':role}
        else:
            with zipfile.ZipFile(path) as archive:value=archive.read(member)
            entry={'archive':str(path),'archive_sha256':sha(path),'member':member,
                'sha256':hashlib.sha256(value).hexdigest(),'bytes':len(value),'role':role}
        assert not re.search(rb'/Users/[A-Za-z0-9_.-]+/',value)
        bindings.append(entry)
        return value
    identities=read(PUBLIC/'amendment10_s1_v1/AVAILABLE_ROWS.json')
    offset=0;all_seeds=set();all_sequences=set()
    for batch in state['completed_batches']:
        directory=Path(batch['private_directory']);public=Path(batch['public_directory'])
        result=read(public/'RESULTS.json');arc=public/'evidence.zip'
        bind(public/'RESULTS.json','batch summary')
        bind(public/'REQUEST.json','frozen generation request')
        bind(public/'PREDICTION_BEFORE_SCORE.json','timestamped selection authority')
        with zipfile.ZipFile(arc) as archive:
            members=archive.namelist()
        contents={name:bind(arc,'complete original batch evidence',name) for name in members}
        raw=[json.loads(x) for x in contents['result/raw.jsonl'].splitlines()]
        labels=[json.loads(x) for x in contents['labels.jsonl'].splitlines()]
        assert len(raw)==len(labels)==batch['rows']*8
        assert sha(directory/'result/raw.jsonl')==result['raw_sha256']==batch['raw_sha256']
        assert hashlib.sha256(contents['result/raw.jsonl']).hexdigest()==result['raw_sha256']
        assert hashlib.sha256(contents['labels.jsonl']).hexdigest()==result['labels_sha256']
        expected=identities[offset:offset+batch['rows']]
        for i,(row,label) in enumerate(zip(raw,labels,strict=True)):
            question=expected[i//8];draw=i%8
            assert (row['id'],row['row_index'],row['draw'],row['sampling_seed'])==(question['id'],offset+i//8,draw,20000+(offset+i//8)*8+draw)
            assert (row['id'],row['draw'])==(label['id'],label['draw'])
            assert row['prompt_sha256']==question['prompt_sha256']
            assert row['prompt_tokens_sha256']==question['prompt_tokens_sha256']
            assert row['sampling_seed'] not in all_seeds and row['sequence_id'] not in all_sequences
            all_seeds.add(row['sampling_seed']);all_sequences.add(row['sequence_id'])
        offset+=batch['rows'];total_outputs+=len(raw)
        summaries.append({'run_id':batch['run_id'],'rows':batch['rows'],'outputs':len(raw),
            'qualified':batch['qualified'],'cost_usd':batch['token_cost_usd'],
            'public_directory':str(public),'raw_sha256':result['raw_sha256']})
    assert offset==sum(x['rows'] for x in state['completed_batches'])
    if state['qualified_rows']>=4300:
        assert sum(x['qualified'] for x in state['completed_batches'][:-1])<4300
    else:
        assert offset==len(identities)
    assert abs(sum(x['cost_usd'] for x in summaries)-state['successful_attempts_token_cost_usd'])<1e-8
    for directory in [PUBLIC/'amendment10_s1_v1',PUBLIC/'amendment10_s1_addenda_v1']:
        for path in sorted(directory.glob('*')):
            if path.is_file() and path.suffix in ['.json','.py','.md']:
                bind(path,'frozen source and accepted addenda')
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in ['.json','.py','.md','.patch']:
            bind(path,'training preparation, complete data identities and CPU checks')
    for path in [Path('audit/claude/20261120e/P012_PLAN_v1_AMENDMENT_10.md'),
        Path('audit/claude/20261120g/AUDIT_3b6ebaac_A10_S1_batch01_and_length_decision.md'),
        Path('audit/claude/20261120h/P012_AMENDMENT_10_ADDENDUM_2_S1_CAP.md')]:
        bind(path,'authority and prediction freeze')
    out=PUBLIC/'amendment10_combined_training_review_v1';out.mkdir(exist_ok=False)
    manifest={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'authority_commit':data['authority_commit'],'bindings':bindings,'batch_summaries':summaries,
        'generated_questions':offset,'outputs':total_outputs,'qualified_pool':state['qualified_rows'],
        'global_seed_and_sequence_uniqueness':True,'batch_stopping_rule_passed':True,
        'private_source_text_and_prompt_tokens_published':False,'training_started':False,
        'independent_full_data_and_source_review':'pending','first_batch_audit':'f0369f2590dfd4f70dab909c81a9d386bde672ae'}
    (out/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'BUDGET.json').write_text(json.dumps(budget,indent=2)+'\n')
    table='\n'.join(f'| {name} | {d["parents"]} | {d["paths_per_parent"]} | {d["rows"]} | {d["sha256"]} |' for name,d in data['datasets'].items())
    (out/'README.md').write_text(f'''# A10 complete S1 data and training path: combined prereview requested

S1 has completed: {offset:,} questions,{total_outputs:,} model outputs,{state['qualified_rows']:,} qualifying parents. The batch stopping rule and global independent seeds/sequence IDs pass. All original batch outputs,labels,qualification records and usage are hash-bound. The first batch passed f0369f25; its frozen labels and selections remain unchanged. Four longer records use the accepted additive token counts. Failed-attempt evidence and reserve remain preserved.

| Dataset | Parents | Solutions each | Rows | SHA256 |
|---|---:|---:|---:|---|
{table}

The private nested training files use the firstP qualifying parents and firstK distinct correct solutions. DATA_MANIFEST in the preparation directory contains per-cell supervised and input-token totals,12 training cells,source-batch hashes and correct-of8 distributions. Public evidence contains IDs,model outputs,labels and hashes; source passages,options and prompt tokens stay private.

Please review all S1 outputs and the complete selected-data/nesting/dose construction together with SOURCE_DIFF.patch,scoring adapter and14 non-executable request templates under amendment10_training_review_v1. The runner candidate includes the accepted LogiQA-only8192 bound; other tasks and generation/evaluation limits retain4096. Prompt masks,optimizer,cosine and sampling parameters are unchanged. API capabilities report65536 context and trainable=true for4B/9B; any actual server rejection stops execution without truncation.

Budget: S1 accounted plus retained failed reserve${budget['S1_accounted_and_retained_failed_reserve_usd']:.4f}; baselines forecast${budget['baselines_forecast_usd']:.4f};12 training/evaluations forecast${budget['training_and_evaluation_forecast_usd']:.4f}; overall${budget['whole_phase_forecast_usd']:.4f}/200. Subcaps100/6/125 apply together with the hard200 total. These are preparation forecasts,not admissions. Recheck live budget and use baseline/L measurements before subsequent admission. No training or new baseline has started.

INPUT_MANIFEST binds{len(bindings)} public files/archive members. All results exploratory,outsideH0–H3. Training awaits this combined review; no external message is sent by this program.
''')
    sys.path.insert(0,'.local/p012_20261111/amendment7_v1')
    from a7_ops import publish
    print(publish([HERE,out],'P012 A10: submit complete S1 data and isolated training path for combined review'))
    print(json.dumps({'outputs':total_outputs,'qualified_pool':state['qualified_rows'],'bindings':len(bindings),'training_started':False}))


if __name__=='__main__':
    main()
