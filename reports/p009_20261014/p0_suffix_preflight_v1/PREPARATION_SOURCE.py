"""Create-only failed-prefix publication and exact unused-suffix code proposal."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import tarfile
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from experiments.learning_regime_p009 import p0_suffix_contract as c

root = Path('.local/p009_20261014/r1')
parent = root/'p0_r1'; preserved = parent/'interrupted_preservation_r1'
child = parent/'suffix_r1'
pub = Path('reports/p009_20261014/p0_interrupted_prefix_v1')
packet = Path('reports/p009_20261014/p0_suffix_preflight_v1')
if any(p.exists() for p in (child,pub,packet)):
    raise FileExistsError('Create-only; preserve partials and reconcile without rerunning')
original = read('reports/p009_20261014/p0_runtime_preflight_v1/ADMISSION.json')
for name, expected in original['source_files'].items():
    if sha(name) != expected:
        raise ValueError('Original nineteen runtime bytes changed')
closed = read(preserved/'PRESERVED.json')
if not closed['passed'] or closed['original_failure_status'] != 'failed':
    raise ValueError('Original preservation not complete')
provider = read(preserved/'PROVIDER.json')
if provider['state'] != 'stopped' or provider['owned_containers']:
    raise ValueError('Original app must have released its container')
log = root/'p0_suffix_checks_r1.log'
if 'Ran 6 tests' not in log.read_text() or '\nOK\n' not in log.read_text():
    raise ValueError('New six fixture results missing')
ledger = read(preserved/'ledger.json'); records = read(preserved/'ORIGINAL_RECORDS.json')
now = datetime.datetime.now(datetime.timezone.utc)
plan = dict(campaign_id=c.CAMPAIGN,created_epoch=now.timestamp(),
    deadline_epoch=datetime.datetime(2026,10,17,20,tzinfo=datetime.timezone.utc).timestamp(),
    total_cap_cents=c.RESERVED_CENTS,stage_caps_cents={'p0_suffix':c.RESERVED_CENTS},
    slots={c.RUN:dict(stage='p0_suffix',reserved_cents=c.RESERVED_CENTS)})
sources = list(original['source_files'])+[
    'experiments/learning_regime_p009/p0_suffix_contract.py',
    'experiments/learning_regime_p009/p0_suffix_runtime.py',
    'experiments/learning_regime_p009/modal_p0_suffix.py',
    'scripts/p009_p0_suffix_io.py','scripts/audit_p009_p0_suffix.py']
spec = dict(scope=c.SCOPE,campaign=c.CAMPAIGN,run_id=c.RUN,worker_seconds=1800,
    platform_seconds=1860,startup_seconds=600,full_window_seconds=2500,
    reserved_cents=326,parent_reserved_cents=248,offsets=dict(c.OFFSETS),
    suffix_outputs=2510,reused_outputs=128,new_training_updates=0,
    plan_sha256=digest(plan),source_files={p:sha(p) for p in sources},
    parent_spec=original,parent_spec_sha256=digest(original),
    parent_claim=records['claim'],parent_terminal=records['terminal'],
    parent_app_id=provider['app_id'],parent_ledger_digest=digest(ledger),
    parent_ledger_keys=sorted(ledger),parent_files=read(preserved/'LOCAL_MANIFEST.json'),
    parent_failure_manifest_file_sha256=sha(preserved/'evidence/failure_manifest.json'),
    parent_preservation_sha256=sha(preserved/'PRESERVED.json'),
    failed_forecast=read(preserved/'evidence/forecasts/004.json'),
    original_science_scope='Same two original 1319 P0 parity endpoints; no training/new arm/score gate',
    whole_experiment_cap_cents=10000,stage0_cap_cents=1000,
    prior_248_reservation_retained=True,prior_time_gate_failed=True,
    current_new_runtime_admission=False)
proof = c.check_parent(spec,preserved/'evidence',ledger,parent/'inputs')
child.mkdir();pub.mkdir();packet.mkdir()
dump(child/'plan.json',plan);dump(child/'SPEC.json',spec)
dump(parent/'PREFIX_RECONCILIATION.json',dict(utc=now.isoformat(),**proof,
    original_four_full_batch_forecast=spec['failed_forecast'],raw_scores_computed=0))
for name in ['PRESERVED.json','ORIGINAL_RECORDS.json','ledger.json','LOCAL_MANIFEST.json',
             'REMOTE_LISTING_BEFORE.json','REMOTE_LISTING_AFTER.json','LEDGER_READ.json']:
    shutil.copyfile(preserved/name,pub/name)
shutil.copyfile(parent/'PREFIX_RECONCILIATION.json',pub/'PREFIX_RECONCILIATION.json')
shutil.copyfile(parent/'runs/p0_parity_pair/return_error.json',pub/'ORIGINAL_CALLBACK_ERROR.json')
dump(pub/'PROVIDER.json',dict(app_id=provider['app_id'],state='stopped',owned_container_count=0,
    stopped_at=provider['original_app_info'][0]['lifecycle']['stopped_at'],
    observed_utc=provider['observed_utc'],private_full_provider_sha256=sha(preserved/'PROVIDER.json'),
    projection='Account actor identity omitted; original private bytes retained'))
selected = {n:v for n,v in spec['parent_files'].items() if n!='intent.json'}
archive = pub/'original_failed_evidence_projection.tar.gz'
def metadata(info):
    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;return info
with tarfile.open(archive,'w:gz') as t:
    for name in sorted(selected):
        t.add(preserved/'evidence'/name,arcname=name,recursive=False,filter=metadata)
with tarfile.open(archive,'r:gz') as t:
    if set(t.getnames()) != set(selected):raise ValueError('Projection roster differs')
    for name,record in selected.items():
        b=t.extractfile(name).read()
        if len(b)!=record['bytes'] or hashlib.sha256(b).hexdigest()!=record['sha256']:
            raise ValueError('Projection original-byte readback differs')
dump(pub/'PROJECTION.json',dict(files=selected,omitted={'intent.json':spec['parent_files']['intent.json']},
    reason='Private runtime intent contains local report/budget references; original retained privately and SHA-bound by failed manifest',
    all_original_raw_batches_included=True,archive_sha256=sha(archive)))
(pub/'README.md').write_text('''# P009 P0 original timing-gate stop — preserved failed attempt

The original call stopped after four complete base batches (128 saved raw rows).
No correct-969 output was attempted. The full ledger contains exactly four unit
intents and four matching done records: no missing or unacknowledged attempted
output. All 21 files / 670,700 bytes matched the original failed manifest; before
and after stopped-Volume listings matched. This is structural/raw-byte evidence,
not an accuracy or partial parity score. No original HF reference was rescored.

The observed full-batch maximum was 11.793591022491455 seconds. At the next gate,
the original rule forecast 1,582.9472081661224 total worker seconds, above its
1,170-second admission line / 1,200-second hard cap. The worker correctly stopped
before submitting batch five. Original failed claim, terminal, callback error,
cost reservation and source remain permanent. Provider stopped at 12:19:05 PDT
(19:19:05 UTC), with zero owned containers. This is an engineering time failure,
not a failed scientific parity comparison. That comparison is still unavailable.

The exact raw/ack/timing/failure bytes are in the projection archive. Only the
private runtime intent is omitted; its original SHA is retained in the full
failure manifest. Provider actor identity is projected out explicitly. No model,
collector, old oracle or test was repeated to create this packet.
''')
dump(pub/'MANIFEST.json',manifest(pub))
dump(packet/'ADMISSION.json',spec);dump(packet/'PLAN.json',plan)
dump(packet/'SOURCE_BUNDLE.json',spec['source_files'])
dump(packet/'BUDGET_PROPOSAL.json',dict(utc=now.isoformat(),whole_experiment_cap_cents=10000,
    stage0_cap_cents=1000,original_failed_slot_cents=248,new_suffix_slot_cents=326,
    cumulative_P0_reserved_cents=574,remaining_stage0_cents=426,
    reserve_basis='ceil(cost_cents(2500 full startup/worker/closing window))+20c nonworker allowance =326c',
    original_claim_not_recycled=True,reservations_not_actual_spend=True,
    future_P2_P3_funding_not_assumed=True,additional_owner_budget=0,
    proposal_runtime_seconds=1800,original_runtime_1200_not_rewritten=True,
    authorization_basis='Existing finite100USD P009 and automatic audited progression; only never-attempted original P0 outputs. This technical amendment still requires exact external review. No retry of completed/unknown work.',
    unallocated_5_USD_untouched=True))
for name in sources:
    dest=packet/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,dest)
shutil.copyfile('tests/test_p009_p0_suffix.py',packet/'test_p009_p0_suffix.py')
shutil.copyfile(log,packet/'p0_suffix_checks_r1.log')
shutil.copyfile(__file__,packet/'PREPARATION_SOURCE.py')
dump(packet/'PREFIX_LINK.json',dict(packet=str(pub),manifest_sha256=sha(pub/'MANIFEST.json'),
    parent_preservation_sha256=spec['parent_preservation_sha256'],prefix_proof=proof))
(packet/'README.md').write_text('''# P009 P0 unattempted suffix — exact technical amendment for review

Only base IDs128..1318 (1,191) and correct-969 IDs0..1318 (1,319) remain: 2,510
new outputs. The original128 are inherited from the immutable failed parent.
No completed or unknown sample is regenerated, and no training occurs. Science,
prompts, engine, checkpoint merge, EOS, raw validation and final parity rules
remain unchanged. Original nineteen runtime files are byte-identical.

The new distinct child uses1,800worker/1,860platform/600startup/2,500fullwindow,
one H100, min0, single-use, zero retries and an entry hard timer. A new$3.26
conservative slot plus the unrecycled original$2.48 is$5.74 of Stage0's$10.
This remains inside the owner's$100 total; later Stage0 work has only$4.26 of
reservation headroom and must fit its own measured/code/numeric gates. The$5
unallocated reserve is untouched. This is a proposed technical time amendment,
not a claim that the original1,200-second gate passed or that costs are invoices.

Every new batch is forecast before its intent. Start with the actual maximum
over ALL four original full batches, then retain the maximum over every new
full batch, including guard, serialization, raw writes, journals and commits.
Keep1.2*(max*remaining+300) and compare actual elapsed+forecast with1,770;
also require forecast cost<=80% of remaining Stage0 allowance. No new four-batch
exemption. At 45 seconds new setup, the initial projection is about1,537seconds;
300seconds future setup/merge/pack is uncalibrated, not a bound or success promise.

The child verifies all original parent files and exact failed ledger before
loading models, and writes a permanent cross-campaign continuation marker after
winning its own claim. Any earlier child claim/intent/directory/marker prevents
another dispatch. Partial failure stays permanent. Fresh zero-container and
exact original-app STOPPED0 checks precede dispatch under the original lock.
No source, old plan, failed claim or original raw byte is changed.

Original inputs, base weights and969checkpoint stay on Volume; no re-upload or
redownload is needed. The new local gate requires a genuine fixed scoped report,
source24/spec/prefix/numeric binding and fresh budget. No such acceptance, gate,
image or child call exists in this packet. The old entry must never be restarted.

After completion: once-only two-campaign ledger/provider collection, compact
export, then independent CPU replay of all2,638 logical outputs from their true
parent/child source. Old HF Boolean references are compared, not rescored.
Both apps must be STOPPED0. The failed parent is never relabeled completed.

Six new fixtures passed once, including a completely mocked80-batch flow that
generates exactly2,510 synthetic rows, never regenerates the first128, rejects a
second marker and detects an unknown original unit. Test log progress is mocked
data, not actual model execution. Source parsing and actual stopped-prefix
structural reconciliation are separate from these fixtures. No partial accuracy
has been calculated or used for this engineering decision.
''')
(packet/'REVIEW_REQUEST.md').write_text('''# Exact P0 suffix runtime, lineage and numeric review

Request `p009-p0-unattempted-suffix-r1`; scope
`p009-p0-unattempted-suffix-runtime-and-numeric`.

Please read the failed-prefix packet and bind this exact24-source/spec/plan.
Review128inherited+2,510never-attempted outputs, no training or science change,
permanent failed parent and cross-campaign marker, one new326c slot while
retaining old248c, cumulative574c within Stage0 1,000c and whole10,000c.
Review the explicit1,800-second technical amendment and all-observed-batch
forecast; do not treat the old1,200-second failure as a pass. Actual unmeasured
setup/merge/closing risk remains disclosed. No automatic retries or new dataset.

Also review the full parent+child raw oracle and two-app release collection.
Exact report acceptance must include scope, target, spec, source24, original
preservation SHA and `bounded_suffix_only=true`. Code/prefix/numeric acceptance
does not mean actual P0 parity passed. Future P2/P3 must fit the remaining stage
budget; there is no automatic borrowing from the unallocated$5.
''')
dump(packet/'MANIFEST.json',manifest(packet))
dump(root/'P0_SUFFIX_PREPARED.json',dict(utc=now.isoformat(),source_files=len(sources),
    spec_sha256=digest(spec),packet_manifest_sha256=sha(packet/'MANIFEST.json'),
    prefix_manifest_sha256=sha(pub/'MANIFEST.json'),new_scientific_calls=0,
    runtime_accepted=False,gates_exist=False,tests=6,parent_failed=True))
print(json.dumps(read(root/'P0_SUFFIX_PREPARED.json'),indent=2))
