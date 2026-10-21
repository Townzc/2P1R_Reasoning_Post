"""Exact pinned native tokenizer encoding; preserve raw Unicode separately.

Candidate only: production use requires the independent continuation CR and
owner failure exception. NFC is the tokenizer's existing normalizer, not a new
data cleanup policy. Neither NFKC, stripping, truncation nor substitution is used.
"""
import hashlib
import json

from experiments.p011 import data_contract as rules


def encode_complete(tokenizer, question, response, path_id):
    prefix, raw_text = rules.native_text(tokenizer, question, response)
    backend = json.loads(tokenizer.backend_tokenizer.to_str())
    if backend.get('normalizer') != {'type': 'NFC'}:
        raise ValueError('Exact pinned tokenizer NFC normalizer required')
    parts = (prefix, response + '<|im_end|>', '\n')
    normalized = ''.join(tokenizer.backend_tokenizer.normalizer.normalize_str(p)
                         for p in parts)
    pre, answer, suffix = [tokenizer(p, add_special_tokens=False,
        truncation=False)['input_ids'] for p in parts]
    ids = pre + answer + suffix
    decoded = tokenizer.decode(ids, skip_special_tokens=False,
                               clean_up_tokenization_spaces=False)
    if decoded != normalized:
        raise ValueError('Native token roundtrip differs beyond pinned NFC')
    if len(ids) > rules.MAX_TOTAL_TOKENS:
        raise ValueError('Selected full answer exceeds the original total limit')
    labels = [-100] * len(pre) + answer + [-100] * len(suffix)
    positions = [i for i, x in enumerate(labels) if x != -100]
    eos = tokenizer.convert_tokens_to_ids('<|im_end|>')
    if (not positions or positions[0] == 0
            or positions != list(range(positions[0], positions[-1] + 1))
            or labels[positions[-1]] != eos):
        raise ValueError('Assistant plus im_end must form one nonempty span')
    row = {'path_id': path_id, 'parent_sha256': rules.identity(rules.parent_key(question)),
        'input_ids': ids, 'labels': labels, 'n_supervised': len(positions),
        'n_processed': len(ids), 'assistant_start': positions[0],
        'assistant_end': positions[-1] + 1, 'eos_token_id': eos,
        'template_final_newline_supervised': False}
    sha = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest()
    proof = {'path_id': path_id, 'encoding_reused': False,
        'normalizer': 'pinned_tokenizer_NFC_per_original_segment',
        'raw_native_text_sha256': sha(raw_text),
        'normalized_native_text_sha256': sha(normalized),
        'decoded_text_sha256': sha(decoded), 'raw_characters': len(raw_text),
        'normalized_characters': len(normalized),
        'normalization_changed_text': raw_text != normalized,
        'original_question_sha256': sha(question),
        'original_response_sha256': sha(response), 'raw_text_rewritten': False}
    return row, proof
