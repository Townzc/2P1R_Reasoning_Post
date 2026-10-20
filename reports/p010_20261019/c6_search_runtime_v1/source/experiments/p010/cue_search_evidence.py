"""Original C6 full probability/raw replay; no model call or correctness label."""
from collections import Counter
from pathlib import Path
import math
from analyses.completion_contract import first_stop
from experiments.p010.common import read, dump, sha, digest
from experiments.p010.cue_selection import propose
from experiments.p010.cue_search_contract import screen_rows, sampling, forecast
from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine


def record_keys():
    base = 'cue/search_r1'
    return [base+'/claim',base+'/terminal'] + [base+'/'+kind+f'/{offset:05d}'
        for offset in range(0,10080,256) for kind in ('screen','screen_done')]


def decode(row, item, tokenizer, mapped, special):
    if (item.get('candidate_id') != row['candidate_id']
            or item.get('problem_id') != row['problem_id']
            or item.get('source_row_sha256') != row['source_row_sha256']
            or item.get('prompt_token_ids') != row['input_ids']
            or item.get('sampling') != sampling(row['rollout'])
            or item.get('output_count') != 1 or not isinstance(item.get('backend_text'),str)):
        raise ValueError('Original cue response identity differs')
    ids = item.get('token_ids')
    if (not isinstance(ids,list) or not ids or len(ids)>1024
            or any(type(x) is not int or not 0<=x<151936 for x in ids) or set(ids)-mapped):
        raise ValueError('Unknown or incomplete raw tokens are not missing answers')
    positions = [i for i,t in enumerate(ids) if t==151643]
    if positions:
        if positions != [len(ids)-1]:
            raise ValueError('Interior or repeated native EOS')
        if item['finish_reason']=='stop':
            if item['stop_reason'] not in (None,151643):
                raise ValueError('Foreign stop token')
        elif not (len(ids)==1024 and item['finish_reason']=='length' and item['stop_reason'] is None):
            raise ValueError('Only exact-cap native EOS permits backend length metadata')
    elif len(ids)!=1024 or item['finish_reason']!='length' or item['stop_reason'] is not None:
        raise ValueError('Short unconfirmed completion is a technical failure')
    # Cue tokens are an explicit forced assistant prefix, not generated again.
    # The1024 cap applies only to new continuation tokens. Logical boundaries
    # and answer extraction see the complete assistant content including cue.
    cue = row['cue_token_ids']
    return first_stop(cue+ids,lambda x:tokenizer.decode(x,skip_special_tokens=False,
        clean_up_tokenization_spaces=False),151643,1024+len(cue),special)


def replay_proposal(root, dev, tokenizer):
    import numpy as np
    root = Path(root)
    allowed = sorted(set(tokenizer.get_vocab().values())-set(tokenizer.all_special_ids))
    if read(root/'ALLOWED_CUE_TOKENS.json') != allowed:
        raise ValueError('Supported non-special cue vocabulary differs')
    seen = set()

    def original_matrix(prefix):
        name = 'root' if not prefix else 'token_'+str(prefix[0])
        if name in seen:
            raise ValueError('Original proposal requests a duplicate prefix')
        seen.add(name)
        directory = root/'probabilities'/name
        intent = read(directory/'INTENT.json')
        done = read(directory/'COMPLETED.json')
        file = directory/'full_probabilities.npy'
        if (intent['prefix'] != list(prefix) or intent['problem_ids'] != [r['problem_id'] for r in dev]
                or intent['gold_used'] is not False or intent['correctness_used'] is not False
                or intent['retries'] != 0 or done['prefix'] != list(prefix)
                or done['rows'] != 30 or done['vocab_size'] != 151936
                or done['dtype'] != 'float32' or done['matrix_sha256'] != sha(file)
                or not math.isfinite(done['seconds']) or done['seconds'] <= 0
                or done['generated_answers'] != 0):
            raise ValueError('Original full probability measurement binding differs')
        array = np.load(file,allow_pickle=False)
        if array.dtype != np.float32 or array.shape != (30,151936):
            raise ValueError('Original full-vocabulary FP32 matrix required')
        return array.tolist()

    replay = propose(original_matrix,[r['problem_id'] for r in dev],allowed,151936)
    if (replay != read(root/'PROPOSAL.json') or len(seen) != 21
            or seen != {p.name for p in (root/'probabilities').iterdir()}):
        raise ValueError('Full original probability replay differs')
    complete = read(root/'PROPOSAL_COMPLETED.json')
    exited = read(root/'PROPOSAL_EXIT.json')
    environment = read(root/'PROPOSAL_ENVIRONMENT.json')
    if (complete['prefix_measurements'] != 21 or complete['generated_answers'] != 0
            or complete['training_updates'] != 0 or exited['exitcode'] != 0
            or exited['joined_before_vllm'] is not True
            or complete['pid'] != exited['pid'] or environment['pid'] != exited['pid']
            or environment['generated_answers'] != 0 or environment['training_updates'] != 0
            or environment['tokenizer_vocab_queries'] != 1 or environment['seed'] != 17
            or environment['attention'] != 'sdpa' or environment['pad_token_id'] != 151643
            or environment['software']['cuda'] != '12.8'
            or 'H100' not in environment['software']['gpu']):
        raise ValueError('Original probability lifetime/exit proof differs')
    required = dict(vllm='0.11.0',transformers='4.56.2',tokenizers='0.22.1',
                    peft='0.17.1',numpy='2.2.6',safetensors='0.6.2')
    versions = environment['software']['versions']
    if any(versions[k] != v for k,v in required.items()) or versions['torch'].split('+')[0] != '2.8.0':
        raise ValueError('Original pinned software differs')
    return replay, allowed


def verify_raw(root, dev, ledger, spec, prior, tokenizer, out):
    root, out = Path(root), Path(out)
    proposal, allowed = replay_proposal(root,dev,tokenizer)
    rows = screen_rows(dev,proposal,allowed)
    if rows != read(root/'SCREEN_ROSTER.json'):
        raise ValueError('Exact original complete development roster differs')
    validate_observed_engine(read(root/'ENGINE.json'))
    result = read(root/'RESULT.json')
    times = result['screen_batch_seconds']
    if (result['run'] != 'search_r1' or result['raw_development_outputs'] != 10080
            or result['candidates'] != 21 or result['dev_questions'] != 30 or result['rollouts'] != 16
            or result['new_training_updates'] != 0 or result['gold_used'] is not False
            or result['correctness_used'] is not False or result['test_data_used'] is not False
            or result['selected_cue'] is not None or len(times) != 40
            or any(not math.isfinite(t) or t<=0 for t in times)):
        raise ValueError('Original complete unscored search scope differs')
    names = {f'{i:05d}.json' for i in range(0,10080,256)}
    for name in ('raw','screen_intents','screen_acks','screen_forecasts'):
        if {p.name for p in (root/name).glob('*.json')} != names:
            raise ValueError('Missing or extra development batch')
    for filename, finished in [('BEFORE_PROPOSAL_FORECAST.json',False),('BEFORE_SCREEN_FORECAST.json',True)]:
        f = read(root/filename)
        if f != forecast(f['elapsed_seconds'],0,[],spec['batch_observations_seconds'],prior,proposal_complete=finished):
            raise ValueError('Original proposal/screen admission differs')
    mapped = set(tokenizer.get_vocab().values())
    special = tuple(tokenizer.all_special_ids)
    decoded, stops = [], Counter()
    for index, offset in enumerate(range(0,10080,256)):
        unit = f'{offset:05d}'
        part = rows[offset:offset+256]
        raw_file = root/'raw'/(unit+'.json')
        raw, intent, ack, f = [read(root/name/(unit+'.json'))
            for name in ('raw','screen_intents','screen_acks','screen_forecasts')]
        if (intent['rows'] != part or intent['sampling'] != [sampling(r['rollout']) for r in part]
                or len(raw) != len(part) or ledger['cue/search_r1/screen/'+unit] != intent
                or ledger['cue/search_r1/screen_done/'+unit] != ack
                or ack != dict(count=len(part),seconds=times[index],raw_sha256=digest(raw))
                or f != forecast(f['elapsed_seconds'],index,times[:index],
                    spec['batch_observations_seconds'],prior,proposal_complete=True)):
            raise ValueError('Original request/raw/ack/forecast differs')
        batch = []
        raw_hash = sha(raw_file)
        for row,item in zip(part,raw):
            stop = decode(row,item,tokenizer,mapped,special)
            batch.append(dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],
                candidate=row['candidate'],rollout=row['rollout'],cue_token_ids=row['cue_token_ids'],
                stop=stop,raw_record_sha256=digest(item),raw_file='raw/'+unit+'.json',raw_file_sha256=raw_hash))
            stops[stop['stop_reason']] += 1
        dump(out/'confirmed_batches'/(unit+'.json'),batch)
        decoded.extend(batch)
    return decoded,dict(rows=10080,logical_stops=dict(stops),technical_unknown=0,
        original_probability_matrices=21,raw_batches=40,model_calls=0,gold_used=False,
        correctness_used=False,primary_scoring=False)
