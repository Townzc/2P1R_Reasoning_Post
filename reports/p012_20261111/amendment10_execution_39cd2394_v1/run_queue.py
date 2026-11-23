"""Serial, restartable operations for the fourteen reviewed A10 endpoints."""
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from evidence import (PUB, PREP, PRIVATE, RUNS, AUTHORITY, REVIEW, CODE, read, write, sha,
                      require, training_binding, package, OWNER_BUDGET, OWNER_BUDGET_COMMIT, OWNER_BUDGET_SHA)

LOCAL = Path(".local/p012_20261111")
sys.path[:0] = [".", str(LOCAL / "amendment7_v1")]
from a7_ops import lock, publish as git_publish

PY = str(LOCAL / "tinker_venv312/bin/python")
ENTRY = str(LOCAL / "amendment4_v1/launch_tinker_private.py")
ENV = dict(os.environ, PYTHONPATH=".", PYTHONUNBUFFERED="1")
BRANCH = "codex/icml-acl-2027"
REMOTE = "origin/" + BRANCH
TEMPLATES = PREP / "request_templates"
COMBINED = "b8f08cc70d3e7d5b0fb9587855abcfa762c34ba0"
FIRST = ["a10_logiqa_4b_baseline4096_s17_v1", "a10_logiqa_9b_baseline4096_s17_v1"]
ARMS = [(17,x) for x in ("L","P","R","S2","S4","K4s","R8")] + [(29,x) for x in ("P","R","L","S2","S4")]
ORDER = FIRST + [f"a10_tinker_lora_4b_logiqa_{arm.lower()}_s{seed}_v1" for seed,arm in ARMS]
POINTS = {"4B":79, "L":78, "P":78.5, "S2":78.5, "S4":78, "R":73, "K4s":78, "R8":75}
CAP = {"baseline":6, "train_eval":125}
CHILDREN = {}
current = None


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git(*args):
    return subprocess.check_output(["git", *map(str,args)])


def publish(paths, message):
    # A push can fail after a successful local commit. Fetch first, then retry a normal push.
    for attempt in range(3):
        try:
            commit = git_publish(paths, message)
            if subprocess.run(["git","merge-base","--is-ancestor",commit,REMOTE]).returncode == 0:
                return commit
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
        with lock("GIT_PUBLICATION.lock"):
            subprocess.run(["git","fetch","origin",BRANCH], check=True)
            require(subprocess.run(["git","merge-base","--is-ancestor",REMOTE,"HEAD"]).returncode == 0,
                    "Remote branch diverged; preserved evidence")
            subprocess.run(["git","push","origin",BRANCH],check=True)
    raise RuntimeError("Normal publication did not reach remote")


def remote_bytes(path):
    require(path.read_bytes() == git("show",f"{REMOTE}:{path}"), "Remote evidence differs: " + str(path))


def schedule_check():
    accepted = read(PREP / "ACCEPTED_REVIEW.json")
    require(accepted["commit"] == REVIEW, "Accepted source identity")
    for key,path in {"runner":"experiments/p012/tinker_lora.py","config":"experiments/p012/training_config.py",
                     "score_adapter":PREP/"score_logiqa.py","freezer":PREP/"freeze_data.py"}.items():
        require(sha(path) == accepted[key+"_sha256"], "Accepted source bytes: "+key)
    cells = read(PREP/"DATA_MANIFEST.json")["cells"]
    require([(x["seed"],x["arm"]) for x in cells] == ARMS, "Frozen schedule")
    require(sha(OWNER_BUDGET) == OWNER_BUDGET_SHA, "Budget authorization bytes")
    owner = read(OWNER_BUDGET)
    require(owner["remaining_training_endpoints"] == ORDER[3:] and owner["accepted_training_review_commit"] == REVIEW,
            "Owner budget authorization scope")
    for name in ORDER:
        path = TEMPLATES / (name + ".json")
        require(path.read_bytes() == git("show",f"{COMBINED}:{path}"), "Frozen template "+name)
    require(sha(PREP/"../amendment10_combined_training_review_v1/BUDGET_SETTLED.json")
            == read(PUB/"INITIAL_BILLING_AND_STORAGE.json")["S1_ledger_sha256"], "S1 ledger identity")


def evaluation_of(name):
    return name.removesuffix("_v1") + "_greedy_v1"


def ledger(replacing_evaluation=None):
    spent = {"baseline":0.0, "train_eval":0.0}
    reserved = dict(spent)
    details = []
    pause_file = PUB / "OWNER_PAUSE_SEED29.json"
    pause = read(pause_file) if pause_file.exists() else {}
    for p in sorted((PUB/"admissions").glob("*.json")):
        gate = read(p)
        if not gate["admitted"]:
            continue
        name, bucket = gate["run_id"],gate["bucket"]
        d = RUNS/name/"result"
        done = (d/"COMPLETE.json").exists() and not (d/"PARTIAL_USAGE.json").exists()
        item = float(gate.get("call_buffered_usd",gate["buffered_next_usd"]))
        measured = read(d/"USAGE.json")["upper_token_cost_usd"] if done else 0
        outstanding = 0 if done else item
        ev = evaluation_of(name)
        if (gate.get("reserved_post_eval_usd") and ev != replacing_evaluation
                and not (PUB/"admissions"/(ev+".json")).exists()):
            outstanding += gate["reserved_post_eval_usd"]
        cancelled = name == pause.get("cancelled_training_run")
        if cancelled:
            usage_path = PUB / pause["training_usage_file"]
            require(not done and sha(usage_path) == pause["training_usage_sha256"], "Cancelled training usage binding")
            measured = read(usage_path)["incurred_training_token_cost_usd"]
            require(measured == pause["incurred_training_token_cost_usd"], "Cancelled training charge")
            outstanding = 0
        spent[bucket] += measured
        reserved[bucket] += outstanding
        details.append(dict(run_id=name,bucket=bucket,completed=done,token_upper_usd=measured,reserved_usd=outstanding,
                            exceeded_reference_limits=gate.get("exceeded_reference_limits", [])))
        if cancelled:
            details[-1].update(status="负责人暂停", failure=False, automatic_retry=False,
                               provider_completed_updates=pause["provider_completed_updates"],
                               training_input_tokens=pause["training_input_tokens"])
    s1 = read(PUB/"INITIAL_BILLING_AND_STORAGE.json")["S1_accounted_usd"]
    return dict(S1_accounted_usd=s1,spent=spent,reserved=reserved,line_items=details,
                total_accounted_usd=s1+sum(spent.values()),total_reserved_usd=sum(reserved.values()))


def estimates(name, req, parent):
    if name in FIRST:
        return req["forecast"]["forecast_usd"],0,req["forecast"]["basis"]
    if parent:
        old = read(PUB/"admissions"/(parent+".json"))
        return old["reserved_post_eval_usd"],0,"Previously reserved greedy evaluation forecast"
    training = req["cpu_counts"]["training_input_tokens"] * req["dose"]["epochs"] * req["prices_per_million"]["train"] / 1e6 * 1.5 + .10
    require(abs(training - req["forecast"]["training_buffered_usd"]) < 1e-9,"Reviewed training forecast")
    reference = FIRST[0] if name == ORDER[2] else evaluation_of(ORDER[2])
    measured = read(RUNS/reference/"result/USAGE.json")["upper_token_cost_usd"]
    return (training, 1.5 * measured,
            "Frozen training tokens x train rate x 1.5 + $0.10; full 4B greedy token cost x 1.5 from " + reference)


def budget_decision(name, parent, bucket, projected_bucket, projected_total):
    require(all(math.isfinite(v) and v >= 0 for v in (projected_bucket, projected_total)), "Invalid cost ledger")
    require(sha(OWNER_BUDGET) == OWNER_BUDGET_SHA, "Owner budget decision hash")
    endpoints = read(OWNER_BUDGET)["remaining_training_endpoints"]
    endpoint = parent or name
    covered = (bucket == "train_eval" and endpoint in endpoints
               and (parent is None or name == evaluation_of(parent)))
    exceeded = []
    if projected_bucket > CAP[bucket]:
        exceeded.append(bucket)
    if projected_total > 200:
        exceeded.append("A10_total")
    decision = dict(admitted=covered or not exceeded, exceeded_reference_limits=exceeded,
                    authorized_to_continue_over_reference_limits=covered)
    if covered:
        decision.update(owner_budget_authority_commit=OWNER_BUDGET_COMMIT, owner_budget_authority_sha256=OWNER_BUDGET_SHA)
    return decision


def resolve_request(name, parent=None, binding=None):
    if parent is None:
        require(name in ORDER, "Request is outside the frozen endpoint order")
    else:
        require(parent in ORDER[2:] and name == evaluation_of(parent), "Unregistered post-training evaluation")
    template = TEMPLATES/((FIRST[0] if parent else name)+".json")
    req = read(template)
    if parent:
        req.update(run_id=name, seed=binding["cell"]["seed"], sampler_path=binding["sampled_weights"],
                   training_run_id=parent, training_request_sha256=binding["training_request_sha256"],
                   sampler_receipt_sha256=binding["sampler_receipt_sha256"])
    req.update(code_commit=CODE, accepted_review_commit=REVIEW, review_status="accepted")
    gatepath = PUB/"admissions"/(name+".json")
    reqpath = PUB/"requests"/(name+".json")
    with lock("BUDGET_ADMISSION.lock"):
        if not gatepath.exists():
            bucket = "baseline" if name in FIRST else "train_eval"
            books = ledger(replacing_evaluation=name if parent else None)
            call, hold, basis = estimates(name,req,parent)
            next_cost = call + hold
            bucket_cost = books["spent"][bucket] + books["reserved"][bucket] + next_cost
            total_cost = books["total_accounted_usd"] + books["total_reserved_usd"] + next_cost
            gate = dict(utc=utc(),run_id=name,review_commit=REVIEW,template_sha256=sha(template),
                        bucket=bucket,buffered_next_usd=next_cost,call_buffered_usd=call,reserved_post_eval_usd=hold,
                        projected_bucket_usd=bucket_cost,projected_total_usd=total_cost,subcap_usd=CAP[bucket],
                        total_cap_usd=200, basis=basis,ledger_before=books,replaces_eval_hold_from=parent,
                        **budget_decision(name,parent,bucket,bucket_cost,total_cost))
            write(gatepath, gate)
        gate = read(gatepath)
        if not gate["admitted"]:
            publish([gatepath],"P012 A10: record stopped financial admission "+name)
            raise ValueError("Hard budget gate stopped " + name)
        if not reqpath.exists():
            req["forecast"].update(admitted=True,forecast_usd=gate["buffered_next_usd"],basis=gate["basis"],
                                   subcap_usd=gate["subcap_usd"],overall_cap_usd=200,
                                   admission_file=str(gatepath),admission_sha256=sha(gatepath))
            if gate.get("owner_budget_authority_commit"):
                req["forecast"]["owner_budget_authority_commit"] = gate["owner_budget_authority_commit"]
                req["forecast"]["dollar_limits_are_reporting_thresholds"] = True
            if req["mode"] == "train":
                req["forecast"]["reserved_greedy_usd"] = gate["reserved_post_eval_usd"]
            write(reqpath,req)
        else:
            saved = read(reqpath)
            require({k:v for k,v in req.items() if k!="forecast"} == {k:v for k,v in saved.items() if k!="forecast"}
                    and saved["forecast"]["admission_sha256"] == sha(gatepath), "Existing request differs "+name)
        commit = publish([gatepath, reqpath],"P012 A10: admit frozen request "+name)
        remote_bytes(reqpath)
        remote_bytes(gatepath)
        d = RUNS/name
        d.mkdir(parents=True,exist_ok=True)
        if not (d/"request.json").exists():
            (d/"request.json").write_bytes(reqpath.read_bytes())
        require((d/"request.json").read_bytes() == reqpath.read_bytes(), "Local request differs")
        return d,commit


def published_packets():
    packets = []
    host = "https://github.com/Townzc/2P1R_Reasoning_Post/blob/"
    lines = ["# A10 已发布端点", "", "每行链接固定在该端点首次发布的提交，可直接转交 Claude。", "",
             "| 端点 | 答对 / 总数 | 准确率 | 审查包 | 独立复核 |", "|---|---:|---:|---|---|"]
    for endpoint in ORDER:
        dest = PUB/"endpoints"/endpoint
        if not (dest/"RESULTS.json").exists():
            continue
        x = read(dest/"RESULTS.json")
        first = git("log", "-1", "--diff-filter=A", "--format=%H", REMOTE,
                    "--", dest/"INPUT_MANIFEST.json").decode().strip()
        require(len(first) == 40, "Endpoint packet is missing on the execution branch: " + endpoint)
        url = host + first + "/" + str(dest/"README.md")
        acceptance = dest/"ACCEPTANCE.json"
        audit = read(acceptance) if acceptance.exists() else {}
        state = audit.get("independent_post_run_audit","pending")
        audit_url = (host + audit["accepted_review_commit"] + "/" + audit["review_document"]) if audit else None
        label = ("4B 基线" if endpoint == FIRST[0] else "9B 基线") if not x["training"] else (
            x["training"]["cell"]["arm"] + " · seed " + str(x["training"]["cell"]["seed"]))
        verdict = "[通过](" + audit_url + ")" if audit_url else "待复核"
        lines.append(f"| {label} | {x['correct']} / {x['responses']} | {100*x['accuracy']:.2f}% "
                     f"| [{first[:8]}]({url}) | {verdict} |")
        packets.append(dict(endpoint=endpoint, packet=str(dest/"README.md"), packet_commit=first, packet_url=url,
                            responses=x["responses"], correct=x["correct"], independent_audit=state,
                            independent_audit_url=audit_url))
    (PUB/"REVIEW_LINKS.md").write_text("\n".join(lines)+"\n")
    return packets


def final_review(packets, books):
    require([item["endpoint"] for item in packets] == ORDER, "Missing endpoint in final review")
    manifest = read(PREP/"DATA_MANIFEST.json")
    expected = {(c["arm"], c["seed"]):c for c in manifest["cells"]}
    bindings = []
    updates = 0
    for item in packets:
        name = item["endpoint"]
        directory = PUB/"endpoints"/name
        result = read(directory/"RESULTS.json")
        inputs = read(directory/"INPUT_MANIFEST.json")
        require(result["responses"] == item["responses"] == 1572 and result["endpoint"] == name,
                "Final endpoint coverage: " + name)
        require(sha(directory/"evidence.zip") == inputs["archive_sha256"], "Final archive hash: " + name)
        dose = None
        if name not in FIRST:
            dose = result["training"]["cell"]
            require(dose == expected.pop((dose["arm"],dose["seed"])), "Final training identity: " + name)
            updates += dose["updates"]
        bindings.append(dict(endpoint=name, review_packet=item["packet_url"], packet_commit=item["packet_commit"],
                             independent_audit_at_delivery=item["independent_audit"], dose=dose,
                             correct=result["correct"], responses=result["responses"],
                             raw_sha256=result["raw_sha256"], labels_sha256=result["labels_sha256"],
                             evidence_zip_sha256=inputs["archive_sha256"], input_manifest_sha256=sha(directory/"INPUT_MANIFEST.json")))
    require(not expected and updates == sum(c["updates"] for c in manifest["cells"]), "Final registered doses")
    dest = PUB/"FINAL_REVIEW.json"
    if dest.exists():
        require(read(dest)["endpoints"] and [b["packet_commit"] for b in read(dest)["endpoints"]]
                == [b["packet_commit"] for b in bindings], "Final delivery snapshot binding")
        return dest
    write(dest,dict(utc=utc(), scientific_review=REVIEW, frozen_plan=AUTHORITY,
                    owner_budget_authority=OWNER_BUDGET_COMMIT, review_index=str(PUB/"REVIEW_LINKS.md"),
                    endpoints=bindings, total_endpoints=len(bindings), total_training_updates=updates,
                    total_greedy_outputs=sum(b["responses"] for b in bindings), final_token_ledger=books))
    return dest


def status(stage,name=None,reason=None):
    packets = published_packets()
    record = dict(utc=utc(),status=stage,current_run=name,reason=reason,order=ORDER,
                  endpoints_published=packets,expected_endpoints=14,budget=ledger(),
                  remaining_queue_budget_authority=dict(commit=OWNER_BUDGET_COMMIT, path=str(OWNER_BUDGET),
                      original_reference_limits_usd={"train_eval":125, "A10_total":200},
                      effect="Publish any threshold crossing and continue the owner's frozen queue"),
                  review_commit=REVIEW,scientific_source_commit=CODE)
    write(PUB/"STATUS.json",record)
    paths = [PUB/"REVIEW_LINKS.md",PUB/"STATUS.json"]
    if stage == "complete":
        paths.append(final_review(packets, record["budget"]))
    publish(paths,"P012 A10: "+stage+" "+(name or "14 endpoints"))


def await_run(name, parent=None, binding=None):
    global current
    current=name
    d,commit = resolve_request(name,parent,binding)
    launch = PUB/"launches"/(name+".json")
    marker = d/"LAUNCH_RECEIPT.json"
    if not launch.exists():
        if not marker.exists():
            require(not (d/"run.log").exists() and not (d/"result").exists(),"Existing cloud call requires inspection: "+name)
            schedule_check()
            with (d/"run.log").open("x") as log:
                child = subprocess.Popen([PY,ENTRY,str(d)],env=ENV,stdin=subprocess.DEVNULL,stdout=log,
                                         stderr=subprocess.STDOUT,start_new_session=True)
            CHILDREN[name]=child
            write(marker,dict(run_id=name,utc=utc(),pid=child.pid,admission_commit=commit,
                              request_sha256=sha(d/"request.json"),source_commit=CODE,accepted_review_commit=REVIEW))
        write(launch,read(marker))
    publish([launch],"P012 A10: record launch "+name)
    remote_bytes(launch)
    pid=read(launch)["pid"]
    require(sha(d/"request.json") == read(launch)["request_sha256"],"Launch receipt binding")
    if not (d/"result/COMPLETE.json").exists():
        status("running",name)
    while True:
        if (d/"result/PARTIAL_USAGE.json").exists():
            raise RuntimeError("Service recorded partial usage for "+name+"; original request retained")
        if name in CHILDREN:
            alive = CHILDREN[name].poll() is None
        else:
            process = subprocess.run(["ps","-p",str(pid),"-o","command="],capture_output=True,text=True)
            alive = process.returncode==0 and d.name in process.stdout and "launch_tinker_private.py" in process.stdout
        if not alive:
            require((d/"result/COMPLETE.json").exists()
                    and (name not in CHILDREN or CHILDREN[name].returncode==0), "Worker stopped without clean completion: "+name)
            break
        time.sleep(6)
    return d


def score(name, endpoint):
    d=RUNS/name
    raw=d/"result/generation/raw.jsonl"
    require(read(d/"result/generation/GENERATION_COMPLETE.json")["raw_sha256"]==sha(raw),"Raw completion hash")
    freeze_path=PUB/"predictions_before_score"/(name+".json")
    if not freeze_path.exists():
        arm=read(RUNS/endpoint/"request.json").get("A10_arm","4B" if endpoint==FIRST[0] else "9B")
        authority_file=Path("audit/claude/20261120e/P012_PLAN_v1_AMENDMENT_10.md")
        write(freeze_path,dict(utc=utc(),run_id=name,authority_commit=AUTHORITY,review_commit=REVIEW,
                               prediction_source=str(authority_file),authority_file_sha256=sha(authority_file),
                               prediction_section=4,frozen_arm=arm,frozen_point_accuracy_percent=POINTS.get(arm),
                               raw_sha256=sha(raw), evaluation_request_sha256=sha(d/"request.json"),
                               note="The amendment states no numeric 9B baseline point." if arm=="9B" else "Original amendment point estimate."))
    publish([freeze_path],"P012 A10: bind frozen prediction before scoring "+name)
    remote_bytes(freeze_path)
    local=d/"PREDICTION_BEFORE_SCORE.json"
    if not local.exists():
        local.write_bytes(freeze_path.read_bytes())
    require(local.read_bytes()==freeze_path.read_bytes() and read(local)["raw_sha256"]==sha(raw),"Prediction binding")
    if not (d/"score_v1/RESULTS.json").exists():
        require(not (d/"score_v1").exists(),"Incomplete local scoring output")
        subprocess.run([PY,str(PREP/"score_logiqa.py"),str(d)],check=True,env=ENV)


def main():
    if (PUB / "OWNER_PAUSE_SEED29.json").exists():
        print("负责人暂停 A10 seed 29。")
        return
    schedule_check()
    for endpoint in ORDER:
        packet = PUB/"endpoints"/endpoint
        if not packet.exists():
            await_run(endpoint)
            binding=None
            evaluation=endpoint
            if endpoint not in FIRST:
                binding=training_binding(endpoint)
                evaluation=evaluation_of(endpoint)
                await_run(evaluation,endpoint,binding)
            score(evaluation,endpoint)
            package(endpoint,evaluation,binding)
        publish([packet],"P012 A10: publish complete independent-review packet "+endpoint)
        remote_bytes(packet/"INPUT_MANIFEST.json")
        manifest = read(packet/"INPUT_MANIFEST.json")
        require(sha(packet/"evidence.zip")==manifest["archive_sha256"],"Published archive hash")
        if not (PRIVATE/"delivered"/endpoint).exists():
            status("endpoint_published",endpoint)
            (PRIVATE/"delivered").mkdir(exist_ok=True)
            (PRIVATE/"delivered"/endpoint).write_text(utc())
    status("complete")


if __name__ == "__main__":
    with (PRIVATE/"queue.lock").open("a") as mutex:
        try:
            fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("Existing A10 supervisor holds the lock.")
        try:
            main()
        except Exception as error:
            traceback.print_exc()
            # Private detailed logs can contain service paths. Only the exception class is public
            # for unforeseen faults; local invariant failures above contain sanitized descriptions.
            reason = str(error) if isinstance(error,(ValueError,RuntimeError)) else type(error).__name__
            write(PRIVATE/"STOP.json",dict(utc=utc(),run=current,reason=reason))
            status("stopped_for_inspection",current,reason)
            raise
