"""Prepared complete C6 benchmark payload replay; no model or symbolic scorer.

Outer source/receipt/provider/parent/selection admission remains required in the
future full wrapper. This module alone never admits a benchmark or analysis.
"""
from collections import Counter
from pathlib import Path
from math import isfinite
from analyses.completion_contract import first_stop
from experiments.p010.common import read,dump,digest,sha
from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine


def decode(row,item,tokenizer,mapped,special):
    expected=dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],
        source_row_sha256=row['source_row_sha256'],prompt_token_ids=row['input_ids'],
        sampling=row['sampling'],output_count=1)
    if any(item.get(k)!=v for k,v in expected.items()) or not isinstance(item.get('backend_text'),str):
        raise ValueError('Original cue benchmark response identity differs')
    ids=item.get('token_ids');cap=row['sampling']['max_tokens'];cue=row['cue_token_ids']
    if (not isinstance(ids,list) or not ids or len(ids)>cap
            or any(type(t) is not int or not 0<=t<151936 for t in ids)
            or row['input_ids']!=row['original_input_ids']+cue
            or len(row['input_ids'])+cap>2048):
        raise ValueError('Full original prompt and forced prefix cannot be truncated')
    unmapped=sorted(set(ids)-mapped)
    if unmapped and (len(ids)!=cap or item.get('finish_reason')!='length'
                     or any(t in (151643,151645) for t in ids)):
        raise ValueError('Unmapped token outside the retained no-EOS cap stream')
    eos=[i for i,t in enumerate(ids) if t==151643]
    if eos:
        if eos!=[len(ids)-1]:raise ValueError('Interior or repeated native EOS')
        if item.get('finish_reason')=='stop':
            if item.get('stop_reason') not in (None,151643):raise ValueError('Foreign stop token')
        elif not (len(ids)==cap and item.get('finish_reason')=='length' and item.get('stop_reason') is None):
            raise ValueError('Only exact-cap native EOS accepts backend length metadata')
    elif len(ids)!=cap or item.get('finish_reason')!='length' or item.get('stop_reason') is not None:
        raise ValueError('Short unconfirmed completion is a technical failure')
    logical=first_stop(cue+ids,lambda x:tokenizer.decode(x,skip_special_tokens=False,
        clean_up_tokenization_spaces=False),151643,cap+len(cue),special)
    return logical,unmapped


def record_keys(run,count):
    if run not in ('base_math','base_gsm','s1_n400_math','t72_n400_math') or type(count) is not int or count<=0:
        raise ValueError('Positive admitted original benchmark generation count required')
    key='cue/benchmark_r1/'+run
    return [key+'/claim',key+'/terminal']+[key+'/'+kind+f'/{offset:05d}'
        for offset in range(0,count,256) for kind in ('batch','batch_done')]


def replay(root,roster,ledger,tokenizer,gold,forecasts,out):
    """One full raw replay with caller-recomputed, exact complete forecasts.

    Reused and empty-cue alias conditions are intentionally absent from new raw.
    Their separately bound original proof is required by the future outer wrapper.
    No correctness values influence the roster, choice of cue or this replay.
    """
    root,out=Path(root),Path(out);rows=roster['rows'];run=roster['run'];count=len(rows)
    if count!=roster['new_outputs'] or count<=0 or len({r['candidate_id'] for r in rows})!=count:
        raise ValueError('All and only original unattempted outputs required')
    if set(gold)!=set(roster['problem_ids']):raise ValueError('Exact full original gold problem roster required')
    if read(root/'BENCHMARK_ROSTER.json')!=roster:raise ValueError('Original frozen roster differs')
    validate_observed_engine(read(root/'ENGINE.json'))
    names={f'{offset:05d}.json' for offset in range(0,count,256)}
    if set(forecasts)!=names:raise ValueError('All original forecasts must be independently recomputed')
    for folder in ('raw','batch_intents','batch_acks','batch_forecasts'):
        if {p.name for p in (root/folder).glob('*.json')}!=names:raise ValueError('Missing or extra original batch')
    mapped=set(tokenizer.get_vocab().values());special=tuple(tokenizer.all_special_ids)
    decoded=[];scoring=[];counts=Counter();stops=Counter();unknown_tokens=0
    key='cue/benchmark_r1/'+run
    for offset in range(0,count,256):
        name=f'{offset:05d}.json';part=rows[offset:offset+256]
        raw,intent,ack,f=[read(root/folder/name) for folder in ('raw','batch_intents','batch_acks','batch_forecasts')]
        if (len(raw)!=len(part) or intent['rows']!=part
                or intent['sampling']!=[r['sampling'] for r in part]
                or ledger[key+'/batch/'+name[:-5]]!=intent or ledger[key+'/batch_done/'+name[:-5]]!=ack
                or ack['count']!=len(part) or ack['raw_sha256']!=digest(raw)
                or not isfinite(ack['seconds']) or ack['seconds']<=0 or f!=forecasts[name]):
            raise ValueError('Original request, saved raw, immutable acknowledgment or forecast differs')
        new_decoded=[];new_scoring=[]
        for row,item in zip(part,raw):
            stop,unmapped=decode(row,item,tokenizer,mapped,special)
            original=gold[row['problem_id']];answer=original['answer']
            if not isinstance(answer,str) or not answer.strip():raise ValueError('Unsupported gold cannot become zero')
            entry=dict(id=row['candidate_id'],problem_id=row['problem_id'],task=row['task'],
                condition=row['condition'],evaluation=row['evaluation'],cue_token_ids=row['cue_token_ids'],
                raw_file='raw/'+name,raw_file_sha256=sha(root/'raw'/name),raw_record_sha256=digest(item),
                stop=stop,backend_finish_reason=item['finish_reason'],backend_stop_reason=item['stop_reason'],
                unmapped_ids=unmapped)
            score=dict(id=entry['id'],problem_id=entry['problem_id'],task=entry['task'],condition=entry['condition'],
                evaluation=entry['evaluation'],gold=answer,answer_segment=stop['answer_segment'],
                stop_reason=stop['stop_reason'],original_gold_row_sha256=digest(original),
                original_decoded_record_sha256=digest(entry))
            new_decoded.append(entry);new_scoring.append(score)
            counts[(row['condition'],row['evaluation'])]+=1;stops[stop['stop_reason']]+=1;unknown_tokens+=len(unmapped)
        dump(out/'confirmed_batches'/name,dict(decoded=new_decoded,scoring=new_scoring))
        decoded.extend(new_decoded);scoring.extend(new_scoring)
    if len(decoded)!=count:raise ValueError('Incomplete original benchmark payload')
    return dict(decoded=decoded,scoring=scoring,outputs=count,technical_unknown=0,
        unmapped_token_occurrences=unknown_tokens,logical_stops=dict(stops),
        condition_counts={'/'.join(k):v for k,v in counts.items()},old_outputs_regenerated=0,
        new_training_updates=0,symbolic_scoring_performed=False,old_binary_reloaded=False)
