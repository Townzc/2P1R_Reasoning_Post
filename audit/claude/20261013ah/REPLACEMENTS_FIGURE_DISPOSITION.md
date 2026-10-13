# Claude audit 20261013ah pt2 — replacements G3, T1 figure/facts, ag disposition @ 8e1b3463

## p008-two-t1-replacement-outcomes-r1: **PASS**
I checked that the device copies match the published files. The git blob listing of the endpoint, result, summary, oracle and eval files has digest f112655d… both on the device and at commit 8e1b3463.

**G3, using the same `g3_endpoint.py` as before (own decode, own stop rule, own parser):**

| physical run | frozen primary | caps | event mismatches | my parser |
|---|---|---|---|---|
| `d1_b1_p0_breadth_t1_replacement_r1` | **969** (73.47%) | 42 | 0 | 969 (0 disagreements) |
| `d1_b1_p0_depth_t1_replacement_r1` | **965** (73.16%) | 43 | 0 | 965 (0 disagreements) |

**Lineage checks (container, git objects only). Both runs pass all of the following:**
- **Source:** SOURCE_BINDING equals the 34-source replacement bundle I reviewed at ed037c1c.
- **Config:** equal to the admission's physical config.
- **Ledger chain** (`config_sha256`, `intent_sha256`, `claim_sha256`, `evidence_sha256`): complete, status completed. The claim's `plan_sha256` equals the replacement plan.
- **LR and schedule:** `recipe.lrs` = `LR_VECTORS["256"]`; schedule = the frozen logical plan.
- **Identity:** `recipe.identity.config` is the logical science config and `physical_run_id` is the physical one.
- **Dose:** across 256 updates, cumulative targets reach 524,287.
- **Journal:** 16 blocks.
- **Lineage file:** `replacement_lineage.json` equals {logical, physical, parent, reconciliation sha, owner digest}.
- **Result:** carries both physical and logical ids.
- **Provider:** stopped, 0 containers.
- **Local oracle:** passes with the same counts.

Walls were 4,252 s and 4,155 s, both under the 6,001 s cap. The state SHA is a recorded checksum, not a binary I inspected.

## p008-t1-figure-and-facts-r1: **PASS**, plus one suggestion
- All 5 pairs, the counts, the depth−breadth pp values (−0.3033, −0.6823, +0.1516, −0.6065, +0.5307) and the caps match my G3 results exactly. The PNG is readable.
- The limits stated on the page are accurate:
  - points only;
  - no winner, equivalence or price threshold;
  - the B8 cell is a T1 bridge only;
  - there is no B×T result;
  - the draws share seed 17;
  - there are only 2 procurement draws;
  - the dollar amounts are hypothetical token-price caps, not equal actual spend;
  - the test set was researcher-seen in September;
  - the parser and caps rules are frozen.
- I accept the page's correction to my ag wording: whether per-cell Wilson intervals overlap is **not** a paired test.

**Suggestion: give viewers the noise scale.** I computed the paired question-level contrast with McNemar, using the frozen per-question correctness from my own G3 files. This is descriptive only and is not a pre-registered test.

| pair | breadth-only / depth-only correct | depth−breadth | paired 95% CI | exact McNemar p |
|---|---|---|---|---|
| D1/B1/0 | 114 / 110 | −0.30 pp | [−2.53, +1.92] | 0.84 |
| D1/B1/4m | 118 / 109 | −0.68 pp | [−2.92, +1.56] | 0.60 |
| D2/B1/0 | 111 / 113 | +0.15 pp | [−2.07, +2.38] | 0.95 |
| D2/B1/4m | 120 / 112 | −0.61 pp | [−2.87, +1.66] | 0.65 |
| D1/B8/0 (bridge) | 65 / 72 | +0.53 pp | [−1.21, +2.27] | 0.61 |

Every point difference is under 0.7 pp, while question-sampling noise alone is about ±2.2 pp. Training-seed variance is not included in these intervals.

A slide could add one line: "paired 95% CIs ≈ ±2.2 pp; all contrasts are indistinguishable from 0 at T1". Any such line must be labelled descriptive, not the pre-registered final analysis. **Whether to show it is the researcher's choice.**

## p008-review-ag-disposition-r1: **PASS**
- **T8 N1 is addressed:** the measurement uses min(saved start, claim)→finish. I confirmed this in the pt1 recompute: the replacements come out about 1 s above claim→finish.
- **CPU N1 is addressed:** `scripts/p008_final_cpu_guard.require_current_entry` requires the module to be `modal_audit_replacements` and to be the only `modal_*` entry in the bundle. The prepare helper calls it. `test_p008_final_cpu_entry_guard` gives 3/3 OK locally.
- **Limit:** this is a process guard. A manual `modal run` of a legacy entry would bypass it. It is acceptable because the manual path is forbidden by policy.
- **CPU N2:** remains disclosed, as stated.
