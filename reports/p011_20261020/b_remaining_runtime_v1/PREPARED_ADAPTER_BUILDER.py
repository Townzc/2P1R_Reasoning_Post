"""Prepare new adapters only; never modifies or executes original production."""
from pathlib import Path
R=Path('experiments/p011/b_remaining')
def write(p,s):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(s)
def replace(s,a,b):
    assert a in s,a[:120]
    return s.replace(a,b)

# Loader retains the exact model, engine and prompt check, with only the new
# transport and saved-verdict selection callbacks selected explicitly.
s=Path('experiments/p011/b_generation_loader.py').read_text()
s=replace(s,'from experiments.p010.teacher_transport import completion','from experiments.p011.b_remaining.transport import completion')
s=replace(s,'from experiments.p011.short_generation import b_requests, b_selection','from experiments.p011.short_generation import b_requests\nfrom experiments.p011.b_remaining.selection import select as b_selection')
write(R/'loader.py',s)

s=Path('experiments/p011/b_input_path.py').read_text()
s=replace(s,'from experiments.p011.short_generation import b_selection','from experiments.p011.b_remaining.selection import select as b_selection, mapped')
s=replace(s,"def generate_inputs(root, binding, review):","def generate_inputs(root, binding, review):\n    raise RuntimeError('Original generation inputs already complete; never rebuild them')\n")
s=replace(s,"'b_student_inputs_r1'","'b_student_inputs_remaining_r1'")
s=replace(s,"'B_STUDENT_INPUT_ATTEMPT.json'","'B_REMAINING_STUDENT_INPUT_ATTEMPT.json'")
s=replace(s,"rec=records[cid]; pid=rec['problem_id']","rec=records[cid]; pid=rec['problem_id']\n        if not mapped(rec):raise ValueError('Unmapped row excluded from every training role')")
s=replace(s,"expected=set(pack['ordered400'])-(set(selection['unverified_fallback_questions']) if k>1 else set())", "expected=set(pack['ordered400'])-set(selection['all16_unmapped_absent_questions'])-(set(selection['unverified_fallback_questions']) if k>1 else set())")
s=replace(s,"'owner_B16_sha256':OWNER_SHA,'selection_sha256':digest(selection),", "'owner_B16_sha256':OWNER_SHA,'selection_sha256':digest(selection),\n        'all16_unmapped_absent_questions':selection['all16_unmapped_absent_questions'],\n        'unmapped_training_rows':0,")
# Bind the new delegated transport/selection decision in addition to old B16.
s=replace(s,"if (review.get('scope') != 'p011-B-generation-student-complete-path-CR'", "if (review.get('delegated_failure_decision_sha256') != '8ca01d6f5d5f5e2dbe58b2e694aaa21685d3398d22d0e1c61d853a01fa92abf8'\n            or review.get('scope') != 'p011-B-remaining-generation-selection-complete-path-CR'")
write(R/'student_input.py',s)

s=Path('experiments/p011/b_current_path.py').read_text()
s=replace(s,'from experiments.p011 import b_numeric, b_generation_execution, b_generation_loader',
    'from experiments.p011 import b_numeric, failed_attempt_ledger\nfrom experiments.p011.b_remaining import execution as b_generation_execution, loader as b_generation_loader\nfrom experiments.p011.b_remaining.transport import DECISION_SHA')
s=replace(s,"SPEC_FILES={phase:f'reports/p011_20261020/b_{phase}_runtime_v1/SPEC.json' for phase in ('generation','student')}",
    "SPEC_FILES={'generation':'reports/p011_20261020/b_remaining_runtime_v1/SPEC.json'}")
s=replace(s,'B_generation_t10_400x16_r1','B_generation_t10_400x16_r2_continuation')
s=replace(s,"'b/generation'","'b/generation_remaining_r2'")
s=replace(s,"SCOPE='p011-B-generation-student-complete-path-CR-A1-A2-lite'", "SCOPE='p011-B-remaining-generation-complete-path-CR-A1-A2-lite'")
s=replace(s,"BASE='/evidence/p011-20261020/b_runs_r1'","BASE='/evidence/p011-20261020/b_remaining_runs_r2'")
s=replace(s,"def validate(spec):\n", "def validate(spec):\n    if (spec.get('phase')!='generation' or spec.get('delegated_failure_decision_sha256')!=DECISION_SHA\n            or not spec.get('failed_attempt_bindings') or not spec.get('prefix_files')\n            or spec.get('remaining_outputs')!=5120 or spec.get('reused_raw_outputs')!=1280\n            or spec.get('reused_transport_outputs')!=1024\n            or spec.get('original_failed_logical_id')!='B_generation_t10_400x16_r1'\n            or spec.get('original_upload_receipt_sha256') is None):\n        raise ValueError('Exact conditional continuation and original failure binding required')\n    from experiments.p011.b_remaining.numeric import verify_scenario\n    verify_scenario(spec['prospective_students_and_score_window'])\n")
s=replace(s,"n=(0,25)","n=(0,20)");s=replace(s,"counts=(0,25)","counts=(0,20)")
s=replace(s,"owner_B16_sha256=OWNER_SHA,budget_owner_decision_sha256=BUDGET_OWNER_SHA)",
    "owner_B16_sha256=OWNER_SHA,budget_owner_decision_sha256=BUDGET_OWNER_SHA,\n        delegated_failure_decision_sha256=DECISION_SHA,prefix_files=spec['prefix_files'],\n        failed_attempt_bindings_sha256=digest(spec['failed_attempt_bindings']),\n        prospective_students_and_score_window_sha256=digest(spec['prospective_students_and_score_window']))")
s=replace(s,"'original_complete_cycle_interval_proxy_accepted')", "'original_complete_cycle_interval_proxy_accepted',\n        'old1280_raw_and1024_transport_byte_reuse_and_new5120_only_accepted',\n        'unmapped_before_EOS_rule_and_all_training_exclusions_accepted',\n        'full6400_first_scoring_including_unscored1280_and_denominators_accepted',\n        'E3_wall_time_and_two_student_sequential_budget_full_windows_accepted')")
s=replace(s,"budget.get('protected_usd')!='0'","budget.get('protected_usd')!='48'")
s=replace(s,"Decimal(str(budget['available_after_retained_prior_reserves_usd']))-reserve<0", "Decimal(str(budget['available_after_retained_prior_reserves_usd']))-reserve<48")
s=replace(s,"protected_usd='0'","protected_usd='48'")
s=replace(s,"or now+job['limits']['full_result_window_seconds']>CUTOFF", "or now+job['limits']['full_result_window_seconds']>CUTOFF\n            or now>=spec['prospective_students_and_score_window']['latest_continuation_dispatch_epoch']")
s=replace(s,"root/LOCAL/'b_io_r1'/'upload'/job_id/'COMPLETED.json'", "root/LOCAL/'b_io_r1'/'upload'/'B_generation_t10_400x16_r1'/'COMPLETED.json'")
s=replace(s,"if upload['job_sha256']!=digest(job) or upload['all_remote_file_bytes_read_back'] is not True:",
    "if (sha(root/LOCAL/'b_io_r1/upload/B_generation_t10_400x16_r1/COMPLETED.json')!=spec['original_upload_receipt_sha256']\n            or upload['job_sha256']!=spec['original_generation_job_sha256']\n            or upload['all_remote_file_bytes_read_back'] is not True):")
s=replace(s,"parent.records_with_failed_parent(root,spec,lifecycle.ledger(root))", "parent.records_with_failed_parent(root,spec,failed_attempt_ledger.ledger(root,spec))")
s=replace(s,"parent.remote_fences(root,spec,store);", "parent.remote_fences(root,spec,store);failed_attempt_ledger.remote_fences(root,spec,store);")
s=replace(s,"result=b_generation_execution.generate(pack['ordered400'],pack['prompts'],pack['rows'],\n        Path(out)/'generation',key,claim,store,volume.commit,llm,constructor,transport,remaining,check)",
    "result=b_generation_execution.generate(pack,Path(out)/'generation',key,claim,store,volume.commit,llm,constructor,transport,remaining,check,\n        '/evidence/p011-20261020/b_runs_r1/B_generation_t10_400x16_r1/generation',job['prefix_files'])")
write(R/'path.py',s)

s=Path('experiments/p011/modal_b_current.py').read_text()
s=replace(s,'from experiments.p011 import b_current_path as path','from experiments.p011.b_remaining import path')
s=replace(s,'from experiments.p011 import b_current_path as run','from experiments.p011.b_remaining import path as run')
s=replace(s,"app=modal.App('p011-B-generation-students')","app=modal.App('p011-B-remaining-5120')")
s=replace(s,'ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parents[3]')
write(R/'modal_entry.py',s)

s=Path('scripts/p011_b_current_io.py').read_text()
s=replace(s,'from experiments.p011 import b_current_path as path, long_transport, b_numeric',
    'from experiments.p011 import long_transport,b_numeric\nfrom experiments.p011.b_remaining import path,transport as new_transport,selection as selected_rules')
s=replace(s,'from experiments.p011 import b_generation_evidence, b_generation_loader, b_student_evidence',
    'from experiments.p011 import b_student_evidence\nfrom experiments.p011.b_remaining import evidence as b_generation_evidence,loader as b_generation_loader')
s=replace(s,"k+'/dispatch',", "k+'/dispatch',") if "k+'/dispatch'," in s else s
s=replace(s,"return [k+'/'+v for v in ('dispatch','claim','terminal','generation')]+[\n        k+f'/{kind}/{i:03d}' for kind in ('batch','batch_done') for i in range(25)]", "return [k+'/'+v for v in ('dispatch','claim','terminal','generation','prefix_transport/004','prefix_transport_done/004')]+[\n        k+f'/{kind}/{i:03d}' for kind in ('batch','batch_done') for i in range(5,25)]")
s=replace(s,"'b_io_r1'","'b_remaining_io_r2'")
s=replace(s,"def upload(root,out,spec,job,review):", "def upload(root,out,spec,job,review):\n    raise RuntimeError('Original B input/model upload receipt must be reused; no repeat transfer')\n")
start=s.index("        transport=b_generation_loader.transport_reader(tokenizer,cfg['vocab_size'])")
end=s.index("        scoring=b_generation_loader.score_rows(pack,raw,decoded)",start)
s=s[:start]+'''        mapped=set(tokenizer.get_vocab().values())
        def transport(raw,decoded):return new_transport.validate_saved(raw,decoded,mapped,cfg['vocab_size'])
        def replay(left,times):
            file=payload/'generation/batches'/f'{25-left:03d}'/'FORECAST.json';f=read(file)
            return b_numeric.forecast(timing,0,left,[],times,timing['worker_start_epoch']+f['elapsed_seconds'])
        proof,raw,decoded=b_generation_evidence.check_body(pack,payload/'generation',k,receipt['claim'],records,
            spec['prefix_files'],transport,replay)
''' + s[end:]
# Saved Boolean reconstruction/selection must use the revised no-unmapped fallback.
s=replace(s,'b_generation_loader.selected_records(', 'selected_rules.selected_records(')
s=replace(s,"assets=root/job['model']['local_path'];verify(assets,job['model']['files']);cfg=read(assets/'config.json')", "assets=root/job['model']['local_path'];verify(assets,{n:v for n,v in job['model']['files'].items() if not n.endswith(('.safetensors','.bin'))});cfg=read(assets/'config.json')")
s=replace(s,"dump(out/'RECORDS.json',records);dump(out/'SELECTION.json',selection)", "dump(out/'RECORDS.json',records);dump(out/'SELECTION.json',selection);dump(out/'UNMAPPED_DENOMINATOR_REPORT.json',selected_rules.denominator_report(records))")
write('scripts/p011_b_remaining_io.py',s)
print('Prepared five new adapters and one new IO file; production not run.')
