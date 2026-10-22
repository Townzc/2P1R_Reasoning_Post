"""Publish the completed new census by byte copy; never rescan or retokenize."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import tarfile

R = Path('.local/p011_20261020/r1')
SOURCE = R / 'ot3_full_math_census_r1'
OUT = Path('reports/p011_20261020/ot3_full_math_census_actual_results_v1')
WORK = R / 'ot3_full_math_census_publication_r1'


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def create(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def copy(source, target):
    with Path(source).open('rb') as src, Path(target).open('xb') as dst:
        for block in iter(lambda: src.read(8 * 1024 * 1024), b''):
            dst.write(block)


def main():
    assert not OUT.exists() and not WORK.exists()
    assert not (SOURCE / 'FAILED.json').exists()
    completed = read(SOURCE / 'COMPLETED.json')
    counts = read(SOURCE / 'COUNTS.json')
    canonical = json.dumps(counts, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == completed['counts_sha256']
    exit_receipt = read(R / 'OT3_CENSUS_UNSTARTED_AFTER_METADATA_FIX_CLI_EXIT.json')
    awake_exit = read(R / 'OT3_CENSUS_BOUNDED_AWAKE_EXIT.json')
    assert exit_receipt['exit_code'] == 0
    assert counts['counts']['math_rows'] == 850000 and counts['new_model_calls'] == 0
    spec_path = Path('reports/p011_20261020/ot3_full_math_census_preflight_v1/SPEC.json')
    spec = read(spec_path)
    acceptance = read(R / 'OT3_FULL_MATH_CENSUS_CR_ACCEPTED.json')
    assert acceptance['target_commit'] == '63f54625de8a730779c86e8817ac872a026951d3'
    WORK.mkdir(); OUT.mkdir()
    create(WORK / 'ATTEMPT.json', {'utc': utc(), 'byte_copy_only': True,
        'scientific_aggregation_or_tokenization_repeated': False, 'automatic_retry': False})
    names = ['ATTEMPT.json', 'COUNTS.json', 'PARENT_COUNTS.jsonl', 'COMPLETED.json']
    inventory = {name: {'bytes': (SOURCE / name).stat().st_size, 'sha256': sha(SOURCE / name)}
        for name in names}
    archive = OUT / 'CENSUS_ORIGINAL_OUTPUTS.tar.gz'
    with archive.open('xb') as stream:
        with tarfile.open(fileobj=stream, mode='w:gz', compresslevel=6) as tar:
            for name in names:
                tar.add(SOURCE / name, arcname=name, recursive=False)
    seen = set()
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            assert member.isfile() and member.name in inventory and member.name not in seen
            h = hashlib.sha256(); size = 0
            with tar.extractfile(member) as f:
                for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(block); size += len(block)
            assert {'bytes': size, 'sha256': h.hexdigest()} == inventory[member.name]
            seen.add(member.name)
    assert seen == set(names)
    create(OUT / 'INVENTORY.json', inventory)
    copy(SOURCE / 'COUNTS.json', OUT / 'COUNTS.json')
    copy(SOURCE / 'COMPLETED.json', OUT / 'CENSUS_COMPLETED.json')
    copy(R / 'OT3_CENSUS_UNSTARTED_AFTER_METADATA_FIX.log', OUT / 'ORIGINAL_CENSUS_PROGRESS.log')
    copy(Path(__file__), OUT / 'PUBLISHER.py')
    flags = [
        'fixed_full_math_census_outputs_and_pinned_source_provenance_accepted',
        'A_group_literal_normalized_counts_and_strict_relaxed_pools_distinguished',
        'answer_only_lengths_dispersion_overlap_and_K1_one_pass_tokens_not_training_dose_accepted',
        'independent_review_scope_and_private_raw_access_limits_explicit',
        'no_old_science_repeated_and_no_new_training_authorization',
    ]
    binding = {'source_target': acceptance['target_commit'], 'source_spec_path': str(spec_path),
        'source_spec_sha256': acceptance['spec_sha256'],
        'source_review_commit': acceptance['report_commit'],
        'source_review_sha256': acceptance['report_sha256'],
        'source_acceptance_packet': 'reports/p011_20261020/review_8125afea_census_PASS_forced_v2_STOP_v1',
        'dataset': spec['dataset'], 'dataset_revision': spec['dataset_revision'],
        'original_metadata_bindings': spec['original_metadata_bindings'],
        'original_readonly_raw_index_bytes': spec['raw_index_bytes'],
        'raw_index_or_parquet_archived_or_rehashed_by_publisher': False,
        'original_benchmark_binding': spec['benchmark_binding'],
        'tokenizer_files_binding': spec['tokenizer_files'],
        'counts_file_sha256': inventory['COUNTS.json']['sha256'],
        'counts_canonical_json_sha256': completed['counts_sha256'],
        'parent_counts_file_sha256': inventory['PARENT_COUNTS.jsonl']['sha256'],
        'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
        'archive_members': len(names), 'new_archive_full_readback_once': True,
        'producer_cli': 99882, 'original_cli_exit': exit_receipt, 'bounded_awake_exit': awake_exit,
        'earlier_preentry_failure': 'Exact preserved CENSUS_PREENTRY_FAILURE.json in source-acceptance packet; occurred before output/tokenizer/raw read.',
        'actual_review_scope': 'p011-OT3-full-math-pool-census-results-actual-A3',
        'required_result_review_flags': flags, 'actual_A3_accepted': False,
        'review_access_limits': ['New parent summaries use SHA256 identities; original question/answer text and raw SQLite are not republished.',
            'A reviewer must state whether source/text/normalization and eligibility were independently recomputed or only checked against saved summaries.',
            'The publisher only copies saved statistics; it does not recompute aggregates, lengths, overlaps, dispersion or K1 token sums.'],
        'new_model_calls': 0, 'old_training_tokens_reencoded': False,
        'training_selection_or_dose_authorized': False,
        'census_diagnostic_shuffle_not_future_training_selection_authority': True}
    create(OUT / 'ACTUAL_RESULT_BINDING.json', binding)
    with (OUT / 'README.md').open('x') as f:
        f.write('# OT3 full math-pool census — actual review pending\n\n'
            'This packet copies the first completed census of the850,000 math rows from the original pinned local ingestion. '
            'COUNTS.json is unchanged saved output; the archive contains its four original output files, including all parent summaries. '
            'No old raw download/ingestion/training encoding or new model was run by this publisher.\n\n'
            'Original A grouping is NFKC(question).strip(). Literal raw-question and whitespace-removed/casefold counts are separate. '
            'At least one/at least16 eligible and the original exactly16/all16 strict pool must not be conflated. '
            'Completeness is not answer correctness. Answer-only lengths exclude EOS; diagnostic K1 one-pass supervised token totals include EOS. '
            'The saved diagnostic shuffle does not authorize any future training selection, dosage or arm.\n\n'
            'Original raw text/SQLite/private files are not republished. The reviewer must describe actual independent access and recomputation scope, '
            'and cannot infer full independent source verification from parent-summary consistency alone. '
            'The earlier preentry missing-acceptance failure and single infrastructure continuation remain in the exact source-acceptance packet.\n')
    files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(OUT.iterdir())}
    create(OUT / 'MANIFEST.json', {'created_utc': utc(), 'files': files,
        'copy_only_no_new_statistics': True, 'actual_A3_pending': True})
    result = {'completed_utc': utc(), 'packet': str(OUT),
        'manifest_sha256': sha(OUT / 'MANIFEST.json'),
        'actual_result_binding_sha256': sha(OUT / 'ACTUAL_RESULT_BINDING.json'),
        'counts_file_sha256': inventory['COUNTS.json']['sha256'],
        'archive_bytes': archive.stat().st_size, 'members': len(names),
        'payload_files_excluding_manifest': len(files), 'no_scientific_recomputation': True}
    create(WORK / 'COMPLETED.json', result)
    create(R / 'OT3_FULL_CENSUS_ACTUAL_PUBLICATION_DONE.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
