"""CPU scoring with exact old-score reuse and paired development contrasts."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
from pathlib import Path
import time

import numpy as np

from experiments.public_math_pilot_v1 import analyze_runtime as prior_analysis
from experiments.public_math_pilot_v1.scoring import environment_identity
from .io import NEW_ARMS, OLD_ARMS, digest, independent_output, read, save, sha


def paired_interval(lower, upper, confidence=.975, replicates=10000):
    lo, hi = np.asarray(lower,dtype=float), np.asarray(upper,dtype=float)
    if lo.ndim != 1 or not len(lo) or lo.shape != hi.shape or np.any(lo>hi):
        raise ValueError("Invalid paired bounds")
    rng=np.random.default_rng(2026092903)
    boot_lo, boot_hi=[],[]
    for start in range(0,replicates,250):
        idx=rng.integers(0,len(lo),size=(min(250,replicates-start),len(lo)))
        boot_lo.extend(lo[idx].mean(axis=1));boot_hi.extend(hi[idx].mean(axis=1))
    alpha=(1-confidence)/2
    return dict(mean_lower=float(lo.mean()), mean_upper=float(hi.mean()),
                interval=[float(np.quantile(boot_lo,alpha)),float(np.quantile(boot_hi,1-alpha))],
                confidence=confidence, questions=len(lo), replicates=replicates, seed=2026092903,
                training_seed_uncertainty_included=False, exploratory=True)


def contrast(left, right):
    if left["questions"] != right["questions"]:
        raise ValueError("Paired denominators differ")
    return (np.asarray(left["per_question_lower"])-np.asarray(right["per_question_upper"]),
            np.asarray(left["per_question_upper"])-np.asarray(right["per_question_lower"]))


def summarize(scored):
    summaries={}
    for name,values in scored.items():
        bounds=prior_analysis.outcome_bounds([[v["judgment"]["correct"]] for v in values],1)
        summaries[name]=dict(bounds, mean_output_tokens=sum(v["raw_record"]["output_tokens"] for v in values)/len(values),
            parse_failures=sum(v["judgment"].get("parseable") is False for v in values),
            length_caps=sum(v["raw_record"]["stop_reason"]=="length_cap" for v in values))
    comparisons={}
    for control in NEW_ARMS:
        for decoding in ("greedy","sampled"):
            treatment, comparator=f"QDW_v0-{decoding}",f"{control}-{decoding}"
            if treatment in summaries and comparator in summaries:
                comparisons[f"QDW-minus-{control}-{decoding}"]=paired_interval(*contrast(summaries[treatment],summaries[comparator]))
        if all(f"{arm}-{dec}" in summaries for arm in ("QDW_v0",control) for dec in ("greedy","sampled")):
            gl,gu=contrast(summaries["QDW_v0-greedy"],summaries[f"{control}-greedy"])
            sl,su=contrast(summaries["QDW_v0-sampled"],summaries[f"{control}-sampled"])
            comparisons[f"QDW-minus-{control}-sampled-minus-greedy"]=paired_interval(sl-gu,su-gl,confidence=.95)
    for decoding in ("greedy","sampled"):
        left,right=f"position_difficulty-{decoding}",f"random-{decoding}"
        if left in summaries and right in summaries:
            comparisons[f"matched-minus-random-{decoding}"]=paired_interval(*contrast(summaries[left],summaries[right]),confidence=.95)
    return dict(schema=1, status="complete" if len(scored)==12 else "incomplete",
                runs=len(scored), summaries=summaries, comparisons=comparisons,
                evaluation="512 previously observed Numina dev questions; not independent confirmation",
                training_seeds=1, new_control_mask_seeds=1, sampled_draws_per_question=1,
                primary_exploratory="QDW minus each control under greedy; two97.5% question intervals",
                secondary_interactions="95% descriptive paired intervals, not additional confirmatory tests")


def reused_scores(prior, references, expected_scorer_hash):
    result={}
    historical=read(Path(__file__).with_name("HISTORICAL_BINDINGS.json"))
    for arm in OLD_ARMS:
        name=f"{arm}-step128-dev"
        records,meta=prior_analysis.load_complete_run(prior,"unused",dict(name=name),references)
        marker=read(prior/"analysis"/"runs"/(name+".json"))
        if marker["score_sha256"] != historical["dev_score_sha256"][name]:
            raise ValueError("Historical scores differ from the independent final audit")
        values=[]
        for raw,ref in zip(records,references):
            value=read(prior/"analysis"/"scores"/name/(raw["id"]+".json"))
            expected=dict(raw_record_sha256=digest(raw), reference_sha256=digest(ref["reference"]),
                          scorer_identity_sha256=expected_scorer_hash, dataset="dev", problem_id=raw["id"])
            if value["identity"] != expected:
                raise ValueError("Historical score does not bind the original raw output/reference/scorer")
            values.append(value)
        if (marker["outputs"] != 512 or marker["score_sha256"] != digest(values) or
                marker["raw_complete_sha256"] != sha(prior/"generation"/name/"COMPLETE.json") or
                marker["model"] != meta["model"]):
            raise ValueError("Historical score-run receipt differs")
        result[f"{arm}-greedy"]=values
    return result


def run(args):
    out,prior=independent_output(args.output,args.prior)
    analysis=out/"analysis"
    analysis.mkdir(parents=True,exist_ok=True)
    with (analysis/"CPU.lock").open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        references=prior_analysis.load_references(args.release)["dev"]
        identity=read(prior/"analysis"/"SCORER_IDENTITY.json")
        if (identity["environment"]!=environment_identity() or
                identity["scoring_source_sha256"]!=sha(Path(prior_analysis.__file__).with_name("scoring.py"))):
            raise ValueError("Historical CPU scorer environment/source changed")
        save(analysis/"SCORER_IDENTITY.json",identity)
        scorer_hash=digest(identity)
        scored=reused_scores(prior,references,scorer_hash)
        jobs=[(a,"greedy") for a in NEW_ARMS]+[(a,"sampled") for a in (*OLD_ARMS,*NEW_ARMS)]
        try:
            with ThreadPoolExecutor(max_workers=4,initializer=prior_analysis._init_scorer) as pool:
                while time.time()+30 < args.deadline_unix:
                    for arm,decoding in jobs:
                        key=f"{arm}-{decoding}"
                        name=key+"-dev"
                        if key in scored or not (out/"generation"/name/"COMPLETE.json").exists():
                            continue
                        records,meta=prior_analysis.load_complete_run(out,"unused",dict(name=name),references)
                        lookup={r["problem_id"]:r["reference"] for r in references}
                        items=[(r,lookup[r["id"]],"dev",analysis/"scores"/name/(r["id"]+".json"),scorer_hash) for r in records]
                        values=list(pool.map(prior_analysis.score_one,items))
                        scored[key]=values
                        save(analysis/"runs"/(name+".json"),dict(outputs=512,score_sha256=digest(values),
                            model=meta["model"],raw_complete_sha256=sha(out/"generation"/name/"COMPLETE.json")))
                        print(json.dumps(dict(event="dev_run_scored",run=key,correct=sum(v["judgment"]["correct"] is True for v in values))),flush=True)
                    report=summarize(scored)
                    save(analysis/"snapshots"/f"runs_{len(scored):02d}.json",report)
                    if len(scored)==12:
                        save(analysis/"RESULTS.json",report)
                        save(out/"CPU_COMPLETE.json",dict(new_scored_outputs=4096, reused_scored_outputs=2048,
                            report_sha256=sha(analysis/"RESULTS.json"),new_model_calls=0))
                        return dict(status="scoring_complete",runs=12)
                    if not args.watch:
                        return dict(status="available_outputs_scored",runs=len(scored))
                    time.sleep(5)
        finally:
            for scorer in prior_analysis._SCORERS:
                scorer.close()
        return dict(status="stopped_at_cpu_deadline",runs=len(scored))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("output","prior","release"):
        p.add_argument("--"+key,required=True)
    p.add_argument("--deadline-unix",type=float,required=True)
    p.add_argument("--watch",action="store_true")
    print(json.dumps(run(p.parse_args()),sort_keys=True),flush=True)
