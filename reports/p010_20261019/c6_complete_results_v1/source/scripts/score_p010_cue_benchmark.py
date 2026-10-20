"""Score only new C6 outputs; original no-cue Boolean tables stay untouched."""
import argparse,datetime,json,time
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,utc
from experiments.p010.cue_benchmark_roster import RUNS


def partitions(rows,run):
    if run not in RUNS or not rows:raise ValueError('Original complete cell required')
    labels=[];result={}
    for row in rows:
        label=row['condition']+'/'+row['evaluation']
        if label not in result:labels.append(label);result[label]=[]
        result[label].append(row)
    expected=([f'no_cue/sample{i}' for i in range(4)] if run.startswith('base_') else [])
    expected+=['cue/greedy']+[f'cue/sample{i}' for i in range(4)]
    n=1319 if run=='base_gsm' else 500
    if labels!=expected or any(len(v)!=n or len({x['problem_id'] for x in v})!=n for v in result.values()):
        raise ValueError('All original new conditions required; no rescoring reused ones')
    ids=None
    for label,part in result.items():
        actual=[x['problem_id'] for x in part]
        if ids is not None and actual!=ids:raise ValueError('Original common question order differs')
        ids=actual
    return result


def projected_math(part):
    """Named500-row view for the unchanged frozen single-endpoint scorer.

    The wrapper separately binds every original ID and condition. The internal
    label 'greedy' is only the scorer's row-schema name; no sampling parameter
    or generated answer is changed.
    """
    return [dict(x,original_benchmark_id=x['id'],original_evaluation=x['evaluation'],
        id='greedy::'+x['problem_id'],evaluation='greedy') for x in part]


def score(a):
    from analyses.completion_contract import completion_score
    from experiments.p010.e9_score_process import supervise_once
    from experiments.p010.e9_scoring import verify_saved_scores
    spec=read(a.spec);oracle=Path(a.oracle);inputs=Path(a.inputs);out=Path(a.out)
    proof=read(oracle/'COMPLETED.json');run=a.run;rows=read(oracle/run/'SCORING_ROWS.json')
    decoded=read(oracle/run/'DECODED_ROWS.json');groups=partitions(rows,run)
    if (proof.get('passed') is not True or proof['spec_sha256']!=sha(a.spec)
            or proof['technical_unknown']!=0 or proof['cells'][run]['scoring_sha256']!=sha(oracle/run/'SCORING_ROWS.json')
            or proof['cells'][run]['decoded_sha256']!=sha(oracle/run/'DECODED_ROWS.json')
            or sha(inputs/'EXISTING_NO_CUE_TABLES.json')!=spec['existing_tables_sha256']
            or [x['id'] for x in decoded]!=[x['id'] for x in rows]):
        raise ValueError('Original whole-group full oracle and saved reused tables required')
    for name,h in {**spec['source_files'],**spec['verification_source_files']}.items():
        if sha(name)!=h:raise ValueError('Original reviewed source changed: '+name)
    cap=1200 if run=='base_gsm' else len(groups)*5200+120
    cutoff=datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp()
    if time.time()+cap+5>cutoff:raise TimeoutError('Whole local new-score window no longer fits')
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    binding=dict(run=run,oracle_sha256=sha(oracle/'COMPLETED.json'),spec_sha256=sha(a.spec),
        original_rows_sha256=sha(oracle/run/'SCORING_ROWS.json'),reused_tables_sha256=spec['existing_tables_sha256'])
    dump(out/'INTENT.json',dict(utc=utc(),binding=binding,local_seconds=cap,no_retry=True,
        repeated_old_scoring=0,new_model_calls=0,per_MATH500_cap_seconds=5200))
    tables={};summaries={}
    try:
        if run=='base_gsm':
            import os,threading
            timer=threading.Timer(cap,lambda:os._exit(124));timer.daemon=True;timer.start()
            try:
                events={x['id']:x['stop'] for x in decoded}
                for label,part in groups.items():
                    values=[dict(id=x['id'],problem_id=x['problem_id'],score=completion_score(
                        dict(answer=x['gold']),events[x['id']])) for x in part]
                    dump(out/'new_scores'/(label+'.json'),values)
                    tables[label]={x['problem_id']:x['score']['task_answer_correct'] for x in values}
                    summaries[label]=dict(correct=sum(tables[label].values()),total=1319,
                        scorer='marked_answer_v1 plus frozen task-boundary completion',symbolic_comparisons=0)
            finally:timer.cancel()
        else:
            for label,part in groups.items():
                if time.monotonic()-start+5200>cap:raise TimeoutError('Original full local score window insufficient')
                projected=projected_math(part)
                current=dict(binding,label=label,original_part_sha256=digest(part),projection_sha256=digest(projected),
                    actual_generation_evaluation=part[0]['evaluation'],projection_is_schema_only=True)
                control=out/'jobs'/label
                supervise_once(control,projected,current,5200)
                verified=verify_saved_scores(control/'payload',projected,current,5200)
                table=verified['endpoints']['greedy']['question_correct'];tables[label]=table
                summaries[label]=dict(correct=sum(table.values()),total=500,
                    original_local_proof_sha256=sha(control/'COMPLETED.json'),
                    frozen_payload_sha256=sha(control/'payload/COMPLETED.json'),
                    independent_adjudication_complete=False,unique_symbolic_pairs=verified['unique_symbolic_pairs'])
        original=read(inputs/'EXISTING_NO_CUE_TABLES.json')[run]
        for label,table in original.items():
            key='no_cue/'+label
            if key in tables:raise ValueError('No original condition may be regenerated or rescored')
            tables[key]=table;summaries[key]=dict(reused_original_saved_Boolean_table=True,
                source_tables_sha256=spec['existing_tables_sha256'],new_scoring=False)
        expected={c+'/'+e for c in ('no_cue','cue') for e in ['greedy']+[f'sample{i}' for i in range(4)]}
        if set(tables)!=expected or time.monotonic()-start>=cap:
            raise ValueError('Complete original10-condition cell or bounded closeout missing')
        dump(out/'QUESTION_CORRECT.json',tables);dump(out/'CONDITION_SUMMARIES.json',summaries)
        done=dict(passed=True,utc=utc(),run=run,original_binding=binding,
            question_correct_sha256=sha(out/'QUESTION_CORRECT.json'),new_outputs=len(rows),
            original_conditions_reused=sorted(original),bootstrap_performed=False,
            technical_unknown=0,elapsed_seconds=time.monotonic()-start,
            old_scoring_repeated=0,old_generation_repeated=0,independent_A3_pending=True)
        dump(out/'COMPLETED.json',done);return done
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),
            completed_new_conditions=sorted(tables),valid_parts_preserved=True,whole_retry=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('spec','oracle','inputs','run','out'):p.add_argument('--'+n,required=True)
    print(json.dumps(score(p.parse_args())))
