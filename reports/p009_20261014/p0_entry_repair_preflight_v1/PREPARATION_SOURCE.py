"""Create-only exact repair and original zero-work failure evidence, no cloud work."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import shutil
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest, verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009 import p0_entry_repair_binding as binding

r=Path('.local/p009_20261014/r1')
old=r/'p0_fast_remaining_r1'
rec=old/'preclaim_failure_reconciliation_r1'
root=r/'p0_entry_repair_r1'
failure=Path('reports/p009_20261014/p0_preclaim_failure_v1')
pub=Path('reports/p009_20261014/p0_entry_repair_preflight_v1')
publisher=Path('reports/p009_20261014/p0_entry_repair_publisher_v1')
if any(p.exists() for p in (root,failure,pub,publisher)):
    raise ValueError('Create-only preparation; preserve partials and reconcile instead of repeating')
verify(rec,read(rec/'MANIFEST.json'))
proof=read(rec/'ZERO_WORK_VERIFIED.json')
plan=read(old/'plan.json')
binding.registration_only(proof['actual_campaign_records'],plan)
provider=read(rec/'PROVIDER_AFTER.json')
validate_stopped_apps(provider['app_ids'],provider['original_app_info'],provider['owned_containers'])
original=read('reports/p009_20261014/p0_fast_remaining_preflight_v1/ADMISSION.json')
for name,expected in original['source_files'].items():
    if sha(name)!=expected:
        raise ValueError('Original reviewed 32 source bytes changed')
log=r/'entry_schema_checks_r2_owner_caps.log'
if 'Ran 11 tests' not in log.read_text() or not log.read_text().rstrip().endswith('OK'):
    raise ValueError('Missing actual new entry fixtures')
now=datetime.now(timezone.utc).isoformat()
owner=dict(read_utc=now,original_user_text='可以提高预算上限，别因为多了一点钱就暂停工作影响进度',
    authority='Direct owner permission to increase the budget for completing the already authorized finite study; exact bounded allocation made by Codex and stated in chat.',
    experiment_cap_cents=11000,stage0_cap_cents=2000,stage1_cap_cents=5000,
    stage2_cap_cents=3500,unallocated_cents=500,project_cap_cents=45000,
    protected_original_cents=5000,scientific_scope_changed=False,
    all_failures_and_setup_retained=True,no_additional_owner_permission_required=True)
dump(r/'OWNER_P009_BUDGET_110_STAGE0_20.json',owner)
sources=dict(original['source_files'])
for name in ('experiments/learning_regime_p009/p0_entry_repair_binding.py',
        'experiments/learning_regime_p009/modal_p0_entry_repair.py',
        'experiments/learning_regime_p009/p0_entry_repair_runtime.py',
        'scripts/p009_p0_entry_repair_io.py','scripts/audit_p009_p0_entry_repair.py',
        'scripts/p009_p0_entry_repair_readonly.py'):
    ast.parse(Path(name).read_text());sources[name]=sha(name)
assert len(sources)==38
spec=deepcopy(original)
spec.update(schema='p009_p0_entry_schema_repair_v1',source_files=sources,
    parent_reserved_cents=752,stage0_cap_cents=2000,experiment_cap_cents=11000,
    stage0_remaining_after_candidate_cents=996,original_two_failed_reserved_cents=500,
    owner_budget_amendment_sha256=sha(r/'OWNER_P009_BUDGET_110_STAGE0_20.json'),
    preclaim_failure=dict(repair_scope=binding.REPAIR_SCOPE,zero_work_proof=proof,
        zero_work_proof_file_sha256=sha(rec/'ZERO_WORK_VERIFIED.json'),
        original_callback_sha256={p.name:sha(p) for p in sorted((rec/'original_callback').iterdir())},
        private_original_log_sha256=sha(rec/'original_cli.log'),
        original_source_commit='e7d2714b6566dd2d2be58da24c8990d01069069a',
        original_runtime_target='5c5222573dece18fe3fe715ecfa3bdbfec1d2d01',
        prior_failed_call_reserved_cents=252,
        public_evidence_packet=str(failure),same_unclaimed_plan=True),
    reserve=dict(new_slot_cents=252,original_claimed_failure_reserves_cents=500,
        preclaim_failed_call_allowance_cents=252,prior_conservative_cents=752,
        total_conservative_cents=1004,stage0_cap_cents=2000,remaining_cents=996,
        settlement_release_used=False,not_actual_cost_or_invoice=True))
root.mkdir();failure.mkdir(parents=True);pub.mkdir(parents=True);publisher.mkdir(parents=True)
dump(root/'plan.json',plan)
dump(root/'SPEC_PREPARED.json',dict(spec_sha256=digest(spec),source_files=sources,
    new_runtime_called=False,admitted=False,requires_real_fixed_new_review=True))
for name in ('ZERO_WORK_VERIFIED.json','ledger.json','VOLUME_ABSENCE.json','ORIGINAL_ENTRY.py','ORIGINAL_ADMISSION.json'):
    shutil.copyfile(rec/name,failure/name)
shutil.copyfile(rec/'original_callback/submitted.json',failure/'ORIGINAL_SUBMITTED.json')
shutil.copyfile(rec/'original_callback/return_error.json',failure/'ORIGINAL_CALLBACK_ERROR.json')
dump(failure/'PROVIDER.json',dict(app_ids=provider['app_ids'],owned_containers=[],
    observed_utc=provider['observed_utc'],original_private_file_sha256=sha(rec/'PROVIDER_AFTER.json'),
    projection='Actor identities omitted; full original private provider preserved with SHA.',
    apps=[dict(app_id=x['app_id'],lifecycle={k:x['lifecycle'][k] for k in ('state','created_at','stopped_at')})
          for x in provider['original_app_info']]))
dump(failure/'PRIVATE_SOURCE_SHA.json',dict(original_private_files=read(rec/'MANIFEST.json'),
    original_log_publicly_omitted=True,original_dispatch_private_metadata_omitted=True,
    omission_reason='Public app/call, error, exact source, zero-work ledger and provider projection suffice; private originals remain unchanged.',
    previous_preservation_sha256=original['parent_preservation_sha256']))
shutil.copyfile(r/'reconcile_preclaim_entry_failure.py',failure/'READONLY_RECONCILIATION_SOURCE.py')
(failure/'README.md').write_text('''# P009 pre-claim entry failure, independently reconciled

Original call `fc-01M4Y5X0QZVYFXKX0RXQTPCX39` in app
`ap-AWwBuFC9C1MSINlMCioi5O` failed at the worker's `spec['inputs']`
lookup. The actual immutable admission stores that manifest under
`spec['parent_spec']['inputs']`. This was an entry-schema implementation defect,
missed by the earlier runtime tests and scoped review; it is not a parity result.

The full original ledger contains only the identical campaign registration:
zero claim, admission intent, attempted units, terminal or generated output.
The remote campaign directory is absent; the parent successor marker remains
absent. Original provider records before and after the full read establish all
three apps STOPPED with zero owned containers. No model was loaded. No failed
terminal is fabricated for a claim that never existed. All original callback,
source, log and provider bytes remain private with hashes; public actor metadata
is explicitly projected. The earlier saved256 raw rows are untouched.

The same unused scientific slot may only be admitted after a separately fixed
repair/source/input/numeric audit and a fresh complete absence check. A new
permanent dispatch marker prevents another call if its response is lost. No
claim is cleared. The failed cloud call still has a full252-cent allowance;
zero scientific work does not mean zero platform cost.
''')
dump(failure/'MANIFEST.json',manifest(failure))
dump(pub/'ADMISSION.json',spec);dump(pub/'PLAN.json',plan)
shutil.copyfile(r/'OWNER_P009_BUDGET_110_STAGE0_20.json',pub/'OWNER_BUDGET_AMENDMENT.json')
dump(pub/'SOURCE_BUNDLE.json',dict(source_files=sources,source_count=38,spec_sha256=digest(spec),
    original_32_byte_identical=True,original_runtime_body_unchanged_except_forecast_import=True,
    actual_model_calls=0,runtime_admitted=False))
for name in sources:
    dest=pub/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,dest)
shutil.copyfile('tests/test_p009_entry_schema_repair.py',pub/'test_p009_entry_schema_repair.py')
for name in ('entry_schema_checks_r1.log','entry_schema_checks_r2_owner_caps.log'):
    shutil.copyfile(r/name,pub/name)
shutil.copyfile(__file__,pub/'PREPARATION_SOURCE.py')
(pub/'README.md').write_text('''# P009 exact entry-schema repair — not admitted or called

The original cloud entry failed before `guard.admit`, model loading or a single
new output. Full original evidence is in `../p0_preclaim_failure_v1`. The old32
source files and both failed scientific ancestors are unchanged. This candidate
corrects the nested input-manifest binding, validates it before registration,
and covers imports/admission with the hard-timer cleanup. It does not change
the frozen EOS tie rule, logical parser, prompts, weights, merge, sampling or
which256 raw rows are inherited. The only new generation remains2,382 rows.

All38 exact runtime/source files are bound in ADMISSION. The original registered
plan and unused run ID remain byte-identical. Before a new dispatch the complete
campaign ledger must be exactly that one plan record, both claimed ancestors
must retain their failed terminals and marker, all prior apps must be STOPPED0,
and both relevant remote directories must be absent. A fresh immutable
`entry_schema_repair_dispatch` marker is created before spawn. Any existing or
ambiguous marker, local intent, claim, unit, terminal or directory blocks another
call permanently. No automatic retry, model output replay or claim deletion.

The direct owner authorized increasing the budget to prevent a small overrun
from blocking progress. Codex made and stated a bounded allocation: P009$110,
Stage0$20, Stage1$50, Stage2$35, unallocated$5. Project$450 spending and$50 protection
remain. This candidate retains the full old$5 failed-claim ceilings plus$2.52
for the failed pre-claim call and$2.52 for the new slot: $10.04, leaving$9.96 in
Stage0. Settlement at metered gross cost plus a delay buffer is separately under
review, but this call does not depend on released reserves. Fresh project meter
evidence remains required. A reservation is not a final invoice or free failure.

The hardware and scientific limits remain oneH100,1200 entry seconds,
1260 platform,600 startup,full1900 dispatch window,256-sequence CUDA graphs,
2048 context,greedy512 and originalseed17. The first and every later new batch
retain the full elapsed +1.2*(maximum all observed intervals*remaining+300)
forecast and1170 soft line. Only the cost threshold uses the newly authorized
Stage0 envelope and full752-cent prior reserve. The failed-parent20.412141s
interval and300 seconds are uncalibrated proxies, never performance guarantees.

Eleven new fixtures execute the actual worker AST with the real published input
schema and mocked cloud/model I/O. They reproduce the original KeyError before
any model call, pass the fixed nested input binding, prove timer cleanup on
pre-claim failures, preserve a terminal after a synthetic model-path failure,
refuse a second claimed execution, reject mismatched manifests/reviews/markers
and retain the owner-amended caps and original time gate. They do not validate
GPU throughput or replace the future2638-output oracle. Initial10 tests passed;
the budget-authority change and public self-contained fixtures justified one
11-test rerun. All old tests and real data scoring remain untouched.

The new I/O adapter preserves the fourth (pre-claim) failed provider separately;
the complete raw oracle uses the unchanged scientific replay body with the
new exact binding and budget forecast. Read-only helpers use the new root/spec,
31 known keys and all four provider exits. The result publisher is separately
bound in the sibling packet. Actual A2 and later scientific gates remain open.
''')
(pub/'REVIEW_REQUEST.md').write_text('''# Exact entry repair and all retained budget/source lineage

Request `p009-p0-entry-schema-repair-r1`. Scope remains
`p009-p0-fast-unattempted-remainder-runtime-and-numeric`, but this NEW target,
38source, spec and pre-claim proof are mandatory; the oldbl PASS is insufficient.
Please independently inspect the actual worker/local entrypoints, not only the
suffix execution core. Review original zero-work ledger/Volume absence/provider
proof, original identical registration, atomic dispatch fence, new nested data
hash, broad timer cleanup, all original failed lineage and256 untouched rows.
Check full$10.04 accounting within the direct-authorized$20/$110 caps, original
1200/full1900 timing, no first-batch exception and exact new collector/oracle.

Return real decision/target/source_files/spec_sha256/parent_preservation_sha256,
the original bounded_suffix_only/native_eos_cap_metadata_accepted/
same_frozen_logical_stop=true flags, plus preclaim_entry_schema_repair_accepted,
preclaim_proof_sha256,stage0_cap_cents2000,experiment_cap_cents11000 and
owner_budget_amendment_sha256. This admits no output until a fresh unused-slot
and full window check. Any actual complete result still needs independent A2.

Also review the included exact read-only adapter under
`p009-p0-fast-remainder-readonly-observation-and-failed-preservation-code`,
binding its actual source SHA and this fixed target. It only observes a real
submitted new call or preserves a real failed claim once; no cloud writes.
No new automatic retry or external message is authorized by this publication.
''')
dump(pub/'MANIFEST.json',manifest(pub))
source=r/'publish_p0_entry_repair_result.py'
ast.parse(source.read_text());shutil.copyfile(source,publisher/'PUBLICATION_SOURCE.py')
dump(publisher/'SOURCE_BINDING.json',dict(scope='p009-p0-fast-remainder-result-publication-code',
    source_path=str(source),source_sha256=sha(source),new_root=str(root),
    admission=str(pub/'ADMISSION.json'),actual_runs=0,actual_publication='NOT_RUN'))
(publisher/'REVIEW_REQUEST.md').write_text('Review the exact source under scope p009-p0-fast-remainder-result-publication-code: create-only full2638 oracle/provider/source binding, original archive/readback unchanged, explicit fourth pre-claim failed-call and amended-budget provenance, all parity outcomes including blocked ones, no private actor/gates, no new scoring/model. The old publisher299c662b PASS does not cover this source. Return decision/target/source_sha256.\n')
dump(publisher/'MANIFEST.json',manifest(publisher))
dump(r/'ENTRY_REPAIR_PREPARED.json',dict(utc=now,source_count=38,spec_sha256=digest(spec),
    packets=[str(failure),str(pub),str(publisher)],runtime_called=False,tests=11,
    preclaim_zero_work_proof_sha256=sha(rec/'ZERO_WORK_VERIFIED.json')))
print('Prepared once',digest(spec),'38source; zero new calls, all three packets pending real review.')
