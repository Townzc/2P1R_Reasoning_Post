"""Read-only publication of completed C6 search or original S1 sample evidence."""
from pathlib import Path
import ast,argparse,json,shutil
from experiments.p010.common import read,dump,sha,manifest,utc
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps

r=Path('.local/p010_20261019/r1');public=Path('reports/p010_20261019')
# Reuse the archive function without executing any prior publisher.
tree=ast.parse((r/'publish_k1_completed_once.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='archive')
import hashlib,tarfile
ns=dict(hashlib=hashlib,tarfile=tarfile,sha=sha)
exec(compile(ast.Module(body=[node],type_ignores=[]),'<original archive/readback helper>','exec'),ns)
archive=ns['archive']

def copy(source,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 with Path(source).open('rb') as f,dest.open('xb') as g:shutil.copyfileobj(f,g)
 assert sha(source)==sha(dest)

def publish(kind,run):
 if kind=='samples':
  assert run in ('s1_s17_n400','s1_s17_n3200')
  receipt=r/'existing_s1_sample_runs'/run;export=r/'existing_s1_sample_exports'/run
  records=r/'existing_s1_sample_records'/run;oracle=r/'existing_s1_sample_oracles'/run
  score=r/'existing_s1_sample_scores'/run;spec_path=public/'existing_s1_sampling_runtime_v1/SPEC.json'
  out=public/'existing_s1_samples_results_v1'/run
 else:
  assert kind=='cue' and run=='search_r1'
  receipt=r/'cue_search_runs'/run;export=r/'cue_search_export_r1';records=r/'cue_search_records_r1'
  oracle=r/'cue_search_oracle_r1';selection=r/'cue_selection_r1';spec_path=public/'c6_search_runtime_v1/SPEC.json'
  out=public/'c6_search_complete_v1'
 env=read(receipt/'RESULT.json');sent=read(receipt/'SUBMITTED.json');intent=read(receipt/'INTENT.json')
 collected=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json');proof=read(oracle/'COMPLETED.json')
 ledger=read(records/'RECORDS.json');rec=read(records/'COMPLETED.json');spec=read(spec_path)
 assert env['status']=='completed' and proof['passed'] and proof['technical_unknown']==0
 assert collected['original_result_sha256']==proof['original_receipt_sha256']==sha(receipt/'RESULT.json')
 assert proof['spec_sha256']==sha(spec_path) and proof['source_files']==spec['source_files']
 assert proof['verification_source_files']==spec['verification_source_files']
 assert rec['records_sha256']==sha(records/'RECORDS.json') and rec['provider_sha256']==sha(export/'PROVIDER_PRIVATE.json')
 assert sha(export/'evidence.tar.gz')==env['artifact']['tar_sha256'] and collected['provider_stopped']
 validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
 for name,value in {**spec['source_files'],**spec['verification_source_files']}.items():assert sha(name)==value,name
 copies={receipt/'RESULT.json':'ORIGINAL_RESULT_ENVELOPE.json',receipt/'INTENT.json':'ORIGINAL_LOCAL_INTENT.json',receipt/'SUBMITTED.json':'ORIGINAL_SUBMITTED.json',
  export/'COMPLETED.json':'ORIGINAL_COLLECTION_COMPLETED.json',export/'evidence.tar.gz':'original_evidence.tar.gz',records/'RECORDS.json':'ORIGINAL_NAMED_LEDGER.json',records/'COMPLETED.json':'LEDGER_COMPLETED.json',
  oracle/'COMPLETED.json':'GENERATION_ORACLE.json',oracle/'DECODED_ROWS.json':'DECODED_ROWS.json'}
 if kind=='samples':
  scored=read(score/'LOCAL_ORACLE_AUDIT.json');done=read(score/'COMPLETED.json');payload=score/'job/payload'
  assert proof['outputs_decoded']==2000 and proof['greedy_outputs_generated']==0 and proof['new_training_updates']==0
  assert proof['original_greedy_reused'] is True and proof['repeated_local_binary_loads']==0
  assert scored['passed'] and done['passed'] and done['oracle_sha256']==sha(score/'LOCAL_ORACLE_AUDIT.json')
  assert scored['full_generation_proof_sha256']==sha(oracle/'COMPLETED.json')
  assert scored['scoring_payload_sha256']==sha(payload/'COMPLETED.json') and scored['scoring_control_sha256']==sha(score/'job/COMPLETED.json')
  assert scored['original_state_sha256']==proof['original_state_sha256']==spec['parents'][run]['proof']['checkpoint']['sha256']
  assert ledger['existing_s1_samples/'+run+'/terminal']==env and rec['original_terminal']==spec['parents'][run]['terminal']
  copies.update({oracle/'SCORING_ROWS.json':'SCORING_ROWS.json',score/'LOCAL_ORACLE_AUDIT.json':'SCORING_ORACLE.json',score/'COMPLETED.json':'SCORING_COMPLETED.json',payload/'COMPLETED.json':'SCORE_PAYLOAD_COMPLETED.json',payload/'ALL_SCORED_ROWS.json':'ALL_SCORED_ROWS.json',payload/'AUDIT_SAMPLES.json':'AUDIT_SAMPLES.json'})
  for p in (payload/'audit_by_evaluation').glob('*.json'):copies[p]='audit_by_evaluation/'+p.name
  summary=dict(run=run,sampled_correct=scored['sampled_correct'],sampled_denominator=2000,sampled_mean_pass_at_1=scored['sampled_mean_pass_at_1'],sampled_per_seed={k:v['correct'] for k,v in scored['endpoints'].items()},logical_stops=scored['logical_stops'],original_state_sha256=scored['original_state_sha256'],old_greedy_reused=True,new_training_updates=0,new_greedy_outputs=0,repeated_local_binary_loads=0)
  extra_files={p.relative_to(payload).as_posix():p for p in payload.rglob('*') if p.is_file()};extra_name='original_scoring_journal.tar.gz'
  failed_roots=[records,oracle,score,payload]
 else:
  selected=read(selection/'SELECTION.json');complete=read(selection/'COMPLETED.json')
  assert proof['rows']==10080 and complete['passed'] and complete['oracle_file_sha256']==sha(oracle/'COMPLETED.json')
  assert complete['selection_sha256']==sha(selection/'SELECTION.json') and complete['spec_sha256']==sha(spec_path)
  assert all(complete[x] is False for x in ('gold_used','correctness_used','test_data_used'))
  assert ledger['cue/search_r1/terminal']==env
  copies.update({selection/'SELECTION.json':'SELECTION.json',selection/'COMPLETED.json':'SELECTION_COMPLETED.json',selection/'INTENT.json':'SELECTION_INTENT.json',export/'evidence/PROPOSAL.json':'ORIGINAL_PROPOSAL.json'})
  summary=dict(run=run,rows=10080,dev_questions=30,original_candidates=21,selected_candidate=complete['selected_candidate'],selected_token_ids=complete['selected_token_ids'],gold_used=False,correctness_used=False,test_data_used=False,benchmark_runs_performed=0,selection_elapsed_seconds=complete['elapsed_seconds'])
  extra_files={p.relative_to(selection).as_posix():p for p in selection.rglob('*') if p.is_file()};extra_name='original_selection_journal.tar.gz';failed_roots=[records,oracle,selection]
 for root in failed_roots:assert not list(root.rglob('FAILED.json'))
 for source in list(copies)+list(extra_files.values()):
  if source.suffix in ('.json','.jsonl','.md','.txt'):
   text=source.read_text();assert '/Users/' not in text and '/var/folders/' not in text,str(source)
 out.mkdir(parents=True,exist_ok=False)
 for source,name in copies.items():copy(source,out/name)
 dump(out/'JOURNAL_ARCHIVE.json',archive(out/extra_name,extra_files))
 life=provider['original_info'][0]['lifecycle']
 dump(out/'PROVIDER.json',dict(app_id=sent['app_id'],lifecycle={k:life[k] for k in ('created_at','state','stopped_at')},owned_count=len(provider['owned']),read_utc=provider['utc'],private_original_sha256=sha(export/'PROVIDER_PRIVATE.json'),projection='Only provider actor identity omitted; original private bytes retained.'))
 summary.update(utc=utc(),execution_commit=intent['execution'],technical_unknown=0,independent_A3_pending=True,bootstrap_performed=False,original_spec_sha256=sha(spec_path),reserved_usd=intent['budget']['new_reserved_usd'],is_final_cost=False)
 dump(out/'SUMMARY.json',summary);dump(out/'VERIFICATION_SOURCE_BINDING.json',spec['verification_source_files'])
 for name in spec['verification_source_files']:copy(Path(name),out/'source'/name)
 copy(Path(__file__),out/'publisher.py')
 (out/'README.md').write_text('# '+('Original S1 new samples' if kind=='samples' else 'Complete C6 gold-free search')+' — actual A3 pending\n\nOriginal completed result and STOPPED/zero-container proof, exact frozen source, complete raw oracle, saved journal and all fixed audit samples are included. Publication only copies and validates stored evidence; no model, training, symbolic score, tokenization, raw decoding, state deserialization or bootstrap is repeated. Public state/model hashes do not assert external auditor access to private binaries. Four sampled draws are means of pass@1, never best-of-four. For C6, selection uses only the original30 dev questions and no gold/correctness/test data; actual benchmark effects have not yet been measured. Original S1 greedy results are reused without regeneration.\n\nIndependent A3 remains required. Provider projection removes actor identity and retains the private original SHA. Reserved USD is a conservative slot allowance, not actual cost, invoice or balance. Historical failed attempts and costs remain. This packet is evidence, not course-report prose.\n')
 dump(out/'MANIFEST.json',manifest(out));dump(r/('PUBLICATION_'+kind+'_'+run+'.json'),dict(utc=utc(),packet=str(out),manifest_sha256=sha(out/'MANIFEST.json'),new_model_calls=0,new_scores=0))
 print(json.dumps(summary))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--kind',choices=['samples','cue'],required=True);p.add_argument('--run',required=True);a=p.parse_args();publish(a.kind,a.run)
