"""C3: immutable selected inputs from completed teachers and original T15 bytes.

New raw continuations are independently decoded once for structural A1 checks.
Symbolic verdicts are bound to their original saved journals, never rescored here.
"""
import argparse
from collections import Counter
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,manifest,verify,utc
from experiments.p010.dataset_selection import select_grid,select_e1d,usable
from experiments.p010.multi_answer_plan import make_plan
from experiments.p010.teacher_contract import sampling,validate_queue
from src.sft_data import encode_row
from analyses.completion_contract import first_stop


def complete_records(export,inputs,tokenizer):
    export=Path(export);e=export/'evidence';proof=read(export/'COMPLETED.json')
    if proof['provider_stopped'] is not True:
        raise ValueError('Original provider must be closed before selection')
    verify(e,proof['artifact']['compact_members'])
    intent=read(e/'INTENT.json');result=read(e/'RESULT.json');spec=intent['spec']
    verify(inputs,spec['input_files'])
    if result['frozen_scorer']!=sha('experiments/learning_regime_p009/math_scoring.py'):
        raise ValueError('Frozen scorer differs')
    for name,value in spec['source_files'].items():
        if sha(name)!=value:raise ValueError('Original execution source differs')
    indexed=read(e/'RECORD_INDEX.json');seen={};special=set(tokenizer.all_special_ids)
    mapped=set(tokenizer.get_vocab().values());counts=Counter()
    for ip in sorted((e/'intents').glob('*.json')):
        stem=ip.stem;batch=read(ip);rows=batch['rows'];validate_queue(rows,result['model'])
        rp=e/'raw'/f'{stem}.json';sp=e/'scores'/f'{stem}.json';ack=read(e/'acks'/f'{stem}.json')
        raw=read(rp);scores={x['id']:x for x in read(sp)['rows']};derived=read(e/'derived'/f'{stem}.json')
        if (ack['raw_sha256']!=sha(rp) or ack['scores_sha256']!=sha(sp)
                or len(rows)!=len(raw) or len(rows)!=len(derived) or ack['count']!=len(raw)):
            raise ValueError('Batch accounting or original raw/score SHA differs')
        for req,x,d in zip(rows,raw,derived):
            cid=req['candidate_id'];ids=x['token_ids']
            if (cid in seen or cid!=x['candidate_id'] or cid!=d['candidate_id']
                    or x['source_row_sha256']!=req.get('source_row_sha256') or x['sampling']!=sampling(req)
                    or x['output_count']!=1 or x['prompt_token_ids']!=req['prompt_token_ids']
                    or digest(x)!=d['raw_record_sha256'] or d['score']!=scores.get(cid)
                    or d!=indexed[cid] or not ids or len(ids)>1024
                    or any(type(t)!=int or t<0 for t in ids)):
                raise ValueError('Independent raw/request/score binding differs')
            # v3's narrowly preserved unmapped length cap remains unusable;
            # the raw IDs and original frozen logical-stop result are unchanged.
            unknown={t for t in ids if t not in mapped}
            if unknown and (not d.get('transport') or len(ids)!=1024
                            or x['finish_reason']!='length' or any(t in (151645,151643) for t in ids)):
                raise ValueError('Unexpected unmapped token')
            native=next((t for t in ids if t in (151645,151643)),tokenizer.eos_token_id)
            stop=first_stop(ids,lambda ts:tokenizer.decode(ts,skip_special_tokens=False,
                clean_up_tokenization_spaces=False),native,1024,special)
            if stop!=d['stop'] or stop['answer_segment']!=d['answer_text'] or usable(d)!=d['usable']:
                raise ValueError('Independent frozen stop or eligibility differs')
            seen[cid]=d;counts[stop['stop_reason']]+=1
    if set(seen)!=set(indexed) or len(seen)!=result['completed_unique_new_outputs']+result.get('inherited_raw_outputs',0):
        raise ValueError('Complete output roster differs')
    return indexed,dict(rows=len(seen),stops=dict(counts),export_completion_sha256=sha(export/'COMPLETED.json'),
        original_result_sha256=sha(e/'RESULT.json'),original_intent_sha256=sha(e/'INTENT.json'),
        frozen_scorer_sha256=result['frozen_scorer'],new_symbolic_scores=0,
        independent_new_raw_decode=True,scoring_truth_reaudit_pending=True)


def reuse_t15(inputs,p009):
    inputs=Path(inputs);p009=Path(p009);binding=read(inputs/'T15_REUSE.json')
    original=read(p009/'p1_actual_r1/ROWS.json');scored=read(p009/'p1_actual_r1/ALL_SCORED_ROWS.json')
    rows={x['id']:x for x in original if x['dataset']=='math_procurement'}
    scores={x['id']:x for x in scored};records={};rawfiles={}
    for cid,ref in binding['records'].items():
        name=ref['file'];path=inputs/'t15_attempt01_original_raw'/name
        if name not in rawfiles:
            if sha(path)!=binding['physical_files'][name]['sha256']:
                raise ValueError('Original P2 physical bytes changed')
            o=read(path);rawfiles[name]=o['outputs'] if isinstance(o,dict) else o
        raw=rawfiles[name][ref['index']];old=rows[cid]
        if digest(raw)!=ref['record_sha256'] or raw['candidate_id']!=cid:
            raise ValueError('Original P2 candidate changed')
        source=old['original_generation_record']
        if (source['id']!=cid or Path(source['raw_file']).name!=name
                or source['raw_file_sha256']!=binding['physical_files'][name]['sha256']
                or source['source_row_sha256']!=raw['source_row_sha256']):
            raise ValueError('P1 verdict not bound to reused P2 raw bytes')
        d=dict(candidate_id=cid,problem_id=old['problem_id'],attempt=old['attempt'],
            answer_text=old['answer_segment'],stop=source['stop'],score=scores[cid],
            gold_supported=True,raw_record_sha256=ref['record_sha256'],
            raw_file='originalP2/'+name,original_p1_row_sha256=digest(old),reused_original=True)
        d['usable']=usable(d);records[cid]=d
    return records,dict(rows=len(records),new_raw_decode=0,new_symbolic_scores=0,
        original_binding_sha256=sha(inputs/'T15_REUSE.json'),
        original_P1_rows_sha256=sha(p009/'p1_actual_r1/ROWS.json'),
        original_P1_scores_sha256=sha(p009/'p1_actual_r1/ALL_SCORED_ROWS.json'))


def prepare(model,export,inputs,p009,tokenizer_dir,out):
    from transformers import AutoTokenizer
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    dump(out/'STARTED.json',dict(utc=utc(),model=model,new_model_calls=0,new_symbolic_scores=0))
    # All three teachers share the pinned Qwen tokenizer bytes. Training uses
    # this original base tokenizer; native teacher EOS remains in raw evidence.
    tok=AutoTokenizer.from_pretrained(tokenizer_dir,local_files_only=True)
    records,check=complete_records(export,inputs,tok)
    old=None;reuse=None
    if model=='t15':
        inherited,reuse=reuse_t15(inputs,p009)
        if set(inherited)&set(records):raise ValueError('Original output was regenerated')
        records.update(inherited)
        old={str(n):read(Path(p009)/'stage1_s1_inputs_r1'/f's1_s17_n{n}_rows.json') for n in (400,3200)}
    roster=read(Path(inputs)/'MATH_ROSTERS.json');source=read(Path(inputs)/'MATH_SOURCE.json')
    selection=select_grid(model,records,roster['s1'],old)
    if model=='t72':
        selection['cells']['e1d_n3200_k1']=select_e1d(records,roster['e1d_order'],read(Path(export)/'evidence/E1D_ACCEPTED.json'))
    dump(out/'STRUCTURAL_A1.json',dict(new=check,original_reuse=reuse,independent_external_A1_pending=True))
    dump(out/'SELECTION.json',selection)
    lookup={x['problem_id']:x for x in source};encoded_cache={};summaries={}
    for cell,selected in selection['cells'].items():
        if selected.get('reuse_original_S1'):
            summaries[cell]=dict(reuse_S1=True,training_calls=0,N=selected['N'],P_cov=selected['P_cov']);continue
        dest=out/cell;dest.mkdir();rows=[];encoded=[];errors=[]
        for cid in selected['selected_ids']:
            d=records[cid];pid=d['problem_id']
            row=dict(problem_id=pid,path_id=cid,prompt=lookup[pid]['problem'],response=d['answer_text'],
                teacher=model,attempt=d['attempt'],saved_record_sha256=digest(d),
                unverified_fallback=not usable(d))
            rows.append(row)
            if cid not in encoded_cache:
                try:encoded_cache[cid]=encode_row(row,tok,2048)
                except ValueError as exc:encoded_cache[cid]={'encoding_error':str(exc)}
            enc=encoded_cache[cid]
            if 'encoding_error' in enc:errors.append(dict(candidate_id=cid,**enc))
            else:encoded.append(enc)
        dump(dest/'rows.json',rows);dump(dest/'encoded.json',encoded)
        summary=dict(N=len(rows),P_cov=len({x['problem_id'] for x in rows}),
            once_each_targets=sum(x['n_supervised'] for x in encoded),encoding_errors=errors,
            training_admitted=False,report_before_training=selected.get('report_before_training',False),
            underfilled_questions=len(selected.get('underfilled_questions',[])),
            nesting_conflicts=selected.get('nesting_conflicts',[]))
        if not errors and not summary['nesting_conflicts']:
            try:
                plan=make_plan(encoded,17,tok.eos_token_id);dump(dest/'plan.json',plan)
                summary.update(q=plan['q'],min_exposures=min(plan['row_exposures']),max_exposures=max(plan['row_exposures']),
                               dose_targets=plan['supervised_targets'],updates=len(plan['updates']),lr_sha256=plan['lr_vector_sha256'])
            except ValueError as exc:summary['coverage_or_schedule_failure']=str(exc)
        dump(dest/'SUMMARY.json',summary);summaries[cell]=summary
    dump(out/'SUMMARY.json',dict(model=model,cells=summaries,new_generation=0,new_training=0,
        external_A1_pending=True,source_files={__file__:sha(__file__),
        'experiments/p010/dataset_selection.py':sha('experiments/p010/dataset_selection.py'),
        'experiments/p010/multi_answer_plan.py':sha('experiments/p010/multi_answer_plan.py')}))
    dump(out/'MANIFEST.json',manifest(out));print(summaries)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('model','export','inputs','p009','tokenizer-dir','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();prepare(a.model,a.export,a.inputs,a.p009,a.tokenizer_dir,a.out)
