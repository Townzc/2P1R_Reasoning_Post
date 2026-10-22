"""Owner D2(a): exact complete benchmark subset, unchanged scientific functions.

The failed worker remains failed. A derived training-only view supplies the
original child's saved result to the unchanged training oracle; it is never
represented as an original complete worker RESULT. No model/remote operation.
"""
from collections import Counter
import math
from pathlib import Path
from experiments.p011 import long_owner_evidence as original
from experiments.p011.long_evaluation import BENCHMARK_COUNTS, paired_question_interval
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest

JOB = 'long_D2_S-F15_s17_owner_r1'
PACKET = 'reports/p011_20261020/d2_option_a_local_scope_v1'
DECISION = 'reports/p011_20261020/OWNER_D2_OPTION_A_20261021.json'
LOCAL = '.local/p011_20261020/r1/d2_option_a_r1'
PRESERVED = '.local/p011_20261020/r1/owner_D2_terminal_failure_preservation_r1'
COUNTS = {'math500':2500, 'aime24':240, 'aime25':240, 'amc23':92}
DISCLOSURE = 'D2 的 worker 在最后一批 AMC 评测时撞上硬计时器（9,000 s）；MATH-500 和 AIME 输出完整，AMC 不完整，未报告。'


def complete_ids():
    return {f'{b}:{i:04d}:{mode}:{seed}' for b,n in BENCHMARK_COUNTS.items()
            if b != 'amc23' for i in range(n)
            for mode,seeds in ([('sample',range(4)),('greedy',[0])]
                              if b == 'math500' else [('sample',range(8))])
            for seed in seeds}


def scoped_requests(requests):
    if len(requests) != 3300 or len({r['id'] for r in requests}) != 3300:
        raise ValueError('Original3300 unique request roster required')
    available = requests[:3072]
    if dict(Counter(r['id'].split(':')[0] for r in available)) != COUNTS:
        raise ValueError('Saved complete benchmark counts differ from owner scope')
    selected = [r for r in available if r['id'].split(':')[0] != 'amc23']
    if len(selected) != 2980 or {r['id'] for r in selected} != complete_ids():
        raise ValueError('Every original MATH/AIME endpoint must be complete')
    if any(r['id'].split(':')[0] != 'amc23' for r in requests[3072:]):
        raise ValueError('Missing228 must be AMC only')
    return selected


def journals(payload, key, ledger):
    expected = set(original.expected_record_keys(key,'student',64))
    absent = {key+'/terminal',key+'/done/eval_0006'}
    if set(ledger) != expected or {k for k,v in ledger.items() if v is None} != absent:
        raise ValueError('Exact original failed named-key roster differs')
    units = set(original.expected_units('student',64))
    result = []
    for directory,remote,names in [('intents','unit',units),
                                 ('completed','done',units-{'eval_0006'})]:
        if {p.stem for p in (payload/directory).glob('*.json')} != names:
            raise ValueError('Unexpected partial training or endpoint journal')
        values = {name:read(payload/directory/(name+'.json')) for name in names}
        if any(value != ledger[key+'/'+remote+'/'+name] for name,value in values.items()):
            raise ValueError('Saved local journal and original acknowledgment differ')
        result.append(values)
    return tuple(result)


def training_view(payload, out):
    """Create-only view; source payload is immutable and remains RESULT-less."""
    if (payload/'RESULT.json').exists():
        raise ValueError('This adapter is only for the exact failed original worker')
    out.mkdir(parents=True,exist_ok=False)
    for p in payload.iterdir():
        if p.is_symlink():raise ValueError('Preserved original payload cannot be symlinked')
        (out/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
    child = read(payload/'TRAINING_PROCESS_RESULT.json')
    dump(out/'RESULT.json',dict(training=child['result'],training_update_seconds=child['update_seconds'],
        derived_training_only_view=True,not_original_worker_result=True,
        source_child_sha256=sha(payload/'TRAINING_PROCESS_RESULT.json')))
    return out


def endpoint(payload, requests, context, eos, tokenizer, config, attempts, done, timing, train_times):
    selected = scoped_requests(requests)
    selected_ids = {r['id'] for r in selected}
    gpu = [{**{k:v for k,v in r.items() if k!='gold'},'request_sha256':digest(r)} for r in requests]
    original.validate_endpoint(gpu,context)
    names = {f'eval_{i:04d}' for i in range(6)}
    if {p.stem for p in (payload/'raw').glob('*.json')} != names:
        raise ValueError('Exactly six original complete raw batches required')
    decoded,stops,raw_bindings = {},Counter(),{}
    for index in range(6):
        name=f'eval_{index:04d}';first=index*512;part=requests[first:first+512]
        rawfile=payload/'raw'/(name+'.json');raw=read(rawfile);rawsha=sha(rawfile)
        ack=done[name];seconds=ack['seconds']
        if (attempts[name] != dict(requests=gpu[first:first+512],sampling=[original.sampling(r,eos) for r in part])
                or len(raw)!=512 or not isinstance(seconds,(float,int)) or not math.isfinite(seconds) or seconds<=0
                or ack!=dict(count=512,raw_file_sha256=rawsha,request_ids=[r['id'] for r in part],seconds=seconds)
                or [v['id'] for v in raw] != [r['id'] for r in part]):
            raise ValueError('Original complete raw batch intent/ack/order differs')
        raw_bindings[name]=rawsha
        for row,item in zip(part,raw):
            if row['id'] not in selected_ids:continue
            value=original.decode_record(row,item,eos,tokenizer,config['vocab_size'])
            value.update(raw_file='raw/'+name+'.json',raw_file_sha256=rawsha)
            decoded[row['id']]=value;stops[value['stop_reason']]+=1
    if set(decoded)!=selected_ids:raise ValueError('Scoped native decode is incomplete')
    final=requests[3072:]
    if attempts['eval_0006']!=dict(requests=gpu[3072:],sampling=[original.sampling(r,eos) for r in final]):
        raise ValueError('Original missing-AMC intent differs')
    expected_forecasts={f'eval_{i:04d}' for i in range(7)}|{f'update_{i:05d}' for i in range(1,65)}
    if {p.stem for p in (payload/'forecasts').glob('*.json')}!=expected_forecasts:
        raise ValueError('Original saved forecast roster differs')
    original.replay_forecast(read(payload/'PRE_ENGINE_FORECAST.json'),timing,0,7,train_times,[])
    engine=read(payload/'ENGINE.json');constructor=read(payload/'LINUX_CONSTRUCTORS.json')
    actual=dict(max_model_len=context,enforce_eager=False,dtype='torch.bfloat16',
        max_num_seqs=original.ENGINE_MAX_SEQS,max_num_batched_tokens=8192,enable_chunked_prefill=True,
        enable_prefix_caching=False,gpu_memory_utilization=.8,compilation_level=3,
        cudagraph_mode='FULL_AND_PIECEWISE',cudagraph_capture_sizes=original.GRAPH_CAPTURE_SIZES.copy())
    if (engine['requested']!=original.engine_settings(context) or engine['actual']!=actual
            or constructor['count']!=3300 or constructor['before_vllm_model_allocation'] is not True
            or constructor['all_native_prompt_texts_verified'] is not True):
        raise ValueError('Original engine/native constructor configuration differs')
    return dict(decoded=list(decoded.values()),scoring_rows=original.scoring_rows(selected,decoded),
        logical_stops=dict(stops),outputs_decoded=2980,technical_unknown_in_scored_scope=0,
        original_saved_raw_count=3072,raw_batch_bindings=raw_bindings,
        amc23=dict(status='incomplete',saved_raw=92,missing=228,expected=320,decoded=0,scored=0,
                   accuracy_reported=False,compared=False),
        original_worker_completed=False,complete_endpoint_cycle_array_available=False,
        endpoint_body_times_not_substituted_for_whole_cycles=True,
        endpoint_forecast_exact_replay_unavailable_without_whole_cycles=True,
        original_forecasts_retained=True,original_decode_and_scoring_rows_functions=True,
        symbolic_scoring_performed=False,new_model_calls=0,disclosure=DISCLOSURE)


def greedy_interval(left,right):
    if set(left)!=set(right) or len(left)!=500 or any(
            len(v)!=1 or type(v[0]) is not bool for table in (left,right) for v in table.values()):
        raise ValueError('Exactly500 paired one-greedy Boolean observations required')
    # Original function accepts four Boolean observations per question. Repeating
    # the one saved bit preserves its mean and every paired-bootstrap draw.
    value=paired_question_interval({k:v*4 for k,v in left.items()},{k:v*4 for k,v in right.items()})
    return dict(value,endpoint='math500_greedy',actual_model_samples_per_question=1,
                adapter='repeat each saved greedy bit four times only at unchanged mean/bootstrap interface',
                additional_model_samples=0)
