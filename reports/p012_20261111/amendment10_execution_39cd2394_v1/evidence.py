"""Verify and package one completed A10 endpoint, using the accepted scorer's labels."""
import hashlib
import json
import math
from pathlib import Path
import zipfile

PUB = Path(__file__).resolve().parent.relative_to(Path.cwd())
PREP = PUB.parent / "amendment10_training_review_v1"
PRIVATE = Path(".local/p012_20261111/amendment10_execution_v1")
RUNS = PRIVATE / "runs"
AUTHORITY = "f42dcd1595807406f67ff694e5235447c6814ebc"
REVIEW = "39cd239476400b4e0a1c5ada281e45f8879cb192"
CODE = "b76682c608e487e9ba2a0be7700430105d6a8792"


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temp.replace(path)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_request(name):
    request = read(RUNS / name / "request.json")
    public = PUB / "requests" / (name + ".json")
    result = RUNS / name / "result"
    require(request == read(public) == read(result / "REQUEST.json"), "Request binding " + name)
    require(request["accepted_review_commit"] == REVIEW and request["code_commit"] == CODE
            and request["authority_commit"] == AUTHORITY and request["prediction_commit"] == AUTHORITY,
            "Review or prediction binding " + name)
    require(request["run_id"] == name and request["forecast"]["admitted"], "Run identity " + name)
    require(read(result / "COMPLETE.json")["success"], "Missing success " + name)
    require(not (result / "PARTIAL_USAGE.json").exists(), "Partial usage " + name)
    gate = Path(request["forecast"]["admission_file"])
    require(sha(gate) == request["forecast"]["admission_sha256"] and read(gate)["admitted"], "Admission " + name)
    require(sha(public) == read(PUB / "launches" / (name + ".json"))["request_sha256"], "Launch identity " + name)
    return request


def training_binding(name):
    from experiments.p012.tinker_lora import cosine_lr, epoch_order

    req = verify_request(name)
    directory = RUNS / name / "result"
    manifest = read(PREP / "DATA_MANIFEST.json")
    arm, seed = req["A10_arm"], req["seed"]
    cell, = [c for c in manifest["cells"] if (c["arm"], c["seed"]) == (arm, seed)]
    data = manifest["datasets"][f"p{cell['P']}_k{cell['K']}"]
    require(req["rank"] == 32 and req["training_max_length"] == 8192, "Training protocol")
    require(req["dataset"]["sha256"] == data["sha256"] == cell["dataset_sha256"]
            == sha(req["dataset"]["path"]), "Training file identity")
    require(sha(data["public_identities"]) == data["public_identities_sha256"]
            == req["cpu_counts"]["source_identities_sha256"], "Training identities")
    n = data["rows"]
    require(n == cell["P"] * cell["K"] and req["dose"]["epochs"] == cell["E"]
            and req["dose"]["expected_updates"] == cell["updates"] == n * cell["E"] // 8,
            "Training dose")
    order = read(directory / "ROW_ORDER.json")
    expected = [i for epoch in range(cell["E"]) for i in epoch_order(n, seed, epoch)]
    require(order == expected, "Frozen epoch order")
    losses = [json.loads(line) for line in (directory / "train_loss.jsonl").read_bytes().splitlines()]
    require(len(losses) == cell["updates"], "Update count")
    for i, step in enumerate(losses):
        require(step["step"] == i + 1 and step["row_indices"] == order[8*i:8*i+8]
                and math.isfinite(step["loss"]) and math.isclose(step["learning_rate"],
                        cosine_lr(req["learning_rate"], i, len(losses)), rel_tol=1e-12),
                "Loss log, indices or learning rate at step " + str(i+1))
    require(sum(step["target_tokens"] for step in losses) == cell["supervised_tokens"], "Target tokens")
    require(read(directory / "USAGE.json")["training_input_tokens"] == cell["training_input_tokens"],
            "Training input tokens")
    server = read(directory / "SERVER_MODEL_INFO.json")
    require(server["is_lora"] is True and server["lora_rank"] == req["rank"]
            and server["model_data"]["model_name"] == req["model"], "Training service model and rank")
    sampler = read(directory / "SAMPLER.json")["path"]
    state = read(directory / "STATE.json")["path"]
    require(sampler.startswith("tinker://") and sampler.split("/")[2] == state.split("/")[2]
            and sampler.endswith("/final") and state.endswith("/final"), "Checkpoint identity")
    return dict(cell=cell, model=req["model"], revision=req["asset"]["revision"], rank=32,
                sampled_weights=sampler, saved_state=state, max_training_length=8192,
                last_step_loss=losses[-1]["loss"], public_dataset_identities=data["public_identities"],
                dataset_rows=n, training_request_sha256=sha(RUNS / name / "request.json"),
                sampler_receipt_sha256=sha(directory / "SAMPLER.json"))


def package(endpoint, evaluation, binding=None):
    d = RUNS / evaluation
    gen = d / "result/generation"
    req = verify_request(evaluation)
    result = read(d / "score_v1/RESULTS.json")
    require(result["raw_sha256"] == sha(gen / "raw.jsonl")
            and result["labels_sha256"] == sha(d / "score_v1/labels.jsonl")
            and result["accepted_source_review_commit"] == REVIEW, "Scorer input/output hashes")
    frozen = read(PREP / "EVALUATION_MANIFEST.json")
    require(result["evaluation_identities_sha256"] == sha(frozen["public_identities_path"])
            and sha(req["evaluation"]["path"]) == frozen["private_input_sha256"], "Test set identity")
    receipt = read(gen / "GENERATION_COMPLETE.json")
    require(receipt["sdk_sample_calls"] == receipt["requests"] == receipt["draws"] == result["responses"] == 1572,
            "Full greedy coverage")
    rows = [json.loads(x) for x in (gen / "raw.jsonl").open()]
    labels = [json.loads(x) for x in (d / "score_v1/labels.jsonl").open()]
    require(len(rows) == len(labels) == 1572 and [r["id"] for r in rows] == [y["id"] for y in labels],
            "Raw and labels alignment")
    usage = read(d / "result/USAGE.json")
    require(usage["sampling"] == read(gen / "USAGE.json")
            and sum(len(x["token_ids"]) for x in rows) == usage["sampling"]["completion_tokens"]
            and sum(x["prompt_tokens"] for x in rows) == usage["sampling"]["prefill_tokens_uncached_upper"],
            "Sampling usage against complete raw output")
    if binding:
        require(req["sampler_path"] == binding["sampled_weights"] and req["training_run_id"] == endpoint
                and req["training_request_sha256"] == binding["training_request_sha256"]
                and req["sampler_receipt_sha256"] == binding["sampler_receipt_sha256"]
                and req["seed"] == binding["cell"]["seed"] and req["model"] == binding["model"],
                "Trained evaluation binding")
    else:
        require("sampler_path" not in req and endpoint == evaluation, "Untrained baseline binding")

    members = {}
    def files(prefix, directory, names):
        for name in names:
            members[prefix + "/" + name] = directory / name

    files("evaluation", d, ["request.json", "PREDICTION_BEFORE_SCORE.json", "score_v1/RESULTS.json",
          "score_v1/labels.jsonl", "result/COMPLETE.json", "result/USAGE.json", "result/VERSIONS.json",
          "result/REQUEST.json", "result/generation/MANIFEST.json", "result/generation/GENERATION_COMPLETE.json",
          "result/generation/USAGE.json", "result/generation/raw.jsonl"])
    for name in dict.fromkeys((endpoint, evaluation)):
        for folder in ("requests", "admissions", "launches"):
            members[f"execution/{folder}/{name}.json"] = PUB / folder / (name + ".json")
    files("frozen", PREP, ["EVALUATION_IDENTITIES.json", "EVALUATION_MANIFEST.json", "ACCEPTED_REVIEW.json"])
    if binding:
        files("training", RUNS / endpoint, ["request.json", "result/REQUEST.json", "result/COMPLETE.json",
              "result/ROW_ORDER.json", "result/train_loss.jsonl", "result/SAMPLER.json", "result/STATE.json",
              "result/USAGE.json", "result/SERVER_MODEL_INFO.json", "result/RENDER_SAMPLES.json", "result/VERSIONS.json"])
        members["frozen/training_identities.json"] = Path(binding["public_dataset_identities"])
        members["frozen/DATA_MANIFEST.json"] = PREP / "DATA_MANIFEST.json"
    files("approved", PREP, ["score_logiqa.py", "freeze_data.py"])
    members["approved/tinker_lora.py"] = Path("experiments/p012/tinker_lora.py")
    members["approved/training_config.py"] = Path("experiments/p012/training_config.py")
    members["approved/pilot_scorer.py"] = Path("reports/p012_20261111/amendment9_logiqa_v1/logiqa_pilot.py")
    members["frozen/AMENDMENT_10.md"] = Path("audit/claude/20261120e/P012_PLAN_v1_AMENDMENT_10.md")
    members["frozen/ACCEPTED_TEMPLATE.json"] = PREP / "request_templates" / (endpoint + ".json")
    members["frozen/INITIAL_BILLING.json"] = PUB / "INITIAL_BILLING_AND_STORAGE.json"
    facts = {k:dict(bytes=p.stat().st_size, sha256=sha(p)) for k,p in members.items()}
    staging = PRIVATE / "packet_staging" / endpoint
    staging.mkdir(parents=True, exist_ok=True)
    archive = staging / "evidence.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for key, source in members.items():
            z.write(source, key)
    with zipfile.ZipFile(archive) as z:
        require(set(z.namelist()) == set(members) and z.testzip() is None, "Packet members")
        for key, record in facts.items():
            require(hashlib.sha256(z.read(key)).hexdigest() == record["sha256"], "Archived hash " + key)
    write(staging / "INPUT_MANIFEST.json", dict(endpoint=endpoint, review_commit=REVIEW, code_commit=CODE,
          prediction_commit=AUTHORITY, archive_sha256=sha(archive), public_members=facts, training=binding,
          private_input_sha256=req["evaluation"]["sha256"], independent_post_audit="pending"))
    write(staging / "RESULTS.json", dict(result, endpoint=endpoint, training=binding,
          evaluation_upper_token_usd=usage["upper_token_cost_usd"],
          training_upper_token_usd=(read(RUNS/endpoint/"result/USAGE.json")["upper_token_cost_usd"] if binding else 0)))
    (staging / "README.md").write_text(f"# A10 LogiQA independent result review\n\n"
          f"Endpoint `{endpoint}` used {req['model']} with seed {req['seed']}. "
          f"The accepted scorer counted {result['correct']}/1,572 correct ({100*result['accuracy']:.2f}%), "
          f"{result['unfinished_count']} unfinished and {result['answer_only_count']} answer-only.\n\n"
          "Please verify all 1,572 labels and the frozen predictions, raw outputs, input identities, "
          "sampler or base-model identity and cost. For trained endpoints verify every update, the five "
          "training-data hashes in the accepted manifest, the selected dataset and the 8,192-token limit. "
          "The evaluation limit was 4,096 tokens. All original LogiQA input texts remain private.\n\n"
          "[Verified archive](evidence.zip) · [Member hashes and bindings](INPUT_MANIFEST.json) · "
          "[Result and termination counts](RESULTS.json)\n")
    target = PUB / "endpoints" / endpoint
    target.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(target)
    return target
