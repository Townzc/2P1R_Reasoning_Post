"""Distinguish a model output vocabulary from the tokenizer's mapped entries.

Only the observed no-EOS,1024-token,length-capped case may contain unmapped
model IDs. Raw IDs/backend metadata stay unchanged. It is never a usable answer.
All other unmapped or out-of-model-vocabulary cases fail and remain preserved.
"""
from analyses.completion_contract import first_stop


def completion(raw, tokenizer, mapped_ids, model_vocab_size, special_ids):
    ids = raw['token_ids']
    if (not ids or len(ids) > 1024 or type(model_vocab_size) is not int
            or any(type(t) is not int or not 0 <= t < model_vocab_size for t in ids)):
        raise ValueError('Invalid model-vocabulary token stream')
    unmapped = sorted({t for t in ids if t not in mapped_ids})
    native_ids = (151645, 151643)
    if unmapped and (len(ids) != 1024 or raw['finish_reason'] != 'length'
                     or any(t in native_ids for t in ids)):
        raise ValueError('Unmapped token outside the preserved no-EOS length-cap case')
    native = next((t for t in ids if t in native_ids), tokenizer.eos_token_id)
    logical = first_stop(ids, lambda ts: tokenizer.decode(ts, skip_special_tokens=False,
                         clean_up_tokenization_spaces=False), native, 1024, special_ids)
    if unmapped and logical['stop_reason'] == 'native_eos':
        raise AssertionError('Unmapped stream cannot become a usable native EOS answer')
    return logical, dict(model_vocab_size=model_vocab_size,
                         unmapped_model_token_ids=unmapped,
                         raw_tokens_and_backend_preserved=True)
