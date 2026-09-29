# Post-E039 decision supervision: finite authorized continuation

The owner requested execution of the supplied Post-E039 plan on the existing
single A800. This supersedes the previous pause only for the finite phase below.
Input handoff SHA256:99b2ec8bf0a53baf1927351c66b57d8b40d70d4b499130e5e381f50b170a2440.
The author's source is the previous result summary, not a new model measurement.
Preserve the E038/E039 negative/inconclusive primary results and all earlier raw
records and resource ledgers. No external messages or submissions are authorized.

## Fixed stages and identities

Stage A evaluates all actual unique original F-replay training prompts (expected
256 per parent) and32 fixed H-training groups ×2 targets for E038/E039 step256.
F uniqueness is defined by actual serialized prompt tokens; do not substitute H
numbers without a scaffold for actual F training examples. H single anchors are
supervised, single countergoals unsupervised, and both paired targets supervised.
Selection is outcome-blind: hash order under frozen operator-pair/hole/anchor
strata. A nested F64/F16 and H32/H8 supply endpoint/midpoint diagnostics.

All1024 original H rows across the two recipes require character/token/causal
provenance for the first semantic commitment to the missing operation. Earlier
operation-dependent numerical commitments must not be ignored. The unchanged
postorder renderer, ordered AST and four counterfactual operation renderings
must reproduce the exact response and common causal prefix. No missing row can
be dropped or relabeled as a final-answer operation. Prompt/padding/EOS are never
upweighted; real EOS remains ordinarily supervised. F program-operation,
input-copy and computed-number masks are descriptive diagnostics only.

Record full ordinary response NLL, first-decision versus other-token NLL,
probabilities/ranks and first literal deviation. Semantic errors and certified
prefix dead ends are separate; unsupported judgments remain unknown. Accept any
valid F program. During fixed Stage A greedy cases observe actual raw/effective
logits and selected tokens at the same prefix, including ties/cache/precision.
Observer instrumentation must preserve the logits tensor and generation settings.
A genuine implementation mismatch or unresolvable first-decision mapping stops
new training. Accuracy, loss magnitude and significance do not control admission.

| Registered ID | State | Parent | Objective | Added updates |
|---|---|---|---|---:|
| E040 | S-U | E038 step256 | Ordinary response CE |128|
| E041 | S-D | E038 step256 | H first-decision weighted CE |128|
| E042 | P-U | E039 step256 | Ordinary response CE |128|
| E043 | P-D | E039 step256 | H first-decision weighted CE |128|

Allocation inspected the actual registry through E039; see registration.json.
All arms retain the parent LoRA adapter rather than adding another adapter.
Qwen2.5-1.5B Base revision8faed761d45a263340a0528343f099c05c9a4323;
LoRA r16/alpha32, FP32 parameters with BF16 autocast, SDPA and TF32 off.
Each uses the exact original H512 and common F512 records for two further epochs,
128 updates of8H+8F with inherited microbatch1 and raw supervised-token denominator.
Reset optimizer/scheduler and training RNG symmetrically; seed17, peakLR5e-5,
inherited optimizer/clipping/dropout, same frozen128-step LR and order for U/D.
Execute frozen LR values; CPU validation permits at most2ULP libc recomputation.
Save scientific adapters at added steps64/128;128 is the sole formal endpoint.
Recover in16-update units and retain optimizer/RNG states. Evaluation preserves
caller RNG and cannot consume the paired arms' training random streams.

For H record i, supervised length L includes normal EOS and decision length K:
`w[t] = L * (5 if decision[t] else 1) / (L + 4*K)`.
Thus each H row's total weight remains L. F weights remain1. Divide the entire
8H+8F weighted sum by the original supervised H+F token count. U uses all ones.
This preserves scalar mass, not gradient norm/direction or effective learning
rate. Lambda1, causal shift, mass conservation, F invariance, masking/EOS,
resume and ordinary-CE parity require real implementation checks.

## Frozen evaluation and inference

Use48 new number/skeleton groups ×2 targets, six operation pairs ×8groups,
root/internal24 each. Exclude every seen train/dev/calibration/diagnostic identity;
protected pools are excluded by existing hashes without opening their bodies.
Freeze the release before any new model calls. This is new-instance exploratory
evidence, not a structural-OOD or external-confirmation claim.

Six states E038,E039,S-U,S-D,P-U,P-D each receive new H greedy96, new F greedy96,
and new F sampled384. No H sampling. F sampling is n4,T0.7,p0.95,k0; allmax512,
with existing stopping/scoring and unconstrained generation. Invalid/wrong/capped
outputs stay in denominators. No repairs, candidate tools or checkpoint selection.

The primary contrasts are J_H(S-D)−J_H(S-U) and J_H(P-D)−J_H(P-U), where J_H means
both targets strictly correct within a number group. Also report their equal
mean; the two recipes are not independent training seeds. Secondary transfer is
F sampled pass@1; retain F greedy/pass@4 and resource/target failure breakdowns.
Use10000 paired number-group bootstrap draws with all six states jointly sampled,
and actual skeleton-family sensitivity. Intervals exclude training-seed,
parent-seed and training-allocation uncertainty; no equivalence or multiplicity
claims. Paired−single, operator margins, D_goal and strata remain exploratory.
Seeds: data2026091711, selection2026091712, generation2026091713,
bootstrap2026091714; exact target substream seeds are recorded in the release/run.

## Finite accounting and operational stops

Stage A640 + new six-state evaluation3456 + endpoint training diagnostics512 +
midpoint128 =4736 planned generations, hard cap5000 including all actual fault
attempts. All512 added updates are planned. Forward diagnostics are separate:
planned7552 sequence equivalents across28 views, hard cap16384. A single pass
reading four one-token candidates counts one sequence, not four generations.
Pending output-less intents remain charged and are never silently repeated.

One existing single-GPU instance only. Whole powered time includes startup,
preparation, idle, CPU and export: maximum14400s and CNY40, whichever comes first,
within the standing shared ceiling. Current verified rate7.98CNY/hour; no recharge,
new instance, GPU, model or paid disk. Retain600s export/shutdown reserve and
provider timer strictly inside the overall deadline. Per-process slices admit the
next recoverable block; inability to fit the entire queue is not a score gate.
Stop on invalid scientific data, unresolved decision mapping, real implementation
inconsistency, nonfinite training, disk/time or authorization limit. Preserve and
report partial stages as missing, never as zero accuracy or a complete factorial.
No G-breadth, RL, second model, seed/LR/lambda search or automatic extra128 updates.

Historical ledgers4784/4864,2112/2304,3344/3600 and27receipts/17623process seconds
are immutable. A new independent phase records every physical process receipt,
forward sequence, token/update dose and generation reservation. Process time is
not billed whole-rental time. Preserve E015 unique weights and the existing full
E038/E039 backup. Delete only independently verified redundant artifacts if needed.
Complete full adapter/recovery/output backup and hashes, then provider-confirmed
shutdown and timer clearing. Finish heavy analysis/publication locally afterward.

Required delivery: STAGE_A_TRAIN_FIT.md, DECISION_SPAN_AUDIT.jsonl,
WEIGHTED_LOSS_CONTRACT.json, CONTINUATION_MANIFEST.json, RESULTS.md,
PER_PROBLEM.jsonl, ERRORS.jsonl, COST_SHUTDOWN.json, and an owner-reviewed draft
one-page discussion brief. Outcomes select only a future proposal, never an
unregistered automatic continuation.
