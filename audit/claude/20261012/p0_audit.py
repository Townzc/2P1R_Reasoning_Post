"""Claude independent audit of reports/p007_audit/policy_p0_v1 (read-only)."""
import json, hashlib, collections, statistics as st, sys
P = sys.argv[1]
m = json.load(open(f"{P}/manifest.json"))
for f, v in m["files"].items():
    print("sha", f, hashlib.sha256(open(f"{P}/{f}", "rb").read()).hexdigest() == v["sha256"])
A = [json.loads(l) for l in open(f"{P}/attempts.jsonl")]
B = json.load(open(f"{P}/batches.json"))
R = json.load(open(f"{P}/results.json"))
cap = 1091289088
byb = collections.defaultdict(list)
for x in A:
    byb[(x["cell"], x["batch_id"])].append(x)
for cell in ["breadth_p0", "depth_p0"]:
    a = [x for x in A if x["cell"] == cell]
    par = collections.defaultdict(list)
    for x in a:
        par[x["problem_id"]].append(x)
    lim = 1 if cell.startswith("breadth") else 4
    viol = 0
    for v in par.values():
        u = 0
        for y in sorted(v, key=lambda y: y["attempt"]):
            viol += u >= lim
            u += y["usable"]
    bs = [b for b in B if b["cell"] == cell]
    chain = all(bs[i]["previously_spent_nanodollars"] >= bs[i - 1]["cumulative_spent_nanodollars"] for i in range(1, len(bs)))
    o = R["cells"][cell]["local_oracle"]
    toks = sum(x["text_token_count"] for x in a)
    print(cell, dict(attempts=len(a), usable=sum(x["usable"] for x in a), parents=len(par),
          parents_with_usable=sum(any(y["usable"] for y in v) for v in par.values()),
          max_attempts_per_parent=max(len(v) for v in par.values()), attempts_after_retirement=viol,
          wallet_monotone=chain, spent=o["spent_nanodollars"], within_cap=o["spent_nanodollars"] <= cap,
          batches=len(bs), gen_s=o["generation_ns"] / 1e9, active_s=o["active_ns"] / 1e9,
          output_tokens=toks, gen_ms_per_token=round(o["generation_ns"] / 1e6 / toks, 3),
          mean_batch_s=round(st.mean((b["finished_ns"] - b["start_ns"]) / 1e9 for b in bs), 2),
          mean_batch_max_tokens=round(st.mean(max(x["text_token_count"] for x in byb[(cell, b["batch_id"])]) for b in bs), 1)))
# equal-output-token prefix of the depth tape (no new generation)
tok_b = sum(x["text_token_count"] for x in A if x["cell"] == "breadth_p0")
cum, kept = 0, []
for b in [b for b in B if b["cell"] == "depth_p0"]:
    xs = byb[("depth_p0", b["batch_id"])]
    t = sum(x["text_token_count"] for x in xs)
    if cum + t > tok_b:
        break
    cum += t; kept += xs
pu = collections.defaultdict(int)
for x in kept:
    pu[x["problem_id"]] += x["usable"]
print("depth prefix at breadth output tokens", dict(tokens=cum, attempts=len(kept), usable=sum(x["usable"] for x in kept),
      parents=len(pu), parents_with_usable=sum(v > 0 for v in pu.values())))
