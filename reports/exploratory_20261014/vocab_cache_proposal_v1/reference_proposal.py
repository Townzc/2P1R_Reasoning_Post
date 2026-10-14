"""Unadmitted pure-CPU proposal; no cloud entry and no live monkeypatch.

This function is not imported by the three active experimental workers.
It makes one vocabulary-size lookup per unchanged token sequence.
"""
from analyses.completion_contract import first_stop


def reference_event_cached(tokens, tokenizer, eos_ids):
    vocabulary_size = len(tokenizer)
    normalized = [tokenizer.eos_token_id if token in eos_ids else token
                  for token in tokens]
    special = ((set(tokenizer.all_special_ids) - set(eos_ids)) |
               {token for token in tokens if token >= vocabulary_size})
    return first_stop(
        normalized,
        lambda ids: tokenizer.decode(ids, skip_special_tokens=True,
                                     clean_up_tokenization_spaces=False),
        tokenizer.eos_token_id, 512, special,
    )
