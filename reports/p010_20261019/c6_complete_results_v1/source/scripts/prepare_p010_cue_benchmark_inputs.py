"""Bind original C6 test cells to saved no-cue proofs, without decoding/scoring."""
from pathlib import Path
from math import ceil
from experiments.p010.common import read, dump, sha, digest, manifest, utc
from experiments.p010.cue_benchmark_roster import RUNS, parameters, roster, checked_selection


def prepare(root, out):
    root, out = Path(root), Path(out)
    if out.exists():
        raise FileExistsError('Original new input preparation already exists')
    old = Path('.local/p009_20261014/r1')
    selection_file = root/'cue_selection_nonfinite_r1/SELECTION.json'
    completed = read(root/'cue_selection_nonfinite_r1/COMPLETED.json')
    selection = read(selection_file)
    if (completed['selection_sha256'] != sha(selection_file)
            or checked_selection(selection) != [1249]):
        raise ValueError('Actual complete original development selection required')
    math_file = root/'student_inputs_r2/MATH_ENDPOINT.json'
    math_rows = read(math_file)
    old_math_file = old/'stage0_inputs_r1/qwen_math_zero.json'
    old_math = read(old_math_file)['prompts']
    if [(x['problem_id'], x['input_ids']) for x in math_rows] != [(x['problem_id'],x['input_ids']) for x in old_math]:
        raise ValueError('Same original full MATH endpoint required')
    gsm_file = old/'p0_r1/inputs/qwen_gsm_zero_parity.json'
    original_gsm = read(gsm_file)['prompts']
    gsm_rows = [dict(candidate_id='C6::'+x['problem_id'],problem_id=x['problem_id'],
        input_ids=x['input_ids'],source_row_sha256=digest(x)) for x in original_gsm]
    ids = dict(math=[x['problem_id'] for x in math_rows],gsm=[x['problem_id'] for x in gsm_rows])
    sources = {}
    def load(path):
        path = Path(path); value = read(path)
        sources[str(path)] = dict(bytes=path.stat().st_size,sha256=sha(path))
        return value
    # These are original saved Booleans, not new scorer executions.
    math_oracle = old/'stage0_generation_budget_r2/exports/qwen_p3/evidence/LOCAL_ORACLE_AUDIT.json'
    raw_math = load(math_oracle)
    p1_rows = load(old/'p1_actual_r1/ROWS.json')
    p1_scores = load(old/'p1_actual_r1/ALL_SCORED_ROWS.json')
    if len(p1_rows) != len(p1_scores) or [x['id'] for x in p1_rows] != [x['id'] for x in p1_scores]:
        raise ValueError('Original complete P1 row/score identity differs')
    pairs = [(a,b) for a,b in zip(p1_rows,p1_scores) if a['dataset']=='qwen_math_zero']
    if (not raw_math['passed'] or [a['problem_id'] for a,b in pairs] != ids['math']
            or [x['problem_id'] for x in raw_math['decoded']['qwen_math_zero']] != ids['math']):
        raise ValueError('Original accepted base MATH provenance differs')
    base_math = {a['problem_id']:b['score']['correct'] for a,b in pairs}
    gsm_oracle = old/'p0_entry_repair_r1/export_r1/evidence/LOCAL_ORACLE_AUDIT.json'
    raw_gsm = load(gsm_oracle)
    if not raw_gsm['passed'] or [x['problem_id'] for x in raw_gsm['scored']['base_638']] != ids['gsm']:
        raise ValueError('Original internal-vLLM GSM proof differs')
    base_gsm = {x['problem_id']:x['score']['task_answer_correct'] for x in raw_gsm['scored']['base_638']}
    s1_raw_file = old/'stage1_s1_r1/oracles/s1_s17_n400/COMPLETED.json'
    s1_score_file = old/'stage1_s1_r1/scores/s1_s17_n400/LOCAL_ORACLE_AUDIT.json'
    s1_sample_raw_file = root/'existing_s1_sample_oracles/s1_s17_n400/COMPLETED.json'
    s1_sample_score_file = root/'existing_s1_sample_scores/s1_s17_n400/LOCAL_ORACLE_AUDIT.json'
    t72_raw_file = root/'student_oracles/t72_s17_n400_k1/COMPLETED.json'
    t72_score_file = root/'student_scores/t72_s17_n400_k1/LOCAL_ORACLE_AUDIT.json'
    s1_raw,s1_score,s1_sample_raw,s1_sample_score,t72_raw,t72_score = [load(p) for p in
        (s1_raw_file,s1_score_file,s1_sample_raw_file,s1_sample_score_file,t72_raw_file,t72_score_file)]
    if any(v.get('passed') is not True for v in [s1_raw,s1_score,s1_sample_raw,s1_sample_score,t72_raw,t72_score]):
        raise ValueError('All original complete model/score proofs required')
    tables = dict(base_math=dict(greedy=base_math),base_gsm=dict(greedy=base_gsm),
        s1_n400_math=dict(greedy=s1_score['question_correct'],
            **{k:v['question_correct'] for k,v in s1_sample_score['endpoints'].items()}),
        t72_n400_math={k:v['question_correct'] for k,v in t72_score['endpoints'].items()})
    provenance = dict(base_math=dict(greedy=(math_oracle,old/'p1_actual_r1/ALL_SCORED_ROWS.json')),
        base_gsm=dict(greedy=(gsm_oracle,gsm_oracle)),
        s1_n400_math=dict(greedy=(s1_raw_file,s1_score_file),
            **{f'sample{i}':(s1_sample_raw_file,s1_sample_score_file) for i in range(4)}),
        t72_n400_math={label:(t72_raw_file,t72_score_file) for label in ['greedy']+[f'sample{i}' for i in range(4)]})
    rosters={}
    for run in RUNS:
        task='gsm' if run=='base_gsm' else 'math'; proofs={}
        for label, table in tables[run].items():
            if set(table)!=set(ids[task]) or any(type(v) is not bool for v in table.values()):
                raise ValueError('Complete original Boolean table required, unknown is not zero')
            raw_file,score_file=provenance[run][label]
            proofs[label]=dict(problem_ids=ids[task],parameters=parameters(task,label),cue_token_ids=[],
                raw_proof_sha256=sha(raw_file),score_proof_sha256=sha(score_file),complete=True,technical_unknown=0)
        rosters[run]=roster(run,gsm_rows if task=='gsm' else math_rows,selection,proofs)
    original_spec=load('reports/p010_20261019/c6_search_runtime_v1/SPEC.json')
    base=original_spec['model']
    model_bindings={run:dict(remote_path=base['remote_path'],files=base['files'],parent=None,
        new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0) for run in ('base_math','base_gsm')}
    for run,folder,key,merged_file in [
            ('s1_n400_math','existing_s1_sample_runs/s1_s17_n400','existing_s1_samples/s1_s17_n400',
             'existing_s1_sample_exports/s1_s17_n400/evidence/ORIGINAL_MODEL_PROOF.json'),
            ('t72_n400_math','student_runs/t72_s17_n400_k1','student/t72_s17_n400_k1',
             'student_exports/t72_s17_n400_k1/evidence/MERGE_PROOF.json')]:
        terminal=load(root/folder/'RESULT.json'); proof=load(root/merged_file)
        if terminal['status']!='completed':raise ValueError('Persisted completed student required')
        files=proof['merged_files']
        if any(terminal['artifact']['all_files'].get('merged/'+n)!=v for n,v in files.items()):
            raise ValueError('Original persisted merged model is absent from final artifact')
        model_bindings[run]=dict(remote_path='/evidence/p010-20261019/'+key+'/merged',files=files,
            parent=dict(terminal_key=key+'/terminal',terminal=terminal,original_merged_files=files),
            new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0)
    reviews={}
    for name,path in [('P009_P0_raw',old/'P0_ACTUAL_A2_INTEGRITY_ACCEPTED.json'),
            ('P009_internal_only',old/'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json'),
            ('P009_P1',old/'P1_COMPLETE_A2_ACCEPTED.json'),
            ('P009_S1',old/'stage1_s1_r1/FIRST_PAIR_STOP_A4_ACCEPTED.json'),
            ('P010_results',root/'K1_E1D_S1_SAMPLES_C9_A3_ACCEPTED.json')]:
        value=load(path);reviews[name]={k:value[k] for k in ('scope','decision','report_sha256','target_commit')}
    basis=dict(utc=utc(),selection_file_sha256=sha(selection_file),selected_cue=[1249],
        selection_complete_file_sha256=sha(root/'cue_selection_nonfinite_r1/COMPLETED.json'),
        endpoint_files={str(p):sha(p) for p in (math_file,old_math_file,gsm_file)},
        original_sources=sources,actual_independent_reviews=reviews,
        new_outputs={k:v['new_outputs'] for k,v in rosters.items()},
        new_batches=sum(ceil(v['new_outputs']/256) for v in rosters.values()),
        no_training_or_encoding_or_decoding_or_scoring=True,scientific_dispatch_admitted=False)
    out.mkdir(parents=True,exist_ok=False)
    for run,value in rosters.items():dump(out/(run+'.json'),value)
    dump(out/'MODEL_BINDINGS.json',model_bindings)
    dump(out/'SELECTION.json',selection)
    dump(out/'EXISTING_NO_CUE_TABLES.json',tables)
    dump(out/'BASIS.json',basis)
    dump(out/'MANIFEST.json',manifest(out))
    dump(out/'COMPLETED.json',dict(utc=utc(),basis_sha256=sha(out/'BASIS.json'),
        new_outputs=21371,new_batches=85,new_encoding=0,new_symbolic_scoring=0,new_model_calls=0))
    return basis


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();value=prepare(a.root,a.out)
    print(json.dumps({k:v for k,v in value.items() if k not in ('original_sources','actual_independent_reviews')}))
