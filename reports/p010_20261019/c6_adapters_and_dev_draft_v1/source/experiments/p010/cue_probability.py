"""Unattempted C6 proposal adapter: full vocabulary, original dev IDs, no gold.

The future reviewed worker must own the deadline, pinned model/source binding,
GPU resources and process join before a vLLM lifetime. This module is not an
entrypoint or an admission for any model call.
"""
import math
import time
from pathlib import Path

from experiments.p010.common import dump, sha, utc


def validate_rows(rows, vocab_size):
    if (not isinstance(rows, list) or len(rows) != 30
            or any(not isinstance(r, dict) or set(r) != {'problem_id', 'input_ids'} for r in rows)
            or len({r['problem_id'] for r in rows}) != 30
            or type(vocab_size) is not int or vocab_size <= 0):
        raise ValueError('Exactly30 frozen, unique, gold-free dev rows required')
    for row in rows:
        ids = row['input_ids']
        if (not isinstance(ids, list) or not ids or len(ids)+2+1024 > 2048
                or any(type(x) is not int or not 0 <= x < vocab_size for x in ids)):
            raise ValueError('Full original dev prompt plus two-token cue must fit')


def next_probabilities(model, rows, prefix, pad_token_id, vocab_size, *, batch_size=4):
    """One original forward per padded minibatch; keep only final-position logits.

    HF proposal probabilities follow the cited beam-search implementation.
    This is distinct from the later vLLM continuations. No sampling, generated
    answer, loss, optimizer, gold or correctness lookup occurs here.
    """
    import torch
    validate_rows(rows, vocab_size)
    if (not isinstance(prefix, tuple) or len(prefix) > 1
            or any(type(x) is not int or not 0 <= x < vocab_size for x in prefix)
            or type(pad_token_id) is not int or not 0 <= pad_token_id < vocab_size
            or type(batch_size) is not int or not 1 <= batch_size <= 8):
        raise ValueError('Only original depth0/1 prefixes and bounded minibatches')
    if model.training:
        raise ValueError('Probability proposal requires eval mode')
    matrix = []
    for first in range(0, 30, batch_size):
        sequences = [row['input_ids']+list(prefix) for row in rows[first:first+batch_size]]
        length = max(map(len, sequences))
        ids = torch.tensor([[pad_token_id]*(length-len(s))+s for s in sequences],
                           dtype=torch.long, device=model.device)
        mask = torch.tensor([[0]*(length-len(s))+[1]*len(s) for s in sequences],
                            dtype=torch.long, device=model.device)
        positions = mask.cumsum(-1)-1
        positions.masked_fill_(mask == 0, 0)
        with torch.inference_mode():
            logits = model(input_ids=ids, attention_mask=mask, position_ids=positions,
                           use_cache=False, logits_to_keep=1).logits
            if tuple(logits.shape) != (len(sequences), 1, vocab_size):
                raise ValueError('Full final-position vocabulary logits required')
            probabilities = torch.softmax(logits[:, -1, :].float(), dim=-1)
            if not bool(torch.isfinite(probabilities).all()):
                raise ValueError('Nonfinite original probabilities')
            matrix.extend(probabilities.cpu().tolist())
    return matrix


class DurableProbabilityProvider:
    """Create-only prefix measurements; unknown/partial prefixes never replay.

    Every full FP32 matrix is stored losslessly. A future local audit can
    reconstruct all beam rankings without querying the model again.
    """
    def __init__(self, model, rows, pad_token_id, vocab_size, output_dir, deadline_epoch):
        validate_rows(rows, vocab_size)
        if not math.isfinite(deadline_epoch) or deadline_epoch <= time.time():
            raise ValueError('Original finite process deadline required')
        self.model, self.rows = model, rows
        self.pad, self.vocab = pad_token_id, vocab_size
        self.out, self.deadline = Path(output_dir), deadline_epoch
        self.out.mkdir(parents=True, exist_ok=False)

    def __call__(self, prefix):
        import numpy as np
        if (not isinstance(prefix, tuple) or len(prefix) > 1
                or any(type(t) is not int or not 0 <= t < self.vocab for t in prefix)):
            raise ValueError('Only original two-depth proposal prefixes')
        if time.time() >= self.deadline:
            raise TimeoutError('Original proposal deadline elapsed')
        name = 'root' if not prefix else 'token_'+str(prefix[0])
        target = self.out/name
        target.mkdir(exist_ok=False)
        dump(target/'INTENT.json', dict(prefix=list(prefix), problem_ids=[r['problem_id'] for r in self.rows],
             utc=utc(), retries=0, gold_used=False, correctness_used=False))
        started = time.monotonic()
        matrix = next_probabilities(self.model, self.rows, prefix, self.pad, self.vocab)
        if time.time() >= self.deadline:
            raise TimeoutError('Forward returned after original proposal deadline')
        array = np.asarray(matrix, dtype=np.float32)
        with (target/'full_probabilities.npy').open('xb') as handle:
            np.save(handle, array, allow_pickle=False)
        dump(target/'COMPLETED.json', dict(prefix=list(prefix), rows=30, vocab_size=self.vocab,
             dtype='float32', matrix_sha256=sha(target/'full_probabilities.npy'),
             seconds=time.monotonic()-started, utc=utc(), generated_answers=0))
        return matrix
