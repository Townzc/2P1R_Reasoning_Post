"""Prepared B-only native T1.5 engine and original-input adapter.

No public entry or admission. The full outer path must bind CR/A1/A2, original
owner B16 decision, inputs, assets, common ledger and deadline before use.
"""
from pathlib import Path
from experiments.p010.common import MODELS, read, verify, digest
from experiments.p010.teacher_contract import SYSTEM
from experiments.p010.teacher_transport import completion
from experiments.p011.b_generation_execution import validate_queue
from experiments.p011.short_generation import b_requests, b_selection
from experiments.learning_regime_p009.math_scoring import last_box
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine


def original_inputs(roster, source, original_requests):
    """Project existing P010 prompt token lists, without tokenizer or old scores."""
    ids = roster['s1']['400']
    if len(ids) != 400 or len(set(ids)) != 400:
        raise ValueError('Exactly original ordered400 parents required')
    lookup = {r['problem_id']: r for r in source}
    if len(lookup) != len(source) or not set(ids) <= set(lookup):
        raise ValueError('Complete original source identities required')
    prompts = {}
    for row in original_requests:
        if row['problem_id'] in ids:
            pid = row['problem_id']
            if row['model'] != 't15' or (pid in prompts and prompts[pid] != row['prompt_token_ids']):
                raise ValueError('Original teacher or native prompt differs')
            prompts[pid] = list(row['prompt_token_ids'])
    rows = b_requests(ids, prompts, 1.0)
    validate_queue(ids, prompts, rows)
    gold = []
    for pid in ids:
        value = last_box(lookup[pid]['solution'])
        if not value['answer']:
            raise ValueError('Unsupported original gold must be reported, not invented')
        gold.append({'problem_id':pid, 'gold':value['answer'],
                     'original_source_row_sha256':digest(lookup[pid])})
    return {'ordered400':ids, 'prompts':prompts, 'rows':rows,
            'source':{pid:lookup[pid] for pid in ids}, 'gold':gold,
            'original_outputs_read_or_scored':0, 'new_token_encodings':0}


def check_native_prompts(tokenizer, pack):
    for pid in pack['ordered400']:
        native = tokenizer.apply_chat_template([
            {'role':'system','content':SYSTEM},
            {'role':'user','content':pack['source'][pid]['problem']}],
            tokenize=True, add_generation_prompt=True)
        if native != pack['prompts'][pid]:
            raise ValueError('Original native prompt differs; no silent re-encoding')


def checked_assets(assets):
    if ((assets['model_id'], assets['revision']) != MODELS['t15']
            or not assets.get('files') or not assets.get('remote_path_producer')):
        raise ValueError('Original pinned T1.5 assets and exact writer required')
    verify(assets['remote_path'], assets['files'])
    cfg = read(Path(assets['remote_path'])/'config.json')
    gen = read(Path(assets['remote_path'])/'generation_config.json')
    if cfg['vocab_size'] != 151936 or gen['eos_token_id'] != [151645,151643]:
        raise ValueError('Original model vocabulary/native EOS config differs')
    return cfg


def transport_reader(tokenizer, vocabulary_size):
    mapped = set(tokenizer.get_vocab().values())
    special = set(tokenizer.all_special_ids)
    def transport(raw):
        stop, evidence = completion(raw, tokenizer, mapped, vocabulary_size, special)
        return {'stop':stop, 'transport':evidence, 'answer_text':stop['answer_segment'],
                'raw_record_sha256':digest(raw)}
    return transport


def load(pack, assets):
    import torch
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    if (torch.cuda.device_count() != 1 or 'H100' not in torch.cuda.get_device_name(0)
            or torch.cuda.get_device_properties(0).total_memory < 75*1024**3):
        raise ValueError('Original single H10080GB allocation required')
    cfg = checked_assets(assets)
    tok = AutoTokenizer.from_pretrained(assets['remote_path'], local_files_only=True)
    check_native_prompts(tok, pack)
    validate_queue(pack['ordered400'], pack['prompts'], pack['rows'])
    for row in pack['rows']:
        SamplingParams(**row['sampling'])
    kwargs = engine_kwargs()
    llm = LLM(model=assets['remote_path'], tokenizer=assets['remote_path'], **kwargs)
    actual = actual_engine(llm.llm_engine.vllm_config)
    if llm.llm_engine.vllm_config.parallel_config.tensor_parallel_size != 1:
        raise ValueError('Original single-GPU engine required')
    return llm, SamplingParams, transport_reader(tok, cfg['vocab_size']), {
        'model':assets, 'engine':actual, 'requested':kwargs,
        'native_prompts_checked':400, 'new_training':0}


def score_rows(pack, raw, transports):
    """Bind complete new raw/decoded rows to original supported gold, no score."""
    if len(raw) != 6400 or len(transports) != 6400:
        raise ValueError('Complete new6400 raw and decoded rows required')
    gold = {r['problem_id']:r for r in pack['gold']}
    rows = []
    for index, (item, decoded) in enumerate(zip(raw, transports)):
        req = pack['rows'][index]['request']; pid = req['problem_id']
        if (item['candidate_id'] != req['candidate_id']
                or item['problem_id'] != pid
                or item['sampling'] != pack['rows'][index]['sampling']
                or decoded['raw_record_sha256'] != digest(item)
                or decoded['answer_text'] != decoded['stop']['answer_segment']):
            raise ValueError('Original complete raw/transport identity differs')
        rows.append({'id':'p011_b_t10/'+req['candidate_id'], 'candidate_id':req['candidate_id'],
            'problem_id':pid, 'attempt':req['attempt'], 'gold':gold[pid]['gold'],
            'answer_segment':decoded['answer_text'], 'stop_reason':decoded['stop']['stop_reason'],
            'original_gold_row_sha256':gold[pid]['original_source_row_sha256'],
            'raw_record_sha256':digest(item), 'decoded_record_sha256':digest(decoded)})
    return rows


def selected_records(pack, raw, transports, scored):
    """Selection uses only saved Boolean verdicts; no decoder/scorer calls."""
    rows = score_rows(pack, raw, transports)
    if ([x['id'] for x in scored] != [r['id'] for r in rows]
            or any(type(x['score'].get('correct')) is not bool for x in scored)):
        raise ValueError('All6400 original ordered Boolean verdicts required')
    from experiments.p010.dataset_selection import usable
    records = {}
    for row, decoded, score in zip(rows, transports, scored):
        item = {'candidate_id':row['candidate_id'], 'problem_id':row['problem_id'],
            'attempt':row['attempt'], 'answer_text':row['answer_segment'],
            'stop':decoded['stop'], 'transport':decoded['transport'], 'score':score,
            'gold_supported':True, 'raw_record_sha256':row['raw_record_sha256'],
            'decoded_record_sha256':row['decoded_record_sha256']}
        item['usable'] = usable(item); records[row['candidate_id']] = item
    return records, b_selection(pack['ordered400'], records)
