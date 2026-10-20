"""One base-model HF probability lifetime; must exit before vLLM is created."""
import os
import time
import traceback
from pathlib import Path
from experiments.p010.common import dump, read, verify, utc
from experiments.p010.cue_probability import DurableProbabilityProvider
from experiments.p010.cue_selection import propose


def child(conn, input_path, out_path, model_spec, claim, stop_epoch):
    try:
        import modal
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from experiments.learning_regime_p009.p0_engine import software
        torch.set_num_threads(4)
        torch.manual_seed(17)
        torch.cuda.manual_seed_all(17)
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
        volume.reload()
        if store.get('cue/search_r1/claim') != claim or time.time() >= stop_epoch-30:
            raise RuntimeError('Original C6 claim or deadline differs')
        verify(model_spec['remote_path'], model_spec['files'])
        out = Path(out_path)
        dev = read(input_path)
        tokenizer = AutoTokenizer.from_pretrained(model_spec['tokenizer_remote_path'],
            local_files_only=True, trust_remote_code=False)
        # Query the vocabulary once, never once per generated token or row.
        vocab = tokenizer.get_vocab()
        allowed = sorted(set(vocab.values())-set(tokenizer.all_special_ids))
        if tokenizer.eos_token_id != 151643 or not allowed or max(allowed) >= 151936:
            raise ValueError('Pinned supported base tokenizer vocabulary differs')
        dump(out/'ALLOWED_CUE_TOKENS.json', allowed)
        volume.commit()
        model = AutoModelForCausalLM.from_pretrained(model_spec['remote_path'],
            torch_dtype=torch.bfloat16, local_files_only=True, trust_remote_code=False,
            attn_implementation='sdpa').to('cuda').eval()
        if (model.config.vocab_size != 151936 or model.config.architectures != ['Qwen2ForCausalLM']
                or model.config.eos_token_id != 151643):
            raise ValueError('Pinned probability model architecture or EOS differs')
        dump(out/'PROPOSAL_ENVIRONMENT.json', dict(software=software(), pid=os.getpid(),
            engine='HF full-vocabulary BF16 model / FP32 softmax', attention='sdpa',
            pad_token_id=151643, allowed_tokens=len(allowed), tokenizer_vocab_queries=1,
            generated_answers=0, training_updates=0, seed=17, utc=utc()))
        volume.commit()
        provider = DurableProbabilityProvider(model, dev, 151643, 151936,
            out/'probabilities', stop_epoch-30)

        def original_probability(prefix):
            if store.get('cue/search_r1/claim') != claim:
                raise RuntimeError('Original C6 claim changed')
            try:
                return provider(prefix)
            finally:
                # Include an incomplete intent on failure; never repeat it.
                volume.commit()

        proposal = propose(original_probability, [r['problem_id'] for r in dev], allowed, 151936)
        dump(out/'PROPOSAL.json', proposal)
        dump(out/'PROPOSAL_COMPLETED.json', dict(utc=utc(), generated_answers=0,
            training_updates=0, prefix_measurements=21, pid=os.getpid()))
        volume.commit()
        conn.send(('complete', dict(prefix_measurements=21, pid=os.getpid())))
    except BaseException:
        conn.send(('error', traceback.format_exc()))
        raise
    finally:
        conn.close()
