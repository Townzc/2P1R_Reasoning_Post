"""One fresh optional-admission cost snapshot; no models or old expense replay."""
import argparse
from pathlib import Path
import json
import subprocess
import time
from experiments.p011 import long_owner_path as original, owner_epoch_accounting as accounting
from experiments.sft_allocation_midpoint.common import read, dump, sha
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    folder = ROOT / args.directory
    folder.relative_to(ROOT / original.LOCAL)
    folder.mkdir(parents=True, exist_ok=False)
    cli = str(ROOT / '.local/midpoint_20261011/venv/bin/modal')
    receipts = []
    for name, tail in (('rates', ['rates']), ('report', ['report', '--for', 'this month', '--tag-names', 'app_id,app_name'])):
        started = time.time()
        result = subprocess.run([cli, 'billing', *tail, '--json'], text=True,
                                capture_output=True, timeout=60)
        (folder / (name + '.json')).write_text(result.stdout)
        (folder / (name + '.stderr')).write_text(result.stderr)
        receipts.append(dict(name=name, started_epoch=started, observed_epoch=time.time(), exit=result.returncode))
        if result.returncode:
            dump(folder / 'FAILED.json', dict(receipts=receipts, original_outputs_retained=True))
            raise RuntimeError('Fresh billing read failed; retain partial snapshot')
    dump(folder / 'READ_RECEIPT.json', receipts)
    records = accounting.snapshots(ROOT)
    apps = {r['app_id'] for r in records}
    rates_file = str((folder / 'rates.json').relative_to(ROOT))
    report_file = str((folder / 'report.json').relative_to(ROOT))
    spec = read(ROOT / original.SPEC)
    value = dict(observed_epoch=min(x['started_epoch'] for x in receipts),
        owner_amendment_sha256=spec['owner_amendment_sha256'],
        rates_file=rates_file, meter_report_file=report_file,
        rates=read(folder / 'rates.json'),
        new_epoch_app_observed_charges_usd=accounting.observed_charges(read(folder / 'report.json'), apps),
        source_evidence_files={str(p.relative_to(ROOT)):sha(p) for p in (
            folder / 'rates.json', folder / 'report.json', folder / 'READ_RECEIPT.json')},
        delayed_meter_not_final_invoice=True, missing_app_meter_is_unknown_not_zero=True,
        completed_duration_bound_not_expense=True, old_failed_reservations_excluded=True)
    dump(folder / 'BUDGET.json', value)
    print(str(folder / 'BUDGET.json'), flush=True)


if __name__ == '__main__':
    main()
