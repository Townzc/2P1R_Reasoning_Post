"""Bounded serial GPU queue. Default is artifact-only preflight, not execution."""
from __future__ import annotations

import argparse
import fcntl
import gc
import json
import os
from pathlib import Path
import shutil
import time

from .io import (PHASE, NEW_ARMS, OLD_ARMS, SAMPLE_SEED, Ledger, digest,
                 independent_output, read, save, sha, source_check)


def checked_component(record, roots):
    index = record["volume"]
    if type(index) is not int or not 0 <= index < len(roots):
        raise ValueError("Invalid checkpoint volume")
    root = Path(roots[index]).resolve()
    path = (root/record["path"]).resolve()
    if root not in path.parents or path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
        raise ValueError("Checkpoint size/hash/path differs")
    return path


def preflight(args):
    out, prior = independent_output(args.output, args.prior)
    source = source_check(args.source_commit, args.inventory_sha256)
    contract = read(out/"TRAIN_CONTRACT.json")
    if (contract["phase"] != PHASE or contract["arms"] != list(NEW_ARMS) or
            contract["protocol_sha256"] != sha(Path(__file__).with_name("PROTOCOL.md")) or
            contract["mask_control_source_sha256"] != sha(Path(__file__).with_name("masks.py")) or
            read(out/"FROZEN.json")["contract_sha256"] != digest(contract)):
        raise ValueError("New contract was not frozen with this source")
    old_contract = read(prior/"TRAIN_CONTRACT.json")
    old_complete = read(prior/"TRAINING_COMPLETE.json")
    if (digest(old_contract) != contract["inherited_training_contract_sha256"] or
            old_complete["contract_sha256"] != digest(old_contract)):
        raise ValueError("Original training identity differs")
    # Check original inference components and raw greedy outputs before any new training.
    from experiments.public_math_pilot_v1.analyze_runtime import load_complete_run, load_references
    from experiments.public_math_pilot_v1.runtime_evaluate import model_identity
    references = load_references(args.release)["dev"]
    historical = read(Path(__file__).with_name("HISTORICAL_BINDINGS.json"))
    if len(references) != 512:
        raise ValueError("Development denominator changed")
    prior_paths, reuse = {}, {}
    for arm in OLD_ARMS:
        endpoint = old_complete["endpoints"][arm]["128"]
        if endpoint["step"] != 128 or not endpoint["terminal"] or not endpoint["scientific"]:
            raise ValueError("Historical endpoint differs")
        expected_component = historical["endpoints"][arm]
        if any(endpoint["files"]["model"][k] != expected_component[k] for k in ("bytes","sha256")):
            raise ValueError("Endpoint differs from the independently retained final audit")
        prior_paths[arm] = checked_component(endpoint["files"]["model"], args.prior_volume_root)
        name = f"{arm}-step128-dev"
        for rel, expected_hash in historical["dev_batch_sha256"].items():
            if rel.startswith("generation/"+name+"/") and sha(prior/rel) != expected_hash:
                raise ValueError("Historical generation differs from the independent final audit")
        rows, meta = load_complete_run(prior, "unused-no-preflight-reuse", dict(name=name), references)
        expected = model_identity(old_contract["scientific_identity"], endpoint, arm, 128, digest(old_contract))
        if meta["model"] != expected or meta["reused_ids"]:
            raise ValueError("Historical greedy endpoint binding differs")
        d = meta["decoding"]
        if (d["do_sample"] or d["seed"] is not None or d["batch_size"] != 16 or
                d["max_new_tokens"] != 2048 or d["precision"] != "FP32_master_BF16_autocast"):
            raise ValueError("Historical greedy decoding differs")
        reuse[arm] = dict(identity=meta, records_sha256=digest(rows),
                         completion_sha256=sha(prior/"generation"/name/"COMPLETE.json"))
    masks = {}
    for arm in NEW_ARMS:
        path = out/"masks"/arm/"MANIFEST.json"
        if sha(path) != contract["control_mask_manifests_sha256"][arm]:
            raise ValueError("Control mask manifest changed")
        masks[arm] = {}
        for r in read(path)["records"]:
            path = (out/"masks"/arm/r["path"]).resolve()
            if (out/"masks"/arm).resolve() not in path.parents or sha(path) != r["sha256"]:
                raise ValueError("Control mask file changed")
            value = read(path)
            if value["id"] != r["id"] or value["condition"] != arm or r["id"] in masks[arm]:
                raise ValueError("Control mask ID/condition differs")
            masks[arm][r["id"]] = value["mask"]
        if len(masks[arm]) != 4096:
            raise ValueError("Control mask coverage differs")
    return contract, old_contract, prior_paths, masks, references, reuse, source


def run(args):
    out, prior = independent_output(args.output, args.prior)
    if not out.is_dir():
        raise ValueError("Freeze controls before running preflight")
    with (out/"GPU.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        contract, old_contract, prior_paths, masks, references, reuse, source = preflight(args)
        if not args.execute:
            return dict(status="artifact_preflight_passed_no_model_calls", old_models=4,
                        control_masks=8192, reused_greedy_outputs=2048)
        if args.power_on_unix is None or args.deadline_unix is None or not (args.power_on_unix <= time.time() < args.deadline_unix and
                0 < args.deadline_unix - args.power_on_unix <= 7.75*3600):
            raise ValueError("GPU deadline must leave 15min within the eight-hour whole-instance cap")
        for volume in args.volume_root:
            volume = Path(volume).resolve()
            if prior == volume or prior in volume.parents or volume in prior.parents:
                raise ValueError("New checkpoint root overlaps historical output")
            if not volume.exists():
                volume.mkdir(parents=True)
            # Two new final recoveries plus one atomic recovery replacement, with reserve.
            if shutil.disk_usage(volume).free < 65*2**30:
                raise RuntimeError("At least65GiB free required before the two-control phase")
        import torch
        from experiments.public_math_pilot_v1.data import load_inputs
        from experiments.public_math_pilot_v1.preflight import drop_model, load_base, host_available_bytes
        from experiments.public_math_pilot_v1.runtime_prepare import prepare_identity
        from experiments.public_math_pilot_v1.runtime_train import frozen_batches
        from experiments.public_math_pilot_v1.runtime_common import generate_rows, require_time
        from experiments.public_math_pilot_v1.tokenization import encode_prompt
        from .train import train_arm, store_for
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("This finite queue requires exactly one visible GPU")
        properties = torch.cuda.get_device_properties(0)
        gpu = dict(name=properties.name, total_memory_bytes=properties.total_memory)
        if "A800" not in properties.name or properties.total_memory < 75*2**30:
            raise RuntimeError("Historical reuse is qualified for A80080GB; a hardware change needs a new qualification")
        if host_available_bytes() < 64*2**30:
            raise RuntimeError("Insufficient host headroom before model loading; inspect retained clean file cache")
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        tokenizer, identity, _ = prepare_identity(args.base, args.release, args.inputs)
        if identity != contract["scientific_identity"]:
            raise ValueError("Original base/tokenizer identity changed")
        # Generation kernel/software identity must equal the inherited greedy runs.
        expected_impl = {n:sha(Path(__file__).parents[1]/"public_math_pilot_v1"/n)
                         for n in ("runtime_common.py", "preflight.py", "tokenization.py")}
        for arm in OLD_ARMS:
            d = reuse[arm]["identity"]["decoding"]
            if (d["torch_version"] != torch.__version__ or
                    d["transformers_version"] != __import__("transformers").__version__ or
                    d["implementation_sha256"] != expected_impl or d["attention"] != "sdpa" or
                    d["cuda_allocator_config"] != os.environ.get("PYTORCH_CUDA_ALLOC_CONF","default")):
                raise ValueError("Software/generation closure differs; historical greedy reuse not admitted")
        released = load_inputs(args.release)
        batches = frozen_batches(released["tokenized_pilot"])
        if ([[r["problem_id"] for r in b] for b in batches] != contract["batches"] or
                [sum(len(r["response_ids"]) for r in b) for b in batches] != contract["denominators"]):
            raise ValueError("Training order or supervised dose changed")
        rows = [dict(id=r["problem_id"], prompt_ids=encode_prompt(tokenizer,r["question"])) for r in references]
        save(out/"ADMISSION.json", dict(source=source, gpu=gpu, power_on_unix=args.power_on_unix,
             model_deadline_unix=args.deadline_unix, contract_sha256=digest(contract),
             inherited_greedy=reuse, new_update_cap=256, new_generation_cap=4096,
             historical_budget_reset=False))
        for arm in NEW_ARMS:
            result = train_arm(args, contract, batches, masks[arm], arm)
            if result["status"] not in ("complete", "already_complete"):
                return dict(status="paused_training", result=result)
        ledger = Ledger(out/"physical_ledger.jsonl")
        jobs = [(a,"greedy") for a in NEW_ARMS] + [(a,"sampled") for a in (*OLD_ARMS,*NEW_ARMS)]
        for arm, decoding in jobs:
            require_time(args.deadline_unix, 300)
            if arm in OLD_ARMS:
                path = prior_paths[arm]
                model_sha = read(prior/"TRAINING_COMPLETE.json")["endpoints"][arm]["128"]["files"]["model"]["sha256"]
                training_sha = digest(old_contract)
            else:
                store = store_for(out, args.volume_root, contract, arm)
                endpoint = store.latest_manifest()
                if not endpoint["terminal"] or endpoint["step"] != 128:
                    raise ValueError("Control endpoint incomplete")
                path = store._verify_file(endpoint["files"]["model"])
                model_sha = endpoint["files"]["model"]["sha256"]
                training_sha = digest(contract)
            mid = dict(identity, model_sha256=model_sha, arm=arm, step=128, training_contract_sha256=training_sha)
            name = f"{arm}-{decoding}-dev"
            folder = out/"generation"/name
            complete = (folder/"COMPLETE.json").exists()
            model = None
            try:
                if not complete:
                    model = load_base(args.base, training=False)
                    state = torch.load(path, map_location="cpu", weights_only=True)
                    model.load_state_dict(state, strict=True)
                    del state; gc.collect()
                generate_rows(model, tokenizer, rows, folder, model_identity=mid, logical_name=name,
                              ledger=ledger, deadline=args.deadline_unix, batch_size=16,
                              seed=SAMPLE_SEED if decoding=="sampled" else None, allow_new_calls=not complete)
            finally:
                if model is not None:
                    drop_model(model); del model; gc.collect(); torch.cuda.empty_cache()
        counts = {k:sum(e["kind"]==k for e in ledger.events()) for k in ledger.caps}
        if counts != dict(optimizer_update=256, generation=4096):
            raise ValueError("Physical ledger does not match completed finite queue")
        save(out/"GPU_COMPLETE.json", dict(contract_sha256=digest(contract), counts=counts,
             generations=[dict(name=f"{a}-{d}-dev", completion_sha256=sha(out/"generation"/f"{a}-{d}-dev"/"COMPLETE.json")) for a,d in jobs],
             reusable_original_greedy_outputs=2048, new_annotations=0))
        return dict(status="gpu_complete_cpu_scoring_and_provider_shutdown_required", counts=counts)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("output", "prior", "release", "base", "inputs", "source-commit"):
        p.add_argument("--"+key, required=True)
    p.add_argument("--volume-root", action="append", required=True)
    p.add_argument("--prior-volume-root", action="append", required=True)
    p.add_argument("--inventory-sha256")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--power-on-unix", type=float)
    p.add_argument("--deadline-unix", type=float)
    print(json.dumps(run(p.parse_args()), sort_keys=True), flush=True)
