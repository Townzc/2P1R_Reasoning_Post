"""Prepared final packet; consumes completed audits and frozen summary only."""
from pathlib import Path
import datetime,json,shutil
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest

r=Path(__file__).resolve().parent
closeout_path=r/'final_closeout_r1/LOCAL_CLOSEOUT.json';closeout=read(closeout_path)
summary_path=r/'final_results_r1.json';summary=read(summary_path)
spec=read('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
assert set(closeout['full_student_oracles'])==set(summary['sources'])
assert closeout['main_endpoint_outputs']==summary['endpoint_outputs']==10552
assert closeout['main_supervised_targets']==summary['supervised_targets']==4194296
assert closeout['main_scientific_updates']==summary['updates']==2048
assert closeout['cpu_audit_labels']==14 and not closeout['containers']
out=Path('reports/p007_audit/token_final_v1');assert not out.exists()
pred={};receipts={};models={}
for row in summary['table']:
 for seed,z in row['seeds'].items():
  run=f"{row['cell']}_s{seed}";ep=r/'students'/(run+'_run_r1')/'result.json';e=read(ep);ap=r/'student_exports'/run/'LOCAL_ORACLE_AUDIT.json';a=read(ap)
  assert sha(ep)==summary['sources'][run]['receipt_sha256']
  assert sha(ap)==summary['sources'][run]['local_audit_sha256']==closeout['full_student_oracles'][run]['oracle_sha256']
  assert a['correct']==z['correct']==e['result']['endpoint']['correct']
  assert a['artifact_digest']==digest(e['artifact_manifest'])==e['receipt']['evidence_sha256']
  q=e['result']['endpoint']['question_correct'];assert len(q)==1319 and sum(q.values())==z['correct'] and all(type(v) is bool for v in q.values())
  pred[run]=q;receipts[run]=e['receipt'];models[run]=dict(z,cell=row['cell'],seed=int(seed),state_sha256=a['state_sha256'],artifact_digest=a['artifact_digest'],source_commit=read(ep.parent/'intent.json')['release']['commit'])
ids=sorted(next(iter(pred.values())));assert all(sorted(q)==ids for q in pred.values())
paired=[dict(problem_id=p,**{run:q[p] for run,q in pred.items()}) for p in ids]
public_closeout={k:v for k,v in closeout.items() if k!='provider'}
public_closeout['provider']=dict(state=closeout['provider']['state'],tasks=closeout['provider']['tasks'])
public_closeout['private_full_closeout_sha256']=sha(closeout_path)
billing_path=sorted((r/'billing').glob('*.json'))[-1];billing=read(billing_path);billing.pop('report',None)
summary.update(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),campaign=spec['campaign_id'],models=models,
 full_closeout_sha256=sha(closeout_path),all_eight_local_oracles_and_cpu_audit_passed=True,all_owned_resources_released=True,
 billing=billing,reservation_usd=closeout.get('reservation_usd',366.50),spending_ceiling_usd=450,protected_usd=50,
 external_review='Claude round12@514cec51 reviewed all eight saved raw outcomes and terminal-state hashes (PASS-WITH-NOTES). This new combined summary, CPU receipt and rendered artifacts remain pending scoped external review.',
 historical_work='Original time-priced pilots, prior engineering, failed work and acquisition costs remain separate and preserved.')
out.mkdir();dump(out/'summary.json',summary);dump(out/'paired_question_scores.json',paired);dump(out/'receipts.json',receipts);dump(out/'CLOSEOUT.json',public_closeout)
for run in sorted(pred):
 for name,suffix in (('LOCAL_ORACLE_AUDIT.json','local_audit'),('artifact_manifest.json','artifact_manifest')):
  shutil.copyfile(r/'student_exports'/run/name,out/f'{run}_{suffix}.json')
cpu_receipt=r/closeout.get('cpu_receipt_relative_path','students/audit_run_r1/result.json')
assert sha(cpu_receipt)==closeout['cpu_audit_receipt_sha256']
shutil.copyfile(cpu_receipt,out/'cloud_audit_envelope.json')
shutil.copyfile('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_SELECTED_SUPPLY_DIAGNOSTICS.json',out/'selected_supply_diagnostics.json')
shutil.copyfile(__file__,out/'report_builder.py')
(out/'REVIEW_REQUEST.md').write_text('''# Final uniform-token-tariff comparison: eight fixed students

Pin review to the ordinary publication commit. All eight local raw-output,
full terminal-state and frozen-dose oracles passed. Finite CPU audit proof
covers the registered 14 evidence folders (four procurement results,
eight new students and two retained operational pilots), and all owned GPU/CPU
containers exited. The high-price breadth procurement maps to its actual
recovery campaign; original failed-prefix evidence and its earlier combined
local oracle remain preserved. The CPU audit is not a new teacher/student run.

Recompute both within-price contrasts and the price interaction for each
training seed, plus the mean of those two observed seeds, from
paired_question_scores.json. The frozen implementation is
scripts/summarize_acquisition_students.py::contrasts: 10,000 shared
paired-question resamples, RNG seed20261013. Confidence intervals condition on
these eight fixed models/teacher traces; they do not estimate seed or
procurement uncertainty. Inspect the primary gaps alongside the interaction.
Each original result has1319 outputs,256updates and524287targets. Check the
stop/cap counts and do not remove capped or formatting-false-negative outputs.

All input/data identities and plans are in the prior token_tariff_v2 packet.
The compact booleans alone cannot validate decoded raw tokens or weights.
Full raw token batches and state.pt files remain locally under the original
new-campaign student_exports folders; per-run manifests provide their hashes.
Local verification is not an external Claude verdict. Previous rounds do not
automatically cover this final CPU receipt, numerical summary, rendered figures or evidence handoff. Claude round12@514cec51 separately covers all eight saved raw outcomes and final-state hashes, with the four known E2 notes.

This is a common hypothetical token cap, not equal realized spending or actual
API dollars. Both training seeds reuse the same per-cell teacher-answer stock;
each cell has only one teacher trajectory. Exposure differs at fixed training
targets, so the comparison does not isolate reasoning diversity or repetition
harm. The official benchmark was observed by this research effort in September.
Correct final answers and different text do not prove reasoning-path quality.
Primary scores are unchanged, including length-cap errors and E2 parser cases.
''')
if closeout.get('cpu_audit_lineage'):
    lineage=closeout['cpu_audit_lineage']
    dump(out/'CPU_AUDIT_LINEAGE.json',lineage)
    with (out/'REVIEW_REQUEST.md').open('a') as f:
        f.write('\n## CPU audit interruption and bounded continuation\n\n'
                'The original CPU audit hit its3300-second limit; its claim, partial proofs and blocked provider replacement are preserved. '
                f"The continuation carries{len(lineage['carried_labels'])} pinned completed label proofs and fully verifies only{len(lineage['newly_verified_labels'])} remaining labels. "
                'Partial verification reads may be repeated, but no training or generation is replayed. '
                'The original audit is never presented as completed. See CPU_AUDIT_LINEAGE.json and the published continuation admission.\n')
dump(out/'manifest.json',dict(schema='audit_packet_manifest_v1',files=manifest(out),scope='All eight corrected students, full local state-dose/raw-score oracles and final independent CPU audit; final outcome review pending.',external_review='pending'))
dump('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FINAL_RESULTS.json',summary)
dump('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FINAL_CLOSEOUT.json',public_closeout)
print(json.dumps(dict(packet=str(out),packet_sha256=sha(out/'manifest.json'),models={k:dict(correct=v['correct'],n=v['n'],caps=v['truncated_outputs']) for k,v in models.items()},contrasts=summary['contrasts'])))
