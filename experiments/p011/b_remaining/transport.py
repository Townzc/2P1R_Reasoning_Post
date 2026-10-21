"""Exact delegated unmapped-before-native-EOS rule; no symbolic comparison."""
from experiments.p010.teacher_transport import completion as original_completion
from experiments.sft_allocation_midpoint.common import digest

DECISION_SHA='8ca01d6f5d5f5e2dbe58b2e694aaa21685d3398d22d0e1c61d853a01fa92abf8'

def completion(raw,tokenizer,mapped_ids,model_vocab_size,special_ids):
    ids=raw['token_ids'];native=(151645,151643)
    if (not ids or len(ids)>1024 or type(model_vocab_size) is not int
            or any(type(t) is not int or not 0<=t<model_vocab_size for t in ids)):
        raise ValueError('Invalid original model vocabulary stream')
    positions=[i for i,t in enumerate(ids) if t not in mapped_ids]
    if not positions or (len(ids)==1024 and raw['finish_reason']=='length'
                         and not any(t in native for t in ids)):
        return original_completion(raw,tokenizer,mapped_ids,model_vocab_size,special_ids)
    eos=next((i for i,t in enumerate(ids) if t in native),None)
    if eos is None or any(p>=eos for p in positions):
        raise ValueError('Unmapped noncap ID must precede the first native EOS')
    p=positions[0]
    visible=tokenizer.decode(ids[:p],skip_special_tokens=False,clean_up_tokenization_spaces=False)
    stop=dict(stop_reason='invalid_special_token',retained_tokens=p+1,actual_eos_at_stop=False,
              answer_segment=visible,boundary_offset=None,trigger_text=None)
    evidence=dict(model_vocab_size=model_vocab_size,
        unmapped_model_token_ids=sorted({ids[i] for i in positions}),unmapped_positions=positions,
        first_native_eos_position=eos,unmapped_noncap_invalid=True,
        raw_tokens_and_backend_preserved=True,delegated_decision_sha256=DECISION_SHA)
    return stop,evidence

def reader(tokenizer,vocabulary_size):
    mapped=set(tokenizer.get_vocab().values());special=set(tokenizer.all_special_ids)
    def decode(raw):
        stop,evidence=completion(raw,tokenizer,mapped,vocabulary_size,special)
        return dict(stop=stop,transport=evidence,answer_text=stop['answer_segment'],raw_record_sha256=digest(raw))
    return decode

def validate_saved(raw,decoded,mapped_ids,vocabulary_size):
    """Read-only raw identity/stop check, without a second text decoding pass."""
    ids=raw['token_ids']
    if (not ids or len(ids)>1024 or any(type(t) is not int or not 0<=t<vocabulary_size for t in ids)
            or decoded['raw_record_sha256']!=digest(raw)
            or decoded['answer_text']!=decoded['stop']['answer_segment']):
        raise ValueError('Saved raw/transport identity differs')
    positions=[i for i,t in enumerate(ids) if t not in mapped_ids]
    evidence=decoded['transport'];stop=decoded['stop']
    if evidence['unmapped_model_token_ids']!=sorted({ids[i] for i in positions}):
        raise ValueError('Saved unmapped IDs differ')
    if positions and not (len(ids)==1024 and raw['finish_reason']=='length' and not any(t in (151645,151643) for t in ids)):
        eos=next((i for i,t in enumerate(ids) if t in (151645,151643)),None)
        if (eos is None or any(p>=eos for p in positions)
                or evidence!=dict(model_vocab_size=vocabulary_size,
                    unmapped_model_token_ids=sorted({ids[i] for i in positions}),unmapped_positions=positions,
                    first_native_eos_position=eos,unmapped_noncap_invalid=True,
                    raw_tokens_and_backend_preserved=True,delegated_decision_sha256=DECISION_SHA)
                or stop['stop_reason']!='invalid_special_token' or stop['retained_tokens']!=positions[0]+1
                or stop['actual_eos_at_stop'] is not False):
            raise ValueError('Saved delegated noncap classification differs')
    if positions and stop['stop_reason']=='native_eos':raise ValueError('Unmapped output cannot be usable')

