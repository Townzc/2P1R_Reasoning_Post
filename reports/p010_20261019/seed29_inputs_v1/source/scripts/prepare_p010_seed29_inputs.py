"""Prepare the four original Tier3 seed replications without changing data.

The existing seed17 question/answer rosters and token arrays are copied exactly.
P009's separately selected seed29 rosters are deliberately not used.
"""
from pathlib import Path
import shutil
from experiments.p010.common import read,dump,sha,digest,manifest,utc
from experiments.p010.multi_answer_plan import make_plan
from experiments.learning_regime_p009.training_plan import UPDATES,TARGETS,LR_VECTOR_SHA256

CELLS={f'{teacher}_s29_n{n}_k1':dict(teacher=teacher,n=n,P=n,K=1,seed=29)
       for teacher in ('t15','t72') for n in (400,3200)}


def check_inventory(rows,encoded,n):
    if (len(rows)!=n or len(encoded)!=n or len({x['problem_id'] for x in rows})!=n
            or len({x['path_id'] for x in rows})!=n
            or [(x['problem_id'],x['path_id']) for x in rows]
            !=[(x['problem_id'],x['path_id']) for x in encoded]):
        raise ValueError('Exact same seed17 unique question/answer order required')
    if any(x['n_processed']>2048 or x['input_ids'][-1]!=151643
           or x['labels'][-1]!=151643 for x in encoded):
        raise ValueError('Original full answer and EOS must remain unchanged')
    if sum(x['n_supervised'] for x in encoded)>TARGETS:
        raise ValueError('Whole inventory exceeds dose; no shrinkage allowed')
    return True


def original_files(root,teacher,n):
    if teacher=='t15':
        base=Path('.local/p009_20261014/r1/stage1_s1_inputs_r1')
        m=read(base/'MANIFEST.json')
        files={k:base/f's1_s17_n{n}_{k}.json' for k in ('rows','encoded')}
        expected={k:m[p.name] for k,p in files.items()}
    else:
        base=Path(root)/'student_inputs_r2';name=f't72_s17_n{n}_k1'
        m=read('reports/p010_20261019/student_runtime_k1_e1d_v1/SPEC.json')['input_files']
        files={k:base/name/(k+'.json') for k in ('rows','encoded')}
        expected={k:m[name+'/'+k+'.json'] for k in files}
    for k,p in files.items():
        if expected[k]!=dict(bytes=p.stat().st_size,sha256=sha(p)):
            raise ValueError('Original already accepted input changed')
    return files


def prepare(root):
    r=Path(root);out=r/'seed29_inputs_r1'
    a=read(r/'T72_DATA_A1_ACCEPTED.json')
    b=read('.local/p009_20261014/r1/STAGE1_S1_INPUTS_ACCEPTED.json')
    if a['decision'] not in ('PASS','PASS-WITH-NOTES') or b['decision'] not in ('PASS','PASS-WITH-NOTES'):
        raise ValueError('Original real input acceptances required')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),scope='original_P010_v3_section_3_7',new_seed=29,
        source_data_seed17=True,original_plan_commit='4287537f7733f5c3568ddb11695d47b566ef75fa',
        new_model_calls=0,new_answer_encodings=0,new_teacher_outputs=0,automatic_retry=False))
    try:
        summaries={};source_refs={}
        for run,cell in CELLS.items():
            files=original_files(r,cell['teacher'],cell['n']);rows=read(files['rows']);encoded=read(files['encoded'])
            check_inventory(rows,encoded,cell['n']);dest=out/run;dest.mkdir()
            for k,p in files.items():
                with p.open('rb') as f,(dest/(k+'.json')).open('xb') as g:shutil.copyfileobj(f,g)
                assert sha(p)==sha(dest/(k+'.json'))
            plan=make_plan(encoded,29,151643);dump(dest/'plan.json',plan)
            model=read('reports/p010_20261019/student_runtime_k1_e1d_v1/SPEC.json')['model']
            config=dict(experiment='P010',run_id=run,**cell,model=[model['model_id'],model['revision']],
                updates=UPDATES,targets=TARGETS,training_rows_sha256=digest(rows),encoded_rows_sha256=digest(encoded),
                plan_sha256=digest(plan),lr_vector_sha256=LR_VECTOR_SHA256,endpoint_count=500,endpoint_repetitions=5,
                original_data_unchanged=True,Tier3=True,runtime_admitted=False)
            dump(dest/'config.json',config)
            summaries[run]=dict(n=len(rows),once_each_targets=sum(x['n_supervised'] for x in encoded),
                q=plan['q'],min_exposures=min(plan['row_exposures']),max_exposures=max(plan['row_exposures']),
                updates=UPDATES,targets=TARGETS,seed=29,source_data_seed=17,answer_texts_and_tokens_unchanged=True)
            source_refs[run]={k:dict(file=str(p),bytes=p.stat().st_size,sha256=sha(p)) for k,p in files.items()}
        endpoint=r/'student_inputs_r2/MATH_ENDPOINT.json'
        expected=read('reports/p010_20261019/student_runtime_k1_e1d_v1/SPEC.json')['input_files']['MATH_ENDPOINT.json']
        assert expected==dict(bytes=endpoint.stat().st_size,sha256=sha(endpoint))
        with endpoint.open('rb') as f,(out/'MATH_ENDPOINT.json').open('xb') as g:shutil.copyfileobj(f,g)
        done=dict(utc=utc(),status='PREPARED_A1_PENDING',cells=summaries,original_input_files=source_refs,
            T72_A1_report_sha256=a['report_sha256'],S1_A1_report_sha256=b['report_sha256'],
            original_plan_commit='4287537f7733f5c3568ddb11695d47b566ef75fa',new_model_calls=0,new_answer_encodings=0,
            new_teacher_outputs=0,new_symbolic_scores=0,actual_A1_A2_and_original_A4_required=True)
        dump(out/'COMPLETED.json',done);dump(out/'MANIFEST.json',manifest(out));return done
    except BaseException as e:
        dump(out/'FAILED.json',dict(utc=utc(),error=str(e),type=type(e).__name__,valid_parts_preserved=True,automatic_retry=False));raise


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('--root',required=True)
    print(json.dumps(prepare(p.parse_args().root),ensure_ascii=False))
