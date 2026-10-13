"""One-time CPU preparation. No model calls or cloud writes."""
import json
from pathlib import Path
from transformers import AutoTokenizer
from experiments.sft_allocation_p008.contract import stable_seed,lrs,DEADLINE_EPOCH,run_roster,BRANCHES
from experiments.sft_allocation_acquisition.contract import messages
from experiments.sft_allocation_midpoint.common import dump,sha,manifest,digest
from src.sft_data import read_jsonl,encode_row

root=Path('.local/p008_20261013');out=root/'phase0_inputs';out.mkdir(exist_ok=False)
source=Path('.local/midpoint_20261011/data_pipeline/reconstruction_r1/sources/gsm8k_train.jsonl')
source_rows=read_jsonl(source);assert len(source_rows)==7473
parents=[dict(id=f'gsm8k/train/{i:05d}',problem=r['question'],answer=r['answer'].rsplit('####',1)[1].strip(),reference=r['answer']) for i,r in enumerate(source_rows)]
ordered=sorted(parents,key=lambda p:stable_seed('dev_split',0,p['id']))
dev=ordered[:500];eligible=ordered[500:];assert len({p['id'] for p in parents})==7473
teacher=AutoTokenizer.from_pretrained('.local/midpoint_20261011/teacher_pilot_preparation/tokenizer',local_files_only=True)
student=AutoTokenizer.from_pretrained('.local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer',local_files_only=True)
requests=[]
for attempt in range(1,5):
 for p in dev[:256]:
  prompt=teacher.apply_chat_template(messages(p),tokenize=True,add_generation_prompt=True)
  assert len(prompt)+1024<=2048
  requests.append(dict(parent=p,problem_id=p['id'],attempt=attempt,candidate_id=f"phase0::{p['id']}::{attempt}",
       prompt_token_ids=prompt,seed=stable_seed('calibration',0,p['id'],attempt)))
assert len({r['seed'] for r in requests})==1024
train=[]
for p in dev[256:264]:
 row=dict(problem_id=p['id'],path_id='gold-fixture::'+p['id'],prompt=p['problem'],answer=p['answer'],response=p['reference'])
 e=encode_row(row,student,2048);row['source']={k:e[k] for k in ('n_prompt','n_processed','n_supervised')};train.append(row)
evalrows=[dict(problem_id=p['id'],prompt=p['problem'],answer=p['answer']) for p in dev[264:280]]
for name,rows in [('calibration_requests.jsonl',requests),('smoke_train.jsonl',train),('smoke_eval.jsonl',evalrows),('eligible_parents.jsonl',eligible),('reserved_dev.jsonl',dev)]:
 with (out/name).open('x') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
dump(out/'smoke_recipe.json',dict(schedule=[[i] for i in range(8)],lrs=lrs(2048)[:8],lr_full_horizon=2048,
      seed=17,supervised_targets=sum(r['source']['n_supervised'] for r in train),engineering_only=True))
files=manifest(out)
dump(out/'manifest.json',dict(files=files,source_sha256=sha(source),excluded_dev=500,eligible_parents=6973,
    calibration_outputs=1024,smoke_updates=8,smoke_outputs=16,prior_research_exposure='possible; not pristine'))
# Publish IDs/hashes and exact request seeds, not teacher output that does not exist.
pub=Path('reports/p008_20261013');pub.mkdir(exist_ok=True)
dump(pub/'INPUT_IDENTITY.json',dict(manifest_sha256=sha(out/'manifest.json'),manifest=json.loads((out/'manifest.json').read_text()),
    reserved_dev_ids=[p['id'] for p in dev],calibration_ids=[p['id'] for p in dev[:256]],
    smoke_train_ids=[p['problem_id'] for p in train],smoke_eval_ids=[p['problem_id'] for p in evalrows],
    dev_rule='sort domain-separated SHA256-derived stable_seed(dev_split,0,id), reserve first500',
    main_question_orders={f'D{d}':[p['id'] for p in sorted(eligible,key=lambda p:stable_seed('question_order',d,p['id']))] for d in (1,2)}))
plan=dict(campaign_id='p008-phase0-20261013-r1',created_epoch=1791876600,deadline_epoch=DEADLINE_EPOCH,
 total_cap_cents=1500,stage_caps_cents={'phase0':1500},slots={
  'teacher_calibration':dict(stage='phase0',reserved_cents=600),
  'student_smoke':dict(stage='phase0',reserved_cents=400),
  'io_probe_a':dict(stage='phase0',reserved_cents=150),
  'io_probe_b':dict(stage='phase0',reserved_cents=150)})
# $2 unallocated headroom for build/storage/setup; not a runnable extra slot.
dump(root/'phase0_plan.json',plan)
configs={}
for role,seconds in [('teacher_calibration',2400),('student_smoke',1500),('io_probe_a',600),('io_probe_b',600)]:
 cfg=dict(run_id=role,max_seconds=seconds,barrier_seconds=180,probe_bytes=8388608,
          input_sha256=sha(out/'manifest.json'),max_outputs=1024 if role=='teacher_calibration' else 16 if role=='student_smoke' else 0,
          max_updates=8 if role=='student_smoke' else 0)
 dump(root/'configs'/(role+'.json'),cfg);configs[role]=cfg
spec=dict(schema='p008_phase0_admission_v1',status='owner_authorized_G0_required_before_dispatch',
 plan=plan,plan_sha256=digest(plan),configs=configs,config_sha256={k:digest(v) for k,v in configs.items()},
 stage_cap_usd=250,phase0_cap_usd=15,protected_usd=50,project_ceiling_usd=450,
 input_sha256=sha(out/'manifest.json'),maximum_new_teacher_outputs=1024,maximum_engineering_updates=8,
 maximum_engineering_eval_outputs=16,maximum_gpu_concurrency=4,
 stage_after_phase0='separate exact branch and main input/code bindings required before main dispatch')
dump(pub/'PHASE0_ADMISSION.json',spec)
dump(pub/'STUDENT_DESIGN_ROSTERS.json',{'branches':[dict(branch=b,roster=run_roster(*b)) for b in BRANCHES]})
print(json.dumps(dict(manifest_sha256=spec['input_sha256'],phase0_plan_sha256=digest(plan),smoke_targets=sum(r['source']['n_supervised'] for r in train))))
