"""Create exact failed-prefix and unattempted-suffix review packets once; no calls."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import gzip
import hashlib
import json
import shutil
import tarfile
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest, verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009 import p0_fast_remaining_contract as c

r = Path('.local/p009_20261014/r1'); f = r/'p0_fast_r1'
preserved = f/'interrupted_preservation_r1'; diag = r/'p0_fast_eos_diagnosis_r1'
out = r/'p0_fast_remaining_r1'
prefix = Path('reports/p009_20261014/p0_fast_failed_prefix_v1')
pub = Path('reports/p009_20261014/p0_fast_remaining_preflight_v1')
if any(p.exists() for p in (out,prefix,pub)):
    raise ValueError('Prior/partial builder; never overwrite or repeat')
saved = read(preserved/'PRESERVED.json'); files = read(preserved/'LOCAL_MANIFEST.json')
assert saved['passed'] and saved['files']==7 and saved['bytes']==1245643
verify(preserved/'evidence',files)
ledger = read(preserved/'ledger.json'); parent = read('reports/p009_20261014/p0_fast_preflight_v1/ADMISSION.json')
assert sha(preserved/'ledger.json') == saved['ledger_sha256']
provider = read(preserved/'PROVIDER_AFTER.json')
sent = read(f/'runs/p0_fast_pair/dispatch_intent.json')
apps = [parent['parent_app_id'],sent['provider_app_id']]
validate_stopped_apps(apps,provider['original_app_info'],provider['owned_containers'])
for n,h in parent['source_files'].items():
    assert sha(n)==h,n
new = ['experiments/learning_regime_p009/'+n+'.py' for n in
       ('p0_stop_metadata','p0_fast_remaining_contract','p0_fast_remaining_runtime','modal_p0_fast_remaining')]
new += ['scripts/p009_p0_fast_remaining_io.py','scripts/audit_p009_p0_fast_remaining.py']
sources = {n:sha(n) for n in list(parent['source_files'])+new}
assert len(sources)==32
for n in sources:
    if n.endswith('.py'):ast.parse(Path(n).read_text())
for name in ('new_stop_metadata_checks_r1.log','new_remaining_checks_r1.log'):
    assert (diag/name).read_text().rstrip().endswith('OK'),name
now = datetime.now(timezone.utc)
plan = dict(campaign_id=c.CAMPAIGN,created_epoch=now.timestamp(),deadline_epoch=1792267200.0,
    slots={c.RUN:dict(stage='p0_fast_remaining',reserved_cents=c.RESERVED_CENTS)},
    stage_caps_cents={'p0_fast_remaining':c.RESERVED_CENTS},total_cap_cents=c.RESERVED_CENTS)
pre = 'midpoint/'+c.PARENT_CAMPAIGN+'/'
diagnosis = read(diag/'DIAGNOSIS.json')
spec = dict(schema='p009_p0_fast_remaining_preflight_v1',scope=c.SCOPE,campaign=c.CAMPAIGN,run_id=c.RUN,
    runtime_admitted=False,offsets=c.OFFSETS,worker_seconds=c.WORKER_SECONDS,
    platform_seconds=c.PLATFORM_SECONDS,startup_seconds=c.STARTUP_SECONDS,
    full_window_seconds=c.FULL_WINDOW,reserved_cents=c.RESERVED_CENTS,
    parent_reserved_cents=c.PARENT_RESERVED_CENTS,stage0_cap_cents=1000,
    stage0_remaining_after_candidate_cents=248,experiment_cap_cents=10000,
    project_cap_cents=45000,protected_original_cents=5000,new_training_updates=0,
    suffix_outputs=2382,inherited_outputs=256,suffix_batches=11,batch_size=256,bootstrap_batches_total=0,
    engine_kwargs=c.engine_kwargs(),plan_sha256=digest(plan),source_files=sources,
    parent_spec=parent,parent_spec_sha256=digest(parent),parent_app_id=sent['provider_app_id'],
    parent_claim=ledger[pre+'claim/'+c.PARENT_RUN],parent_terminal=ledger[pre+'terminal/'+c.PARENT_RUN],
    parent_preservation_sha256=sha(preserved/'PRESERVED.json'),parent_files=files,
    parent_failure_manifest_file_sha256=sha(preserved/'evidence/failure_manifest.json'),
    parent_ledger_digest=digest(ledger),parent_ledger_keys=sorted(ledger),
    parent_raw_sha256=sha(preserved/'evidence/base_638/raw/0000.json'),
    parent_failed_batch_proxy_seconds=diagnosis['failed_batch_through_terminal_proxy_seconds'],
    ancestor_marker=read(preserved/'evidence/FRESH_CONFIGURATION_MARKER.json'),
    native_eos_cap_metadata=dict(original_bytes_unchanged=True,cap=512,native_eos_id=151643,
        permitted_tie='single real EOS at final token512; backend length; stop_reason null',
        frozen_first_stop_unchanged=True,score_change=False,backend_reason_preserved=True),
    forecast=dict(formula='elapsed+1.2*(max(parent_failed_batch_through_terminal,ALL_new_full_batches)*remaining+300)',
        parent_proxy_not_completed_batch=True,parent_proxy_includes_failure_closeout=True,
        future_300_uncalibrated=True,soft_worker_seconds=1170,fraction_of_remaining_stage0=.8,
        no_measurement_exception=True,forecast_not_future_bound=True),
    reserve=dict(full_window1900_cents=c.cost_cents(1900),nonworker_allowance_cents=20,
        new252_plus_prior500_equals752=True,not_actual_cost_or_invoice=True,
        remaining_stage0_248_not_admission_for_future_work=True))
# One new exact structural binding of the saved failed prefix, never decode/score.
proof = c.check_parent(spec,preserved/'evidence',ledger,r/'p0_r1/inputs')
out.mkdir(); prefix.mkdir(parents=True); pub.mkdir(parents=True)
dump(out/'plan.json',plan);dump(out/'PARENT_BINDING_VERIFIED.json',proof)
dump(out/'SPEC_PREPARED.json',dict(spec_sha256=digest(spec),source_count=len(sources),new_cloud_calls=0))
selected = {n:v for n,v in files.items() if n!='intent.json'}
archive = prefix/'original_failed_fast_projection.tar.gz'
with archive.open('xb') as h, gzip.GzipFile(fileobj=h,mode='wb',mtime=0) as z:
    with tarfile.open(fileobj=z,mode='w') as tar:
        for name in sorted(selected):
            info=tar.gettarinfo(str(preserved/'evidence'/name),arcname=name)
            info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
            with (preserved/'evidence'/name).open('rb') as h:tar.addfile(info,h)
with tarfile.open(archive,'r:gz') as tar:
    observed={}
    for member in tar.getmembers():
        if not member.isfile() or member.name not in selected or member.name in observed:
            raise ValueError('Unsafe or duplicated original archive member')
        b=tar.extractfile(member).read()
        observed[member.name]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    assert observed==selected
dump(prefix/'PROJECTION.json',dict(files=selected,omitted={'intent.json':files['intent.json']},
    source_private_manifest_sha256=sha(preserved/'LOCAL_MANIFEST.json'),archive_sha256=sha(archive),
    reason='Only private runtime intent with local review paths omitted; all original raw and failed records retained.'))
for a,b in [('ledger.json','LEDGER.json'),('PRESERVED.json','PRESERVED.json'),
            ('ORIGINAL_RECORDS.json','ORIGINAL_RECORDS.json'),('LOCAL_MANIFEST.json','ORIGINAL_MANIFEST.json')]:
    shutil.copyfile(preserved/a,prefix/b)
for a,b in [('DIAGNOSIS.json','DIAGNOSIS.json'),('SOURCE_READ.json','UPSTREAM_SOURCE_READ.json'),
            ('vllm_v011_sched_utils.py','vllm_v011_sched_utils.py')]:shutil.copyfile(diag/a,prefix/b)
dump(prefix/'PROVIDER.json',dict(observed_utc=provider['observed_utc'],app_ids=apps,
    state='stopped',owned_container_count=0,source_private_sha256=sha(preserved/'PROVIDER_AFTER.json'),
    projection='Actor identities omitted; exact private original bytes retained.',
    apps=[dict(app_id=a['app_id'],lifecycle={k:a['lifecycle'][k] for k in ('state','created_at','stopped_at')})
          for a in provider['original_app_info']]))
(prefix/'README.md').write_text('''# Plan-A P0 failed at a real EOS/length metadata boundary

The exactly reviewed26-source Plan-A P0 was submitted once, executed e56233827d828ee2c320b02ed9e7f5ca7ad7c2b5, and failed at20:55:17.866775UTC. Actual app STOPPED13:55:21PDT; independent final provider observation21:00:07UTC shows both ancestors stopped and zero owned containers. The original1200s cap was not reached or extended. All7 original files/1,245,643bytes and20 immutable ledger records were preserved once. No complete P0/parity/A2 result exists.

Exactly256 base rows were generated and saved; the first unit has no done acknowledgement because validation stopped before it. Correct969 generated nothing. The whole attempted batch is present with original prompt IDs and token bytes, so there are zero unknown attempted outputs. No score, gold comparison, token mutation or old HF rescore was performed. The earlier eager128 remain historical and excluded from PlanA.

Only gsm8k/test/00115 violates the old transport check: its one real EOS151643 is original token512, with finish_reason=length and stop_reason=null. Pinned [vLLM0.11 V1 check_stop](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/v1/core/sched/utils.py) checks the length cap before EOS. This is a validation compatibility error, not evidence of a malformed generated stream or scientific parity failure. The candidate only accepts that exact metadata tie. Original backend labels and raw bytes stay untouched. The already-frozen CPU first_stop prioritizes actual EOS over length at this boundary, and remains byte-identical; genuine logical caps remain incorrect. No additional answer extraction/scoring rule is introduced.

The new candidate structurally validates all256 rows without decoding or scoring. Eight new edge-case tests pass once. The engine's actual graph/max256/8192/bf16/context2048 configuration was saved and matched. The20.4121413230896s first-unit-start to failed-terminal interval includes failure closeout; it is a conservative bookkeeping proxy, not a completed-batch acknowledgement, causal speedup measurement or future upper bound. All failed reservations/costs remain. The key named actual_cost_cents in the original ledger stores the252c conservative reservation, not a provider invoice.

The tar preserves the selected original bytes and is independently read back. Only private runtime intent is omitted with its original hash; the exact provider projection omits actor identities with private-source hash. Both original failed statuses and the initial parent successor marker remain permanent. No automatic model retry or old-batch generation is authorized by this packet.
''')
dump(prefix/'MANIFEST.json',manifest(prefix))
for name,value in [('ADMISSION.json',spec),('PLAN.json',plan),('SOURCE_BUNDLE.json',sources),
                   ('PARENT_BINDING.json',proof),('PARENT_FILES.json',files)]:dump(pub/name,value)
for n in sources:
    dst=pub/'source'/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(n,dst)
for name in ('test_p009_stop_metadata.py','test_p009_fast_remaining.py'):
    shutil.copyfile(Path('tests')/name,pub/name)
for name in ('new_stop_metadata_checks_r1.log','new_remaining_checks_r1.log'):
    shutil.copyfile(diag/name,pub/name)
shutil.copyfile(__file__,pub/'PREPARATION_SOURCE.py')
(pub/'README.md').write_text('''# Exact unattempted Plan-A P0 remainder — candidate, not admitted

Complete the same two1319 endpoints using the original256 saved outputs plus only2382 never-attempted outputs. Base starts at index256 with four256-row chunks and one39-row chunk; correct969 starts at0 with five256-row chunks and one39-row chunk. Same high-throughput V1 engine, prompts, greedy512, context2048, seed17, native EOS, frozen logical parser and original969 checkpoint/merge; no training, regenerated prefix, input transfer or weight download. Old19/24/26 sources remain unchanged. The old stopped parent stays failed with its missing done acknowledgement; the combined CPU oracle explicitly inherits unacknowledged-but-saved raw and never invents an ack. The earlier eager128 are excluded and unscored.

The new32-source bundle adds the narrow EOS-at-cap metadata validator, exact suffix contract/runtime/entry, local gate/collector and full merged oracle. Eight validator edge tests and nine new mocked suffix tests passed once. Mocks cover no-prefix regeneration, no first-batch exception, forecast refusal before generation, lost-response fencing and all sunk reserves. They are not GPU/remote integration or actual comparability evidence. The real256-prefix structural binding passed without answer scoring.

Use only modal_p0_fast_remaining::main, distinct campaign p009-p0-fast-remaining-20261014-r1/run p0_fast_remaining. OneH100/4CPU/32GiB,1200worker from entry/1260platform/600startup/full1900, zero retry/min0/max1/single-use. The original two failed claims remain; new winning claim takes a permanent fast-parent continuation marker. Original eager successor marker remains and old suffix stays retired. Shared original dispatch lock, exact failed-lineage, published source, no local/remote/ledger prior attempt and fresh provider checks prevent competing submissions. Missing/ambiguous marker is never cleared. Partial transmission preserves valid pieces; no whole-helper retry.

Every new chunk, including the first, is gated. The retained20.4121413230896s failed-parent interval is a proxy including failure closeout, explicitly not a completed-batch timing. Use max(proxy,ALL new full guard/forecast/I/O/ack intervals), actual elapsed including model load/merge/graphs,1.2*(max*remaining+300), soft1170 and original whole-worker hard cap. No new paid bootstrap exception, fast-host selection or dropping slow observations. The300s future setup/closing allowance and proxy are uncalibrated, not guarantees. Full actual result11forecasts and source/provider/claim/raw lineage are independently replayed by the merged oracle.

New252c plus retained500c =752c of Stage0's1000c;248c remains for future independently admitted P1/P2/P3 work. P00910000c/project45000c/protected5000c and stage50/35 stay unchanged; unallocated500c is not borrowed. Reservation is not expense and failures are not recycled. Future14450 output workload has no runtime/complete-window budget admission yet; the earlier hypothetical496c grouping no longer fits248c and is not authorized. No claim that later Stage0 is already funded or that tonight's Stage1 is guaranteed. Any inability to fit real future stage budget must be surfaced rather than silently shrink science or borrow.

Admission requires a real complete fixed scoped Claude report for exact32source/spec, original saved256 lineage, native-EOS transport compatibility with unchanged scoring, proxy/timer,252c+500c budget, all original inputs and once-only fence. Current RUNTIME_ACCEPTED/BUDGET_CHECK/gates/call are absent. Existing bi PASS and local tests do not authorize this child. Complete result publication and independent actual A2 are separate; the old fresh2638 publisher cannot publish a merged suffix. Automatic next-stage progression remains conditional on actual science, exact audits and funding.
''')
(pub/'REVIEW_REQUEST.md').write_text('''# Exact high-throughput P0 unattempted remainder

Request p009-p0-fast-unattempted-remainder-r1. Scope p009-p0-fast-unattempted-remainder-runtime-and-numeric.

Please independently inspect the real failed-prefix packet, pinned vLLM length-before-EOS branch, all original256 token records and their unit/no-done status. Review the exact32-source runtime/merged oracle, unchanged original26 and frozen scoring, same256 chunk boundaries, inherited256/new2382/no training, parent+ancestor markers,1200/1260/600/full1900,20.412141 failed-closeout proxy and all-new-full-batch max (not a calibrated bound), zero bootstrap exceptions,252new+500old=752c, and Stage0 remaining248c with future P2/P3 still unfunded/unadmitted.

Return actual decision, fixed target, source_files, spec_sha256, parent_preservation_sha256, bounded_suffix_only, native_eos_cap_metadata_accepted and same_frozen_logical_stop. The 8+9 tests are new offline evidence, not GPU testing; actual A2 and any future publisher are separate. Do not turn code approval into scientific parity or normalize the old failure/ack/raw bytes. No extra GPU probe, raw replay, cap extension or unallocated-budget borrowing is proposed.
''')
dump(pub/'MANIFEST.json',manifest(pub))
print(json.dumps(dict(source_count=len(sources),spec_sha256=digest(spec),prefix_manifest=sha(prefix/'MANIFEST.json'),
    packet_manifest=sha(pub/'MANIFEST.json'),new_model_calls=0,prepared_utc=now.isoformat()),indent=2))
