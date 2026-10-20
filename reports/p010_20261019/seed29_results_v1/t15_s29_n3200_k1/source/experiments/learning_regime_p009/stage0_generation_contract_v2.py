"""Finite P2/P3 transport contract; no scoring, dispatch or admission authority."""
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import json
import math
from pathlib import Path

from experiments.sft_allocation_midpoint.common import digest, sha
from experiments.learning_regime_p009.high_throughput_v1 import BATCH_SIZE


MODELS = {
    'teacher': dict(model_id='Qwen/Qwen2.5-Math-1.5B-Instruct',
        revision='aafeb0fc6f22cbf0eaeed126eff8be45b0360a35',
        architecture='Qwen2ForCausalLM', vocab_size=151936, eos_token_ids=[151645, 151643]),
    'qwen': dict(model_id='Qwen/Qwen2.5-1.5B',
        revision='8faed761d45a263340a0528343f099c05c9a4323',
        architecture='Qwen2ForCausalLM', vocab_size=151936, eos_token_ids=[151643]),
    'olmo': dict(model_id='allenai/OLMo-2-0425-1B',
        revision='a1847dff35000b4271fa70afc5db10fd29fedbdf',
        architecture='Olmo2ForCausalLM', vocab_size=100352, eos_token_ids=[100257]),
}

# Exact filenames and hashes from the already frozen Stage0 input release.
DATASETS = {
    'math_procurement': dict(model='teacher', file='math_teacher_requests8993.jsonl',
        sha256='d835c0296f2d98575578566c0a06d203b6d95918ab7af00c87efdd7c8cd4e0ce',
        n=8993, max_new_tokens=1024, procurement=True),
    'teacher_gsm_zero': dict(model='teacher', file='teacher_gsm_zero.json',
        sha256='14d332a3d50ff9b89358df30200dc4de373f39cddd18d84bb94b4491975ed47a',
        n=1319, max_new_tokens=512, procurement=False),
    'teacher_math_zero': dict(model='teacher', file='teacher_math_zero.json',
        sha256='64f07d5923e81af08bd7763d033b62ec7d6d09ef0f543539cfad70e6545377b6',
        n=500, max_new_tokens=1024, procurement=False),
    'qwen_math_zero': dict(model='qwen', file='qwen_math_zero.json',
        sha256='e091b60d6548bd68f64920f8b5853d56547e55576fee8cc892f1867f7e80443f',
        n=500, max_new_tokens=1024, procurement=False),
    'qwen_math_four': dict(model='qwen', file='qwen_math_four.json',
        sha256='60e3d2f03883aff0462c55e803ccac139316113a886d717cd47de0d79a73b406',
        n=500, max_new_tokens=1024, procurement=False),
    'olmo_gsm_zero': dict(model='olmo', file='olmo_gsm_zero.json',
        sha256='0e66a93d6fe147168b5ede7e70fc1cf44f8accc0b81df14c355770a6d8c2d101',
        n=1319, max_new_tokens=512, procurement=False),
    'olmo_gsm_four': dict(model='olmo', file='olmo_gsm_four.json',
        sha256='5a98f29a6062f48ba8ad55206ad7a8bb429079426012d58db5616ab06f57625f',
        n=1319, max_new_tokens=512, procurement=False),
}

# A candidate grouping, not permission to call a worker. No old P0 endpoint is
# listed. Exact model/upload/source/review/numeric gates must precede dispatch.
SLOTS = {
    'teacher_p2_p3': dict(model='teacher',
        datasets=['math_procurement', 'teacher_gsm_zero', 'teacher_math_zero'],
        worker_seconds=7200, reserved_cents=985, stage0_remaining_before_cents=2996),
    'qwen_p3': dict(model='qwen', datasets=['qwen_math_zero', 'qwen_math_four'],
        worker_seconds=1800, reserved_cents=326, stage0_remaining_before_cents=2011),
    'olmo_p3': dict(model='olmo', datasets=['olmo_gsm_zero', 'olmo_gsm_four'],
        worker_seconds=1800, reserved_cents=326, stage0_remaining_before_cents=1685),
}
PRIOR_RESERVED_CENTS = 1004
STAGE0_CAP_CENTS = 4000
EXPERIMENT_CAP_CENTS = 13000
STARTUP_SECONDS = 600
EXTRA_WINDOW_SECONDS = 700
ALLOWANCE_CENTS = 20
RATE = Decimal('0.00122044')


def cost_cents(seconds):
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Finite nonnegative time required')
    return int((Decimal(str(seconds))*RATE*100).to_integral_value(rounding=ROUND_CEILING))


def slot_checked(run_id):
    slot = deepcopy(SLOTS[run_id])
    slot['platform_seconds'] = slot['worker_seconds']+60
    slot['startup_seconds'] = STARTUP_SECONDS
    slot['full_window_seconds'] = slot['worker_seconds']+EXTRA_WINDOW_SECONDS
    if cost_cents(slot['full_window_seconds'])+ALLOWANCE_CENTS != slot['reserved_cents']:
        raise ValueError('Candidate full-window reserve differs')
    if PRIOR_RESERVED_CENTS+sum(s['reserved_cents'] for s in SLOTS.values()) > STAGE0_CAP_CENTS:
        raise ValueError('No release of an old reservation or borrowing from unallocated funds')
    return slot


def dataset(name):
    return deepcopy(DATASETS[name])


def ids_checked(ids, vocab, maximum):
    if (not isinstance(ids, list) or not 1 <= len(ids) <= maximum
            or any(type(x) is not int or not 0 <= x < vocab for x in ids)):
        raise ValueError('Missing, truncated, padded or invalid token IDs')


def normalize_rows(name, content):
    """Copy source identities and token IDs; no answer decoding/filtering here."""
    ds = DATASETS[name]; model = MODELS[ds['model']]
    if ds['procurement']:
        original = content
    else:
        if (content.get('n') != ds['n'] or content.get('max_context') != 2048
                or content.get('max_new_tokens') != ds['max_new_tokens']
                or content.get('eos_token_id') != model['eos_token_ids'][0]):
            raise ValueError('Frozen endpoint metadata differs')
        original = content['prompts']
    if not isinstance(original, list) or len(original) != ds['n']:
        raise ValueError('Full frozen roster required; no subsampling')
    rows = []; seen = set()
    for raw in original:
        if ds['procurement']:
            if set(raw) != {'candidate_id', 'problem_id', 'attempt', 'seed', 'prompt_token_ids'}:
                raise ValueError('Unexpected teacher request schema')
            cid, pid = raw['candidate_id'], raw['problem_id']
            attempt, seed, ids = raw['attempt'], raw['seed'], raw['prompt_token_ids']
            if (type(attempt) is not int or not 1 <= attempt <= 4
                    or cid != f'{pid}::attempt{attempt:02d}'
                    or type(seed) is not int or not 0 <= seed < 2**32):
                raise ValueError('Frozen teacher attempt or per-request seed differs')
        else:
            if set(raw) != {'problem_id', 'input_ids'}:
                raise ValueError('Unexpected endpoint row schema')
            pid, ids = raw['problem_id'], raw['input_ids']
            cid, attempt, seed = name+'::'+pid, None, 17
        if not isinstance(pid, str) or not pid or cid in seen:
            raise ValueError('Missing or repeated frozen request identity')
        ids_checked(ids, model['vocab_size'], 2048-ds['max_new_tokens'])
        rows.append(dict(candidate_id=cid, problem_id=pid, attempt=attempt, seed=seed,
            input_ids=list(ids), source_row_sha256=digest(raw)))
        seen.add(cid)
    return rows


def load_rows(root, name):
    ds = DATASETS[name]; path = Path(root)/ds['file']
    if path.is_symlink() or sha(path) != ds['sha256']:
        raise ValueError('Original frozen input bytes required')
    if ds['procurement']:
        # Only physical JSONL newlines delimit records; U+2028 in JSON is data.
        with path.open(encoding='utf-8') as f:
            content = [json.loads(line) for line in f]
    else:
        content = json.loads(path.read_text())
    return normalize_rows(name, content)


def sampling(name, row):
    ds = DATASETS[name]
    return dict(n=1, temperature=.8 if ds['procurement'] else 0,
        top_p=.95 if ds['procurement'] else 1, top_k=-1, repetition_penalty=1,
        max_tokens=ds['max_new_tokens'], seed=row['seed'], stop=None,
        stop_token_ids=list(MODELS[ds['model']]['eos_token_ids']), ignore_eos=False,
        detokenize=True, skip_special_tokens=False, include_stop_str_in_output=True)


def transport_checked(name, rows, outputs):
    """Check original transport, not logical first-stop or mathematical truth."""
    ds = DATASETS[name]; model = MODELS[ds['model']]
    if len(rows) != len(outputs) or not 1 <= len(rows) <= BATCH_SIZE:
        raise ValueError('Missing/extra output; retain original bytes and never replay')
    for row, raw in zip(rows, outputs):
        if (raw.get('candidate_id') != row['candidate_id']
                or raw.get('problem_id') != row['problem_id']
                or raw.get('source_row_sha256') != row['source_row_sha256']
                or raw.get('sampling') != sampling(name, row)
                or raw.get('prompt_token_ids') != row['input_ids']
                or raw.get('output_count') != 1
                or not isinstance(raw.get('backend_text'), str)):
            raise ValueError('Output identity/prompt/sampling differs')
        ids = raw['token_ids']; ids_checked(ids, model['vocab_size'], ds['max_new_tokens'])
        positions = [i for i, token in enumerate(ids) if token in model['eos_token_ids']]
        if positions:
            if positions != [len(ids)-1]:
                raise ValueError('Interior/repeated EOS; do not repair returned tokens')
            if raw.get('finish_reason') == 'stop':
                if raw.get('stop_reason') not in (None, ids[-1]):
                    raise ValueError('Unexpected native EOS stop reason')
            elif not (len(ids) == ds['max_new_tokens'] and raw.get('finish_reason') == 'length'
                      and raw.get('stop_reason') is None):
                raise ValueError('Only native EOS at the exact token cap permits length metadata')
        elif (len(ids) != ds['max_new_tokens'] or raw.get('finish_reason') != 'length'
              or raw.get('stop_reason') is not None):
            raise ValueError('Unknown short termination or non-native stopping')
    return len(outputs)


def remaining_forecast(run_id, elapsed, durations, remaining_batches):
    slot = slot_checked(run_id)
    total_batches = sum(math.ceil(DATASETS[n]['n']/BATCH_SIZE) for n in slot['datasets'])
    if (not math.isfinite(elapsed) or elapsed < 0 or not durations
            or any(not math.isfinite(x) or x <= 0 for x in durations)
            or type(remaining_batches) is not int or not 0 <= remaining_batches < total_batches):
        raise ValueError('Real complete new-worker batch intervals required')
    remaining = 1.2*(max(durations)*remaining_batches+300)
    total = elapsed+remaining
    cents = cost_cents(total+EXTRA_WINDOW_SECONDS)+ALLOWANCE_CENTS
    return dict(elapsed_worker_seconds=elapsed, full_batch_max_seconds=max(durations),
        observed_batches=len(durations), remaining_batches=remaining_batches,
        remaining_seconds=remaining, predicted_worker_seconds=total, predicted_cents=cents,
        stage0_remaining_before_cents=slot['stage0_remaining_before_cents'],
        admitted=(total <= slot['worker_seconds']-30
                  and cents*5 <= slot['stage0_remaining_before_cents']*4
                  and cents <= slot['reserved_cents']),
        old_P0_timings_used=False, future_allowance_seconds=300,
        calibrated_bound=False, first_measurement_exception=False)
