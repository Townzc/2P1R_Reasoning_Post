"""Read post-cleanup inventory and apply 84404ebe R-1 without billing changes."""
import datetime
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo
import zipfile
import modal
from cleanup_old_weights import AUTH, LOCAL, PUB, VOLUME, read, sha, utc, write


def main():
    assert os.environ['MODAL_PROFILE'] == 'tangzhice'
    receipt = read(PUB / 'DELETION_RECEIPT.json')
    assert receipt['complete'] and receipt['removed_paths_exactly_manifest']
    old = read(LOCAL / 'after.json')
    volumes = json.loads(subprocess.check_output(['.local/midpoint_20261011/venv/bin/modal', 'volume', 'list', '--json'], text=True))
    assert {v['name'] for v in volumes} == {VOLUME, 'p012-g0-assets-results-20261111'}
    p012 = modal.Volume.from_name('p012-g0-assets-results-20261111', create_if_missing=False)
    files = [{'path': e.path, 'type': int(e.type), 'bytes': e.size, 'mtime': e.mtime}
             for e in p012.iterdir('/', recursive=True)]
    inv = {'utc': utc(), 'volumes': [{'name': VOLUME, 'listing_utc': old['utc'], 'files': old['files']},
                                    {'name': 'p012-g0-assets-results-20261111', 'listing_utc': utc(), 'files': files}]}
    write(LOCAL / 'workspace_after.json', inv)
    sizes = {v['name']: sum(f['bytes'] for f in v['files'] if f['type'] == 1) / 2**30 for v in inv['volumes']}
    cells = read(Path('reports/p012_20261111/amendment8_modal_review_v1/CANDIDATE_MANIFEST.json'))['cells']
    assert len(cells) == 22
    current_checkpoints = {}
    for f in files:
        parts = f['path'].split('/')
        if f['type'] == 1 and len(parts) > 3 and parts[0] == 'training' and parts[2] == 'checkpoint':
            current_checkpoints[parts[1]] = current_checkpoints.get(parts[1], 0) + f['bytes']
    # The identical main-grid export path has no optimizer states and its largest
    # measured complete checkpoint is below 6 GiB. Reserve 6 GiB for every A8 cell.
    comparable = {k: b for k, b in current_checkpoints.items()
                  if k.startswith(('qwen_', 'llama_', 'a5_', 'a8_'))}
    assert comparable and max(comparable.values()) / 2**30 < 6
    planned = []
    for cell in cells:
        existing = current_checkpoints.get(cell['run_id'], 0) / 2**30
        planned.append({'run_id': cell['run_id'], 'model': cell['model'],
                        'checkpoint_upper_GiB': 6, 'checkpoint_already_in_V_GiB': existing,
                        'remaining_upper_GiB': max(0, 6 - existing)})
    v = sum(sizes.values())
    future = sum(p['remaining_upper_GiB'] for p in planned)
    vp = v + future + 1  # Additional 1 GiB for future inputs/logs and small export metadata.
    now = datetime.datetime.now(datetime.timezone.utc)
    days = (datetime.date(2026, 11, 24) - now.astimezone(ZoneInfo('America/Los_Angeles')).date()).days
    daily = max(0, vp - 1024) * .09 / 30
    completed = datetime.datetime.fromisoformat(receipt['completed_utc'])
    first_day = completed.date() + datetime.timedelta(days=1)
    result = {'utc': utc(), 'authority_commit': AUTH, 'workspace': 'tangzhice',
              'cleanup_complete': True, 'inventory_verified': True,
              'cleanup_receipt_sha256': sha((PUB / 'DELETION_RECEIPT.json').read_bytes()),
              'workspace_inventory_sha256': sha((LOCAL / 'workspace_after.json').read_bytes()),
              'volume_GiB': sizes, 'post_cleanup_total_GiB': v,
              'all_22_A8_checkpoints': planned, 'remaining_checkpoint_upper_GiB': future,
              'future_non_checkpoint_allowance_GiB': 1, 'V_prime_GiB': vp,
              'already_written_checkpoints_included_once': True,
              'all_A8_weights_assumed_retained': True,
              'largest_observed_same_recipe_checkpoint_GiB': max(comparable.values()) / 2**30,
              'included_GiB': 1024, 'monthly_usd_per_GiB': .09, 'month_days_divisor': 30,
              'expected_daily_net_usd': daily, 'days_to_Nov24': days,
              'fixed_billing_lag_reserve_usd': 1, 'storage_plus_lag_reserve_usd': daily * days + 1,
              'official_pricing': {'url': 'https://modal.com/pricing',
                  'verified_UTC': '2026-11-15T05:34:04.582765+00:00',
                  'published_rate_usd_per_GiB_month': .09, 'published_included_TiB_month': 1,
                  'verification': 'Official Modal pricing page, volume storage entry; independently agrees with usage readings.'},
              'first_full_UTC_day_guard': {'UTC_day': first_day.isoformat(),
                  'available_after_UTC_date': (first_day + datetime.timedelta(days=1)).isoformat(),
                  'expected_net_usd': daily, 'stop_new_admissions_if_actual_exceeds_expected_by_usd': .10,
                  'status': 'not_yet_complete; read authenticated usage UI or provider API once closed'},
              'partial_2026_11_15_UTC_day': {'expected_upper_usd': .46, 'full_day_guard_applies': False},
              'account_or_billing_settings_changed': False}
    write(PUB / 'STORAGE_RESERVE.json', result)
    with zipfile.ZipFile(PUB / 'WORKSPACE_AFTER_INVENTORY.zip', 'x', zipfile.ZIP_DEFLATED) as z:
        z.write(LOCAL / 'workspace_after.json', 'workspace_after.json')
    print(json.dumps({k: result[k] for k in ('post_cleanup_total_GiB', 'V_prime_GiB',
                                            'expected_daily_net_usd', 'storage_plus_lag_reserve_usd')}))


if __name__ == '__main__':
    main()
