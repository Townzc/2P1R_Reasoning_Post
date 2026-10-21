"""New owner controls: filter saved fallback flags, reuse original token rows."""
from pathlib import Path
import shutil,time
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
from experiments.p010.multi_answer_plan import make_plan
from experiments.learning_regime_p009.training_plan import TARGETS,UPDATES,LR_VECTOR_SHA256
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'.local/p011_20261020/r1'
def main():
    out=R/'fallback_clean_inputs_r1';out.mkdir(exist_ok=False)
    dump(out/'ATTEMPT.json',dict(started_epoch=time.time(),original_rows_reencoded=False,new_teacher_generation=False,new_original_scoring=False))
    try:
        inventories={}
        for n in (400,3200):
            source=R/'c1_inputs_r1'/f't72_n{n}';old=read(source/'config.json');rows=read(source/'rows.json');enc=read(source/'encoded.json')
            if (len(rows)!=n or len(enc)!=n or digest(rows)!=old['training_rows_sha256'] or digest(enc)!=old['encoded_rows_sha256']
                    or [x['path_id'] for x in rows]!=[x['path_id'] for x in enc]
                    or any(type(x['unverified_fallback']) is not bool for x in rows)):raise ValueError('Original exact saved rows/flags differ')
            keep=[i for i,r in enumerate(rows) if r['unverified_fallback'] is False]
            removed=[r['path_id'] for r in rows if r['unverified_fallback'] is True]
            clean=[rows[i] for i in keep];encoded=[enc[i] for i in keep]
            run=f't72_clean_s17_n{n}_k1';folder=out/run;folder.mkdir()
            dump(folder/'rows.json',clean);dump(folder/'encoded.json',encoded)
            plan=make_plan(encoded,17,151643);dump(folder/'plan.json',plan)
            config=dict(experiment='P011',teacher='t72',run_id=run,nominal_original_P=n,P=n,K=1,P_cov=len(clean),n=len(clean),seed=17,
                model=old['model'],updates=UPDATES,targets=TARGETS,lr_vector_sha256=LR_VECTOR_SHA256,
                fallback_filter='saved_unverified_fallback_is_true_only',removed_fallback_ids=removed,
                selected_ids=[r['path_id'] for r in clean],training_rows_sha256=digest(clean),encoded_rows_sha256=digest(encoded),plan_sha256=digest(plan),
                original_source_files={str((source/f).relative_to(ROOT)):sha(source/f) for f in ('config.json','rows.json','encoded.json')},
                raw_answers_unchanged=True,original_token_rows_reused=True,coverage_change_disclosed=True)
            dump(folder/'config.json',config)
            for f in ('MATH_ENDPOINT.json','GOLD.jsonl'):
                shutil.copyfile(R/'b_runtime_student_inputs_r1/B1'/f,folder/f)
            dump(folder/'ORIGINAL_ROW_REUSE.json',dict(original_indices=keep,removed_fallback_ids=removed,original_count=n,retained_count=len(clean),
                no_reencoding=True,no_reselection=True,held_training_targets=TARGETS,held_updates=UPDATES))
            inventories[run]=manifest(folder)
            print('PREPARED',run,len(clean),'removed',len(removed),'q',plan['q'],flush=True)
        dump(out/'COMPLETED.json',dict(inventories=inventories,completed_epoch=time.time(),new_model_calls=0,new_teacher_calls=0,old_scores_repeated=0))
    except BaseException as exc:dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),partial_preserved=True));raise
if __name__=='__main__':main()
