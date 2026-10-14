"""Isolated CUDA process. Original token IDs are returned, never scored here."""
import importlib.metadata
from pathlib import Path
import traceback
from experiments.sft_allocation_midpoint.common import read, sha, dump, manifest, digest
from experiments.learning_regime_p009.p0_contract import REFERENCE_STATE, REFERENCE_IDENTITY


def software():
    import torch
    versions = {p: importlib.metadata.version(p) for p in
                ('vllm', 'torch', 'transformers', 'tokenizers', 'peft', 'numpy', 'safetensors')}
    required = dict(vllm='0.11.0', transformers='4.56.2', tokenizers='0.22.1',
                    peft='0.17.1', numpy='2.2.6', safetensors='0.6.2')
    if any(versions[p] != x for p, x in required.items()) or versions['torch'].split('+')[0] != '2.8.0':
        raise ValueError('Pinned engine versions differ')
    if (torch.version.cuda != '12.8' or not torch.cuda.is_available() or torch.cuda.device_count() != 1
            or 'H100' not in torch.cuda.get_device_name(0)
            or torch.cuda.get_device_properties(0).total_memory < 75*1024**3):
        raise ValueError('Exactly one H100-80GB required')
    torch.set_num_threads(4)
    return dict(versions=versions, cuda=torch.version.cuda, gpu=torch.cuda.get_device_name(0))


def merge_reference(base, checkpoint, destination, proof):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, TaskType, get_peft_model
    from experiments.sft_allocation_midpoint.checkpoint import load
    checkpoint = Path(checkpoint)
    if sha(checkpoint/'state.pt') != REFERENCE_STATE:
        raise ValueError('Not the completed correct-969 reference')
    state = load(checkpoint)
    if (digest(state['identity']) != REFERENCE_IDENTITY or state['step'] != 256
            or state['supervised_tokens'] != 524287):
        raise ValueError('Reference identity/dose changed')
    model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True,
                dtype=torch.float32, attn_implementation='sdpa').cuda()
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0,
        bias='none', target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],
        task_type=TaskType.CAUSAL_LM))
    params = {n: p for n, p in model.named_parameters() if p.requires_grad}
    if list(params) != state['trainable_names'] or set(params) != set(state['adapter']):
        raise ValueError('Adapter identity differs')
    with torch.no_grad():
        for name, param in params.items():
            value = state['adapter'][name]
            if param.shape != value.shape or value.dtype != torch.float32 or not torch.isfinite(value).all():
                raise ValueError('Adapter shape/dtype/finite failed')
            param.copy_(value)
            if not torch.equal(param.detach().cpu(), value):
                raise ValueError('Adapter copy changed values')
    model.eval()
    merged = model.merge_and_unload(safe_merge=True).to(dtype=torch.bfloat16)
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=False)
    merged.save_pretrained(destination, safe_serialization=True)
    AutoTokenizer.from_pretrained(base, local_files_only=True).save_pretrained(destination)
    dump(proof, dict(reference_state_sha256=REFERENCE_STATE, identity_sha256=REFERENCE_IDENTITY,
        source_manifest=read(checkpoint/'manifest.json'), adapter_parameters=len(params),
        adapter_exact_copy=True, merge_dtype='float32', saved_dtype='bfloat16',
        optimizer_and_rng='preserved in original state; not restored for pure greedy evaluation',
        new_training_updates=0, merged_files=manifest(destination)))


def child(connection, mode, paths):
    try:
        info = software()
        if mode == 'merge':
            merge_reference(**paths); connection.send(('merged', info)); return
        from vllm import LLM, SamplingParams
        model = LLM(model=paths['model'], tokenizer=paths['tokenizer'], dtype='bfloat16',
            tensor_parallel_size=1, max_model_len=2048, max_num_seqs=32,
            max_num_batched_tokens=4096, gpu_memory_utilization=.65,
            enforce_eager=True, enable_prefix_caching=False, seed=17,
            generation_config='vllm', disable_log_stats=True, trust_remote_code=False)
        sampling = SamplingParams(n=1, temperature=0, top_p=1, top_k=-1,
            repetition_penalty=1, max_tokens=512, seed=17, stop=None,
            stop_token_ids=[151643], ignore_eos=False, detokenize=True,
            skip_special_tokens=False, include_stop_str_in_output=True)
        connection.send(('ready', info))
        while True:
            command, rows = connection.recv()
            if command == 'close':
                return
            if command != 'generate':
                raise ValueError('Unknown parent command')
            outputs = model.generate([dict(prompt_token_ids=r['input_ids']) for r in rows],
                                     sampling, use_tqdm=False)
            if len(outputs) != len(rows):
                raise ValueError('Missing vLLM output')
            raw = []
            for row, generated in zip(rows, outputs):
                if len(generated.outputs) != 1:
                    raise ValueError('Only one greedy completion allowed')
                answer = generated.outputs[0]
                raw.append(dict(problem_id=row['problem_id'],
                    prompt_token_ids=list(generated.prompt_token_ids), token_ids=list(answer.token_ids),
                    backend_text=answer.text, finish_reason=answer.finish_reason,
                    stop_reason=answer.stop_reason))
            connection.send(('outputs', raw))
    except BaseException:
        connection.send(('error', traceback.format_exc()))
        raise
    finally:
        connection.close()
