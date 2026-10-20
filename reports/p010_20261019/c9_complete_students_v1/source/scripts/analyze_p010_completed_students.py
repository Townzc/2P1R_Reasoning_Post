"""One deterministic analysis of saved P010 Boolean outcomes, without rescoring."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from experiments.p010.common import read,dump,sha,utc
from analyses.p010_paired_questions import paired_summary

ROOT=Path('reports/p010_20261019')
CELLS={
 't15_n400_k1':('T1.5',400,1,'s1_s17_n400'),
 't15_n3200_k1':('T1.5',3200,1,'s1_s17_n3200'),
 't15_n400_k4':('T1.5',400,4,'t15_s17_n400_k4'),
 't15_n400_k8':('T1.5',400,8,'t15_s17_n400_k8'),
 't7_n400_k1':('T7',400,1,'t7_s17_n400_k1'),
 't7_n3200_k1':('T7',3200,1,'t7_s17_n3200_k1'),
 't72_n400_k1':('T72',400,1,'t72_s17_n400_k1'),
 't72_n3200_k1':('T72',3200,1,'t72_s17_n3200_k1'),
 't72_e1d_n3200_k1':('T72-E1d',3200,1,'t72_s17_e1d_n3200_k1')}

def checked_table(table,ids,correct):
    if (not isinstance(table,dict) or set(table)!=set(ids) or len(ids)!=len(set(ids))
            or any(type(v) is not bool for v in table.values()) or sum(table.values())!=correct):
        raise ValueError('Full original Boolean outcomes and exact question IDs required')
    return [table[p] for p in ids]

def load(path,binding):
    path=Path(path);m=read(path.parent/'MANIFEST.json')[path.name]
    if sha(path)!=m['sha256'] or path.stat().st_size!=m['bytes']:raise ValueError('Immutable analysis input changed: '+str(path))
    binding[str(path)]=m
    return read(path)

def inputs():
    endpoint=Path('.local/p010_20261019/r1/student_inputs_r2/MATH_ENDPOINT.json')
    binding={str(endpoint):dict(bytes=endpoint.stat().st_size,sha256=sha(endpoint))}
    ids=[x['problem_id'] for x in read(endpoint)]
    assert len(ids)==500 and len(set(ids))==500
    greedy={};sampled={};rows=[]
    for name,(teacher,n,k,run) in CELLS.items():
        if name in ('t15_n400_k1','t15_n3200_k1'):
            original=Path('reports/p009_20261014/stage1_s1_results_v1')/run
            primary=load(original/'LOCAL_ORACLE_AUDIT.json',binding)
            secondary=load(ROOT/'existing_s1_samples_results_v1'/run/'SCORING_ORACLE.json',binding)
            assert primary['passed'] and primary['technical_unknown']==0 and secondary['passed']
            assert primary['state_sha256']==secondary['original_state_sha256']
            assert primary['updates_verified']==1024 and primary['targets_verified']==2097148
            correct=primary['correct'];table=primary['question_correct'];caps=primary['logical_stops']['length_cap']
        else:
            primary=secondary=load(ROOT/'student_results_v1'/run/'SCORING_ORACLE.json',binding)
            assert primary['passed'] and primary['updates_verified']==1024 and primary['targets_verified']==2097148
            correct=primary['endpoints']['greedy']['correct'];table=primary['endpoints']['greedy']['question_correct']
            caps=primary['logical_stops']['greedy']['length_cap']
        values=checked_table(table,ids,correct)
        draws=[checked_table(secondary['endpoints']['sample'+str(i)]['question_correct'],ids,secondary['endpoints']['sample'+str(i)]['correct']) for i in range(4)]
        means=[sum(draw[j] for draw in draws)/4 for j in range(500)]
        total=sum(sum(draw) for draw in draws)
        assert total==secondary['sampled_correct'] and len(means)==500
        greedy[name]=dict(complete=True,technical_unknown=0,metric='greedy',question_ids=ids,question_values=values)
        sampled[name]=dict(complete=True,technical_unknown=0,metric='sampled_mean_pass_at_1',question_ids=ids,question_values=means,samples_per_question=4)
        rows.append(dict(cell=name,teacher=teacher,n=n,k=k,seed=17,updates=1024,targets=2097148,greedy_correct=correct,greedy_total=500,greedy_percent=correct/5,greedy_caps=caps,sampled_correct=total,sampled_total=2000,sampled_percent=total/20,status='complete_local_independent_A3_pending_or_prior_accepted',runtime_source_or_scoring_changed=False))
    gsm={};gsm_ids=None
    for n in (400,3200):
        p=ROOT/'e4_endpoint_results_v1'/f'e4_s17_n{n}';proof=load(p/'ENDPOINT_ORACLE.json',binding);decoded=load(p/'DECODED_ROWS.json',binding)
        assert proof['passed'] and proof['technical_unknown']==0 and proof['decoded_rows_sha256']==sha(p/'DECODED_ROWS.json')
        current=[x['problem_id'] for x in decoded]
        if gsm_ids is None:gsm_ids=current
        if current!=gsm_ids:raise ValueError('Original E4 question order differs')
        table={x['problem_id']:x['score']['task_answer_correct'] for x in decoded}
        values=checked_table(table,gsm_ids,proof['correct'])
        gsm[f'e4_n{n}']=dict(complete=True,technical_unknown=0,metric='greedy',question_ids=gsm_ids,question_values=values)
    roster=load(ROOT/'c9_paired_analysis_preparation_v1/FIXED_COMPARISON_ROSTER.json',binding)
    return dict(greedy=greedy,sampled=sampled,gsm=gsm,math_ids=ids,gsm_ids=gsm_ids,rows=rows,roster=roster,binding=binding)

def execute(out):
    if np.__version__!='2.2.6':raise ValueError('Original formal analysis numpy2.2.6 required')
    value=inputs();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),source_files={p:sha(p) for p in ['scripts/analyze_p010_completed_students.py','analyses/p010_paired_questions.py','experiments/p010/common.py']},input_files=value['binding'],new_model_calls=0,new_scores=0,bootstrap_previously_run=False))
    try:
        for group,vectors,contrasts,ids,metric in [
          ('MATH_GREEDY',value['greedy'],value['roster']['primary_MATH'],value['math_ids'],'greedy'),
          ('MATH_SAMPLED',value['sampled'],value['roster']['primary_MATH'],value['math_ids'],'sampled_mean_pass_at_1'),
          ('GSM_E4',value['gsm'],value['roster']['GSM_E4'],value['gsm_ids'],'greedy')]:
            dump(out/(group+'_VECTORS.json'),vectors)
            result=paired_summary(vectors,contrasts,ids,metric);dump(out/(group+'_PAIRED.json'),result)
            columns=['name','left','right','difference_pp','ci_low_pp','ci_high_pp','meets_frozen_3pp_and_positive_lower']
            with (out/(group+'_PAIRED.csv')).open('x',newline='') as f:
                w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader()
                for row in result['contrasts']:w.writerow({**{k:row[k] for k in columns if k not in ('ci_low_pp','ci_high_pp')},'ci_low_pp':row['pointwise_95_ci_pp'][0],'ci_high_pp':row['pointwise_95_ci_pp'][1]})
        dump(out/'COMPLETE_MATH_CELLS.json',value['rows'])
        with (out/'T4_COMPLETE_MATH_CELLS.csv').open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(value['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(value['rows'])
        dump(out/'UNAVAILABLE.json',dict(owner_cancelled=value['roster']['unavailable_owner_cancelled'],C6='original_gpu_complete_local_selection_failed_no_benchmark_effect_available',E5='superseded_unattempted_by_delegated_E9',E9='exact_input_A1_pending_no_calls',Tier3_seeds='unattempted',Z1='Claude_owned_not_read_or_recomputed_by_Codex',missing_values_never_zero=True))
        dump(out/'COMPLETED.json',dict(utc=utc(),passed=True,math_models=9,primary_contrasts=9,secondary_contrasts=9,E4_contrasts=1,draws=10000,seed=20261019,numpy_version=np.__version__,new_scores=0,new_model_calls=0,new_raw_decodes=0,independent_A3_required=True,course_report_prose_generated=False,pointwise_conditional_intervals=True,training_seed_population=False,familywise=False,equivalence=False))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),completed_parts_preserved=True,automatic_retry=False));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);execute(p.parse_args().out)
