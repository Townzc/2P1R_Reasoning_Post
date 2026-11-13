"""A4 bridge inference: same reviewed generation logic with vLLM LoRARequest.

Never merge the adapted output head into Qwen's tied embedding matrix.
"""
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
from .evaluation import (EvalConfig, execution_commit, sha256_file, termination_tokens,
                         render_prompt_tokens, stop_flags, LLAMA_G0_DATE)
from .bridge_config import TARGETS


def verify_adapter(bridge, model, revision):
    import re
    if not re.fullmatch(r"[a-z0-9_]+",bridge['run_id']):raise ValueError('Invalid run')
    root=Path('/p012/training')/bridge['run_id'];path=Path(bridge['path'])
    if path!=root/'checkpoint' or path.is_symlink():raise ValueError('Invalid adapter location')
    if sha256_file(root/'CHECKPOINT_FILES.json')!=bridge['manifest_sha256']:raise ValueError('Adapter inventory changed')
    status=json.loads((root/'STATUS.json').read_text());manifest=json.loads((root/'MANIFEST.json').read_text())
    if not status['success'] or manifest['model']['repo']!=model or manifest['model']['revision']!=revision:raise ValueError('Wrong training/model')
    declared=json.loads((root/'CHECKPOINT_FILES.json').read_text());seen=set()
    for f in declared:
        rel=Path(f['path'])
        if rel.is_absolute() or '..' in rel.parts or f['path'] in seen:raise ValueError('Invalid adapter entry')
        seen.add(f['path']);file=path/rel
        if file.is_symlink() or file.stat().st_size!=f['bytes'] or sha256_file(file)!=f['sha256']:raise ValueError('Adapter file changed')
    actual={str(f.relative_to(path)) for f in path.rglob('*') if f.is_file()}
    if actual!=seen or not {'adapter_config.json','adapter_model.safetensors'}<=seen:raise ValueError('Incomplete adapter')
    cfg=json.loads((path/'adapter_config.json').read_text())
    if cfg['r']!=32 or cfg['lora_alpha']!=64 or set(cfg['target_modules'])!=set(TARGETS.split(',')):raise ValueError('Different LoRA configuration')
    return {'track':'modal_lora_bridge','training_run_id':bridge['run_id'],
            'initialization_repo':model,'initialization_revision':revision,
            'adapter_manifest_sha256':bridge['manifest_sha256'],'all_files_verified':sorted(seen),'merged':False}


def run_vllm(config: EvalConfig, input_path: Path, output_dir: Path, bridge: dict) -> None:
    """Generation only. Scores are a separate operation after raw bytes exist.

    Rows require stable id and problem. Optional messages are explicit frozen
    few-shot conversations; optional prompt is a complete pre-rendered plain
    completion. This wrapper does not choose examples from any test split.
    """
    config.validate()
    # Read the required export before paying to load a model.
    template_text = Path(config.chat_template_file).read_text() if config.chat_template_file else None
    if template_text is not None and not template_text.strip():
        raise ValueError("The exported training template is empty")
    code_commit = execution_commit()
    started = time.monotonic()
    # JSON strings may contain literal Unicode line separators. JSONL records
    # are separated by physical newlines, not every character in splitlines().
    rows = [json.loads(line) for line in input_path.open() if line.strip()]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Input IDs must be unique and nonempty")
    if (config.protocol.startswith("lm_eval_") or config.protocol == "omi2") and config.batch_size < len(rows):
        raise ValueError("Submit the complete base/main-grid endpoint in one generation batch")
    if config.training_run_id is not None:
        raise ValueError("Bridge uses initial weights plus unmerged adapter")
    checkpoint_evidence = verify_adapter(bridge, config.model, config.revision)
    output_dir.mkdir(parents=True, exist_ok=False)
    from vllm import LLM, SamplingParams
    hub_revision = config.revision
    llm = LLM(model=config.model, revision=hub_revision,
              tokenizer_revision=hub_revision, dtype=config.dtype,
              generation_config="vllm",
              max_model_len=config.max_model_len, trust_remote_code=False,
              gpu_memory_utilization=0.85, seed=config.seed, enable_lora=True, max_lora_rank=32)
    from vllm.lora.request import LoRARequest
    adapter = LoRARequest(bridge["run_id"], 1, bridge["path"])
    tokenizer = llm.get_tokenizer()
    if template_text is not None:
        tokenizer.chat_template = template_text
    if config.apply_chat_template and not tokenizer.chat_template:
        raise ValueError("Supply the frozen training-family template for a base tokenizer")
    from transformers import GenerationConfig
    generation_config = GenerationConfig.from_pretrained(config.model, revision=hub_revision)
    termination = termination_tokens(tokenizer, generation_config.eos_token_id, config.template_family)
    stop_ids = set(termination["stop_token_ids"])
    params = SamplingParams(n=config.n, temperature=config.temperature,
                            top_p=config.top_p, top_k=config.top_k, max_tokens=config.max_tokens,
                            seed=config.seed, stop=list(config.stop_strings) or None,
                            stop_token_ids=sorted(stop_ids), ignore_eos=False,
                            include_stop_str_in_output=False)
    manifest = {"config": asdict(config), "code_commit": code_commit,
                "input_sha256": sha256_file(input_path),
                "source_sha256": sha256_file(Path(__file__)),
                "input_rows": len(rows), **termination,
                "chat_template_date_string": LLAMA_G0_DATE if config.template_family == "llama3" and config.apply_chat_template and not config.chat_template_file else None,
                "model_load_seconds": time.monotonic() - started,
                "checkpoint_verification": checkpoint_evidence,
                "chat_template": tokenizer.chat_template,
                "chat_template_sha256": hashlib.sha256(template_text.encode()).hexdigest() if template_text is not None else None,
                "versions": {p: importlib.metadata.version(p) for p in ("vllm", "transformers", "torch")}}
    (output_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (output_dir / "raw.jsonl").open("x") as raw:
        for start in range(0, len(rows), config.batch_size):
            batch = rows[start:start + config.batch_size]
            prompts = []
            for row in batch:
                tokens = render_prompt_tokens(row, tokenizer, config)
                if len(tokens) + config.max_tokens > config.max_model_len:
                    raise ValueError(f"Context would truncate input/output for {row['id']}")
                prompts.append({"prompt_token_ids": tokens})
            block_started = time.monotonic()
            generated = llm.generate(prompts, params, use_tqdm=False, lora_request=adapter)
            block_seconds = time.monotonic() - block_started
            if len(generated) != len(batch):
                raise RuntimeError("Missing request output")
            for row, prompt, result in zip(batch, prompts, generated, strict=True):
                if len(result.outputs) != config.n:
                    raise RuntimeError("Missing sampled draw")
                if {c.index for c in result.outputs} != set(range(config.n)):
                    raise RuntimeError("Duplicate or invalid draw indices")
                for completion in result.outputs:
                    if completion.finish_reason not in {"stop", "length"}:
                        raise RuntimeError("Generation did not finish normally")
                    ids = list(completion.token_ids)
                    record = {"id": row["id"], "draw": completion.index,
                              "prompt_token_ids": prompt["prompt_token_ids"],
                              "token_ids": ids, "text": completion.text,
                              "finish_reason": completion.finish_reason,
                              "stop_reason": completion.stop_reason,
                              **stop_flags(ids, stop_ids, completion.finish_reason,
                                           completion.stop_reason, config.max_tokens)}
                    raw.write(json.dumps(record, ensure_ascii=False) + "\n")
                raw.flush()
            with (output_dir / "timing.jsonl").open("a") as timing:
                timing.write(json.dumps({"start": start, "requests": len(batch),
                    "seconds": block_seconds,
                    "prompt_tokens": sum(len(p["prompt_token_ids"]) for p in prompts),
                    "completion_tokens": sum(len(c.token_ids) for g in generated for c in g.outputs)}) + "\n")
            print(json.dumps({"completed_requests": start + len(batch), "total_requests": len(rows),
                              "block_seconds": block_seconds}), flush=True)
    (output_dir / "GENERATION_COMPLETE.json").write_text(json.dumps({
        "requests": len(rows), "draws": len(rows) * config.n,
        "elapsed_seconds": time.monotonic() - started,
        "raw_sha256": sha256_file(output_dir / "raw.jsonl")}) + "\n")


def main():
    p=argparse.ArgumentParser()
    for name in ('config','inputs','output','bridge'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run_vllm(EvalConfig(**json.loads(a.config.read_text())),a.inputs,a.output,json.loads(a.bridge.read_text()))

if __name__=='__main__':main()
