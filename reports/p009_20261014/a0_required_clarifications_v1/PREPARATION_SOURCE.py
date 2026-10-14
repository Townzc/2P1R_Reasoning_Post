"""Once-only local source supplement; no cloud calls or model generation."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

from transformers import AutoTokenizer
import transformers
from experiments.sft_allocation_midpoint.common import dump, manifest, read, sha
from src.sft_data import prefix, read_jsonl

root = Path('.local/p009_20261014/r1')
out = Path('reports/p009_20261014/a0_required_clarifications_v1')
if out.exists():
    raise FileExistsError('Create-only; preserve partial output and reconcile, do not repeat')
original = Path('reports/p009_20261014/design_and_inputs_v1')
assets = root / 'source_assets_r1'
inputs = root / 'stage0_inputs_r1'
review = root / 'review_e1d8d469'
expected_report = '7641217c0a16df13b636c0e39c645a5dfd5118e388f70b6c73580fa1b00b14ed'
if sha(review / 'REPORT.md') != expected_report:
    raise ValueError('Original report differs')
spec = read('reports/p009_20261014/p0_runtime_preflight_v1/ADMISSION.json')
for path, expected in spec['source_files'].items():
    if sha(path) != expected:
        raise ValueError('Pending exact P0 source changed')

# New requested BOS diagnostic. No weights, generation, scoring, or prior oracle.
tokenizer = AutoTokenizer.from_pretrained(assets / 'olmo', local_files_only=True)
gsm = read_jsonl(inputs / 'gsm8k_test1319.jsonl')
examples = read(inputs / 'gsm_dev_examples.json')
demo = ''.join(prefix(x['problem']) + x['reference'] + '\n\n' for x in examples)
checks = []
for name, preamble in [('olmo_gsm_zero', ''), ('olmo_gsm_four', demo)]:
    stored = read(inputs / (name + '.json'))['prompts']
    mismatch = default_difference = injected_bos = 0
    for row, saved in zip(gsm, stored):
        if row['problem_id'] != saved['problem_id']:
            raise ValueError('Endpoint order differs')
        text = preamble + prefix(row['prompt'])
        default = tokenizer(text)['input_ids']
        explicit = tokenizer(text, add_special_tokens=False)['input_ids']
        default_difference += default != explicit
        mismatch += explicit != saved['input_ids']
        injected_bos += bool(default and default[0] == tokenizer.bos_token_id)
    if len(stored) != len(gsm) or mismatch or default_difference or injected_bos:
        raise ValueError('OLMo default encoding does not match frozen no-BOS prompts')
    checks.append(dict(endpoint=name, n=len(stored), stored_mismatches=mismatch,
                       default_vs_no_special_mismatches=default_difference,
                       default_leading_bos_count=injected_bos))

now = datetime.datetime.now(datetime.timezone.utc)
out.mkdir()
resources = out / 'resources'
resources.mkdir()
for path in sorted((assets / 'olmo').iterdir()):
    if path.is_file():
        dest = resources / 'olmo' / path.name
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, dest)
tests = sorted((assets / 'math_train').glob('*/test-*.parquet'))
if len(tests) != 7:
    raise ValueError('Expected seven original test source shards')
for path in tests:
    dest = resources / 'math_original_test' / path.parent.name / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, dest)
shutil.copyfile(assets / 'math_train/README.md', resources / 'MATH_SOURCE_README.md')
resource_manifest = manifest(resources)
dump(out / 'RESOURCE_MANIFEST.json', resource_manifest)
archive = out / 'source_supplement.tar.gz'
def public_tar_metadata(info):
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    info.mtime = 0
    return info
with tarfile.open(archive, 'w:gz') as tar:
    for name in sorted(resource_manifest):
        tar.add(resources / name, arcname=name, recursive=False, filter=public_tar_metadata)
with tarfile.open(archive, 'r:gz') as tar:
    if set(tar.getnames()) != set(resource_manifest):
        raise ValueError('Supplement member roster differs')
    for name, expected in resource_manifest.items():
        data = tar.extractfile(name).read()
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise ValueError('Supplement original-byte readback differs')
# Keep only the verified archive in the public packet; private source assets remain.
shutil.rmtree(resources)
shutil.copyfile(review / 'REPORT.md', out / 'REVIEW_REPORT.md')
shutil.copyfile(review / 'READ_RECEIPT.json', out / 'READ_RECEIPT.json')
shutil.copyfile('experiments/learning_regime_p009/PROTOCOL.md', out / 'PROTOCOL.md')
shutil.copyfile(__file__, out / 'PREPARATION_SOURCE.py')
dump(out / 'OLMO_BOS_DIAGNOSTIC.json', dict(
    observed_utc=now.isoformat(), transformers=transformers.__version__,
    model_revision='a1847dff35000b4271fa70afc5db10fd29fedbdf',
    tokenizer_class=type(tokenizer).__name__, bos_token_id=tokenizer.bos_token_id,
    eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
    add_bos_token=getattr(tokenizer, 'add_bos_token', None),
    tokenizer_json_postprocessor=read(assets/'olmo/tokenizer.json').get('post_processor'),
    model_config_has_bos='bos_token_id' in read(assets/'olmo/config.json'),
    checks=checks, model_calls=0, scoring_calls=0,
    convention='No leading BOS; add_special_tokens=False for prompts and answer text; append exactly one native EOS100257 to supervised full answers. No chat template for this base model.',
    evidence='Pinned model card uses the default tokenizer call; config/generation_config do not add BOS; tokenizer has no postprocessor. Default equals explicit no-special encoding for all2638 frozen OLMo endpoint prompts. Training must use the same explicit convention.'
))
dump(out / 'DISPOSITION.json', dict(
    created_utc=now.isoformat(), source_review_commit='e1d8d469399f214bc156985f5979c5eeee498ad7',
    source_report_sha256=expected_report, verbatim_verdict='PASS-WITH-REQUIRED-CLARIFICATIONS',
    original_target='e6350f0bf1f987d7c8a5acd76bbf924b6ed33f4e',
    original_manifest_sha256=sha(original/'MANIFEST.json'),
    original_stage0_input_manifest_sha256=sha(inputs/'MANIFEST.json'),
    stage0_input_review='PASS per report section2; OLMo previously structural only',
    R1='S1 Stage1 only attempt01, itself eligible and correct; extra attempts never rescue eligibility; NC/S2 up-to8 source difference disclosed.',
    R2='B includes all traversed-question attempted costs; D begins raw seed17 order at first question and charges every first attempt, independent of eventual correctness; A/B share first-format-eligible P_nat.',
    definitions_frozen_before_any_P009_output=True, actual_teacher_outputs=0,
    design_acceptance_file_written=False, runtime_admitted=False,
    pending_exact_P0_sources_unchanged=True,
    limitations=['Original overallverdict is not silently renamed PASS.',
      'Source supplement permits independent OLMo encoding and dev-order checking; this local check is not independent reviewer replication.',
      'Short-demo4shot is length-conditioned/descriptive, not a representative lower bound theorem.',
      'No optional3072-context evaluation is authorized or prepared.',
      'N3<=2USD singlebatch was nonblocking advice on the design; pending exactP0proposal remains248c/fourpaidbatches perrole within original outputs until actual runtime review.']
))
(out/'README.md').write_text('''# P009 A0 required clarifications — before any model output

The original report gives **PASS-WITH-REQUIRED-CLARIFICATIONS**; Stage0 inputs pass, while R1/R2 govern later stages. This supplement freezes those definitions before P2 and preserves the original target/input bytes. It does not create a runtime acceptance.

- **R1:** S1 Stage1 uses only an eligible/correct attempt01 answer. Attempts02–04 cannot admit a question. NC/S2 reuse D1 successes within up to eight attempts, a disclosed cross-setting difference.
- **R2:** B pays for attempts on all questions it traverses, including skipped failures. D starts from the first question of the same raw seed17 order, pays for every first attempt, and retains format-eligible first attempts irrespective of correctness. P_nat requires format-eligible attempt01 plus eligible correctness within four attempts. No free label-based skipping; physical costs remain separate from virtual comparison ceilings.
- **N1/N2:** MATH is labeled short-demo4shot. The supplementary archive contains the seven original MATH test shards, plus pinned OLMo tokenizer/config/card files. The new BOS check confirms default tokenization equals explicit no-special encoding for all2,638 stored OLMo prompts. Future training uses that same no-leading-BOS convention and a single answer EOS100257.
- **N3:** The exact P0 bootstrap request is already separate. It proposes one1,200s worker/$2.48 reservation and four paid complete prefix batches per role, all retained in the two full endpoints. The report's onebatch/$2 suggestion is not recorded as approval of that different exact proposal.

No model weights downloaded, no raw outputs rescored, no cloud upload/image/claim/model call. Original P0 source19 and original immutable design/input packet are unchanged. Exact runtime review remains mandatory. Please explicitly close the R1/R2 clarifications and give a scoped Stage0 design verdict tied to the original target plus this supplement; the current P0 gate cannot consume the broader required-clarifications verdict as an invented PASS.
''')
dump(out/'MANIFEST.json', manifest(out))
print(json.dumps(dict(output=str(out), files=len(manifest(out)), resources=len(resource_manifest),
    archive_bytes=archive.stat().st_size, manifest_sha256=sha(out/'MANIFEST.json'), utc=now.isoformat())))
