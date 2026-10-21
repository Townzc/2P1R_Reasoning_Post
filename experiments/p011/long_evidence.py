"""A/D complete payload verification candidate, before the outer CR-bound oracle.

Reads original state/raw/journal evidence only. No model allocation, training,
inference, symbolic scoring, checkpoint restoration or remote operation occurs.
The eventual CLI must separately authenticate source/input/review/claim/receipt,
artifact hashes and actual STOPPED0. These functions alone grant no admission.
"""
from collections import Counter
import math
from pathlib import Path

from experiments.sft_allocation_midpoint.common import read, sha, digest
from experiments.p011.long_training import ARMS, TARGETS, validate_plan
from experiments.p011.long_execution import validate_endpoint, engine_settings
from experiments.p011.long_evaluation import MAX_NEW_TOKENS, sampling, scoring_rows
from experiments.p011.long_numeric import forecast


def positive(values, count):
    if (type(values) is not list or len(values) != count or any(
            type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values)):
        raise ValueError('All original finite positive intervals required')
    return values


def expected_shapes(config, arm):
    """Qwen2 tied-embedding parameter coverage, independently from saved names."""
    h, middle = config['hidden_size'], config['intermediate_size']
    heads, kv, layers = (config[k] for k in
                        ('num_attention_heads', 'num_key_value_heads', 'num_hidden_layers'))
    if (arm not in ARMS or config['architectures'] != ['Qwen2ForCausalLM']
            or config['model_type'] != 'qwen2' or config['tie_word_embeddings'] is not True
            or any(type(v) is not int or v <= 0 for v in (h, middle, heads, kv, layers))
            or h % heads):
        raise ValueError('Pinned Qwen2 tied-embedding architecture required')
    shapes = {}
    if ARMS[arm]['mode'] == 'full':
        shapes['model.embed_tokens.weight'] = (config['vocab_size'], h)
    for i in range(layers):
        parent = f'model.layers.{i}.'
        matrices = {'q_proj': (h, h), 'k_proj': (kv*h//heads, h),
                    'v_proj': (kv*h//heads, h), 'o_proj': (h, h),
                    'gate_proj': (middle, h), 'up_proj': (middle, h), 'down_proj': (h, middle)}
        for name in TARGETS:
            stem = parent + ('self_attn.' if name in ('q_proj','k_proj','v_proj','o_proj') else 'mlp.') + name
            output, inputs = matrices[name]
            if ARMS[arm]['mode'] == 'lora':
                stem = 'base_model.model.'+stem
                shapes[stem+'.lora_A.default.weight'] = (64, inputs)
                shapes[stem+'.lora_B.default.weight'] = (output, 64)
            else:
                shapes[stem+'.weight'] = (output, inputs)
                if name in ('q_proj','k_proj','v_proj'):
                    shapes[stem+'.bias'] = (output,)
        if ARMS[arm]['mode'] == 'full':
            for name in ('input_layernorm', 'post_attention_layernorm'):
                shapes[parent+name+'.weight'] = (h,)
    if ARMS[arm]['mode'] == 'full':
        shapes['model.norm.weight'] = (h,)
    return shapes


def check_state(state, identity, encoded, plan, rates, arm, model_config):
    """Inspect every trainable tensor and AdamW slot; never instantiate a model."""
    import torch
    updates = plan['optimizer_updates']
    targets = sum(encoded[i]['n_supervised'] for row in plan['updates'] for i in row)
    processed = sum(encoded[i]['n_processed'] for row in plan['updates'] for i in row)
    if (state['schema'] != 'p011_complete_training_state_v1' or state['identity'] != identity
            or state['step'] != updates or state['cursor'] != updates
            or state['schedule'] != plan['updates'] or state['lrs'] != rates
            or state['supervised_tokens'] != targets or targets != plan['supervised_tokens']
            or state['processed_tokens'] != processed or state['adaptation_mode'] != ARMS[arm]['mode']
            or state['parameter_payload_meaning'] !=
            'all_trainable_parameters; full model for full arm, adapters for LoRA'):
        raise ValueError('Complete original state identity/dose/trajectory differs')
    names, tensors, optimizer = state['trainable_names'], state['adapter'], state['optimizer']
    shapes = expected_shapes(model_config, arm)
    if names != list(shapes) or set(tensors) != set(shapes):
        raise ValueError('Complete architecture-derived trainable parameter coverage required')
    groups = optimizer['param_groups']
    if len(groups) != 1:
        raise ValueError('Original one-group AdamW required')
    group = groups[0]
    params = group['params']
    if (len(params) != len(names) or len(set(params)) != len(params)
            or set(optimizer['state']) != set(params) or group['lr'] != rates[-1]
            or tuple(group['betas']) != (.9,.999) or group['eps'] != 1e-8
            or group['weight_decay'] != 0 or group['foreach'] is not False
            or group['amsgrad'] is not False or group['maximize'] is not False):
        raise ValueError('Original complete AdamW coverage or hyperparameters differ')
    parameter_count = 0
    for name, index in zip(names, params):
        tensor, slot = tensors[name], optimizer['state'][index]
        if (not isinstance(tensor,torch.Tensor) or tuple(tensor.shape) != shapes[name]
                or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all()
                or set(slot) != {'step','exp_avg','exp_avg_sq'}
                or not isinstance(slot['step'],torch.Tensor) or slot['step'].numel() != 1
                or float(slot['step']) != updates):
            raise ValueError('Complete finite trainable tensor/AdamW step required')
        for key in ('exp_avg','exp_avg_sq'):
            value = slot[key]
            if (not isinstance(value,torch.Tensor) or value.shape != tensor.shape
                    or value.dtype != tensor.dtype or not torch.isfinite(value).all()
                    or (key == 'exp_avg_sq' and bool((value < 0).any()))):
                raise ValueError('Complete finite AdamW moments required')
        parameter_count += tensor.numel()
    rng = state['rng']
    if (set(rng) != {'python','numpy','torch','cuda'} or not rng['python']
            or len(rng['numpy']) != 5 or len(rng['numpy'][1]) != 624
            or not isinstance(rng['torch'],torch.Tensor) or rng['torch'].dtype != torch.uint8
            or rng['torch'].numel() == 0 or len(rng['cuda']) != 1
            or not isinstance(rng['cuda'][0],torch.Tensor) or rng['cuda'][0].dtype != torch.uint8
            or rng['cuda'][0].numel() == 0):
        raise ValueError('All original Python/NumPy/Torch/CUDA RNG states required')
    return dict(targets=targets,processed=processed,updates=updates,
                trainable_tensors=len(names),trainable_parameters=parameter_count)


def load_state_once(root, identity, encoded, plan, rates, arm, config):
    import torch
    path = Path(root)/f"checkpoint_{plan['optimizer_updates']:04d}"
    record = read(path/'manifest.json')
    file = path/'state.pt'
    if (record['schema'] != 'p011_complete_training_state_v1' or record['file'] != 'state.pt'
            or record['identity_sha256'] != digest(identity) or file.stat().st_size != record['bytes']
            or sha(file) != record['sha256']):
        raise ValueError('Original terminal state bytes/identity differ')
    # mmap avoids a second in-memory copy of a full-parameter checkpoint.
    state = torch.load(file,map_location='cpu',weights_only=True,mmap=True)
    proof = check_state(state,identity,encoded,plan,rates,arm,config)
    if any(record[k] != state[k] for k in ('step','supervised_tokens','processed_tokens')):
        raise ValueError('Terminal state manifest dose differs')
    del state
    return {**proof,'state_sha256':record['sha256'],'record':record}


def expected_units(kind, updates):
    if kind not in ('student','baseline') or type(updates) is not int or updates < 0:
        raise ValueError('Admitted original job kind/update count required')
    if (kind == 'baseline') != (updates == 0):
        raise ValueError('Baseline zero updates and student positive updates required')
    training = ([f'update_{i:05d}' for i in range(1,updates+1)] +
                ['terminal_state','terminal_model_export']) if kind == 'student' else []
    return training + [f'eval_{i:04d}' for i in range(104)]


def expected_record_keys(key, kind, updates):
    if not key or key.endswith('/'):
        raise ValueError('Exact original nonempty record prefix required')
    return [key+'/claim',key+'/terminal'] + [key+'/'+stage+'/'+unit
        for unit in expected_units(kind,updates) for stage in ('unit','done')]


def verify_journals(root, key, kind, updates, ledger):
    root = Path(root)
    units = set(expected_units(kind,updates))
    values = {}
    if set(ledger) != set(expected_record_keys(key,kind,updates)):
        raise ValueError('Exact named-key roster has missing/extra records')
    for directory, remote in (('intents','unit'),('completed','done')):
        if {p.stem for p in (root/directory).glob('*.json')} != units:
            raise ValueError('Missing, extra or partial original unit')
        values[directory] = {name:read(root/directory/(name+'.json')) for name in units}
        if any(value != ledger[key+'/'+remote+'/'+name] for name,value in values[directory].items()):
            raise ValueError('Original local and immutable remote acknowledgments differ')
    return values['intents'],values['completed']


def replay_forecast(value, timing, left, batches, train_times, eval_times):
    now = timing['worker_start_epoch']+value['elapsed_worker_seconds']
    if value != forecast(timing,left,batches,train_times,eval_times,now):
        raise ValueError('Original complete-observation forecast differs')


def verify_training(root, encoded, plan, rates, arm, config, identity, attempts, done, timing):
    root = Path(root)
    proof = validate_plan(encoded,plan,rates,arm)
    child, result = read(root/'TRAINING_PROCESS_RESULT.json'),read(root/'RESULT.json')
    times = positive(child['update_seconds'],proof['U'])
    targets = processed = 0
    for step, indices in enumerate(plan['updates'],1):
        name = f'update_{step:05d}'
        expected = dict(step=step,indices=indices,lr=rates[step-1],
            supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),
            processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
        targets += expected['supervised_tokens'];processed += expected['processed_tokens']
        actual = done[name]
        if (attempts[name] != expected or any(actual.get(k)!=v for k,v in expected.items())
                or actual['cumulative_supervised'] != targets or actual['cumulative_processed'] != processed
                or actual['seconds'] != times[step-1]
                or any(type(actual[k]) not in (int,float) or not math.isfinite(actual[k])
                       for k in ('loss','gradient_norm','max_allocated_bytes'))
                or actual['gradient_norm'] < 0 or actual['max_allocated_bytes'] <= 0):
            raise ValueError('Exact complete per-update dose/finite proof differs')
        replay_forecast(read(root/'forecasts'/(name+'.json')),timing,
                        proof['U']-step+1,104,times[:step-1],[])
    state = load_state_once(root,identity,encoded,plan,rates,arm,config)
    exported, joined = read(root/'MODEL_EXPORT.json'),read(root/'TRAINING_EXIT.json')
    trained = {**proof,'actual_supervised_tokens':targets,'actual_processed_tokens':processed,
               'terminal_state':state['record'],'model_export_sha256':digest(exported)}
    if (child['result'] != trained or result['training'] != trained
            or result['training_update_seconds'] != times
            or attempts['terminal_state'] != proof or done['terminal_state'] != state['record']
            or attempts['terminal_model_export'] != dict(mode=ARMS[arm]['mode'],final_state=state['record'])
            or done['terminal_model_export'] != {'proof_sha256':digest(exported)}
            or exported['relative_path'] != 'model_for_vllm' or exported['final_state'] != state['record']
            or exported['mode'] != ARMS[arm]['mode'] or exported['evaluation_performed'] is not False
            or exported['optimizer_updates_after_terminal_state'] != 0
            or not exported['files'] or not any(n.endswith('.safetensors') for n in exported['files'])
            or joined != dict(pid=child['pid'],exitcode=0,joined_before_vllm=True,
                              model_export_file_sha256=sha(root/'MODEL_EXPORT.json'))):
        raise ValueError('Final-state/export/process-exit chain differs')
    return {**state,'training_seconds':times,'model_export':exported}


def decode_record(request, item, eos, tokenizer, vocab_size):
    """Native EOS/special/cap contract; no short-chain new-question delimiter."""
    if (item['id'] != request['id'] or item['request_sha256'] != digest(request)
            or item['prompt_token_ids'] != request['prompt_token_ids']
            or item['sampling'] != sampling(request,eos) or len(item['answers']) != 1):
        raise ValueError('Full original long response identity differs')
    answer = item['answers'][0];ids = answer['token_ids']
    if (not ids or len(ids)>MAX_NEW_TOKENS or any(type(i) is not int or not 0<=i<vocab_size for i in ids)
            or not isinstance(answer['backend_text'],str)):
        raise ValueError('Original full model-vocabulary response required')
    specials = set(tokenizer.all_special_ids)-set(eos)
    terminal = next(((i,'native_eos' if token in eos else 'invalid_special_token')
                     for i,token in enumerate(ids) if token in eos or token in specials),None)
    unknown = sorted(set(ids)-set(tokenizer.get_vocab().values()))
    if terminal:
        index, stop = terminal
        # A native configured stop cannot have generated tokens following it.
        if stop == 'native_eos' and (index != len(ids)-1 or answer['finish_reason'] not in ('stop','length')):
            raise ValueError('Native stop is not terminal or backend reports incomplete work')
        if unknown:
            raise ValueError('Unmapped tokens before a native/special completed stop')
        visible = ids[:index]
    else:
        if len(ids) != MAX_NEW_TOKENS or answer['finish_reason'] != 'length':
            raise ValueError('Incomplete stream is technical unknown, not an incorrect answer')
        stop,visible = 'length_cap',ids
    text = tokenizer.decode(visible,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    return dict(id=request['id'],request_sha256=digest(request),stop_reason=stop,answer_text=text,
        generated_tokens=len(ids),retained_tokens=len(visible)+(1 if terminal else 0),
        backend_finish_reason=answer['finish_reason'],backend_stop_reason=answer['stop_reason'],
        backend_text_sha256=digest(answer['backend_text']),unmapped_model_token_ids=unknown,
        raw_record_sha256=digest(item))


def verify_endpoint(root, requests, context, eos, tokenizer, config, attempts, done, timing, train_times):
    root = Path(root)
    gpu = [{**{k:v for k,v in r.items() if k!='gold'},'request_sha256':digest(r)} for r in requests]
    validate_endpoint(gpu,context)
    result = read(root/'RESULT.json')
    times = positive(result['endpoint_batch_seconds'],104)
    if result['raw_endpoint_count'] != 3300 or result['unique_questions'] != 600:
        raise ValueError('All3300 original endpoints required')
    if {p.stem for p in (root/'raw').glob('*.json')} != {f'eval_{i:04d}' for i in range(104)}:
        raise ValueError('Missing/extra original raw endpoint batch')
    decoded,stops = {},Counter()
    for index,first in enumerate(range(0,len(requests),32)):
        name = f'eval_{index:04d}';part=requests[first:first+32]
        rawfile=root/'raw'/(name+'.json');raw=read(rawfile)
        expected = dict(requests=gpu[first:first+32],sampling=[sampling(r,eos) for r in part])
        if (attempts[name] != expected or len(raw) != len(part)
                or done[name] != dict(count=len(part),raw_file_sha256=sha(rawfile),
                                     request_ids=[r['id'] for r in part],seconds=times[index])):
            raise ValueError('Complete original raw batch intent/ack differs')
        replay_forecast(read(root/'forecasts'/(name+'.json')),timing,0,104-index,train_times,times[:index])
        for row,item in zip(part,raw):
            value=decode_record(row,item,eos,tokenizer,config['vocab_size'])
            value.update(raw_file='raw/'+name+'.json',raw_file_sha256=sha(rawfile))
            decoded[row['id']]=value;stops[value['stop_reason']]+=1
    expected_forecasts = {f'eval_{i:04d}' for i in range(104)} | {
        f'update_{i:05d}' for i in range(1,len(train_times)+1)}
    if {p.stem for p in (root/'forecasts').glob('*.json')} != expected_forecasts:
        raise ValueError('Missing/extra original all-observation forecasts')
    replay_forecast(read(root/'PRE_ENGINE_FORECAST.json'),timing,0,104,train_times,[])
    engine = read(root/'ENGINE.json')
    settings = engine_settings(context)
    expected_actual = dict(max_model_len=context,enforce_eager=False,dtype='torch.bfloat16',
        max_num_seqs=32,max_num_batched_tokens=8192,enable_chunked_prefill=True,
        enable_prefix_caching=False,gpu_memory_utilization=.8,compilation_level=3,
        cudagraph_mode='FULL_AND_PIECEWISE',cudagraph_capture_sizes=[1,2,4,8,16,32])
    constructor = read(root/'LINUX_CONSTRUCTORS.json')
    if (engine['requested'] != settings or engine['actual'] != expected_actual
            or constructor['count'] != 3300 or constructor['before_vllm_model_allocation'] is not True
            or constructor['all_native_prompt_texts_verified'] is not True):
        raise ValueError('Original engine or Linux constructor/prompt proof differs')
    return dict(decoded=list(decoded.values()),scoring_rows=scoring_rows(requests,decoded),
        logical_stops=dict(stops),outputs_decoded=3300,technical_unknown=0,
        symbolic_scoring_performed=False,training_or_model_calls=0)
