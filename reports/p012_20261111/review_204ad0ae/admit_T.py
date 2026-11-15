"""Reserve exactly the four b24f787a requests released by204ad0ae."""
from pathlib import Path
import copy
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys

sys.path.insert(0, '.')
sys.path.insert(0, '.local/p012_20261111/amendment7_v1')
from a7_ops import lock, publish
from current_budget import accounting, enforce
from experiments.p012.training_config import grid_dose

R = Path('reports/p012_20261111')
L = Path('.local/p012_20261111')
SOURCE = R / 'amendment8_tinker_review_v1'
OUT = R / 'amendment8_T_admission_v1'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())
write = lambda p, x: Path(p).write_text(json.dumps(x, indent=2) + '\n')
ACCEPTED = 'b24f787a4c92eab9993eb03702df161a6c64c989'
RELEASE = '204ad0ae932f90579cc285ff41483e6b295007a4'


def main():
    manifest = read(SOURCE / 'CANDIDATE_MANIFEST.json')
    storage = read(R / 'review_204ad0ae/STORAGE_API_CHECK.json')
    assert storage['admitted'] and storage['paid_storage_verified_by_api']
    assert datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(storage['observed_utc']) < datetime.timedelta(minutes=20)
    assert read(R / 'review_204ad0ae/ACCEPTANCE.json')['T_released_by_A_verdict']
    actual_hash = sha('experiments/p012/training_config.py')
    assert actual_hash == manifest['base_training_config_sha256']
    assert sha('experiments/p012/tinker_lora.py') == manifest['runner_source_sha256']
    candidate_path = SOURCE / 'candidate/training_config.py'
    assert sha(candidate_path) == manifest['candidate_training_config_sha256']
    spec = importlib.util.spec_from_file_location('a8_accepted_config', candidate_path)
    candidate = importlib.util.module_from_spec(spec); spec.loader.exec_module(candidate)
    prepared = []
    for row in manifest['rows']:
        original = SOURCE / 'requests' / (row['run_id'] + '.json')
        assert sha(original) == row['request_sha256']
        request = read(original)
        assert request['dose'] == candidate.grid_dose(request['cell']) == row['dose']
        if not row['run_id'].startswith('a8_t02_'):
            assert grid_dose(request['cell']) == request['dose']
        assert sha(request['dataset']['path']) == request['dataset']['sha256'] == row['dataset_sha256']
        assert len(Path(request['dataset']['path']).read_text().splitlines()) == row['dataset_rows']
        assert abs(row['training_buffered_usd'] - (row['training_input_tokens'] * request['prices_per_million']['train']/1e6*1.25 + .1)) < 1e-9
        assert request['seed'] == 17 and request['rank'] == 32
        prepared.append((row, request))
    with lock('BUDGET_ADMISSION.lock'):
        assert not OUT.exists(), 'Refuse duplicate admission'
        before = accounting(); enforce(before)
        total = sum(row['forecast_usd'] for row, _ in prepared)
        assert total == manifest['total_forecast_usd'] and total <= 40
        assert before['A8_accounted_and_reserved_usd'] == 0
        assert before['combined_reserved_usd'] + total <= 485
        OUT.mkdir(); (OUT / 'requests').mkdir()
        code_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'accepted_source_review_commit': ACCEPTED, 'A_result_release_commit': RELEASE,
            'prediction_commit': manifest['authority_commit'], 'admitted': True,
            'base_budget': before, 'A8_forecast_usd': total, 'A8_cap_usd': 40,
            'combined_after_admission_usd': before['combined_reserved_usd'] + total, 'combined_cap_usd': 485,
            'global_storage_reserve_usd_already_in_original_T': 30,
            'storage_read': {'path': str(R / 'review_204ad0ae/STORAGE_API_CHECK.json'),
                             'sha256': sha(R / 'review_204ad0ae/STORAGE_API_CHECK.json')},
            'arms': [{k: row[k] for k in ('run_id', 'training_buffered_usd', 'reserved_greedy_usd', 'forecast_usd')}
                     for row, _ in prepared],
            'source_at_admission': {'code_commit': code_commit, 'training_config_sha256': actual_hash,
                                    'tinker_lora_sha256': manifest['runner_source_sha256']},
            'R1_timing': 'T01/T03/T04 use61163c22 now; T02 uses845af084 after B/C completes',
            'no_new_experiments': True, 'automatic_retries': False}
        write(OUT / 'ADMISSION.json', record)
        for row, original in prepared:
            request = copy.deepcopy(original)
            request.update(accepted_review_commit=ACCEPTED, A_result_release_commit=RELEASE,
                authority='Owner-approved A8; b24f787a source and204ad0ae release', code_commit=code_commit,
                prediction_binding=row['prediction'],
                execution_training_config_sha256=manifest['candidate_training_config_sha256']
                if row['run_id'].startswith('a8_t02_') else actual_hash)
            request['forecast'].update(admitted=True, admission_file=str(OUT / 'ADMISSION.json'),
                admission_sha256=sha(OUT / 'ADMISSION.json'))
            directory = L / 'amendment8_tinker_runs_v1' / row['run_id']
            directory.mkdir(parents=True, exist_ok=False)
            write(directory / 'request.json', request)
            write(OUT / 'requests' / (directory.name + '.json'), request)
        (L / 'amendment8_tinker_v1').mkdir(exist_ok=True)
        after = accounting(); enforce(after)
        assert abs(after['combined_reserved_usd'] - record['combined_after_admission_usd']) < 1e-8
        assert abs(after['A8_accounted_and_reserved_usd'] - total) < 1e-8
        write(OUT / 'CHECKS.json', {'utc': record['utc'], 'four_reviewed_request_hashes_match': True,
            'dataset_hashes_rows_and_doses_match': True, 'unchanged_scientific_runner': True,
            'three_arms_compatible_with_live_61163c22': True, 'T02_waits_accepted_patch': True,
            'all_four_reservations_counted_exactly_once': True, 'paid_storage_counted_once': True,
            'combined_budget_includes_A8': True})
        (OUT / 'README.md').write_text(
            '# A8 T group admission\n\n'
            f"Four accepted arms are reserved: ${total:.6f} / $40; combined accounted and reserved "
            f"${record['combined_after_admission_usd']:.6f} / $485. The existing $30 global storage "
            'reserve is included once. Storage admission uses the actual API rate and usage.\n\n'
            'T01, T03 and T04 start with the current 61163c22 configuration. After all B/C calls complete, '
            'the finite controller applies the exact accepted 845af084 candidate, records its commit '
            'and starts T02. Training, generation, scoring and frozen predictions are unchanged. '
            'Greedy evaluations are serialized, with actual costs reconciled between endpoints.\n\n'
            'The canonical combined ledger is review_204ad0ae/current_budget.py. It adds A8 to the '
            'unchanged original T/A6/A7 accounting; historical GSM all_tracks snapshots exclude A8. '
            'All four requests are exploratory and excluded from H0–H3.\n')
        commit = publish([OUT, R / 'review_204ad0ae/admit_T.py'],
            'P012 A8: admit exactly four T arms after accepted source, A verdict and live budget/storage checks')
        print(json.dumps({'commit': commit, 'A8_usd': total, 'combined_usd': after['combined_reserved_usd']}))


if __name__ == '__main__':
    main()
