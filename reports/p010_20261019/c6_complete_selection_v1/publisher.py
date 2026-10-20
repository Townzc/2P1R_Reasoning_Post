"""Publish saved C6 completion and full journal; no scientific functions execute."""
from pathlib import Path
import ast,hashlib,json,shutil,tarfile
from experiments.p010.common import read,dump,sha,manifest,utc

r=Path('.local/p010_20261019/r1');p=Path('reports/p010_20261019')
source=r/'cue_selection_nonfinite_r1';out=p/'c6_complete_selection_v1'
node=next(n for n in ast.parse((r/'publish_k1_completed_once.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='archive')
ns=dict(hashlib=hashlib,tarfile=tarfile,sha=sha)
exec(compile(ast.Module(body=[node],type_ignores=[]),'<original archive helper>','exec'),ns)

def copy(a,b):
 b.parent.mkdir(parents=True,exist_ok=True)
 with Path(a).open('rb') as f,b.open('xb') as g:shutil.copyfileobj(f,g)
 assert sha(a)==sha(b)

done=read(source/'COMPLETED.json');grouped=read(source/'grouping/COMPLETED.json');intent=read(source/'INTENT.json')
selected=read(source/'SELECTION.json');review=read(r/'C6_NONFINITE_RESUME_A2_ACCEPTED.json');owner=read(r/'C6_NONFINITE_OWNER_DECISION.json')
spec=p/'c6_nonfinite_resume_preflight_v1/SPEC.json';failure=p/'c6_search_selection_failure_v2'
assert done['passed'] and done['technical_unknown']==0 and done['selection_sha256']==sha(source/'SELECTION.json')
assert done['spec_sha256']==sha(spec)==intent['spec_sha256']==review['spec_sha256']
assert done['original_oracle_sha256']==sha(r/'cue_search_oracle_r1/COMPLETED.json')
assert all(done[k] is False for k in ('gold_used','correctness_used','test_data_used'))
assert grouped['rows']==10080 and grouped['technical_unknown']==0 and grouped['inherited_confirmed_keys']==731 and grouped['inherited_confirmed_rows']==3700
assert grouped['original_failed_key_new_attempts']==1 and grouped['repeated_confirmed_parser_attempts']==0
assert intent['review_report_sha256']==review['report_sha256']==sha(review['local_report_file'])
assert intent['owner_decision_source_sha256']==owner['decision_source_sha256']==sha(owner['local_decision_file'])
assert not list(source.rglob('FAILED.json'))
assert sha(failure/'MANIFEST.json')=='59ee7f8acd81c420399b2f01f20a8229d4f86c7fc325f8b645770ca8cb555fc0'
for name,h in review['source_files'].items():assert sha(name)==h,name
files={f.relative_to(source).as_posix():f for f in source.rglob('*') if f.is_file()}
copies={source/'COMPLETED.json':'COMPLETED.json',source/'SELECTION.json':'SELECTION.json',source/'INTENT.json':'LOCAL_INTENT.json',source/'grouping/COMPLETED.json':'GROUPING_COMPLETED.json',source/'grouping/INHERITED_CONFIRMED.json':'INHERITED_CONFIRMED.json',r/'cue_search_export_r1/evidence/PROPOSAL.json':'ORIGINAL_PROPOSAL.json',r/'C6_NONFINITE_RESUME_A2_ACCEPTED.json':'A2_ACCEPTED.json',r/'C6_NONFINITE_OWNER_DECISION.json':'DELEGATED_D3_ACCEPTED.json',Path(review['local_report_file']):'ORIGINAL_A2_REPORT.md',Path(owner['local_decision_file']):'ORIGINAL_OWNER_DECISIONS.md'}
for f in set(files.values())|set(copies):
 if f.suffix in ('.json','.md','.txt'):
  t=f.read_text();assert '/Users/' not in t and '/var/folders/' not in t,str(f)
out.mkdir(parents=True,exist_ok=False)
for a,b in copies.items():copy(a,out/b)
dump(out/'COMPLETE_JOURNAL_ARCHIVE.json',ns['archive'](out/'complete_selection_journal.tar.gz',files))
dump(out/'ORIGINAL_EVIDENCE_REFERENCES.json',dict(fixed_commit='94a27ffc39e8e358d45edc00c1fc8e96129269ef',packet=str(failure),manifest_sha256=sha(failure/'MANIFEST.json'),original_raw_archive_parts='ORIGINAL_EVIDENCE_PARTS.json',original_failed_selection_retained=True,original_731_confirmed_keys_reused=True,new_model_calls=0,new_training_updates=0,new_primary_scores=0))
summary=dict(utc=utc(),completed_utc=done['utc'],rows=grouped['rows'],selected_candidate=done['selected_candidate'],selected_token_ids=done['selected_token_ids'],inherited_confirmed_keys=731,inherited_confirmed_rows=3700,new_parser_attempts=grouped['new_parser_attempts'],original_failed_key_new_attempts=1,repeated_confirmed_parser_attempts=0,technical_unknown=0,original_failure_retained=True,rule_amendment_after_observed_failure=True,local_elapsed_seconds=done['elapsed_seconds'],gold_used=False,correctness_used=False,test_data_used=False,benchmark_outputs_generated=0,independent_actual_A3_pending=True)
dump(out/'SUMMARY.json',summary);copy(Path(__file__),out/'publisher.py')
(out/'README.md').write_text('# C6 saved complete selection — actual A3 pending\n\nThe one approved local completion reused all 731 confirmed answer keys / 3,700 confirmed rows. It made 815 new parser attempts, including exactly one new attempt on the previously failed infinity key; it did not regenerate any model output. All 10,080 original dev responses are now grouped, with zero technical unknowns. Saved selection chooses candidate 2, token ID [1249]. The full 1,703-file journal is preserved with archive readback hashes.\n\nOriginal GPU outputs, probabilities, source, terminal/STOPPED proof and failed local attempt remain in the fixed original evidence packet linked by ORIGINAL_EVIDENCE_REFERENCES.json. The signed-infinity rule was approved after the original failure, with independent exact A2; this is disclosed rather than described as a pre-failure rule. No gold, correctness or test labels were used. No benchmark effect has yet been measured. Publication copies saved bytes only; it does not invoke a parser, selection computation, tokenizer, oracle or model. Actual independent selection A3 is requested separately.\n')
dump(out/'MANIFEST.json',manifest(out))
dump(r/'C6_COMPLETE_SELECTION_PUBLICATION.json',dict(utc=utc(),packet=str(out),manifest_sha256=sha(out/'MANIFEST.json'),selection_sha256=sha(out/'SELECTION.json'),new_scientific_computation=False))
print(json.dumps(summary))
