from pathlib import Path
import json,sys,zipfile
from a7_accounting import *

name=sys.argv[1];tr=ROOT/'a7_runs_v1'/name;r=read(tr/'request.json')
ev=tr.with_name(name.replace(f'_s{r["seed"]}_',f'_s{r["seed"]}_greedy_'))
term=read(ev/'TERMINATION.json');pred=read(ev/'PREDICTION_BEFORE_SCORE.json')
assert pred['prediction_commit']==AUTHORITY and pred['utc'] and pred['raw_sha256']==sha(ev/'result/generation/raw.jsonl')
pub=PUBLIC/name.replace('_20261113','');pub.mkdir(exist_ok=False)
result={'track':'tinker_lora','exploratory':True,'excluded_from_H0_H3':True,'authority_commit':AUTHORITY,
    'A7_group':r['A7_group'],'model':r['model'],'arm':r['A7_arm'],'cell':r['cell'],'seed':r['seed'],
    'dose':r['dose'],'rank':r['rank'],'learning_rate':r['learning_rate'],'dataset':r['dataset'],
    'MATH5000':term['all'],'MATH500':term['math500'],'training_run_id':name,
    'training_request_sha256':sha(tr/'request.json'),'training_usage':read(tr/'result/USAGE.json'),
    'evaluation_usage':read(ev/'result/USAGE.json'),'training_complete':read(tr/'result/COMPLETE.json'),
    'evaluation_complete':read(ev/'result/COMPLETE.json'),'prediction_before_score':pred,
    'raw_sha256':sha(ev/'result/generation/raw.jsonl'),'labels_sha256':sha(ev/'score_v1/labels.jsonl'),
    'independent_numeric_audit':'pending',
    'data_interpretation':read(PUBLIC/'review_8a8fac5c/DATA_CHARACTERISTIC.json')}
(pub/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
with zipfile.ZipFile(pub/'evidence.zip','x',zipfile.ZIP_DEFLATED) as z:
    for root,prefix in [(tr/'result','training'),(ev/'result','evaluation'),(ev/'score_v1','scores')]:
        for f in root.rglob('*'):
            if f.is_file():
                data=f.read_bytes();assert b'/Users/' not in data;z.writestr(prefix+'/'+str(f.relative_to(root)),data)
    z.write(ev/'TERMINATION.json','TERMINATION.json');z.write(ev/'PREDICTION_BEFORE_SCORE.json','PREDICTION_BEFORE_SCORE.json')
a=term['all'];(pub/'README.md').write_text(f'# {r["A7_group"]}: {r["model"]} / {r["A7_arm"]}, seed{r["seed"]}\n\nMATH5000: **{100*a["accuracy"]:.2f}%** ({a["correct"]}/5000); MATH500: **{100*term["math500"]["accuracy"]:.2f}%**. Cap rate{100*a["length_cap_rate"]:.2f}%; loops{a["loop_count"]}; normally terminated correct/denominator{a["normally_terminated_correct"]}/{a["normally_terminated_count"]}.\n\nExploratory LoRA/Tinker, excluded from H0-H3. Prediction22890560 was recorded with UTC and raw-output hash before the unchanged scorer ran. Evidence archive includes all5000 outputs, registered labels, termination flags, training identity and row order. Independent numerical review pending.\n')
with (pub/'README.md').open('a') as f:
    f.write('\n4B M512 long.jsonl contains40 of512 rows with only a boxed answer and no reasoning;9B contains none. Interpret SC-1/SC-2 primarily using9B;4B is a repetition with this limitation. Frozen data,labels and predictions remain unchanged. Authority:8a8fac5c.\n')
print(str(pub),flush=True)
