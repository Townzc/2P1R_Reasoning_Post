"""Create one local admission gate or collect one completed suffix; never dispatch."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps, read_stopped_apps
from experiments.learning_regime_p009.p0_fast_remaining_contract import (
    CAMPAIGN, RUN, PARENT_CAMPAIGN, PARENT_RUN, ANCESTOR_CAMPAIGN, ANCESTOR_RUN,
    FULL_WINDOW, check_parent,
)

from experiments.learning_regime_p009.p0_entry_repair_binding import validate_repair_release as validate_release

SPEC = Path('reports/p009_20261014/p0_entry_repair_preflight_v1/ADMISSION.json')
CLI = '.local/midpoint_20261011/venv/bin/modal'


def gates(root):
    spec = read(SPEC); plan = read(root/'plan.json')
    review = read(root/'RUNTIME_ACCEPTED.json'); budget = read(root/'BUDGET_CHECK.json')
    preserved = root.parent/'p0_fast_r1/interrupted_preservation_r1'
    original_inputs = root.parent/'p0_r1'
    if (root/'gates.json').exists() or time.time()+FULL_WINDOW > plan['deadline_epoch']:
        raise ValueError('Prior gate or no complete dispatch window')
    if (sha(review['local_report_path']) != review['report_sha256']
            or sha(preserved/'PRESERVED.json') != spec['parent_preservation_sha256']
            or not 0 <= time.time()-budget['observed_epoch'] <= 3600):
        raise ValueError('Real exact report, original preservation or fresh budget missing')
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Reviewed bytes changed')
    verify(original_inputs/'inputs', spec['parent_spec']['inputs'])
    proof = check_parent(spec, preserved/'evidence', read(preserved/'ledger.json'), original_inputs/'inputs')
    provider = read(preserved/'PROVIDER_AFTER.json')
    apps = [spec['parent_spec']['parent_app_id'], spec['parent_app_id']]
    validate_stopped_apps(apps, provider['original_app_info'], provider['owned_containers'])
    zero = root.parent/'p0_fast_remaining_r1/preclaim_failure_reconciliation_r1'
    if (sha(zero/'ZERO_WORK_VERIFIED.json') != spec['preclaim_failure']['zero_work_proof_file_sha256']
            or read(zero/'ZERO_WORK_VERIFIED.json') != spec['preclaim_failure']['zero_work_proof']):
        raise ValueError('Actual immutable zero-work reconciliation required')
    release = dict(
        source_files=spec['source_files'], runtime_review=review,
        review_target=review['target_commit'], budget=budget, parent_prefix_proof=proof,
        input_readback=read(original_inputs/'UPLOAD_VERIFIED.json')['files'])
    validate_release(spec, plan, release)
    dump(root/'gates.json', release)
    print('One local gate prepared; zero uploads or scientific calls.')


def collect(root):
    import modal
    dest = root/'closeout_r1'
    if dest.exists():
        raise ValueError('Prior/partial collector; no whole-tool retry')
    spec = read(SPEC); sent = read(root/'runs'/RUN/'dispatch_intent.json')
    envelope = read(root/'runs'/RUN/'result.json')
    validate_release(spec, sent['plan'], sent['release'])
    if envelope['receipt']['status'] != 'completed':
        raise ValueError('Completed-only collector')
    apps = [spec['parent_spec']['parent_app_id'], spec['parent_app_id'], sent['provider_app_id']]
    containers = json.loads(subprocess.check_output([CLI,'container','list','--json'], text=True))
    owned = [x for x in containers if x['app_id'] in apps]
    provider = read_stopped_apps(CLI, apps, owned)
    failed_app = spec['preclaim_failure']['zero_work_proof']['original_app_id']
    failed_provider = read_stopped_apps(CLI, [failed_app], [x for x in containers if x['app_id']==failed_app])
    dump(dest/'PRECLAIM_PROVIDER.json', dict(app_ids=[failed_app], original_app_info=failed_provider,
        owned_containers=[], utc=datetime.now(timezone.utc).isoformat()))
    dump(dest/'INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
        campaign=CAMPAIGN, run=RUN, app_ids=apps, read_only=True))
    db = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    prefixes = tuple('midpoint/'+c+'/' for c in (ANCESTOR_CAMPAIGN,PARENT_CAMPAIGN,CAMPAIGN))
    ledger = {k:v for k,v in db.items() if k.startswith(prefixes)}
    if (ledger[prefixes[2]+'terminal/'+RUN] != envelope['receipt']
            or ledger[prefixes[1]+'terminal/'+PARENT_RUN] != spec['parent_terminal']
            or ledger[prefixes[0]+'terminal/'+ANCESTOR_RUN] != spec['parent_spec']['parent_terminal']
            or digest(envelope['artifact_manifest']) != envelope['receipt']['evidence_sha256']):
        raise ValueError('Three-campaign immutable lineage differs')
    dump(dest/'ledger.json', ledger)
    dump(dest/'provider.json', dict(app_ids=apps, state='stopped', original_app_info=provider,
        owned_containers=owned, owned_container_ids=[], utc=datetime.now(timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json', dict(passed=True, ledger_sha256=sha(dest/'ledger.json'),
        original_receipt_sha256=sha(root/'runs'/RUN/'result.json')))
    print('Completed suffix and both failed ancestors collected once.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=('gates','collect'))
    p.add_argument('--root', required=True); a = p.parse_args()
    (gates if a.action == 'gates' else collect)(Path(a.root))
