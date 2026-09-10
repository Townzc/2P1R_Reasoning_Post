"""CPU preparation and one bounded, inference-only E013 checkpoint diagnostic.

Kept outside src/scripts so the complete historical E013 source set stays frozen.
No command downloads a model. Only an explicitly requested launch uses CUDA.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

from analyses.real_math_e013_failures import common_prefix
from scripts.audit_family_matching import verified_tokenizer
from scripts.audit_real_math_engineering_outputs import audit_predictions as original_audit_predictions
from scripts.run_relation_engineering import check_ledger
from src.real_math_engineering import dump, git, load_frozen, source_files
from src.real_math_experiment import generate
from src.sft_data import sha256_file

CONFIG = Path('configs/real_math_e014/diagnostic.json')
RELEASE = Path('configs/real_math_e014/release_r2.json')
INPUTS = Path('reports/real_math_e014_inputs_r2')
ORIGINAL = Path('runs/gsm8k_overfit_e013_r1')


class AuditTokenizer:
    """Read-only audit view: snapshot vocabulary size once, delegate decoding.

    The frozen E013 auditor asks for len(tokenizer) for every recorded token.
    Some fast-tokenizer builds enumerate the vocabulary on each call. This
    view is confined to that CPU auditor and never reaches model generation.
    """
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.size = len(tokenizer)

    def __len__(self):
        return self.size

    def __getattr__(self, name):
        return getattr(self.tokenizer, name)


def audit_predictions(path, expected_rows, tokenizer, cfg):
    return original_audit_predictions(path, expected_rows, AuditTokenizer(tokenizer), cfg)


def stream_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def token_hash(ids):
    return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()


def dependencies():
    return sorted(set(source_files() + [
        'analyses/real_math_e013_failures.py', 'analyses/e014.py',
        'analyses/e014_audit.py', 'tests/test_e014.py', str(CONFIG)]))


def provenance():
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Publish tracked source changes before preparing or running E014')
    names = dependencies()
    git('ls-files', '--error-unmatch', *names)
    head = git('rev-parse', 'HEAD')
    if head != git('rev-parse', 'origin/main'):
        raise ValueError('Synchronize published origin/main before E014')
    return {'source_commit': head, 'source_worktree_dirty': False,
            'source_files_sha256': {n: sha256_file(n) for n in names}}


def library_sources():
    from transformers.generation.utils import GenerationMixin
    from transformers.models.qwen2.modeling_qwen2 import Qwen2ForCausalLM
    return {c.__module__: stream_hash(inspect.getfile(c))
            for c in (GenerationMixin, Qwen2ForCausalLM)}


def effective_generation_config(saved, tokenizer, cfg):
    """Resolve the same explicit config as E013, including library default merging."""
    from transformers import GenerationConfig
    from transformers.generation.utils import GenerationMixin
    explicit = GenerationConfig(do_sample=False, num_beams=1, max_new_tokens=cfg['max_new_tokens'],
        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id, use_cache=True)
    resolved, unused = GenerationMixin._prepare_generation_config(
        SimpleNamespace(generation_config=saved), explicit)
    if unused:
        raise ValueError('Unexpected generation model arguments')
    return resolved.to_dict()


def check_generation_settings(settings, cfg):
    expected = {'do_sample': False, 'num_beams': 1, 'use_cache': True,
        'max_new_tokens': cfg['max_new_tokens'], 'eos_token_id': 151643, 'pad_token_id': 151643,
        'repetition_penalty': 1.0, 'no_repeat_ngram_size': 0, 'forced_eos_token_id': None,
        'forced_bos_token_id': None, 'stop_strings': None, 'cache_implementation': None}
    if any(settings[k] != v for k, v in expected.items()):
        raise ValueError('Effective generation settings differ from the intended E013 replay')


def verify_checkpoint(folder, expected_manifest_sha):
    manifest_path = ORIGINAL / 'checkpoint_manifest.json'
    if sha256_file(manifest_path) != expected_manifest_sha:
        raise ValueError('Original checkpoint manifest differs')
    manifest = json.loads(manifest_path.read_text())
    folder = Path(folder)
    files = manifest['files']
    actual = {p.name for p in folder.iterdir()}
    if actual != set(files) or manifest['kind'] != 'weights_only_not_optimizer_rng_resume':
        raise ValueError('Missing or extra checkpoint files')
    for name, expected in files.items():
        p = folder / name
        if Path(name).name != name or p.is_symlink() or not p.is_file():
            raise ValueError('Checkpoint entries must be ordinary files')
        if p.stat().st_size != expected['bytes'] or stream_hash(p) != expected['sha256']:
            raise ValueError('Checkpoint content differs: ' + name)
    return {'all_files_verified': True, 'file_count': len(files),
            'bytes': sum(x['bytes'] for x in files.values()),
            'manifest_sha256': expected_manifest_sha}


def make_cases(train, encoded, original, cfg):
    if len(train) != 32 or len(encoded) != 32 or len(original) != 32:
        raise ValueError('Keep all original 32 training parents')
    failed = [p['problem_id'] for p in original if not p['score']['terminated_correct']]
    controls = [p['problem_id'] for p in original if p['score']['terminated_correct']][:2]
    if failed != cfg['selected_failed_ids'] or controls != cfg['selected_control_ids']:
        raise ValueError('Post-hoc diagnostic case rule differs')
    selected = set(failed + controls)
    ordered = [r['problem_id'] for r in train if r['problem_id'] in selected]
    if ordered != cfg['single_example_decode_order'] or len(selected) != 10:
        raise ValueError('Selected case identity/order differs')
    cases = []
    for i, (row, enc, pred) in enumerate(zip(train, encoded, original)):
        if row['problem_id'] != pred['problem_id'] or row['problem_id'] != enc['problem_id']:
            raise ValueError('Reference/prediction row alignment differs')
        target = enc['input_ids'][enc['n_prompt']:]
        prompt = enc['input_ids'][:enc['n_prompt']]
        shared = common_prefix(target, pred['generated_ids'])
        cases.append({'problem_id': row['problem_id'], 'row_index': i,
            'selected_for_batch1': row['problem_id'] in selected,
            'selection_role': 'failed' if row['problem_id'] in failed else
                              ('control' if row['problem_id'] in controls else 'replay_only'),
            'prompt_ids': prompt, 'target_ids': target,
            'original_generated_ids': pred['generated_ids'],
            'original_common_prefix_tokens': shared,
            'original_first_difference': shared if shared < len(target) else None,
            'original_score': pred['score'],
            'prompt_ids_sha256': token_hash(prompt), 'target_ids_sha256': token_hash(target)})
    return cases


def input_state(tokenizer, cfg):
    old_cfg, old_manifest, train, _, encoded, _, budget = load_frozen(tokenizer)
    if sha256_file(Path(old_cfg['data_dir']) / 'manifest.json') != cfg['e013_input_manifest_sha256']:
        raise ValueError('E013 parent/reference freeze differs')
    if sha256_file(ORIGINAL / 'final_train.jsonl') != cfg['reference_prediction_sha256']:
        raise ValueError('E013 recorded training generations differ')
    manifest = json.loads((ORIGINAL / 'run_manifest.json').read_text())
    if manifest['status'] != 'completed' or manifest['source_commit'] != cfg['e013_source_commit']:
        raise ValueError('Wrong original model run')
    if json.loads((ORIGINAL / 'record_verification.json').read_text())['status'] != 'passed_record_consistency_checks':
        raise ValueError('Original record verification is missing')
    predictions = audit_predictions(ORIGINAL / 'final_train.jsonl', train, tokenizer, old_cfg)
    return old_cfg, train, encoded, budget, predictions, make_cases(train, encoded, predictions, cfg)


def prepare(tokenizer, checkpoint):
    cfg = json.loads(CONFIG.read_text())
    if INPUTS.exists() or RELEASE.exists():
        raise FileExistsError('E014 input release is immutable')
    source = provenance()
    old_cfg, train, encoded, budget, predictions, cases = input_state(tokenizer, cfg)
    verified = verify_checkpoint(checkpoint, cfg['checkpoint_manifest_sha256'])
    from transformers import GenerationConfig
    effective = effective_generation_config(GenerationConfig.from_pretrained(checkpoint, local_files_only=True), tokenizer, old_cfg)
    check_generation_settings(effective, cfg)
    total = sum(r['n_supervised'] for r in encoded)
    batches = []
    for start in range(0, len(cases), old_cfg['eval_batch_size']):
        group = cases[start:start + old_cfg['eval_batch_size']]
        width = max(len(r['prompt_ids']) for r in group)
        batches.append({'row_indices': [r['row_index'] for r in group], 'prompt_width': width,
                        'left_padding': [width - len(r['prompt_ids']) for r in group],
                        'maximum_context_tokens': width + old_cfg['max_new_tokens']})
    if any(b['maximum_context_tokens'] > old_cfg['max_length'] for b in batches):
        raise ValueError('Original generation context bound differs')
    if any(e['labels'][-1] != tokenizer.eos_token_id or e['input_ids'][-1] != tokenizer.eos_token_id
           or any(v != -100 for v in e['labels'][:e['n_prompt']]) for e in encoded):
        raise ValueError('Prompt mask or supervised EOS differs')
    nll = json.loads((ORIGINAL / 'metrics.json').read_text())['train_reference_nll']
    if total != nll['supervised_tokens'] or total * 32 != budget['supervised_response_tokens']:
        raise ValueError('NLL/exposure denominators differ')
    evidence = {'phase': 'C018_E014_CPU_PREPARATION', 'pretrained_model_calls': 0,
        'server_contacted': False, 'gpu_seconds_added': 0,
        'train_rows_checked': len(cases), 'eos_labels_checked': len(cases),
        'unique_supervised_tokens': total, 'eos_fraction_of_supervised_tokens': len(cases) / total,
        'original_training_microbatch': old_cfg['microbatch_size'],
        'original_generation_batch_size': old_cfg['eval_batch_size'], 'batches': batches,
        'checkpoint': verified, 'original_reference_nll': nll,
        'saved_generation_default_max_new_tokens': json.loads((Path(checkpoint) / 'generation_config.json').read_text())['max_new_tokens'],
        'explicit_runtime_max_new_tokens': old_cfg['max_new_tokens'],
        'effective_generation_config': effective,
        'containing_batch_time_sum_for_selected_seconds_proxy': sum(p['generation_batch_seconds']
            for p, c in zip(predictions, cases) if c['selected_for_batch1']),
        'time_proxy_is_upper_bound': False,
        'reference_token_counts': [r['n_supervised'] for r in encoded],
        'failed_original_prefix_lengths': [c['original_common_prefix_tokens'] for c in cases if c['selection_role'] == 'failed'],
        'scope': 'Static/frozen-record checks only; no pretrained forward pass or established causal explanation.'}
    INPUTS.mkdir()
    dump(INPUTS / 'cases.json', cases)
    dump(INPUTS / 'cpu_evidence.json', evidence)
    dump(INPUTS / 'manifest.json', {**source, 'phase': 'E014_INPUTS',
        'config_sha256': sha256_file(CONFIG), 'library_sources_sha256': library_sources(),
        'e013_manifest_sha256': cfg['e013_input_manifest_sha256'],
        'files_sha256': {name: sha256_file(INPUTS / name) for name in ('cases.json', 'cpu_evidence.json')}})
    dump(RELEASE, {'phase': 'E014_RELEASE', 'manifest_sha256': sha256_file(INPUTS / 'manifest.json'),
                   'model_execution_performed': False})
    return evidence


def load_release(tokenizer):
    cfg = json.loads(CONFIG.read_text())
    release = json.loads(RELEASE.read_text())
    if sha256_file(INPUTS / 'manifest.json') != release['manifest_sha256']:
        raise ValueError('Input manifest differs from published release')
    manifest = json.loads((INPUTS / 'manifest.json').read_text())
    if manifest['config_sha256'] != sha256_file(CONFIG) or set(manifest['source_files_sha256']) != set(dependencies()):
        raise ValueError('Frozen E014 dependency set differs')
    for name, expected in manifest['source_files_sha256'].items():
        historic = subprocess.check_output(['git', 'show', manifest['source_commit'] + ':' + name])
        if sha256_file(name) != expected or hashlib.sha256(historic).hexdigest() != expected:
            raise ValueError('Frozen E014 runtime source differs: ' + name)
    if library_sources() != manifest['library_sources_sha256']:
        raise ValueError('Installed generation/Qwen2 Python source differs')
    for name, digest in manifest['files_sha256'].items():
        if Path(name).name != name or sha256_file(INPUTS / name) != digest:
            raise ValueError('Frozen E014 artifact differs')
    state = input_state(tokenizer, cfg)
    if state[-1] != json.loads((INPUTS / 'cases.json').read_text()):
        raise ValueError('Reconstructed case tokens/positions/order differ')
    return cfg, state


def difference(a, b):
    shared = common_prefix(a, b)
    return {'identical': a == b, 'common_prefix_tokens': shared,
            'a_token': a[shared] if shared < len(a) else None,
            'b_token': b[shared] if shared < len(b) else None}


def probe_queries(case, streams):
    target = case['target_ids']
    queries = [{'kind': 'reference_eos', 'target_position': len(target) - 1, 'alternative_id': None}]
    if case['selected_for_batch1']:
        for name, ids in streams.items():
            j = common_prefix(target, ids)
            if j < len(target) and j < len(ids):
                queries.append({'kind': name + '_first_difference', 'target_position': j,
                                'alternative_id': ids[j]})
    return queries


def distribution_record(logits, target, alternative=None):
    import torch
    vector = logits.detach().float()
    if vector.ndim != 1 or not torch.isfinite(vector).all():
        raise ValueError('Expected finite single-position vocabulary logits')
    logp = torch.log_softmax(vector, dim=-1)
    top = int(vector.argmax().item())
    ranks = 1 + int((vector > vector[target]).sum().item())
    ids = torch.topk(vector, min(5, len(vector))).indices.tolist()
    return {'target_id': target, 'target_log_probability': float(logp[target].item()),
        'target_rank_strict_greater': ranks, 'argmax_id': top,
        'target_is_argmax': target == top, 'argmax_log_probability': float(logp[top].item()),
        'target_minus_argmax_logit': float((vector[target] - vector[top]).item()),
        'alternative_id': alternative,
        'alternative_log_probability': float(logp[alternative].item()) if alternative is not None else None,
        'target_minus_alternative_logit': float((vector[target] - vector[alternative]).item()) if alternative is not None else None,
        'top5': [{'id': i, 'log_probability': float(logp[i].item())} for i in ids]}


def reference_measurement(logits, case, queries):
    """Shift once: target j is predicted by full-sequence logit n_prompt+j-1."""
    import torch
    n_prompt, target = len(case['prompt_ids']), case['target_ids']
    if logits.ndim != 2 or logits.shape[0] != n_prompt + len(target):
        raise ValueError('Full reference logits must include prompt and terminal EOS')
    shifted = logits[n_prompt - 1:n_prompt + len(target) - 1].float()
    target_tensor = torch.tensor(target, device=shifted.device)
    logp = torch.log_softmax(shifted, dim=-1)
    losses = (-logp.gather(1, target_tensor[:, None])[:, 0]).tolist()
    argmax = shifted.argmax(-1).tolist()
    if any(not math.isfinite(x) or x < 0 for x in losses):
        raise ValueError('Nonfinite/negative reference loss')
    events = []
    for query in queries:
        j = query['target_position']
        if not 0 <= j < len(target):
            raise ValueError('Reference query is outside target sequence')
        events.append({**query, 'causal_logit_index': n_prompt + j - 1,
            'context_token_count': n_prompt + j,
            'context_ids_sha256': token_hash(case['prompt_ids'] + target[:j]),
            'conditioning': 'reference_prefix_full_forward_use_cache_false',
            **distribution_record(shifted[j], target[j], query['alternative_id'])})
    correct = sum(a == b for a, b in zip(target, argmax))
    return {'problem_id': case['problem_id'], 'target_ids': target,
            'prompt_ids_sha256': case['prompt_ids_sha256'],
            'target_nll': losses, 'argmax_ids': argmax,
            'loss_sum': math.fsum(losses), 'supervised_tokens': len(target),
            'reference_nll': math.fsum(losses) / len(target), 'target_top1_correct': correct,
            'eos_is_argmax': target[-1] == argmax[-1], 'queries': events}


def diagnosis(cases, replay, singles, references):
    by_replay = {p['problem_id']: p for p in replay}
    by_single = {p['problem_id']: p for p in singles}
    comparisons = []
    for c in cases:
        pid = c['problem_id']
        r = by_replay[pid]
        row = {'problem_id': pid, 'selection_role': c['selection_role'],
               'original_vs_replay': difference(c['original_generated_ids'], r['generated_ids'])}
        if c['selected_for_batch1']:
            s = by_single[pid]
            row.update(replay_vs_single=difference(r['generated_ids'], s['generated_ids']),
                       replay_score=r['score'], single_score=s['score'])
        comparisons.append(row)
    matches = sum(c['original_vs_replay']['identical'] for c in comparisons)
    changed = sum(not c['replay_vs_single']['identical'] for c in comparisons if 'replay_vs_single' in c)
    count = sum(r['supervised_tokens'] for r in references)
    total = math.fsum(r['loss_sum'] for r in references)
    old_nll = json.loads((ORIGINAL / 'metrics.json').read_text())['train_reference_nll']['nll']
    tolerance = json.loads(CONFIG.read_text())['nll_agreement_abs_tolerance']
    return {'phase': 'E014_DIAGNOSIS', 'original_vs_replay_exact': matches, 'replay_denominator': 32,
        'batch_contrast_interpretable': matches == 32,
        'selected_batch_sensitive_count': changed, 'selected_denominator': 10,
        'selected_single_terminated_correct': sum(p['score']['terminated_correct'] for p in singles),
        'reference_supervised_tokens': count, 'reference_loss_sum': total, 'reference_nll': total / count,
        'absolute_nll_difference_from_e013': abs(total / count - old_nll),
        'reference_nll_agrees_with_e013_within_tolerance': abs(total / count - old_nll) <= tolerance,
        'reference_top1_correct': sum(r['target_top1_correct'] for r in references),
        'reference_eos_top1_correct': sum(r['eos_is_argmax'] for r in references),
        'comparisons': comparisons, 'training_updates': 0, 'scientific_launch_authorized': False,
        'interpretation': ('Original batch8 replay differs: checkpoint hashes may match while runtime/numerical '
            'reproducibility does not. Do not isolate a batch-size effect.' if matches != 32 else
            'Replay agrees. A selected batch1 difference is batch-sensitive output, not proof of a software bug.'),
        'limitations': ['Selected cases are post-hoc and not a new evaluation population.',
            'Reference-conditioned EOS is not the EOS distribution on a diverged generated prefix.',
            'Full-forward logits do not reproduce the exact cached generation kernel.',
            'No automatic training, decode-cap adjustment, new teacher or holdout evaluation follows.']}


def server_preflight(cfg):
    import torch
    packages = cfg['server_packages']
    if sys.platform != 'linux' or sys.version_info[:2] != (3, 12) or torch.__version__ != '2.8.0+cu128':
        raise ValueError('Require recorded Linux/Python3.12/PyTorch2.8.0+cu128')
    if any(importlib.metadata.version(k) != v for k, v in packages.items()):
        raise ValueError('Recorded package versions differ')
    timeout = shutil.which('timeout')
    if not timeout or 'GNU coreutils' not in subprocess.check_output([timeout, '--version'], text=True):
        raise ValueError('GNU timeout is mandatory')
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                                  '--format=csv,noheader,nounits'], text=True).strip().splitlines()
    active = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid',
                                     '--format=csv,noheader,nounits'], text=True).strip()
    if len(gpu) != 1 or 'A800' not in gpu[0] or int(gpu[0].split(',')[1].strip()) < 75000 or active:
        raise ValueError('One idle A800 80GB is required')
    if gpu[0].split(',')[2].strip() != cfg['driver_version']:
        raise ValueError('Original driver differs; review before interpreting replay')
    free = shutil.disk_usage('runs').free / 1024 ** 3
    if free < cfg['min_free_gib']:
        raise ValueError('Insufficient free space for compact diagnostic outputs')
    return {'gpu': gpu[0], 'active_compute_processes': 0, 'free_gib': free,
            'torch': torch.__version__, 'python': sys.version.split()[0], 'packages': packages}


def worker(args, tokenizer):
    cfg, state = load_release(tokenizer)
    out = Path('runs') / cfg['run_id']
    if os.environ.get('CS294_BOUNDED_RUN_ID') != cfg['run_id'] or not out.is_dir():
        raise ValueError('E014 requires its unique bounded wrapper')
    source = provenance()
    preflight = json.loads(Path(args.preflight).read_text())
    if preflight['source_commit'] != source['source_commit'] or preflight['phase'] != 'E014':
        raise ValueError('Missing matching E014 preflight')
    if preflight['release_sha256'] != sha256_file(RELEASE) or not preflight['checkpoint']['all_files_verified']:
        raise ValueError('Preflight release/weights differ')
    manifest = {**source, 'phase': 'E014', 'status': 'running', 'config': cfg,
        'release_sha256': sha256_file(RELEASE), 'preflight_sha256': sha256_file(args.preflight),
        'server': preflight['server'], 'checkpoint': preflight['checkpoint'],
        'tokenizer': preflight['tokenizer'],
        'model_execution_performed': False, 'training_updates': 0,
        'started_at_utc': datetime.now(timezone.utc).isoformat()}
    dump(out / 'run_manifest.json', manifest)
    phases = {}
    started = time.monotonic()
    def stop(*_):
        raise TimeoutError('E014 watchdog terminated; preserve partial files without retry')
    signal.signal(signal.SIGTERM, stop)
    try:
        import torch
        from transformers import AutoModelForCausalLM
        if not torch.cuda.is_available():
            raise ValueError('Registered pretrained diagnostic requires CUDA')
        torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        def timed(name, operation):
            tick = time.perf_counter()
            result = operation()
            torch.cuda.synchronize()
            phases[name] = time.perf_counter() - tick
            return result
        verify_checkpoint(args.checkpoint_dir, cfg['checkpoint_manifest_sha256'])
        model = timed('checkpoint_load', lambda: AutoModelForCausalLM.from_pretrained(
            args.checkpoint_dir, dtype=torch.float32, attn_implementation='sdpa', local_files_only=True).cuda())
        if any(p.dtype != torch.float32 for p in model.parameters()):
            raise ValueError('Saved parameters must remain FP32')
        model.eval(); model.gradient_checkpointing_disable(); model.config.use_cache = False
        tokenizer.pad_token = tokenizer.eos_token
        manifest['model_execution_performed'] = True
        torch.cuda.reset_peak_memory_stats()
        old_cfg, train, encoded, _, original, cases = state
        settings = effective_generation_config(model.generation_config, tokenizer, old_cfg)
        check_generation_settings(settings, cfg)
        if settings != json.loads((INPUTS / 'cpu_evidence.json').read_text())['effective_generation_config']:
            raise ValueError('Loaded model generation configuration differs from CPU inspection')
        manifest['effective_generation_config'] = settings
        selected = [r for r, c in zip(train, cases) if c['selected_for_batch1']]
        replay = timed('original_batch8_replay', lambda: generate(model, tokenizer, train, old_cfg, out / 'replay_batch8.jsonl'))
        singles = timed('selected_batch1', lambda: generate(model, tokenizer, selected,
                         {**old_cfg, 'eval_batch_size': 1}, out / 'selected_batch1.jsonl'))
        by_replay = {p['problem_id']: p['generated_ids'] for p in replay}
        by_single = {p['problem_id']: p['generated_ids'] for p in singles}
        references = []
        def measure_all():
            with (out / 'reference_tokens.jsonl').open('x') as log:
                for case, enc in zip(cases, encoded):
                    streams = {'original_batch8': case['original_generated_ids'],
                               'replay_batch8': by_replay[case['problem_id']]}
                    if case['selected_for_batch1']:
                        streams['selected_batch1'] = by_single[case['problem_id']]
                    ids = torch.tensor([enc['input_ids']], device='cuda')
                    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                        output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False)
                    record = reference_measurement(output.logits[0], case, probe_queries(case, streams))
                    references.append(record)
                    log.write(json.dumps(record, allow_nan=False) + '\n'); log.flush()
                    del output, ids
            return references
        timed('all32_reference_tokens', measure_all)
        dump(out / 'diagnosis.json', diagnosis(cases, replay, singles, references))
        manifest['status'] = 'completed'
        manifest['peak_allocated_mib'] = torch.cuda.max_memory_allocated() / 1024 ** 2
        manifest['peak_reserved_mib'] = torch.cuda.max_memory_reserved() / 1024 ** 2
    except Exception as exc:
        manifest.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        raise
    finally:
        dump(out / 'phase_timings.json', {'completed_phases_seconds': phases,
            'wall_seconds': time.monotonic() - started,
            'incomplete_phase_time_included_in_wall_only': True})
        manifest['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        manifest['artifact_sha256'] = {p.name: sha256_file(p) for p in out.iterdir()
            if p.suffix in ('.json', '.jsonl') and p.name != 'run_manifest.json'}
        tmp = out / 'run_manifest.tmp'; dump(tmp, manifest); tmp.replace(out / 'run_manifest.json')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', nargs='?', default='inspect', choices=('prepare', 'inspect', 'launch', 'worker'))
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--checkpoint-dir', required=True)
    p.add_argument('--ledger', default='.local/resource_ledger.json')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--preflight')
    a = p.parse_args()
    tokenizer, token_record = verified_tokenizer(Path(a.tokenizer_dir))
    if a.action == 'prepare':
        result = prepare(tokenizer, a.checkpoint_dir)
        print(json.dumps({'phase': result['phase'], 'rows': result['train_rows_checked'],
                          'checkpoint': result['checkpoint']})); return 0
    if a.action == 'worker':
        worker(a, tokenizer); return 0
    cfg, _ = load_release(tokenizer)
    source = provenance()
    # Both the release and original artifacts must be in this published checkout.
    git('ls-files', '--error-unmatch', str(RELEASE), *map(str, INPUTS.iterdir()))
    budget = json.loads(Path('configs/resource_budget.json').read_text())
    accounting = check_ledger(cfg, a.ledger, budget)
    report = {'phase': 'E014', 'status': 'not_run', 'source_commit': source['source_commit'],
        'release_sha256': sha256_file(RELEASE), 'accounting': accounting,
        'checkpoint': verify_checkpoint(a.checkpoint_dir, cfg['checkpoint_manifest_sha256']),
        'tokenizer': token_record,
        'model_execution_performed': False, 'training_updates': 0}
    if a.action != 'launch' or not a.execute:
        print(json.dumps(report, indent=2)); return 0
    report['server'] = server_preflight(cfg)
    report['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    preflight = Path('.local') / ('e014_preflight_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
    dump(preflight, report)
    check_ledger(cfg, a.ledger, budget)
    return subprocess.call([sys.executable, '-m', 'scripts.run_bounded', '--run-id', cfg['run_id'],
        '--max-seconds', str(cfg['max_seconds']), '--ledger', a.ledger,
        '--expected-ledger-sha256', cfg['expected_ledger_sha256'], '--require-full-cap', '--',
        sys.executable, '-m', 'analyses.e014', 'worker', '--tokenizer-dir', a.tokenizer_dir,
        '--checkpoint-dir', a.checkpoint_dir, '--preflight', str(preflight)])


if __name__ == '__main__':
    sys.exit(main())
