"""Prepare delegated E9 exact original T72 texts with OLMo encoding once.

No generation, scoring, training, data reselection, dose reduction or truncation.
If a whole answer does not fit, preserve it and report the actual incompatibility.
"""
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,manifest,verify,utc,MODELS
from experiments.learning_regime_p009.training_plan import make_plan,TARGETS,UPDATES,LR_VECTOR_SHA256
from src.sft_data import encode_row,prefix,read_jsonl


def inspect_cell(rows,encoded,n):
    if (len(rows)!=n or len(encoded)!=n or len({r['problem_id'] for r in rows})!=n
            or len({r['path_id'] for r in rows})!=n):
        raise ValueError('Exact original complete T72 answer roster required')
    for row,item in zip(rows,encoded):
        if (row['problem_id']!=item['problem_id'] or row['path_id']!=item['path_id']
                or item['input_ids'][-1]!=100257 or item['labels'][-1]!=100257):
            raise ValueError('Original answer identity or native EOS differs')
    over=[dict(problem_id=r['problem_id'],path_id=r['path_id'],full_tokens=e['n_processed'])
        for r,e in zip(rows,encoded) if e['n_processed']>2048]
    total=sum(e['n_supervised'] for e in encoded)
    return dict(n=n,once_each_targets=total,whole_context_unsupported=over,max_full_tokens=max(e['n_processed'] for e in encoded),
        every_answer_can_fit_dose=total<=TARGETS,planning_allowed=not over and total<=TARGETS,
        omitted_answers=0,truncated_answers=0,new_selection=False)


def prepare(root):
    from transformers import AutoTokenizer
    r=Path(root);out=r/'e9_inputs_r1'
    authority=read(r/'OWNER_NIGHT_D1_D2_ACCEPTED.json');a1=read(r/'T72_DATA_A1_ACCEPTED.json')
    assert authority['D2']['approved'] is True and authority['D2']['Tier3_replaces']=='E5_Qwen3B'
    assert sha(authority['local_report_file'])==authority['report_sha256']
    assert a1['decision'] in ('PASS','PASS-WITH-NOTES') and {'n400_k1','n3200_k1'}<=set(a1['accepted_cells'])
    original=read('reports/p010_20261019/student_runtime_k1_e1d_v1/SPEC.json')
    olmo=read('reports/p010_20261019/e4_runtime_v1/SPEC.json')['model']
    tokenizer_dir=Path('.local/p009_20261014/r1/source_assets_r1/olmo')
    token_files={n:v for n,v in olmo['files'].items() if n in ('config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt')}
    verify(tokenizer_dir,token_files)
    gold=Path('.local/p009_20261014/r1/stage0_inputs_r1/math500.jsonl')
    assert sha(gold)=='132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d'
    source_rows={}
    for n in (400,3200):
        run=f't72_s17_n{n}_k1';p=r/'student_inputs_r2'/run/'rows.json'
        assert {'bytes':p.stat().st_size,'sha256':sha(p)}==original['input_files'][run+'/rows.json']
        source_rows[n]=read(p)
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),authority_sha256=sha(r/'OWNER_NIGHT_D1_D2_ACCEPTED.json'),
        T72_actual_A1_sha256=sha(r/'T72_DATA_A1_ACCEPTED.json'),new_model_calls=0,new_symbolic_scores=0,automatic_retry=False))
    try:
        tok=AutoTokenizer.from_pretrained(tokenizer_dir,local_files_only=True)
        assert tok.eos_token_id==100257
        cached={};summaries={};configs={}
        for n,rows in source_rows.items():
            encoded=[]
            for row in rows:
                key=digest(row)
                if key not in cached:
                    # Large bound permits a complete diagnostic encoding. The
                    # actual unchanged2048 rule is checked below, never truncated.
                    value=encode_row(row,tok,1000000)
                    dump(out/'confirmed_encodings'/(key+'.json'),value);cached[key]=value
                encoded.append(cached[key])
            check=inspect_cell(rows,encoded,n);summaries[str(n)]=check
            dest=out/f'e9_s17_n{n}';dump(dest/'rows.json',rows);dump(dest/'encoded.json',encoded)
            if check['planning_allowed']:
                plan=make_plan(encoded,17,100257);dump(dest/'plan.json',plan)
                cfg=dict(experiment='P010',arm='E9',run_id=f'e9_s17_n{n}',model=MODELS['olmo'],n=n,seed=17,
                    updates=UPDATES,targets=TARGETS,eos_token_id=100257,rows_sha256=digest(rows),
                    encoded_sha256=digest(encoded),plan_sha256=digest(plan),lr_vector_sha256=LR_VECTOR_SHA256,
                    original_T72_rows_sha256=sha(r/'student_inputs_r2'/f't72_s17_n{n}_k1/rows.json'),
                    endpoint='MATH-500',max_new_tokens=1024,context=2048,Tier3=True,runtime_admitted=False)
                dump(dest/'config.json',cfg);configs[str(n)]=cfg
                check.update(q=plan['q'],min_exposures=min(plan['row_exposures']),max_exposures=max(plan['row_exposures']))
        goldrows=read_jsonl(gold);assert len(goldrows)==500 and len({x['problem_id'] for x in goldrows})==500
        endpoint=[];over_endpoint=[]
        for i,row in enumerate(goldrows):
            text=prefix(row['problem']);ids=tok(text,add_special_tokens=False)['input_ids']
            assert ids and 100257 not in ids
            if len(ids)+1024>2048:over_endpoint.append(dict(problem_id=row['problem_id'],prompt_tokens=len(ids)))
            endpoint.append(dict(candidate_id=f'math/{i:03d}',problem_id=row['problem_id'],input_ids=ids,
                source_row_sha256=digest(dict(problem_id=row['problem_id'],prompt_text=text))))
        dump(out/'MATH_ENDPOINT.json',endpoint)
        status='PREPARED_A1_PENDING' if all(x['planning_allowed'] for x in summaries.values()) and not over_endpoint else 'BLOCKED_FULL_ANSWER_OR_ENDPOINT_CONSTRAINT'
        done=dict(utc=utc(),status=status,cells=summaries,unique_answers_encoded_once=len(cached),
            endpoint_count=500,endpoint_unsupported=over_endpoint,max_endpoint_prompt_tokens=max(len(x['input_ids']) for x in endpoint),
            tokenizer_files=token_files,original_MATH_gold_sha256=sha(gold),model=olmo,
            original_T72_A1_report_sha256=a1['report_sha256'],owner_amendment_report_sha256=authority['report_sha256'],
            new_model_calls=0,new_symbolic_scores=0,old_outputs_regenerated=0,
            every_original_answer_retained=True,new_runtime_A1_A2_required=True,A4_before_paid_Tier3_required=True)
        dump(out/'COMPLETED.json',done);dump(out/'MANIFEST.json',manifest(out));return done
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),error=str(exc),type=type(exc).__name__,partial_valid_parts_preserved=True,automatic_retry=False));raise

if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('--root',required=True)
    print(json.dumps(prepare(p.parse_args().root),ensure_ascii=False))
