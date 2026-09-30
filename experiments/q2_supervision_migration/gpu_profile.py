"""Finite engineering profile, never a scientific experiment or resume runner.

Run as a module on an isolated Linux GPU host. Inputs must already be local.
The parent owns one new session/process group and enforces the wall-clock cap.
EvalPlus process isolation is NOT a security sandbox; use an isolated container.
Imports of torch/TRL/EvalPlus occur only inside the explicitly launched worker.
Generation failures before the backend returns leave attempted/ambiguous intent;
never replay them. EvalPlus internal FAIL still conflates candidate exceptions
with some inner subprocess faults; outer errors/timeouts always abort.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
import uuid

from .contracts import (SuiteVerdict, VerdictStatus, identity_hash, reserve_batch,
                        record_sample, seal_batch, reward_from_verdicts)

MODEL_ID = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'
MODEL_REVISION = '2e1fd397ee46e1388853d2af2c993145b0f1098a'
MAX_SECONDS = 1800
PROFILE = dict(max_steps=2, per_device_train_batch_size=4,
               gradient_accumulation_steps=4, num_generations=8,
               num_iterations=1, max_completion_length=640, temperature=1.0,
               learning_rate=1e-6, lr_scheduler_type='constant', warmup_steps=0,
               beta=0.0, optim='adafactor', bf16=True,
               use_vllm=True, vllm_mode='colocate', vllm_tensor_parallel_size=1,
               vllm_gpu_memory_utilization=0.3, vllm_enable_sleep_mode=False,
               loss_type='dapo', scale_rewards='group',
               importance_sampling_level='token',
               vllm_importance_sampling_correction=True,
               vllm_importance_sampling_mode='sequence_mask',
               vllm_importance_sampling_clip_max=3.0, use_liger_kernel=False,
               remove_unused_columns=False, save_strategy='no',
               eval_strategy='no', logging_steps=1, report_to=[],
               dataloader_num_workers=0)


class ProfileError(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def durable_json(path, value):
    """Exclusive create: interrupted or completed work is never overwritten."""
    data = json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False).encode() + b'\n'
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def check_deadline(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('profile deadline reached; no retry')
    return remaining


def pinned_json(path, expected_sha):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha or ''):
        raise ProfileError('a lowercase SHA256 pin is required')
    if sha256(path) != expected_sha:
        raise ProfileError(f'input SHA256 mismatch: {Path(path).name}')
    return json.loads(Path(path).read_text())


def train_subset(split):
    train, heldout = split.get('train_ids'), split.get('eval_ids')
    if split.get('PROVISIONAL_smoke_only') or not isinstance(train, list) or not isinstance(heldout, list):
        raise ProfileError('frozen train/eval split required')
    if any(not isinstance(x, str) or not re.fullmatch(r'Mbpp/\d+', x) for x in train + heldout):
        raise ProfileError('invalid MBPP task ID')
    if len(train) < 8 or not heldout or len(set(train)) != len(train) or len(set(heldout)) != len(heldout):
        raise ProfileError('insufficient or duplicate split IDs')
    if set(train) & set(heldout):
        raise ProfileError('train/eval overlap')
    return sorted(train)[:8]


def validate_args(args, *, system=None):
    if (system or platform.system()) != 'Linux':
        raise ProfileError('GPU profile is Linux-only')
    if not args.execute_engineering_profile:
        raise ProfileError('--execute-engineering-profile is required')
    if not math.isfinite(args.max_seconds) or not 1 <= args.max_seconds <= MAX_SECONDS:
        raise ProfileError('worker cap must be in [1, 1800] seconds')
    if not math.isfinite(args.scorer_timeout) or not 1 <= args.scorer_timeout <= 120:
        raise ProfileError('scorer timeout must be in [1, 120] seconds')
    if args.seed != 0:
        raise ProfileError('engineering profile seed is fixed at 0')
    for field in ('data_json', 'split_json', 'model_manifest'):
        if not Path(getattr(args, field)).is_file():
            raise ProfileError(f'local {field} required')
    if not Path(args.model_path).is_dir():
        raise ProfileError('local model directory required')
    return train_subset(pinned_json(args.split_json, args.split_sha256))


def verify_model(root, manifest_path, deadline):
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get('model_id') != MODEL_ID or manifest.get('revision') != MODEL_REVISION:
        raise ProfileError('wrong model identity/revision')
    entries = manifest.get('files')
    if not isinstance(entries, list) or not entries:
        raise ProfileError('model manifest must contain a nonempty file list')
    files = {x['path']: x['sha256'] for x in entries}
    sizes = {x['path']: x['bytes'] for x in entries}
    if len(files) != len(entries):
        raise ProfileError('duplicate model manifest file')
    if 'config.json' not in files:
        raise ProfileError('model manifest files must include config.json')
    if not any(n.endswith('.safetensors') for n in files) or 'tokenizer_config.json' not in files:
        raise ProfileError('complete model/tokenizer manifest required')
    root = Path(root).resolve()
    for name, digest in files.items():
        check_deadline(deadline)
        path = (root / name).resolve()
        # HF cache symlinks may be resolved outside snapshots; stage an ordinary local copy.
        if not path.is_relative_to(root) or not path.is_file() or not re.fullmatch(r'[0-9a-f]{64}', str(digest)):
            raise ProfileError('unsafe or incomplete model manifest')
        if path.stat().st_size != sizes[name] or sha256(path) != digest:
            raise ProfileError(f'model file mismatch: {name}')
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual != set(files):
        raise ProfileError('model manifest must cover every staged file')
    return identity_hash(manifest)


def stop_owned_group(proc, *, grace=2):
    """Only accept a live Popen created here with start_new_session=True."""
    if getattr(proc, '_q2_owned_group', None) != proc.pid or proc.pid <= 1 or proc.pid == os.getpgrp():
        raise ProfileError('refusing to signal an unowned process group')
    if proc.poll() is None:
        try:
            if os.getpgid(proc.pid) != proc.pid:
                raise ProfileError('owned worker no longer leads its own process group')
        except ProcessLookupError:
            pass
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    # Leader may have exited while a scorer/vLLM descendant remains.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait(timeout=5)


def launch_guarded(command, out, seconds, *, phase='train', popen=subprocess.Popen):
    out = Path(out)
    started = time.monotonic()
    with (out / f'{phase}.stdout.log').open('xb') as stdout, (out / f'{phase}.stderr.log').open('xb') as stderr:
        proc = popen(command, stdout=stdout, stderr=stderr, start_new_session=True,
                     env={**os.environ, 'Q2_PROFILE_PARENT_PID': str(os.getpid()),
                          'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                          'HF_DATASETS_OFFLINE': '1', 'WANDB_DISABLED': 'true'})
        proc._q2_owned_group = proc.pid
        status = 'failed'
        error = None
        try:
            durable_json(out / f'{phase}_worker_start.json', {'pid': proc.pid, 'pgid': proc.pid,
                         'max_seconds': seconds, 'parent_pid': os.getpid()})
            proc.wait(timeout=max(0.01, seconds - min(8.0, seconds / 2)))
            status = 'completed' if proc.returncode == 0 else 'failed'
        except subprocess.TimeoutExpired:
            status, error = 'timeout', 'hard parent deadline; no retry'
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            stop_owned_group(proc)
            durable_json(out / f'{phase}_launcher_receipt.json', {'status': status, 'error': error,
                         'returncode': proc.returncode, 'elapsed_seconds': time.monotonic() - started,
                         'pid': proc.pid, 'cleanup_scope': 'owned_process_group_only',
                         'scientific_result': False})
    return 0 if status == 'completed' else 1


def _scorer_process(conn, data_path, data_sha, selected, out):
    """Spawned BEFORE torch loading; EvalPlus internal forks stay CPU-only."""
    try:
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        os.environ['MBPP_OVERRIDE_PATH'] = str(Path(data_path).resolve())
        os.environ['XDG_CACHE_HOME'] = str((Path(out) / 'fresh_scorer_cache').resolve())
        os.environ['HF_HUB_OFFLINE'] = '1'
        if sha256(data_path) != data_sha:
            raise ProfileError('raw MBPP data pin mismatch')
        from evalplus.data import get_mbpp_plus
        from evalplus.evaluate import get_groundtruth
        from evalplus.eval import MBPP_OUTPUT_NOT_NONE_TASKS, untrusted_check
        all_problems = get_mbpp_plus(version='v0.2.0')
        problems = {key: all_problems[key] for key in selected}
        # Only eight TRAIN canonical reference programs are executed.
        cache_key = identity_hash({'raw_sha256': data_sha, 'train_ids': selected})
        gt = get_groundtruth(problems, cache_key, MBPP_OUTPUT_NOT_NONE_TASKS)
        import pickle
        gt_path = Path(out) / 'profile_groundtruth.pickle'
        with gt_path.open('xb') as stream:
            pickle.dump(gt, stream)
            stream.flush()
            os.fsync(stream.fileno())
        durable_json(Path(out) / 'groundtruth_manifest.json',
                     {'sha256': sha256(gt_path), 'train_ids': selected,
                      'cache_key': cache_key, 'origin': 'locally_computed_canonical_references'})
        conn.send({'ready': True, 'prompts': {key: problems[key]['prompt'] for key in selected}})
        while True:
            request = conn.recv()
            if request is None:
                return
            task, code = request
            if task not in problems:
                raise ProfileError('non-profile task sent to scorer')
            p, reference = problems[task], gt[task]
            verdicts = {}
            for label, suite in (('base', 'base'), ('extra', 'plus')):
                try:
                    inputs, expected = p[f'{suite}_input'], reference[suite]
                    timings = reference.get(f'{suite}_time')
                    if not timings or len(timings) != len(inputs) or len(expected) != len(inputs):
                        raise ProfileError('missing/misaligned canonical test timings')
                    status, details = untrusted_check('mbpp', code, inputs, p['entry_point'],
                        expected=expected, atol=p['atol'], ref_time=timings, fast_check=False)
                    if status not in ('pass', 'fail', 'timeout'):
                        raise ProfileError('unknown EvalPlus verdict')
                    verdicts[label] = {'status': status, 'detail': json.dumps({'tests_observed': len(details),
                                                             'test_count': len(inputs)})}
                except BaseException as exc:
                    verdicts[label] = {'status': 'scorer_error', 'detail': repr(exc)}
            conn.send(verdicts)
    except BaseException as exc:
        try:
            conn.send({'fatal': repr(exc)})
        except (EOFError, BrokenPipeError):
            pass
    finally:
        conn.close()


def receive(conn, timeout, deadline):
    if not conn.poll(min(timeout, check_deadline(deadline))):
        raise TimeoutError('scorer outer timeout; no retry')
    value = conn.recv()
    if 'fatal' in value:
        raise ProfileError(value['fatal'])
    return value


def record_generation_return(batch, prompt_ids, completion_ids, decoded_text, raw_decoded_text):
    """Persist returned tokens before trainer logprob forwards/reward evaluation."""
    expected = len(batch.intent()['tasks'])
    if any(len(x) != expected for x in (prompt_ids, completion_ids, decoded_text, raw_decoded_text)):
        raise ProfileError('generation return size mismatch')
    durable_json(batch.directory / 'generation_return.json', {
        'prompt_ids': prompt_ids, 'completion_ids': completion_ids,
        'decoded_text': decoded_text, 'raw_decoded_text': raw_decoded_text,
        'boundary': 'single_turn_backend_return_before_policy_logprob_forward'})


def _worker(args):
    if os.environ.get('Q2_PROFILE_PARENT_PID') != str(os.getppid()):
        raise ProfileError('worker must be launched by the guarded parent')
    deadline = time.monotonic() + args.max_seconds
    out = Path(args.out)
    selected = validate_args(args)
    if sha256(args.data_json) != args.data_sha256:
        raise ProfileError('raw MBPP data SHA256 mismatch')
    versions = {name: importlib.metadata.version(name) for name in
                ('torch', 'transformers', 'trl', 'vllm', 'evalplus')}
    expected = dict(torch='2.11.0', transformers='4.56.2', trl='1.7.0', vllm='0.23.0', evalplus='0.3.1')
    if any(versions[k].split('+')[0] != v for k, v in expected.items()):
        raise ProfileError('profile package versions differ from inspected API pins')
    driver = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                            capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if not driver or any(int(v.split('.')[0]) < 580 for v in driver.splitlines()):
        raise ProfileError('CUDA 13 profile requires NVIDIA R580+ driver')
    libc_name, libc_version = platform.libc_ver()
    if libc_name != 'glibc' or tuple(map(int, libc_version.split('.')[:2])) < (2, 35):
        raise ProfileError('profile lock targets glibc >=2.35')
    if sys.version_info[:2] != (3, 11):
        raise ProfileError('profile lock targets Python 3.11')
    model_identity = verify_model(args.model_path, args.model_manifest, deadline)
    durable_json(out / 'input_receipt.json', {'model_identity': model_identity,
        'model_revision': MODEL_REVISION, 'split_sha256': args.split_sha256,
        'data_sha256': args.data_sha256, 'selected_train_ids': selected,
        'versions': versions, 'driver': driver, 'libc': libc_version,
        'vllm_engine_seed': 0, 'profile': PROFILE, 'max_worker_seconds': args.max_seconds})
    ctx = mp.get_context('spawn')
    conn, other = ctx.Pipe()
    scorer = ctx.Process(target=_scorer_process,
        args=(other, args.data_json, args.data_sha256, selected, str(out)), daemon=False)
    scorer.start()
    other.close()
    ready = receive(conn, min(180, args.max_seconds), deadline)
    if not ready.get('ready'):
        raise ProfileError('scorer did not initialize')
    # All GPU imports and loading happen only after the independent scorer exists.
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForCausalLM, TrainerCallback
    from trl import GRPOConfig, GRPOTrainer
    if torch.cuda.device_count() != 1:
        raise ProfileError('exactly one visible GPU required')
    device = torch.cuda.get_device_properties(0)
    if device.total_memory < 75 * 1024**3 or not torch.cuda.is_bf16_supported():
        raise ProfileError('one >=75 GiB bf16-capable GPU required')
    durable_json(out / 'device.json', {'name': device.name, 'total_memory_bytes': device.total_memory})
    torch.cuda.reset_peak_memory_stats()
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True, trust_remote_code=False)
    ds = Dataset.from_list([{'task_id': t, 'prompt': [{'role': 'user', 'content':
        'Write a complete Python function that solves the task below. '
        'Return the full function definition in a single ```python code block.\n\n' + ready['prompts'][t].strip()}]}
        for t in selected])
    lengths = [len(tokenizer.apply_chat_template(x['prompt'], add_generation_prompt=True)) for x in ds]
    max_model_length = max(lengths) + 640
    config = GRPOConfig(output_dir=str(out / 'trainer'), seed=0, **PROFILE,
        model_init_kwargs={'dtype': 'bfloat16', 'local_files_only': True, 'trust_remote_code': False, 'attn_implementation': 'sdpa'},
        vllm_max_model_length=max_model_length)
    config_hash = identity_hash({'profile': PROFILE, 'max_model_length': max_model_length})
    state = {'batches': 0, 'active': None, 'steps': 0, 'durations': []}
    started = time.monotonic()

    def suite_reward(prompts, completions, completion_ids, task_id, trainer_state=None, **kwargs):
        check_deadline(deadline)
        batch = state['active']
        if batch is None or len(task_id) != 16 or len(completions) != 16 or len(completion_ids) != 16:
            raise ProfileError('unexpected generation batch contract')
        if list(task_id) != batch.intent()['tasks']:
            raise ProfileError('reward task order differs from generation intent')
        texts = [c[0]['content'] if isinstance(c, list) and len(c) == 1 else c for c in completions]
        if any(not isinstance(x, str) for x in texts):
            raise ProfileError('unexpected completion format')
        returned = json.loads((batch.directory / 'generation_return.json').read_text())
        if returned['completion_ids'] != completion_ids or returned['decoded_text'] != texts:
            raise ProfileError('reward hook differs from persisted backend completion')
        # Preserve every raw generation before any scorer call can fail.
        durable_json(batch.directory / 'raw_generations.json', {'texts': texts,
            'completion_ids': completion_ids, 'task_id': list(task_id),
            'committed_updates': int(trainer_state.global_step),
            'policy_identity_kind': 'source_manifest_and_committed_update_lineage'})
        rewards, fatal = [], None
        for i, (text, ids, task) in enumerate(zip(texts, completion_ids, task_id)):
            base = extra = SuiteVerdict(VerdictStatus.MISSING, 'not scored after earlier batch failure')
            if fatal is None:
                try:
                    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.S)
                    code = (blocks[-1] if blocks else text).strip()
                    conn.send((task, code))
                    verdicts = receive(conn, args.scorer_timeout, deadline)
                    base, extra = (SuiteVerdict(**verdicts[k]) for k in ('base', 'extra'))
                    rewards.append(float(reward_from_verdicts(base, extra, 'union')))
                except BaseException as exc:
                    fatal = exc
                    if base.status == VerdictStatus.MISSING:
                        base = SuiteVerdict(VerdictStatus.TIMEOUT if isinstance(exc, TimeoutError)
                                            else VerdictStatus.SCORER_ERROR, repr(exc))
            record_sample(batch, sample_index=i, completion_text=text,
                completion_token_ids=ids, base=base, extra=extra,
                finish_reason='generation_boundary_not_provided_by_trl_reward_hook')
        seal_batch(batch)
        if fatal is not None:
            raise ProfileError('unresolved scorer result; batch preserved; update forbidden') from fatal
        return rewards

    class ReceiptCallback(TrainerCallback):
        def on_train_begin(self, args, training_state, control, model=None, optimizer=None, **kwargs):
            inner = getattr(optimizer, 'optimizer', optimizer)
            if type(inner).__name__ != 'Adafactor' or len(inner.state) != 0:
                raise ProfileError('profile must begin with a fresh empty Adafactor')
            if training_state.global_step != 0 or not all(p.requires_grad for p in model.parameters()):
                raise ProfileError('profile requires fresh full-model training, not adapters/resume')
            durable_json(out / 'fresh_optimizer.json', {'class': type(inner).__name__,
                'state_entries': len(inner.state), 'initial_global_step': 0,
                'full_model_parameters': sum(p.numel() for p in model.parameters()),
                'all_parameters_trainable': True})

        def on_pre_optimizer_step(self, args, training_state, control, model=None, **kwargs):
            check_deadline(deadline)
            grads = [p.grad for p in model.parameters() if p.grad is not None]
            if any(not bool(torch.isfinite(g).all()) for g in grads):
                raise ProfileError('nonfinite gradient; no optimizer update permitted')
            durable_json(out / f'pre_update_{int(training_state.global_step) + 1}.json',
                         {'gradient_tensors': len(grads), 'all_finite': True})

        def on_log(self, args, training_state, control, logs=None, **kwargs):
            for key, value in (logs or {}).items():
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    raise ProfileError(f'nonfinite trainer metric: {key}')

        def on_step_end(self, args, training_state, control, **kwargs):
            check_deadline(deadline)
            step = int(training_state.global_step)
            if step not in (1, 2) or step != state['steps'] + 1:
                raise ProfileError('unexpected committed update count')
            state['steps'] = step
            durable_json(out / f'update_{step}.json', {'committed_update': step,
                'elapsed_seconds': time.monotonic() - started,
                'cuda_peak_allocated': torch.cuda.max_memory_allocated(),
                'cuda_peak_reserved': torch.cuda.max_memory_reserved()})

    class FiniteTrainer(GRPOTrainer):
        def _generate_single_turn(self, prompt_ids, images, multimodal_fields):
            result = super()._generate_single_turn(prompt_ids, images, multimodal_fields)
            completion_ids, _ = result
            if state['active'] is None:
                raise ProfileError('generation without reserved batch')
            record_generation_return(state['active'], prompt_ids, completion_ids,
                self.processing_class.batch_decode(completion_ids, skip_special_tokens=True),
                self.processing_class.batch_decode(completion_ids, skip_special_tokens=False))
            return result

        def _generate_and_score_completions(self, inputs):
            check_deadline(deadline)
            if state['batches'] >= 2 or self.state.global_step != state['batches']:
                raise ProfileError('unexpected extra generation; no replay')
            tasks = [x['task_id'] for x in inputs]
            if len(tasks) != 16 or set(Counter(tasks).values()) != {8} or not set(tasks) <= set(selected):
                raise ProfileError('expected two profile prompt groups of eight')
            batch_index = state['batches']
            state['active'] = reserve_batch(out / 'batches', run_id=out.name, phase_id='engineering_only',
                batch_index=batch_index, tasks=tasks, config_sha256=config_hash,
                policy_sha256=identity_hash({'source': model_identity, 'committed_updates': self.state.global_step}))
            t0 = time.monotonic()
            result = super()._generate_and_score_completions(inputs)
            state['durations'].append(time.monotonic() - t0)
            state['batches'] += 1
            durable_json(state['active'].directory / 'generation_complete.json',
                         {'global_step': int(self.state.global_step), 'seconds': state['durations'][-1],
                          'last_loaded_step': int(self._last_loaded_step)})
            if self._last_loaded_step != self.state.global_step:
                raise ProfileError('rollout weight synchronization step not verified')
            state['active'] = None
            return result

    trainer = FiniteTrainer(model=args.model_path, args=config, train_dataset=ds,
        processing_class=tokenizer, reward_funcs=suite_reward, callbacks=[ReceiptCallback()])
    trainer.train(resume_from_checkpoint=False)
    if state['steps'] != 2 or state['batches'] != 2:
        raise ProfileError('profile did not commit exactly two updates')
    check_deadline(deadline)
    final = out / 'final_model'
    trainer.save_model(str(final))
    tokenizer.save_pretrained(final)
    saved = {}
    for f in sorted(final.rglob('*')):
        if f.is_file():
            check_deadline(deadline)
            with f.open('rb') as stream:
                os.fsync(stream.fileno())
            saved[str(f.relative_to(final))] = sha256(f)
    if not saved or not any(n.endswith('.safetensors') for n in saved):
        raise ProfileError('no complete safe model export')
    durable_json(out / 'final_model_manifest.json', {'files': saved, 'updates': 2,
        'optimizer_state_retained': False, 'use': 'fresh_optimizer_fork_only'})
    # Export a deterministic TRAIN-prompt probe for a separate reload process.
    probe_ids = tokenizer.apply_chat_template(ds[0]['prompt'], add_generation_prompt=True,
                                              return_tensors='pt').to('cuda')
    trainer.model.eval()
    with torch.inference_mode():
        before = trainer.model(input_ids=probe_ids).logits[:, -1, :].float().cpu()
    probe_path = out / 'reload_probe.pt'
    with probe_path.open('xb') as stream:
        torch.save({'input_ids': probe_ids.cpu(), 'logits': before}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    durable_json(out / 'reload_probe_manifest.json', {'sha256': sha256(probe_path),
        'prompt': ds[0]['prompt'], 'task_id': selected[0], 'origin': 'profile_own_tensor_export'})
    check_deadline(deadline)
    conn.send(None)
    scorer.join(timeout=min(5, check_deadline(deadline)))
    if scorer.is_alive() or scorer.exitcode != 0:
        raise ProfileError('scorer did not exit cleanly')
    durable_json(out / 'training_complete.json', {'status': 'training_exported_reload_pending',
        'updates': 2, 'training_completions': 32, 'train_candidate_ids': selected,
        'generation_and_scoring_seconds': state['durations'],
        'elapsed_seconds': time.monotonic() - started,
        'cuda_peak_allocated': torch.cuda.max_memory_allocated(),
        'cuda_peak_reserved': torch.cuda.max_memory_reserved(),
        'heldout_scoring': False, 'scientific_result': False, 'automatic_retry': False})


def _reload_worker(args):
    if os.environ.get('Q2_PROFILE_PARENT_PID') != str(os.getppid()):
        raise ProfileError('reload must be launched by guarded parent')
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    out, final = Path(args.out), Path(args.out) / 'final_model'
    manifest = json.loads((out / 'final_model_manifest.json').read_text())
    for name, digest in manifest['files'].items():
        path = (final / name).resolve()
        if not path.is_relative_to(final.resolve()) or sha256(path) != digest:
            raise ProfileError('saved model artifact changed before reload')
    probe_manifest = json.loads((out / 'reload_probe_manifest.json').read_text())
    if sha256(out / 'reload_probe.pt') != probe_manifest['sha256']:
        raise ProfileError('reload probe changed')
    probe = torch.load(out / 'reload_probe.pt', map_location='cpu', weights_only=True)
    started = time.monotonic()
    torch.cuda.reset_peak_memory_stats()
    fresh = AutoModelForCausalLM.from_pretrained(final, local_files_only=True,
        trust_remote_code=False, torch_dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda').eval()
    tokenizer = AutoTokenizer.from_pretrained(final, local_files_only=True, trust_remote_code=False)
    ids = tokenizer.apply_chat_template(probe_manifest['prompt'], add_generation_prompt=True,
                                       return_tensors='pt')
    if not torch.equal(probe['input_ids'], ids):
        raise ProfileError('reloaded tokenizer changed probe rendering')
    with torch.inference_mode():
        after = fresh(input_ids=ids.to('cuda')).logits[:, -1, :].float().cpu()
    before = probe['logits']
    delta = float((before - after).abs().max())
    consistent = bool(torch.allclose(before, after, atol=0.02, rtol=0.002))
    durable_json(out / 'reload_check.json', {'max_abs_logit_difference': delta,
        'atol': 0.02, 'rtol': 0.002, 'passed': consistent,
        'probe_kind': 'one_training_prompt_last_token', 'seconds': time.monotonic() - started,
        'cuda_peak_allocated': torch.cuda.max_memory_allocated(),
        'scope': 'fresh_process_model_tokenizer_reload_not_optimizer_resume'})
    if not consistent:
        raise ProfileError('fresh model reload logit mismatch')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ('model-path', 'model-manifest', 'data-json', 'data-sha256', 'split-json', 'split-sha256', 'out'):
        p.add_argument('--' + flag, required=True)
    p.add_argument('--max-seconds', type=float, default=MAX_SECONDS)
    p.add_argument('--scorer-timeout', type=float, default=120)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--execute-engineering-profile', action='store_true')
    p.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--_reload', action='store_true', help=argparse.SUPPRESS)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    validate_args(args)
    if args._worker:
        try:
            (_reload_worker if args._reload else _worker)(args)
        except BaseException as exc:
            durable_json(Path(args.out) / ('reload_failure.json' if args._reload else 'worker_failure.json'),
                         {'error': repr(exc), 'retry': False})
            os._exit(1)  # Parent promptly stops our scorer/vLLM descendants; no atexit pool wait.
        os._exit(0)
    if args._reload:
        raise ProfileError('reload phase is parent-controlled')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    durable_json(out / 'profile_intent.json', {'profile': PROFILE, 'max_seconds': args.max_seconds,
        'started_unix': time.time(), 'run_nonce': str(uuid.uuid4()), 'scientific_result': False})
    command = [sys.executable, '-m', 'experiments.q2_supervision_migration.gpu_profile',
               *(argv if argv is not None else sys.argv[1:]), '--_worker']
    # Both child phases share one finite wall-clock allowance.
    deadline = time.monotonic() + args.max_seconds
    def interrupted(signum, frame):
        raise InterruptedError(f'launcher received signal {signum}')
    old_term = signal.signal(signal.SIGTERM, interrupted)
    try:
        result = launch_guarded(command, out, check_deadline(deadline), phase='train')
        if result:
            return result
        result = launch_guarded(command + ['--_reload'], out, check_deadline(deadline), phase='reload')
        if result == 0:
            durable_json(out / 'profile_complete.json', {'status': 'engineering_only_completed',
                'updates': 2, 'training_completions': 32, 'scientific_result': False,
                'heldout_scoring': False, 'fresh_process_reload_verified': True})
        return result
    finally:
        signal.signal(signal.SIGTERM, old_term)


if __name__ == '__main__':
    raise SystemExit(main())
