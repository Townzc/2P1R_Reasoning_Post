"""Claude independent audit of reports/p007_audit/pilot_v1 (read-only)."""
import json, hashlib, collections, sys
P = sys.argv[1]
m = json.load(open(f"{P}/manifest.json"))
for f, v in m["files"].items():
    print("sha", f, hashlib.sha256(open(f"{P}/{f}", "rb").read()).hexdigest() == v["sha256"])
S = json.load(open(f"{P}/parent_supply.json")); C = json.load(open(f"{P}/prefix_costs.json")); R = json.load(open(f"{P}/results.json"))
print("parents", len(S), "unique", len({s["problem_id"] for s in S}), "attempted", sum(s["attempted"] for s in S), "usable", sum(s["usable"] for s in S))
for k in ["1", "2", "4"]:
    reached = sum(s["attempts_to_k"].get(k) is not None for s in S)
    print("k", k, "reached", reached, "censored", len(S) - reached, "reported", R["supply"][k])
print("usable per parent", sorted(collections.Counter(s["usable"] for s in S).items()))
pc = {(p["problem_id"], p["k"]): p for p in C}
bad = sum(1 for s in S for k, a in s["attempts_to_k"].items()
          if (s["problem_id"], int(k)) not in pc or pc[(s["problem_id"], int(k))]["reached"] != (a is not None)
          or (a is not None and pc[(s["problem_id"], int(k))]["attempts"] != a))
print("prefix table mismatches", bad)
for k in [1, 2, 4]:
    xs = [p for p in C if p["k"] == k and p["reached"]]
    print("k", k, "mean attempts among reached", round(sum(p["attempts"] for p in xs) / len(xs), 3))
