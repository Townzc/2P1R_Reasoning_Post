"""Post-hoc E013/E015 raw-record comparison and receipt reconciliation; no model calls."""
import argparse
from pathlib import Path
import json,hashlib,math
from scripts.audit_family_matching import verified_tokenizer
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tokenizer-dir',required=True)
parser.add_argument('--ledger',required=True)
parser.add_argument('--out-dir',required=True)
args=parser.parse_args()
folder=Path(args.out_dir)
for name in ('paired_comparison.json','ledger_verification.json'):
 if (folder/name).exists():raise FileExistsError('Preserve immutable comparison outputs')
folder.mkdir(parents=True,exist_ok=True)
root=Path('runs'); old=root/'gsm8k_overfit_e013_r1'; new=root/'gsm8k_terminal_decay_e015_r1'; refold=root/'gsm8k_generation_e014_r1'
def lines(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a,b=lines(old/'final_train.jsonl'),lines(new/'final_train.jsonl');assert len(a)==len(b)==32
pairs=[]
for x,y in zip(a,b):
 for k in ('problem_id','prompt','response','answer','source'):assert x[k]==y[k]
 pairs.append({'problem_id':x['problem_id'],'old_correct_terminated':x['score']['terminated_correct'],'new_correct_terminated':y['score']['terminated_correct'],'old_truncated':x['score']['truncated'],'new_truncated':y['score']['truncated'],'old_reference_exact':x['score']['reference_exact_match'],'new_reference_exact':y['score']['reference_exact_match'],'old_output_tokens':x['generated_tokens'],'new_output_tokens':y['generated_tokens']})
ra,rb=lines(refold/'reference_tokens.jsonl'),lines(new/'reference_tokens.jsonl');tok,_=verified_tokenizer(Path(args.tokenizer_dir));mismatches=[]
for x,y in zip(ra,rb):
 assert x['problem_id']==y['problem_id'] and x['target_ids']==y['target_ids']
 for j,(target,argmax) in enumerate(zip(y['target_ids'],y['argmax_ids'])):
  if target!=argmax:mismatches.append({'problem_id':y['problem_id'],'target_position':j,'target_id':target,'argmax_id':argmax,'target_text':tok.decode([target],skip_special_tokens=False,clean_up_tokenization_spaces=False),'argmax_text':tok.decode([argmax],skip_special_tokens=False,clean_up_tokenization_spaces=False),'target_nll':y['target_nll'][j],'target_minus_best_other_logit':y['target_minus_best_other_logit'][j]})
ha,hb=lines(old/'train_history.jsonl'),lines(new/'train_history.jsonl')
fields={}
for key in ['response_nll','grad_norm']:
 differences=[abs(x[key]-y[key]) for x,y in zip(ha[:192],hb[:192])]
 fields[key]={'exact_matches':sum(d==0 for d in differences),'first_difference_step':next((i+1 for i,d in enumerate(differences) if d!=0),None),'maximum_absolute_difference':max(differences),'mean_absolute_difference':math.fsum(differences)/192,'step192_old':ha[191][key],'step192_new':hb[191][key]}
mold=json.loads((old/'metrics.json').read_text());mnew=json.loads((new/'metrics.json').read_text())
base_new=json.loads((new/'base_reference_nll.json').read_text());assert base_new==mold['base_train_reference_nll']
ledger=json.loads(Path(args.ledger).read_text());receipts=[]
for job in ledger['jobs']:
 p=root/job['run_id']/'resource_receipt.json';r=json.loads(p.read_text());assert r['run_id']==job['run_id'] and r['charged_seconds']==job['charged_seconds']
 receipts.append({'run_id':job['run_id'],'charged_seconds':job['charged_seconds'],'receipt_sha256':sha(p)})
assert len(receipts)==19 and sum(x['charged_seconds'] for x in receipts)==6686
report={'phase':'E015_POSTHOC_LOCAL_COMPARISON','old_run_id':old.name,'new_run_id':new.name,'paired_rows':pairs,'old_failures_repaired':sum(not p['old_correct_terminated'] and p['new_correct_terminated'] for p in pairs),'old_successes_lost':sum(p['old_correct_terminated'] and not p['new_correct_terminated'] for p in pairs),'old_reference_argmax_misses':sum(sum(t!=z for t,z in zip(r['target_ids'],r['argmax_ids'])) for r in ra),'new_reference_argmax_misses':len(mismatches),'new_mismatches':mismatches,'nonexact_but_correct_ids':[p['problem_id'] for p in pairs if p['new_correct_terminated'] and not p['new_reference_exact']],'base_reference_metrics_exactly_equal':True,'pre_decay_training_logs':fields,'planned_first192_learning_rates_identical':True,'early_trajectory_bitwise_equal':False,'causal_limit':'Configuration contrast and successful engineering endpoint, not a verified same-state terminal-LR causal intervention. Gradient norms diverge atstep3 and logged trainingNLL atstep4, before the schedule changes at193. The source of GPU numerical trajectory divergence is unresolved; do not label it a proven SDPA/CUDA bug.','original_supervised_and_processed_token_dose_equal':json.loads((old/'actual_budget.json').read_text())==json.loads((new/'actual_budget.json').read_text()),'new_dev_or_test_generations':0,'nll_reduction_ratio':mold['train_reference_nll']['nll']/mnew['train_reference_nll']['nll'],'input_artifact_hashes':{str(p):sha(p) for p in [old/'final_train.jsonl',new/'final_train.jsonl',old/'train_history.jsonl',new/'train_history.jsonl',refold/'reference_tokens.jsonl',new/'reference_tokens.jsonl']},'server_contacted':False,'model_call':False}
(folder/'paired_comparison.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(folder/'ledger_verification.json').write_text(json.dumps({'phase':'E015_LEDGER_RECONCILIATION','status':'passed','receipts':receipts,'jobs':19,'used_seconds':6686,'remaining_seconds':514,'reservations':0,'authorized_process_seconds':7200,'private_ledger_sha256':sha(Path(args.ledger)),'history_reset':False},indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('paired_rows','input_artifact_hashes')},indent=2))
