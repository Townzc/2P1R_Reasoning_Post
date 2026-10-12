"""Finite CPU-only Modal admission and Volume round-trip check; no model calls.

Run only from published source with a prewritten immutable campaign JSON and a
new local receipt directory. The campaign reserves two dollars inside P007's
twenty-dollar engineering envelope. This tests platform primitives, not GPU
checkpoint/resume equivalence. Cloud SDK credentials never enter the image.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import time

import modal

HERE = Path(__file__).resolve().parent
app = modal.App("sft-allocation-midpoint-cpu-preflight")
image = modal.Image.debian_slim(python_version="3.12").add_local_file(
    HERE / "guard.py", "/opt/midpoint/guard.py", copy=True)
volume = modal.Volume.from_name("sft-allocation-midpoint-v1", create_if_missing=True, version=1)
claims = modal.Dict.from_name("sft-allocation-midpoint-claims-v1", create_if_missing=True)
OPTIONS = dict(image=image, cpu=(1.0, 1.0), memory=(1024, 1024), timeout=120,
               startup_timeout=120, retries=0, min_containers=0, max_containers=2,
               buffer_containers=0, scaledown_window=2, single_use_containers=True,
               serialized=True, include_source=False, volumes={"/evidence": volume})


@app.function(**OPTIONS)
def write_once(plan, source_hash, attempt_id):
    import sys
    import os
    # Serialized function globals cannot contain an unhydrated Dict handle.
    claims = modal.Dict.from_name("sft-allocation-midpoint-claims-v1", create_if_missing=True)
    sys.path.insert(0, "/opt/midpoint")
    from guard import RunGuard, GuardError, canonical_json, identity_hash
    guard = RunGuard(claims, plan)
    guard.register(now_epoch=time.time())
    intent = dict(run_id="writer", config_sha256=identity_hash(plan),
                  source_sha256=source_hash, data_sha256=identity_hash({"fixture": [3, 1, 4]}))
    if attempt_id not in {"candidate_a", "candidate_b"}:
        raise ValueError("fixed two-writer contest only")
    prefix = "midpoint/" + plan["campaign_id"] + "/"
    gate = dict(source_sha256=source_hash, plan_sha256=identity_hash(plan))
    if not claims.put(prefix + "ready/" + attempt_id, gate, skip_if_exists=True):
        raise RuntimeError("this physical writer input was already attempted; reconcile")
    wait_until = min(time.time() + 30, plan["deadline_epoch"] - 90)
    while not all(claims.get(prefix + "ready/" + name) == gate
                  for name in ("candidate_a", "candidate_b")):
        if time.time() >= wait_until:
            raise TimeoutError("both writers were not concurrently ready")
        time.sleep(0.1)
    try:
        admission = guard.admit(intent, attempt_id=attempt_id, now_epoch=time.time(),
                                max_runtime_seconds=90)
    except GuardError as exc:
        prior = claims.get(prefix + "claim/writer")
        if (str(exc) not in {"run already claimed; completed, failed, or ambiguous work cannot replay",
                            "run is already terminal; missing claims cannot authorize replay"}
                or prior is None or prior["intent_sha256"] != identity_hash(intent)
                or prior["plan_sha256"] != identity_hash(plan)
                or prior["attempt_id"] == attempt_id):
            raise
        return {"attempt_id": attempt_id, "status": "admission_denied", "reason": str(exc),
                "matching_other_claim_verified": True}
    # The claim precedes all fixture writes. Any failure remains non-replayable.
    guard.check_active(admission, now_epoch=time.time(), spent_cents=0, next_cost_cents=100)
    target = Path("/evidence") / plan["campaign_id"]
    target.mkdir(exist_ok=False)
    payload = dict(kind="cpu_fixture_not_model_checkpoint", values=[3, 1, 4],
                   winning_attempt=attempt_id, source_sha256=source_hash,
                   campaign_id=plan["campaign_id"])
    raw = (canonical_json(payload) + "\n").encode()
    with (target / "fixture.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    volume.commit()
    digest = hashlib.sha256(raw).hexdigest()
    receipt = guard.finish(admission, status="completed", evidence_sha256=digest,
                           actual_cost_cents=100, finished_epoch=time.time())
    return dict(attempt_id=attempt_id, status="completed", payload_sha256=digest,
                accounting="full_reserved_dollar_not_invoice", receipt=receipt)


@app.function(**OPTIONS)
def read_independently(plan, source_hash):
    import sys
    claims = modal.Dict.from_name("sft-allocation-midpoint-claims-v1", create_if_missing=True)
    sys.path.insert(0, "/opt/midpoint")
    from guard import RunGuard, identity_hash
    guard = RunGuard(claims, plan)
    guard.register(now_epoch=time.time())
    intent = dict(run_id="reader", config_sha256=identity_hash(plan),
                  source_sha256=source_hash, data_sha256=identity_hash({"fixture": [3, 1, 4]}))
    admission = guard.admit(intent, attempt_id="independent_reader", now_epoch=time.time(),
                            max_runtime_seconds=90)
    guard.check_active(admission, now_epoch=time.time(), spent_cents=0, next_cost_cents=100)
    volume.reload()
    raw = (Path("/evidence") / plan["campaign_id"] / "fixture.json").read_bytes()
    payload = json.loads(raw)
    if (payload["values"] != [3, 1, 4] or payload["source_sha256"] != source_hash
            or payload["campaign_id"] != plan["campaign_id"]):
        raise RuntimeError("independent fixture mismatch")
    digest = hashlib.sha256(raw).hexdigest()
    receipt = guard.finish(admission, status="completed", evidence_sha256=digest,
                           actual_cost_cents=100, finished_epoch=time.time())
    return dict(payload=payload, payload_sha256=digest, receipt=receipt,
                accounting="full_reserved_dollar_not_invoice")


@app.local_entrypoint()
def main(plan_json: str, receipt_dir: str):
    from experiments.sft_allocation_midpoint.guard import identity_hash
    plan_path, out = Path(plan_json), Path(receipt_dir)
    plan = json.loads(plan_path.read_text())
    if (plan["total_cap_cents"] != 200 or plan["stage_caps_cents"] != {"cpu_preflight": 200}
            or plan["slots"] != {k: {"stage": "cpu_preflight", "reserved_cents": 100}
                                 for k in ("writer", "reader")}):
        raise ValueError("exact two-dollar CPU envelope required")
    if plan["deadline_epoch"] - time.time() < 240:
        raise ValueError("insufficient immutable preflight window")
    root = HERE.parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    remote = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/codex/icml-acl-2027"], cwd=root, text=True).split()[0]
    if commit != remote:
        raise ValueError("publish source on assigned branch first")
    source = {}
    for path in (HERE / "guard.py", Path(__file__).resolve()):
        relative = str(path.relative_to(root))
        tracked = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=root)
        if path.read_bytes() != tracked:
            raise ValueError("execution source differs from published bytes")
        source[relative] = hashlib.sha256(tracked).hexdigest()
    source_hash = identity_hash(source)
    out.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        with (out / name).open("x") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
    save("intent.json", dict(plan=plan, commit=commit, source=source,
                             started_epoch=time.time(), new_model_work=0))
    try:
        writers = list(write_once.starmap([(plan, source_hash, "candidate_a"),
                                          (plan, source_hash, "candidate_b")]))
        save("writers.json", writers)
        winners = [r for r in writers if r["status"] == "completed"]
        if len(winners) != 1 or sum(r["status"] == "admission_denied" for r in writers) != 1:
            raise RuntimeError("expected exactly one admitted writer; preserve and reconcile")
        readback = read_independently.remote(plan, source_hash)
        save("readback.json", readback)
        if readback["payload_sha256"] != winners[0]["payload_sha256"]:
            raise RuntimeError("independent Volume read/hash failed")
        save("result.json", dict(status="passed", new_model_work=0,
                                 actual_provider_cost_usd=None, reserved_upper_usd=2,
                                 finished_epoch=time.time(), source_commit=commit))
    finally:
        prefix = "midpoint/" + plan["campaign_id"] + "/"
        keys = ["campaign", "ready/candidate_a", "ready/candidate_b"]
        keys += [kind + "/" + run for kind in ("intent", "claim", "terminal")
                 for run in ("writer", "reader")]
        keys += ["attempt/writer/" + x for x in ("candidate_a", "candidate_b")]
        keys += ["attempt/reader/independent_reader"]
        # Expiring Dict records are independently retained even after failure.
        save("admission_ledger.json", {key: claims.get(prefix + key) for key in keys})
    print("CPU preflight passed: one admitted writer and independent persisted hash verified; zero model work.")
