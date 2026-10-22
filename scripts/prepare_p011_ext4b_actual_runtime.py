"""Once-only actual job metadata from completed new inputs; no encoding or model."""
import argparse
from pathlib import Path
from copy import deepcopy
from experiments.p011.ext4b_contract import admit,LARGE,SMALL
from experiments.p011.ext4b_runtime_contract import prepared_spec,SPEC,INPUTS
from experiments.p011.ext4b_path import ACTUAL,published
from experiments.p011.owner_0205_common import read,sha,digest,create,utc


def main():
    p=argparse.ArgumentParser();p.add_argument('--data-review',required=True);a=p.parse_args()
    admit('reports/p011_20261020/ext4b_relaxed_input_preflight_v2/SPEC.json',a.data_review)
    spec=prepared_spec(SPEC);published(Path.cwd(),spec)
    complete=read(INPUTS/'COMPLETED.json');inventory=read(INPUTS/'MANIFEST.json')['files']
    if (complete['unique_selected_questions']!=12096 or complete['strict_subset_questions']!=3024
            or complete['GPU_calls']!=0 or complete['actual_A2_accepted'] is not False):
        raise ValueError('Exact revised data constructor completion required')
    out=ACTUAL.parent;out.mkdir(parents=True,exist_ok=False);create(out/'ATTEMPT.json',{'utc':utc(),'no_encoding_model':True})
    try:
        basis=read(spec['original_model_job_spec']['path'])
        if sha(spec['original_model_job_spec']['path'])!=spec['original_model_job_spec']['sha256']:raise ValueError('Saved model metadata source changed')
        base=deepcopy(basis['jobs']['long_A7_S-F15_s17_owner_r1']);rows=read(INPUTS/'ROW_METADATA.json');endpoints=read(INPUTS/'ENDPOINT_GPU.json')
        names=['ENCODED.jsonl','ROW_METADATA.json','RATES_S-F15.json','ENDPOINT_GPU.json',LARGE+'_PLAN.json',SMALL+'_PLAN.json']
        files={n:inventory[n] for n in names};jobs={}
        for name,count in ((LARGE,12096),(SMALL,3024)):
            plan=read(INPUTS/(name+'_PLAN.json'));saved=complete['cells'][name]
            if (saved['plan_sha256']!=inventory[name+'_PLAN.json']['sha256']
                    or plan['row_path_ids']!=[r['path_id'] for r in rows[:count]]
                    or plan['supervised_tokens']!=complete['same_supervised_B_including_EOS']
                    or plan['optimizer_updates']!=(plan['supervised_tokens']+63999)//64000
                    or plan['optimizer_updates']!=complete['same_optimizer_updates']):raise ValueError('Actual nested roster/dose/update count differs')
            jobs[name]={'logical_id':name,'cell':name,'kind':'student','category':'A','arm':'S-F15','seed':17,
                'questions':count,'B':plan['supervised_tokens'],'U':plan['optimizer_updates'],'q':plan['q'],
                'input_plan_sha256':digest(plan),'input_plan_file_sha256':inventory[name+'_PLAN.json']['sha256'],
                'input_files':files,'local_input_files':{**files,'ENDPOINT_LOCAL.json':inventory['ENDPOINT_LOCAL.json']},
                'model':base['model'],'context':max(r['required_context'] for r in endpoints),'eos_token_ids':base['eos_token_ids'],
                'resources':{'gpu':'H100','cpu':4,'memory_mib':98304},
                'limits':{'worker_hard_ceiling_seconds':50400,'score_seconds':7200,'closeout_seconds':14405,
                          'per_cell_cumulative_cap_usd':'45','pair_cap_usd':'90','checkpoint_interval_updates':500,'maximum_infrastructure_resumes':1}}
        value={'schema':'p011_ext4b_actual_jobs_v1','spec_sha256':sha(SPEC),'input_manifest_sha256':sha(INPUTS/'MANIFEST.json'),
            'data_completion_sha256':sha(INPUTS/'COMPLETED.json'),'jobs':jobs,'actual_supervised_Bprime':complete['same_supervised_B_including_EOS'],
            'same_updates':complete['same_optimizer_updates'],'data_source_review_sha256':sha(a.data_review),
            'full_source_and_actual_reviews_still_required_before_GPU':True,
            'metadata_preparation_is_not_CR_acceptance':True,'estimated_cost_is_not_admission':True,'no_new_encoding_or_model':True}
        create(ACTUAL,value);create(out/'COMPLETED.json',{'utc':utc(),'actual_job_manifest_sha256':sha(ACTUAL),'actual_A2_accepted':False})
        print(ACTUAL,flush=True)
    except BaseException as exc:create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()
