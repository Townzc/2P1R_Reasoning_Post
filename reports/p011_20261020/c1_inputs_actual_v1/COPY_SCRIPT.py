"""Create-only original-byte C1 handoff; no constructor, forward or statistics."""
from pathlib import Path
from datetime import datetime, timezone
import gzip
import hashlib
import json
import subprocess
import tarfile

R = Path('.local/p011_20261020/r1')
P = Path('reports/p011_20261020')
INPUT = R / 'c1_inputs_r1'
REVIEW = P / 'review_d229bb27_C1_source_accepted_v1'
ACTUAL = P / 'c1_inputs_actual_v1'
TIMING = P / 'c1_whole_iteration_timing_preflight_v1'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def dump(p, value):
    with p.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


def manifest(root, name='MANIFEST.json'):
    dump(root / name, {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
        'sha256': sha(p)} for p in sorted(root.rglob('*')) if p.is_file()})


def main():
    if any(p.exists() for p in (REVIEW, ACTUAL, TIMING)):
        raise ValueError('Existing publication; never rerun this builder')
    completed = json.loads((INPUT / 'INPUT_COPY_COMPLETED.json').read_text())
    inventory = json.loads((INPUT / 'TASK_INVENTORY.json').read_text())
    accepted = json.loads((R / 'C1_FULL_PATH_SOURCE_CR_ACCEPTED.json').read_text())
    sessions = json.loads((R / 'CLI_SESSIONS.json').read_text())
    if sessions['c1_input_copy']['state'] != 'EXIT0_CONSUMED':
        raise ValueError('Original copy CLI must be consumed')
    if (INPUT / 'FAILED.json').exists() or completed['tokenizations'] or completed['model_calls']:
        raise ValueError('Only complete zero-tokenization input copy allowed')
    if inventory['unique_sequences'] != 9594 or inventory['journal_chunks'] != 300:
        raise ValueError('Unexpected actual input inventory')
    now = datetime.now(timezone.utc).isoformat()
    dump(R / 'C1_ACTUAL_TIMING_PUBLICATION_ATTEMPT.json', {'utc': now,
        'copy_cli': 94183, 'automatic_retry_allowed': False})
    REVIEW.mkdir(); ACTUAL.mkdir(); TIMING.mkdir()

    report = Path(accepted['local_report_path'])
    (REVIEW / report.name).write_bytes(report.read_bytes())
    projected = dict(accepted)
    projected.pop('local_report_path')
    projected['original_private_acceptance_file_sha256'] = sha(R / 'C1_FULL_PATH_SOURCE_CR_ACCEPTED.json')
    projected['public_report_path'] = report.name
    projected['projection'] = 'Only absolute local_report_path removed; original private SHA retained.'
    dump(REVIEW / 'SOURCE_CR_ACCEPTANCE_PUBLIC.json', projected)
    readproof = report.parent / 'C1_FULL_READ_CONFIRMED.json'
    (REVIEW / readproof.name).write_bytes(readproof.read_bytes())
    (REVIEW / 'README.md').write_text('''# Actual C1 source review — original input copy only

Claude accepted source12 at817f7d67 as PASS-WITH-NOTES and explicitly permitted
one original-byte input copy. This is not actual input A1 or numeric A2-lite,
and does not authorize an upload, worker, GPU or paid call. Exact original report
and acceptance projection preserve the private acceptance SHA.

Git event02:58:04UTC, actual full read03:00:28UTC, and report self-described
around03:05UTC are different observations. The later self-description is kept
as written. Reviewer reported46 test passes and one torch import unavailable;
Codex did not rerun those old tests. Future complete-loop timing repair requires
short exact source review within the same shared request.
''')
    manifest(REVIEW)

    expected = json.loads((INPUT / 'MANIFEST.json').read_text())
    expected['MANIFEST.json'] = {'bytes': (INPUT / 'MANIFEST.json').stat().st_size,
                                'sha256': sha(INPUT / 'MANIFEST.json')}
    for name in expected:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or (INPUT / name).is_symlink():
            raise ValueError('Unsafe original artifact member')
    archive = ACTUAL / 'original_inputs.tar.gz'
    with archive.open('xb') as sink:
        with gzip.GzipFile(filename='', fileobj=sink, mode='wb', compresslevel=6, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w|') as tar:
                for name in sorted(expected):
                    info = tarfile.TarInfo(name); info.size = expected[name]['bytes']
                    info.mode = 0o644; info.mtime = 0
                    with (INPUT / name).open('rb') as f:
                        tar.addfile(info, f)
    observed = {}
    with tarfile.open(archive, mode='r|gz') as tar:
        for item in tar:
            if not item.isfile() or item.name not in expected or item.name in observed:
                raise ValueError('Unexpected archive member; preserve partial output')
            h = hashlib.sha256(); size = 0
            with tar.extractfile(item) as f:
                for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(b); size += len(b)
            observed[item.name] = {'bytes': size, 'sha256': h.hexdigest()}
    if observed != expected:
        raise ValueError('Archive readback differs; never whole-publisher retry')
    for name in ('INPUT_COPY_COMPLETED.json', 'INPUT_FILES.json',
                 'ORIGINAL_GROUP_BINDING.json', 'TASK_INVENTORY.json'):
        (ACTUAL / name).write_bytes((INPUT / name).read_bytes())
    (ACTUAL / 'ORIGINAL_MANIFEST.json').write_bytes((INPUT / 'MANIFEST.json').read_bytes())
    (ACTUAL / 'COPY_SCRIPT.py').write_bytes(Path(__file__).read_bytes())
    dump(ACTUAL / 'ARCHIVE_READBACK.json', {'archive': archive.name,
        'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
        'original_members': observed, 'original_member_count': len(observed),
        'all_original_bytes_equal': True, 'tokenizations': 0, 'model_calls': 0,
        'input_copy_executed_once': True, 'original_copy_cli': 94183,
        'source_acceptance_packet': str(REVIEW), 'actual_A1_accepted': False})
    dump(ACTUAL / 'SUMMARY.json', {'written_utc': now, 'copy_completed_utc': completed['utc'],
        'inventory': inventory, 'original_file_count': 18,
        'original_file_bytes': sum(v['bytes'] for v in completed['files'].values()),
        'source_target_used_for_copy': accepted['target_commit'],
        'source_files_used_for_copy': completed['source_files'],
        'original_private_acceptance_file_sha256': sha(R / 'C1_FULL_PATH_SOURCE_CR_ACCEPTED.json'),
        'actual_A1_accepted': False, 'numeric_A2_lite_accepted': False, 'paid_admitted': False})
    (ACTUAL / 'README.md').write_text('''# C1 actual original inputs — A1 pending

One approved copy completed at03:00:37.611207UTC. It reused eighteen original
config/rows/encoded files without tokenization, model loading, forward passes,
generation, scoring or training. Six original teacher/count memberships remain;
only identical input_ids and labels are shared:9,594 unique sequences,300 journal
chunks,5,214,325 input tokens and4,589,326 supervised tokens; maximum length1,758.
These counts are copied from the original constructor inventory, not recomputed.

original_inputs.tar.gz preserves all22 original manifest members plus the
original MANIFEST itself (23 files). One readback matched each byte count/SHA.
ORIGINAL_MANIFEST is the unchanged constructor inventory; PUBLIC_MANIFEST is the
new public packet inventory. The archive contains exact original group files.
Source acceptance authorized this copy under817f7d67; the subsequent timing-only
runtime repair does not repeat or alter it. Actual input A1 and numerical runtime
admission remain pending in the single C1 shared request. No output is an NLL result.
''')
    manifest(ACTUAL, 'PUBLIC_MANIFEST.json')

    old = json.loads((P / 'c1_full_path_window_addendum_v1/SOURCE_BINDING.json').read_text())
    sources = dict(old['source_files'])
    sources['experiments/p011/c1_execution.py'] = sha('experiments/p011/c1_execution.py')
    dump(TIMING / 'SOURCE_BINDING.json', {'source_files': sources, 'source_count': 12,
        'changed_source_files': ['experiments/p011/c1_execution.py'],
        'unchanged_source11_from_accepted_target': accepted['target_commit'],
        'old_execution_sha256': old['source_files']['experiments/p011/c1_execution.py'],
        'source_review_report_sha256': accepted['report_sha256'],
        'actual_input_public_manifest_sha256': sha(ACTUAL / 'PUBLIC_MANIFEST.json'),
        'actual_input_inventory_sha256': expected['TASK_INVENTORY.json']['sha256'],
        'original_group_binding_sha256': accepted['original_group_binding_sha256'],
        'new_tests': {'tests/test_p011_c1_whole_iteration_timing.py': sha('tests/test_p011_c1_whole_iteration_timing.py')},
        'new_check_count': 4, 'new_check_seconds': .036, 'old_tests_rerun': False,
        'actual_spec_selected': False, 'actual_timing_basis_selected': False,
        'new_paid_calls': 0, 'new_reserved_usd': 0})
    (TIMING / 'NEW_CHECKS.log').write_bytes((R / 'c1_whole_iteration_new_checks_r1.log').read_bytes())
    (TIMING / 'SOURCE_DIFF.patch').write_bytes(subprocess.check_output(
        ['git', 'diff', '--', 'experiments/p011/c1_execution.py']))
    dump(TIMING / 'REVIEW_REQUIREMENTS.json', {
        'shared_request': 'p011-C1-complete-path-CR-A1-A2-lite-r1',
        'source_scope': 'p011-C1-complete-path-CR',
        'required_explicit_source_conclusions': {
            'whole_chunk_iteration_includes_all_three_commits': True,
            'remote_chunk_done_included': True,
            'next_forecast_and_readonly_replay_use_same_complete_cycle': True,
            'final_proof_summary_commit_excluded_and_future_allowance_disclosed': True,
            'input_byte_copy_not_repeated': True,
            'old_body_only_timing_basis_rejected': True},
        'actual_A1_numeric_A2_remain_separate': True,
        'real_measured_or_explicitly_accepted_prior_proxy_basis_still_required': True,
        'no_paid_measurement_exception_given': True})
    (TIMING / 'README.md').write_text('''# C1 complete-iteration timing correction — short exact CR pending

Claude N1 identified two excluded volume commits in each old chunk timing.
The worker now starts its timer at loop entry and ends after all three commits
and remote chunk_done. The next forecast uses that complete interval. A separate
COMPLETE_ITERATION_TIMES file preserves intervals and old body-only ack values;
the readonly checker verifies and replays the same full intervals. The final
proof/summary persistence is explicitly outside each chunk and remains within
the numerical future allowance; no recursive timing claim is made.

validate_spec now rejects missing/false whole_chunk_iteration_timing. The prior
source acceptance does not authorize this new runtime. A real timing basis for
batch1 forwards, FP32 loss, all commits and fixed overhead is still absent.
Old training durations are not direct C1 measurements; reviewer estimates and
synthetic fixtures are not selected actual caps or numerical acceptance.

Four new synthetic/mocked-body tests passed once in0.036s: all commits reach the
next forecast and read-only replay; old timing basis rejected; body-only duration
substitution rejected; timing-scope tampering rejected. Existing successful tests
were not rerun. No corpus was re-encoded and no actual model/forward was invoked.
The original approved input copy completed before this source edit. Eleven other
source files and all scientific token/mask/NLL definitions remain unchanged.

Review this bounded correction and the actual input A1 within the SAME C1 shared
request. Final numeric A2-lite must still bind the actual spec, timing, input,
source and original limits before upload or dispatch. No new independent gate.
''')
    manifest(TIMING)
    dump(R / 'C1_ACTUAL_TIMING_PUBLICATION_DONE.json', {'utc': datetime.now(timezone.utc).isoformat(),
        'packets': [str(REVIEW), str(ACTUAL), str(TIMING)],
        'archive_bytes': archive.stat().st_size, 'archive_members': len(observed),
        'input_constructor_repeated': False, 'new_model_calls': 0})
    print(json.dumps({'packets': [str(REVIEW), str(ACTUAL), str(TIMING)],
        'archive_bytes': archive.stat().st_size, 'archive_members': len(observed)}), flush=True)


if __name__ == '__main__':
    main()
