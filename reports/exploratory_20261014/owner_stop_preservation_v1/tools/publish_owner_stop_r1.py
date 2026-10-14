"""Publish the completed stopped-evidence inventory once, without new scores."""
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import tarfile
from experiments.sft_allocation_midpoint.common import read, dump, sha, manifest
from experiments.sft_allocation_p008.evidence_bundle import safe_name

ROOT = Path('.local/exploratory_20261014/r1')
PRESERVE = ROOT / 'interrupted_preservation_r1'
RECON = ROOT / 'interrupted_reconciliation_r1'
OUT = Path('reports/exploratory_20261014/owner_stop_preservation_v1')


def main():
    verified = read(RECON / 'VERIFIED.json')
    assert verified['preservation_and_inventory_verified']
    assert not verified['endpoint_score_oracle_passed']
    assert verified['new_model_calls'] == 0
    OUT.mkdir(exist_ok=False)
    stamp = datetime.now(timezone.utc).isoformat()
    dump(OUT / 'SUMMARY.json', dict(created_utc=stamp, **verified))
    for src, dst in [
        (ROOT / 'owner_stop_20261014_r1/OWNER_STOP_INTENT.json', 'OWNER_STOP.json'),
        (PRESERVE / 'PRESERVED_ALL.json', 'PRESERVED_ALL.json'),
        (PRESERVE / 'ledger.json', 'ledger.json'),
        (PRESERVE / 'LEDGER_READ.json', 'LEDGER_READ.json'),
        (RECON / 'STUDENT_CHECKPOINT_VERIFIED.json', 'STUDENT_CHECKPOINT_VERIFIED.json'),
        (ROOT / 'billing_after_owner_stop_r1/PROJECT_BUDGET_RECONCILIATION.json', 'BILLING.json'),
    ]:
        shutil.copyfile(src, OUT / dst)
    provider = read(ROOT / 'owner_stop_20261014_r1/PROVIDER_READ.json')
    dump(OUT / 'PROVIDER_RELEASE.json', dict(
        projection=True, omitted_fields='provider actor identities and unrelated workspace rows',
        original_private_file_sha256=sha(ROOT / 'owner_stop_20261014_r1/PROVIDER_READ.json'),
        read_at_utc=provider['read_at_utc'], container_count=provider['container_count'],
        apps=[dict(run=r['run'], app_id=r['app'], state=r['lifecycle']['state'],
                   stopped_at=r['lifecycle']['stopped_at']) for r in provider['apps']]))
    archive_members = {}
    tarpath = OUT / 'saved_evidence.tar.gz'
    with tarfile.open(tarpath, 'w:gz') as archive:
        for run in verified['runs']:
            evidence = PRESERVE / run / 'evidence'
            local_manifest = read(PRESERVE / run / 'LOCAL_MANIFEST.json')
            dest = OUT / run
            dest.mkdir()
            for name in ('LOCAL_MANIFEST.json', 'REMOTE_LISTING_BEFORE.json', 'REMOTE_LISTING_AFTER.json', 'PRESERVED.json'):
                shutil.copyfile(PRESERVE / run / name, dest / name)
            shutil.copyfile(RECON / (run + '_INVENTORY.json'), dest / 'INVENTORY.json')
            shutil.copyfile(ROOT / 'runs' / run / 'return_error.json', dest / 'original_return_error.json')
            for name, record in local_manifest.items():
                # Full checkpoint remains private and on the original Volume.
                # Original intent embeds gate/readback metadata; bind its hash
                # instead of publishing that private release envelope.
                if name.endswith('.pt') or name == 'intent.json':
                    continue
                safe_name(name)
                arcname = run + '/' + name
                archive.add(evidence / name, arcname=arcname, recursive=False)
                archive_members[arcname] = record
    observed = {}
    import hashlib
    with tarfile.open(tarpath, 'r:gz') as archive:
        for member in archive:
            safe_name(member.name)
            assert member.isfile() and member.name not in observed
            data = archive.extractfile(member).read()
            observed[member.name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    assert observed == archive_members
    dump(OUT / 'ARCHIVE_READBACK.json', dict(passed=True, sha256=sha(tarpath), files=observed,
         excluded='state.pt and intent.json; original full manifests and checkpoint proof preserved'))
    tools = OUT / 'tools'
    tools.mkdir()
    for name in ('preserve_owner_stopped_r1.py', 'reconcile_owner_stopped_r1.py', 'publish_owner_stop_r1.py'):
        shutil.copyfile(ROOT / name, tools / name)
    lines = ['| Run | Saved raw outputs | Original acknowledged | Saved without final batch ack | Never attempted |',
             '|---|---:|---:|---:|---:|']
    for run, row in verified['runs'].items():
        lines.append(f"| {run} | {row['saved_raw_rows']} | {row['original_acknowledged_rows']} | {row['unacknowledged_saved_raw_rows']} | {row['never_attempted_rows']} |")
    text = f'''# Exploratory experiments stopped and preserved

Recorded {stamp}. Owner explicitly chose “停止并保全，准备修复送审”. The three original apps were stopped once at08:05:16–18UTC (01:05PDT); independent provider reads through08:05:47UTC confirmed all three STOPPED and zero containers. Each original terminal remains **failed** due to the requested interruption, with its original claim, callback error, failure manifest and costs retained. No model, training, evaluation, upload or scoring was repeated.

{chr(10).join(lines)}

The three attempted prefixes have no missing raw rows in the saved inventory. Each last16-output batch lacks its original completion acknowledgment. Those48 rows remain unacknowledged; this inventory did not independently decode/score any endpoint output. No full1319-question result or partial accuracy is reported, and no missing acknowledgment was fabricated. All three endpoints remain incomplete.

The wrong-teacher student completed **256 updates and524,287 targets**. Its original222,109,365-byte full checkpoint was copied, hash checked, loaded locally once, and matched to all256 exact frozen schedule/LR records and16 remote training-block acknowledgments. Adapter/optimizer tensors are finite, optimizer steps are256 and RNG fields are retained. State SHA256: `45d3871207d9a9b42c2dcc7f72ef71c289d943b3d9e4fedfafd016a8c502ef57`. This is state preservation, not a tested cross-host restore or permission to resume. The full binary stays private and on the original Volume; the public packet contains its original manifest and verification proof.

All690 committed original files (231,420,287bytes) were preserved once. Before/after stopped Volume listings match. The archive includes original raw/scored files, local journals, failure records and checkpoint manifest. It excludes the full `.pt` and the original intent embedding private gate metadata; their hashes remain in the full original manifests. `ledger.json` is the single original campaign snapshot. Public provider data is explicitly projected to omit actor identities; original private bytes remain preserved.

## Performance repair submitted for review

All three interruption tracebacks stop inside `len(tokenizer)` in the per-token reference-validation comprehension. This supports the repeated vocabulary lookup as a material overhead source. Original cloud batch intervals and the one local timing diagnostic remain evidence, not a calibrated future-host speed guarantee or proof that no other overhead exists.

The [unapplied cache proposal](https://github.com/Townzc/2P1R_Reasoning_Post/blob/1a3c910ecb438bd16f0cff860973168c98edc56d/reports/exploratory_20261014/vocab_cache_proposal_v1/REVIEW_REQUEST.md) moves the same vocabulary-size lookup outside the token comprehension. Its4 new edge fixtures and32 saved-event comparisons were already completed before stopping and were not repeated here. Original37 scientific source bytes remain unchanged. Exact proposal code review is requested through INDEX; this packet does not declare it PASS or admit an executable replacement/continuation.

Owner stop approval authorizes preservation and repair preparation only: **no retries, new scientific calls or extra budget**. Any possible future continuation must preserve these failed parents, every already-attempted ID and the completed student state; it is not authorized by this record. p007 remains paused and original P008 materials remain closed and immutable.

## Accounting

The08:08:43–44UTC delayed billing snapshot attributes $5.43330865 to these three original app IDs. It is not a final invoice, complete current cost or balance. The original$30 ceiling remains; no reservation is recycled and setup/download/storage/failure costs are retained. Conservative residual plus the full priorP008 reservation and full$30 envelope is$384.84256089 against the unchanged$450 project spending ceiling and$50 protection. See `BILLING.json` for exact scope and read times.
'''
    (OUT / 'README.md').write_text(text)
    (OUT / 'REVIEW_REQUEST.md').write_text('''# Stopped original evidence and repair-context review

Scope: exploratory-owner-stop-preservation. Review the original failed terminals/claims, complete local manifests, archive readback, all three interrupted endpoint inventories, original256-update student state proof and the explicit lack of independent endpoint scoring. Check690 files/231420287bytes,272/144/80 saved raw rows,256/128/64 original acknowledgments, three unacknowledged16-row batches and0 attempted rows missing raw. Public state proof is not reviewer binary inspection. All3failed parents remain failed; no new call, retry or continuation is admitted.

Read the exact cache proposal request at1a3c910e separately. This packet adds real stop-time failure stacks and preserved-prefix context; it does not expand proposal PASS into runtime/suffix/state-restoration admission. No future implementation should regenerate attempted outputs or retrain the completed256-step student without separate explicit authorization and exact review.

Do not treat partial endpoints as full1319 scores, pending acknowledgments as accepted, local timing as a cloud speed guarantee, or reserved/lagged cost as an invoice. The source37 and P008 materials are unchanged. Review/read-only requests are published through INDEX; no external comment was sent.
''')
    dump(OUT / 'MANIFEST.json', dict(schema='exploratory_owner_stop_preservation_v1',
                                   created_utc=stamp, files=manifest(OUT)))
    print(json.dumps(dict(packet=str(OUT), files=len(read(OUT / 'MANIFEST.json')['files']),
                         archive_members=len(archive_members), source_37_unchanged=True)))


if __name__ == '__main__':
    main()
