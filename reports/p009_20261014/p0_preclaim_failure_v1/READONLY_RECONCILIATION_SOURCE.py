"""One read-only reconciliation of the original pre-admission KeyError."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import threading
import traceback

import modal
from modal.exception import NotFoundError
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from scripts.p009_p0_fast_remaining_readonly import provider

ROOT = Path('.local/p009_20261014/r1/p0_fast_remaining_r1')
OUT = ROOT/'preclaim_failure_reconciliation_r1'
CAMPAIGN = 'p009-p0-fast-remaining-20261014-r1'
RUN = 'p0_fast_remaining'
SPEC = Path('reports/p009_20261014/p0_fast_remaining_preflight_v1/ADMISSION.json')

def main():
    if OUT.exists():
        raise ValueError('Create-only reconciliation; preserve any partial attempt')
    sent = read(ROOT/'runs'/RUN/'dispatch_intent.json')
    submitted = read(ROOT/'runs'/RUN/'submitted.json')
    error = read(ROOT/'runs'/RUN/'return_error.json')
    if error != dict(type='KeyError', error="'inputs'", retry_authorized=False):
        raise ValueError('Different failure; cannot infer zero work')
    if (ROOT/'runs'/RUN/'result.json').exists():
        raise ValueError('Unexpected result')
    spec = read(SPEC)
    apps = [spec['parent_spec']['parent_app_id'], spec['parent_app_id'], sent['provider_app_id']]
    before = provider(apps)
    validate_stopped_apps(apps, before['original_app_info'], before['owned_containers'])
    OUT.mkdir(exist_ok=False)
    dump(OUT/'READ_INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
        read_only=True, scientific_calls=0, original_call_id=submitted['call_id'],
        original_app_id=sent['provider_app_id'], source_sha256=sha(__file__)))
    dump(OUT/'PROVIDER_BEFORE.json', before)
    shutil.copytree(ROOT/'runs'/RUN, OUT/'original_callback')
    shutil.copyfile(ROOT/'run_r1.log', OUT/'original_cli.log')
    shutil.copyfile(SPEC, OUT/'ORIGINAL_ADMISSION.json')
    shutil.copyfile('experiments/learning_regime_p009/modal_p0_fast_remaining.py', OUT/'ORIGINAL_ENTRY.py')
    try:
        db = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        prefixes = tuple('midpoint/'+c+'/' for c in (
            'p009-p0-parity-20261014-r1', 'p009-p0-fast-20261014-r1', CAMPAIGN,
            'p009-p0-suffix-20261014-r1'))
        ledger = {k:v for k,v in db.items() if k.startswith(prefixes)}
        dump(OUT/'ledger.json', ledger)
        expected = {prefixes[2]+'campaign': sent['plan']}
        actual = {k:v for k,v in ledger.items() if k.startswith(prefixes[2:])}
        if actual != expected:
            raise ValueError('Expected registration only; any claim/terminal/unit/other record blocks zero-work finding')
        if ledger.get(prefixes[1]+'continuation/p0_fast_pair') is not None:
            raise ValueError('Unexpected claimed successor')
        vol = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        absent = {}
        for campaign in (CAMPAIGN, 'p009-p0-suffix-20261014-r1'):
            try:
                entries = list(vol.iterdir('/'+campaign, recursive=True))
            except NotFoundError:
                absent[campaign] = dict(status='NotFoundError', confirmed_absent=True)
            else:
                raise ValueError('Any prior directory or partial evidence blocks zero-work reconciliation')
        dump(OUT/'VOLUME_ABSENCE.json', absent)
        after = provider(apps)
        validate_stopped_apps(apps, after['original_app_info'], after['owned_containers'])
        dump(OUT/'PROVIDER_AFTER.json', after)
        dump(OUT/'ZERO_WORK_VERIFIED.json', dict(utc=datetime.now(timezone.utc).isoformat(),
            original_call_failed=True, original_call_id=submitted['call_id'],
            original_app_id=sent['provider_app_id'], original_error=error,
            actual_campaign_records=actual, claims=0, terminals=0, unit_intents=0,
            new_outputs=0, unknown_generation=0, model_loaded=False,
            volume_absent=True, all_original_apps_stopped=True,
            original_256_untouched=True, no_remote_writes=True,
            plan_registration_is_not_a_claim=True, failed_terminal_fabricated=False,
            ledger_sha256=sha(OUT/'ledger.json'), runtime_admission=False,
            new_execution_requires_exact_review=True))
        dump(OUT/'MANIFEST.json', manifest(OUT))
        print('Original pre-claim failure reconciled: registered plan only; zero claim/unit/output, STOPPED0.')
    except BaseException as exc:
        dump(OUT/'READ_FAILURE.json', dict(type=type(exc).__name__, error=str(exc),
             traceback=traceback.format_exc(), retry_authorized=False))
        raise

if __name__ == '__main__':
    timer = threading.Timer(1200, lambda: os._exit(124)); timer.daemon=True; timer.start()
    try:
        main()
    finally:
        timer.cancel()
