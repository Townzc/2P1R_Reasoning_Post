"""Publish only new extension results; never run scientific computations."""
from pathlib import Path
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import tarfile

R = Path('.local/p011_20261020/r1')
BASE = R / 'ext3b_runs_r1'
LOCAL = BASE / 'local_endpoint_links_r1'
OUT = Path('reports/p011_20261020/ext3b_complete_actual_results_v1')
SAVE = R / 'ext3b_actual_results_publication_r1'
JOBS = ['long_R9072x1_S-F15_s17', 'long_R3024xE3_S-F15_s17']


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def put(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def utc():
    return datetime.now(timezone.utc).isoformat()


assert not OUT.exists() and not SAVE.exists()
analysis = read(LOCAL / 'analysis/COMPLETED.json')
assert analysis['contrast'] == 'LARGE_minus_SMALL'
assert analysis['bootstrap_draws'] == 10000 and analysis['bootstrap_seed'] == 20261021
cost = read(R / 'ext3b_terminal_cost_reconciliation_r1/COMPLETED.json')
acceptance = read(R / 'EXT3B_LOCAL_ENDPOINT_LINKS_CR_ACCEPTED.json')
assert acceptance['decision'] == 'PASS'
members, excluded, bindings, results = {}, {}, {}, {}


def add(name, file):
    file = Path(file)
    assert name not in members and file.is_file() and not file.is_symlink(), name
    members[name] = file


for job in JOBS:
    attempt = job + '_attempt1'
    audit = LOCAL / 'audit' / attempt
    score = LOCAL / 'score' / attempt
    collect = BASE / 'collect' / attempt
    dispatch = BASE / 'dispatch' / attempt
    proof = read(audit / 'COMPLETE_PROOF.json')
    scored = read(score / 'COMPLETED.json')
    receipt = read(collect / 'ORIGINAL_RESULT.json')
    provider = read(collect / 'PROVIDER_STOPPED0.json')
    intent = read(dispatch / 'INTENT.json')
    assert receipt['status'] == 'completed' and proof['passed']
    assert proof['training']['targets'] == 123808531 and proof['training']['updates'] == 1935
    assert proof['endpoint']['outputs_decoded'] == 2500
    assert scored['saved_score_proof']['passed'] and scored['saved_score_proof']['outputs'] == 2500
    assert provider['state'] == 'stopped' and provider['owned_containers'] == 0
    assert not (audit / 'FAILED.json').exists() and not (score / 'FAILED.json').exists()
    payload = Path(read(audit / 'PAYLOAD_REFERENCE.json')['path'])
    original_inventory = read(payload / 'EVIDENCE_MEMBERS.json')
    for file in sorted(payload.rglob('*')):
        if not file.is_file():
            continue
        rel = file.relative_to(payload).as_posix()
        name = attempt + '/runtime/' + rel
        if rel == 'ADMISSION.json' or rel.startswith('model_for_vllm/') or file.suffix in ('.pt', '.bin', '.safetensors'):
            excluded[name] = {'original_saved_inventory': original_inventory.get(rel),
                             'binary_or_accounting_bytes_not_reread': True}
        else:
            add(name, file)
    for name in ['ATTEMPT.json', 'COMPLETE_PROOF.json', 'DECODED.json', 'SCORING_ROWS.json', 'PAYLOAD_REFERENCE.json']:
        add(attempt + '/audit/' + name, audit / name)
    for name in ['ATTEMPT.json', 'COMPLETED.json', 'PROVIDER_STOPPED0.json', 'ORIGINAL_RESULT.json']:
        add(attempt + '/collect/' + name, collect / name)
    for file in sorted(score.rglob('*')):
        if file.is_file():
            add(attempt + '/score/' + file.relative_to(score).as_posix(), file)
    add(attempt + '/dispatch/SUBMITTED.json', dispatch / 'SUBMITTED.json')
    bindings[job] = {'attempt': attempt, 'job_sha256': proof['job_sha256'],
        'original_result_sha256': sha(dispatch / 'RESULT.json'),
        'oracle_sha256': sha(audit / 'COMPLETE_PROOF.json'),
        'score_sha256': sha(score / 'COMPLETED.json'),
        'collect_sha256': sha(collect / 'COMPLETED.json'),
        'provider_sha256': sha(collect / 'PROVIDER_STOPPED0.json'),
        'private_intent_sha256': sha(dispatch / 'INTENT.json'),
        'original_worker_artifact': receipt['artifact'],
        'actual_worker_source_files': intent['source_files'],
        'local_closeout_spec_sha256': proof['new_local_closeout_spec_sha256'],
        'first_failed_prefix_reused': proof['failed_pre_science_prefix_reused'],
        'private_binary_external_access_claimed': False}
    results[job] = {'attempt': attempt, 'questions': intent['job_spec']['questions'],
        'B': 123808531, 'U': 1935, 'single_training_seed': 17,
        'saved_score_proof': scored['saved_score_proof'],
        'original_worker_completed': True, 'actual_A3_accepted': False}
for file in sorted((LOCAL / 'analysis').iterdir()):
    if file.is_file():
        add('analysis/' + file.name, file)

OUT.mkdir()
SAVE.mkdir()
put(SAVE / 'ATTEMPT.json', {'utc': utc(), 'once_only': True, 'scientific_operations': 0})
archive = SAVE / 'original_scientific_bytes.tar.gz'
inventory = {}
with archive.open('xb') as stream:
    with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w|') as tar:
            for name, file in sorted(members.items()):
                raw = file.read_bytes()
                inventory[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                                   'original_file': str(file)}
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode = len(raw), 0, 0o644
                tar.addfile(info, io.BytesIO(raw))
seen = set()
with tarfile.open(archive, 'r:gz') as tar:
    for item in tar:
        raw = tar.extractfile(item).read()
        assert item.name not in seen
        assert len(raw) == inventory[item.name]['bytes']
        assert hashlib.sha256(raw).hexdigest() == inventory[item.name]['sha256']
        seen.add(item.name)
assert seen == set(inventory)
parts = []
archive_hash = hashlib.sha256()
with archive.open('rb') as stream:
    while True:
        raw = stream.read(40 * 1024 * 1024)
        if not raw:
            break
        archive_hash.update(raw)
        name = f'original_scientific_bytes.tar.gz.part{len(parts):03d}'
        with (OUT / name).open('xb') as target:
            target.write(raw)
        parts.append({'file': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
put(OUT / 'ARCHIVE_INVENTORY.json', inventory)
put(OUT / 'ARCHIVE_READBACK.json', {'utc': utc(), 'archive_bytes': archive.stat().st_size,
    'archive_sha256': archive_hash.hexdigest(), 'parts': parts, 'members': len(inventory),
    'every_new_member_read_back_once': True, 'private_exclusions': excluded,
    'original_large_collect_archive_not_reverified': True,
    'original_small_collect_archive_not_reverified': True,
    'no_old_science_or_scoring_or_bootstrap_repeated': True})
put(OUT / 'SAVED_SCORES_AND_CONTRASTS.json', {'cells': results,
    'matched_dose_comparison': analysis, 'actual_A3_accepted': False,
    'no_new_statistics_computed_by_publisher': True})
flags = [
    'exact_two_original_attempts_matched_B123808531_U1935_and_source87_local89_accepted',
    'independent5000_native_token_decode_text_region_stop_and_correctness_coverage_disclosed',
    'original_frozen_scores_and_two_LARGE_minus_SMALL_paired10000_seed20261021_contrasts_accepted',
    'original_preentry_failures_local_failed_prefix_and_once_only_continuation_preserved',
    'MATH_only_AIME_AMC_NOT_RUN_no_missing_zero_or_unregistered_A7_contrast_accepted',
    'single_training_seed_private_binary_full_symbolic_engine_and_original_window_limits_disclosed',
    'exact_four_app_terminal_cost_projection_not_final_invoice_or_budget_release_disclosed']
put(OUT / 'ACTUAL_RESULT_BINDING.json', {'scope': 'p011-ext-3B-complete-original-results-actual-A3',
    'actual_evidence': bindings, 'required_true_flags': flags, 'actual_A3_accepted': False,
    'source_target': '63523da98cb0325c6a5956d05c251fda6cb0500b',
    'local_correction_target': 'ebfea411bb02b06b09048e182d90ff1a9511f110',
    'actual_input_target': '5f1003c5f459ed3f4f1780decae49e2141a37d1a',
    'actual_job_manifest_sha256': 'bf556ba4e18ab52b6613d6e86eec207ec6dedab9937accb2b754f94368453a24',
    'input_manifest_sha256': 'afd5fe1bd7e13d28353d28fe4e7b6e2e296babcbc7752dc5cec843bdb7d17bfc'})
put(OUT / 'EXISTING_EVIDENCE_REFERENCES.json', {
    'actual_inputs': {'commit': '5f1003c5f459ed3f4f1780decae49e2141a37d1a',
                     'packet': 'reports/p011_20261020/ext3b_actual_inputs_v1'},
    'preentry_failures': {'commit': '63523da98cb0325c6a5956d05c251fda6cb0500b',
                         'packet': 'reports/p011_20261020/ext3b_preentry_schema_failures_v1'},
    'local_failed_prefix': {'commit': 'ebfea411bb02b06b09048e182d90ff1a9511f110',
                           'packet': 'reports/p011_20261020/ext3b_local_endpoint_links_preflight_v1'},
    'exact_local_source_acceptance': {'commit': 'c32525d13518e3d9ce8afa51d794b5c77322ff4b',
                                    'packet': 'reports/p011_20261020/review_0ebb26a4_ext3b_local_links_accepted_v1'},
    'old_large_input_archive_and_all_other_closed_science_republished': False})
put(OUT / 'TERMINAL_COST_PUBLIC_PROJECTION.json', cost)
with (OUT / 'PREPARED_PUBLISHER.py').open('xb') as target:
    target.write(Path(__file__).read_bytes())
(OUT / 'README.md').write_text('''# Matched-dose 3B extension: actual A3 pending

The separately authorized comparison is 9,072 questions once versus the first 3,024 questions approximately three times. Both original completed workers used 123,808,531 supervised tokens including EOS and 1,935 updates. Each produced MATH-500 greedy500 and four sampled500 endpoints, totaling5,000 original outputs. AIME24/AIME25/AMC23 are NOT_RUN; missing values are not zeros. The two fixed contrasts are LARGE minus SMALL, using the original question bootstrap with10,000 draws and seed20261021. A7 has a different pool; no A7 contrast is added.

This packet copies only these new raw tokens, original runtime metadata, first full local state/optimizer/RNG/trajectory/native proofs, first frozen scores and first two contrasts. It does not run science. The two preentry schema failures and the large pre-science symlink audit failure remain recorded in fixed referenced packets. The reviewed local continuation reuses only the already passed large prefix; the small cell received its first full oracle. No model or completed scientific stage was repeated. The original absolute result windows and score caps remain.

Private full checkpoints, export weights and admission accounting are excluded using their saved inventories, without rereading the binaries for publication. Source PASS is not actual-results A3. Independent review must state actual5,000-output decoding/correctness coverage and its private-binary/full-symbolic-engine access limits. Frozen labels and vectors remain unchanged. The bootstrap concerns sampled questions, not a training-seed population; the training seed is17. Course interpretation belongs to the owner.

Concatenate the numbered parts in lexical order for the new gzip archive. ARCHIVE_INVENTORY binds every member; ARCHIVE_READBACK records one complete readback. Existing input/asset/source/failure evidence is referenced, not republished. Terminal charges concern only the four exact extension apps and are delayed tagged observations, not a final invoice or a release of any budget. Other original owner150 and forced12 scopes are not reconciled again.
''')
manifest = {file.name: {'bytes': file.stat().st_size, 'sha256': sha(file)}
            for file in sorted(OUT.iterdir()) if file.is_file()}
put(OUT / 'MANIFEST.json', manifest)
put(R / 'EXT3B_ACTUAL_RESULTS_PUBLICATION_DONE.json', {'finished_utc': utc(),
    'packet': str(OUT), 'members': len(inventory), 'archive_bytes': archive.stat().st_size,
    'parts': len(parts), 'manifest_sha256': sha(OUT / 'MANIFEST.json'),
    'binding_sha256': sha(OUT / 'ACTUAL_RESULT_BINDING.json'),
    'actual_A3_pending': True, 'never_repeat': True})
print(json.dumps(read(R / 'EXT3B_ACTUAL_RESULTS_PUBLICATION_DONE.json')), flush=True)
