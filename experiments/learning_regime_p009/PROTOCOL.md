# P009 — learning-regime finder, owner-authorized specification v1

Prepared before any P009 generation or training. This document incorporates the
owner's direct approvals of 2026-10-14. A0 design review and exact A1 runtime/data/
cost review remain required. This file is not a runtime admission record.

Source proposal: Claude `134c2546e54a9089439a69aedf82a142275c2a56`,
`audit/claude/20261014ay/PREREG_learning_regime_DRAFT.md`, SHA-256
`7f7d075c46e5991d6d641cf2c77d68d98c7d0c8032196a4c46c82b0f87fb3e0b`.
The original draft remains unchanged. The owner subsequently selected all five
Stage 2 conditions A/B/C/B-prime/D, with two seeds, within a new $100 total cap.
The owner also chose to retain the teacher's 2,048 context and exclude exactly
seven overlength MATH training rows, recording them as unsupported/not generated.

## Authority and automatic progression

This is a new finite experiment. P007/P008 and the October14 exploratory work,
their raw data and analyses remain closed and immutable. Their monitors remain
paused. Existing artifacts may be read for the explicitly authorized reuse and
the two new P0 parity evaluations; no old scientific call is restarted.

Within this specification, move to the next stage automatically only after all
of these are true: the registered scientific gate passes; exact applicable
source/input/numeric review passes; complete outcomes have independent local
raw verification and actual provider shutdown; forecast, hard reservation and
project budget all fit; the next named slot has no existing claim, dispatch,
attempt, intent, unit or terminal. A reviewer's suggestion is not a scope or
budget change. Send A4 and stage completion/failure notifications without asking
for another routine permission. Stop and notify if the gates fail or scope,
funding, scientific dose or runtime limits need changing. No automatic retries.

The 12-hour target is an engineering goal, not an admission condition or a promise.
Do not shorten training, evaluation or review to meet it. The draft's 12–25 hours
of active work and 1.5–3 calendar days are planning estimates, not observations.

## Questions and interpretation

H1: does either candidate show a positive distinct-question data-size effect at
fixed supervised training dose under the prespecified two-seed gate?
H2, conditional on H1: does buying verified answers outperform buying additional
first attempts under a common teacher-token spending ceiling?

P008 and the exploratory 934-versus-969 comparison motivate this study; they do
not establish that saturation caused the earlier results or that correctness
is irrelevant. Natural-wrong training changed coverage, lengths and exposure.
Failure of a new learning-curve gate does not prove allocation-insensitivity,
equivalence or an accuracy ceiling. Passing it does not prove a causal explanation
of P008. Negative-control failure triggers investigation, not a proven bug.

## Fixed scientific recipe

- Teacher: `Qwen/Qwen2.5-Math-1.5B-Instruct` at
  `aafeb0fc6f22cbf0eaeed126eff8be45b0360a35`; original chat serialization and
  sampling temperature0.8/top-p0.95/no top-k/repetition-penalty1.0, one response
  per attempt, maximum1,024 new tokens, native EOS151645/151643. Teacher context
  remains2,048. Every attempted output, duplicate and failure retains its cost.
- Students: Qwen2.5-1.5B base for NC and S1; S2 uses
  `allenai/OLMo-2-0425-1B` at `a1847dff35000b4271fa70afc5db10fd29fedbdf`.
  Llama-3.2-1B config access returned HTTP401/GatedRepoError before any output;
  the draft explicitly permits the OLMo-only fallback. No silent model switch.
- All new students:1,024 updates,2,097,148 supervised targets including their
  own EOS, seed17 or29, LoRA r16/alpha32/dropout0, same seven projection modules,
  optimizer, masking and target-normalized loss as P008. No packing or truncation.
  A single frozen1,024-value LR vector uses64 warmup steps to1e-4 followed by
  cosine to1e-5; runtime consumes exact stored bytes, not host recomputation.
- Reuse the whole-answer q/q+1 schedule builder. At least one exposure for every
  selected answer is mandatory, including n3,200. If exact dose/schedule or
  context feasibility fails, block that input release; never drop rows silently,
  truncate, pad targets, increase dose or permit q0.
- Teacher procurement tokens and student-tokenizer supervision are separate.
  OLMo uses its own terminal EOS100257 and exact new tokenization.
- Final checkpoint only. No dev/test-dependent intermediate checkpoint choice.
  Evaluation is vLLM0.11.0, bf16, greedy, direct frozen prompt token IDs,
  context2,048, GSM8K1,319 with512 new tokens, MATH-500 with1,024 new tokens.
  LoRA is merged for evaluation. Save original returned token IDs and backend
  stop metadata; CPU-only independent scoring follows. Generation must not repeat
  vocabulary enumeration or per-token reference scoring on a paid GPU.
- GSM logical stopping/scoring reuses the frozen `first_stop/completion_score`
  and marked_answer_v1. Report both backend and logical stop counts; an earlier
  task boundary is not relabeled native EOS. Logical length caps count incorrect.
  MATH last-boxed extraction/equivalence, malformed-output and stopping behavior
  must be locked by P1 before admitting student training. No post-result repair.

## Data and Stage 0

NC = GSM8K/Qwen; S1 = MATH/Qwen; S2 = GSM8K/OLMo. Existing D1 raw/source evidence
is reused. D1 B8/p0 breadth supplies3,436 verified usable unique-question rows.
Both student tokenizers encode all3,436 within2,048; total supervised lengths
are1,002,615 Qwen and946,461 OLMo, before selecting the nested3,200 subsets.
Stage 1 freezes the exact first eligible per-question D1 answer and input manifest
before new student scores. D1 attempt tapes for Stage2 stay source-bound.

MATH source pins: EleutherAI/hendrycks_math
`21a5633873b6a120296cce3e2df9d5550074f4a3`; HuggingFaceH4/MATH-500
`6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be`. Exact normalized-text audit finds
zero train/MATH-500 overlap. This is not a semantic or pretraining-contamination
guarantee. MATH contains7,500 rows but7,499 normalized unique questions; the
duplicate algebra/train/925 and959 remains in acquisition accounting. For future
unique-question student curves and Stage2 raw rosters, choose the earliest source
row in the frozen original file order **before reading correctness**. For the
known pair this is algebra/train/925; train/959 cannot supply a second first-try
eligibility chance. Both original generation costs remain in physical accounting,
and both raw records stay preserved. The immutable initial input SUMMARY used
the earlier wording "earliest eligible"; this pre-output R1 clarification
supersedes that downstream selection wording, without changing the8,993 requests.

Seven teacher-context exclusions, explicitly approved by the owner:
counting_and_probability/train/603; geometry/train/101,388,522,543;
prealgebra/train/174,1087. They are known unsupported rows, never unknown model
outputs and never counted generated. P2 is7,493 first attempts plus three extra
attempts for a fixed hash-selected500 supported rows: maximum8,993 outputs.
All first attempts precede the preselected attempt2..4 rows. Selection uses only
IDs before seeing outputs. Teacher input plus full generation cap must fit2,048.

R1, frozen before any P2 output: S1 Stage1 eligibility uses **attempt01 only**.
That first output must itself be format-eligible and correct, and that exact
output is the training answer. A success on attempt02..04 cannot rescue an
ineligible first attempt. Extra attempts serve descriptive retry analysis and
Stage2 only. This differs from NC/S2, which reuse D1 answers correct within up
to eight attempts; report the cross-setting eligibility difference explicitly.

P0: two new parity evaluations only, on the existing base638 reference and the
correct breadth969 replacement checkpoint SHA
`c3e6de44d072defadee03d552c98874c9937ad14614454540a8f2812999cc341`.
The old failed parent is not this checkpoint and remains failed. No training.
Compare identical1,319 problem IDs with saved HF outcomes. Per model:

1. Absolute accuracy gap<=1pp and discordance<=4%: comparable pass.
2. Gap>1pp and<=3pp: internal-only pass, do not mix engines in a treatment effect.
3. Gap>3pp: stop and investigate; a software bug is not inferred automatically.
4. Gap<=1pp but discordance>4%: draft is unspecified; fail closed for review,
   rather than silently granting passage. Gates use exact counts, not rounded pp.

P1: prepare a version-pinned math-verify scorer (candidate0.9.0), last boxed
answer extraction and deterministic string fallback only for defined parse/tool
failure, never to override a valid symbolic non-equivalence. Before freezing its
SHA, independently inspect50 deterministically sampled string/symbolic
disagreements from generated teacher responses; if fewer, inspect all and report
the count. Publish the complete fixed sample and adjudications for owner spot
checking. This is an error audit, not a selection of easy or favorable answers.
Use isolated processes for timeouts; math-verify's signal alarms are unsuitable
inside worker threads. Exact dependency versions and gold normalization remain
A1/P1 requirements, not implied accepted by this document.

P3: Qwen MATH0/4-shot and OLMo GSM0/4-shot, plus teacher0-shot on each test set.
P0 base also supplies the Qwen/GSM0-shot engineering reference. Do not regenerate
an old HF endpoint under its historical run identity. MATH dev comes from the
remaining original test4,500 outside MATH-500 and outside normalized train
questions. Fixed hash order selects four whole demonstrations each<=57 Qwen
tokens (no answer shortening): prealgebra/test/537,
counting_and_probability/test/460, precalculus/test/320, prealgebra/test/744.
Maximum resulting MATH-500 prompt978 leaves all1,024 output tokens. This
length-conditioned dev selection is disclosed as "short-demo 4-shot", not a
representative demonstration sample. GSM reuses the original four
dev examples; OLMo maximum four-shot prompt853. No test answers select examples.

G0 per candidate: teacher−student0-shot>=20pp; every relevant complete endpoint
has logical caps<=15% and technicalunknown0. Teacher/4-shot gap and retry success
are descriptive. A failing candidate does not enter Stage1. If none pass, stop.

## Stage 1 and G1

For each G0-passing candidate: seed17 n100/400/1,600/3,200 nested subsets from a
single frozen permutation of unique correct-answer question IDs; seed29 n400/
3,200 from its own permutation. NC has seed17 n400/3,200 only. Maximum14 new
students. The two seeds change data permutation and training randomness together;
they do not isolate initialization variance.

Run NC400/3,200 first. If gap>=5pp, stop/report, admit no positive regime. Then
run each eligible candidate's seed17 pair. Report A4 immediately. If every
candidate gap<2pp, cancel all remaining scientific slots; no partial denominators.
Otherwise complete registered remaining n100/n1,600 and seed29 pairs.

G1 requires seed17 gap>=5pp, paired-question10,000-bootstrap95% lower>0, and
seed29 gap>=2.5pp in the same direction. Bootstrap seed20261014 and the method
are frozen before new outcomes: NumPy2.5.4 PCG64/default_rng, shared question
samples, original paired_percentile implementation with batches of100,
percentile quantiles0.025/0.975 using method='linear'. Align complete Boolean
outcomes on identical lexicographically sorted problem IDs, never intersection
or unknown-to-zero conversion. The source SHA and exact convention are in
reports/p009_20261014/ANALYSIS_CONVENTION.json. Intervals are pointwise conditional
on the observed model/data choices, not simultaneous or population/seed guarantees.
If both settings pass, choose the larger seed17 gap; if difference<1pp chooseS1.
If none pass, stop. Stage1 selection uses already-seen benchmark questions;
Stage2 is conditional/adaptive inference, not an untouched confirmatory test.

## Stage 2: five conditions, same dose, two seeds

Only the G1-selected setting enters. n*=1,600 unless its seed17 n1,600 accuracy
is within1pp of n3,200 or higher, in which case n*=400. Maximum four teacher
attempts per question. Use only native-EOS, untruncated, parseable outputs.

- P_nat follows the raw seed17 question order and retains n* questions whose
  attempt01 is format-eligible and which have an eligible correct answer within
  four attempts. Freeze this order over the supported unique-question domain
  before correctness filtering. Count every traversed/skipped/censored question
  and every attempted output in the acquisition trace. A and B have this same
  eligible question set.
- A uses the literal first attempt, irrespective of correctness. If that first
  attempt is not format-eligible, it cannot be replaced silently with a later
  one; matched-set eligibility and all excluded costs require exact A6 review.
- B uses the first eligible correct attempt.
- R2, frozen before any P2 output: B's teacher-token ceiling includes every
  attempt on every question it traverses in the raw seed17 order until P_nat
  reaches n*, including failed attempts and questions it skips. D starts at the
  **first question of that same raw order**, never at the filtered P_nat list.
  D buys one first attempt per traversed question, charges format-ineligible
  outputs too, and retains each format-eligible first attempt regardless of
  correctness. D receives no free knowledge of whether retries could succeed.
  Whole outputs are indivisible: stop before the next first attempt would exceed
  B's ceiling. Report exact unused slack; call this a common spending ceiling,
  not exactly equal realized token expenditure. No fractional answer truncation.
  A6 must bind the actual raw roster, cost trace and censored next item. All real
  generation charges, including any output excluded by a virtual ceiling, remain
  in the physical/project ledger; a virtual comparison never erases paid work.
- P_mix follows the same order, at most n* questions with both eligible correct
  and wrong answers within4 attempts. B-prime uses first correct and C first
  wrong on this identical set. If fewer than300 eligible questions, C is omitted
  as specified in the draft and the shortage reported. B-prime remains a
  descriptive registered condition if its complete schedule is feasible; there
  is no B-prime-minus-C contrast. An empty/infeasible set blocks that condition
  for a concrete disposition, rather than creating synthetic or repeated rows.

At most5 conditions x2 seeds =10 students. The selected data are shared between
the two Stage2 training seeds; report that this differs from Stage1's simultaneous
permutation/training change. Reuse available GSM D1 first-four tapes without
new teacher calls. Missing first-four attempts remain unavailable, not invented.
MATH supplementary attempts have distinct unused candidate IDs and a maximum4
total attempts including P2; include them in the Stage2 cap.

Primary B−D: both seed intervals strictly above0 supports verification under
this conditional common-ceiling design; both strictly below0 favors new questions;
otherwise unresolved. Secondary B−A and B-prime−C are reported without winner
selection. Confidence intervals that include0 are not equivalence or an upper
bound on the true effect. Label agreement does not certify reasoning validity.
P_nat/P_mix selection, lengths, teacher costs and exposures are fully reported;
the conditional support design is not an unrestricted allocation-policy effect.

## Money, finite execution and reviews

New hard cap$100: Stage0$10, Stage1$50, Stage2$35, unallocated$5. No automatic
borrowing between stage caps. The unallocated$5 is not executable allowance
until a concrete allocation is approved. Include failed calls, setup/build,
input preparation on paid hosts, storage, transfer and collection charges.

Project spend ceiling remains$450 with at least$50 protected from the original
$500 envelope. The draft's '$15.76 remaining' both subtracts protection twice
and treats closed-stage reservations as additional actual spending. Preserve
those old immutable reservations; do not reset claims. Reconcile project cost
with current metering, pending/unmetered usage and the entire new allowance.
Metering is delayed, not an invoice, account balance or refunded charge.

Before each worker, use full observed batch time including serialization,
journaling and I/O, plus measured setup/closing, to forecast cost. Use the slowest
applicable observed batch; no favorable-host/time selection. Forecast must fit
80% of the remaining stage allowance, and a separate conservative hard-time
reservation must fit the stage and project. Unknown timing is not a zero cost.

The first vLLM parity pipeline has no matching full-batch measurement. Its
bootstrap calibration procedure must be explicitly reviewed in A1 before any
paid call. It must be a bounded, already-budgeted part of P0, preserve reusable
raw outputs once, measure complete batches, and abort before unaffordable work.
This is not yet admitted and cannot be bypassed using generation-only old timings.

At most4 P009 H100 workers concurrently initially, counting pending/unknown/
unmatched containers. Exact slot lists, per-entry hard timers, platform/startup/
closing margins, absolute technical windows and source/input hashes must be
published before each stage's first call. Never alter a registered plan or free
an old failed claim to retry. Preserve every attempt and STOPPED0 evidence.

A0: this design, exact gates, owner amendments and known feasibility constraints.
A1: exact applicable runtime, identities, data, EOS/LR/schedules, budget and I/O.
A2: real P0/P1, then frozen scorer. A3: complete G0 raw replay. A4: first size
pairs and registered futility. A5: G1 raw/bootstrap/cost. A6: actual five-condition
data/cost/feasibility. A7: complete results G3. A8: dated handoff, final cost
reconciliation, zero resources, pause this finite experiment's monitor.

No outside messages or subagents. Audit requests are published in the existing
INDEX and ordinary branch pushes. The optional CPU-only stopping simulation
is outside the critical path; it must be a separately labeled descriptive
artifact if prepared, never additional scientific training or teacher calls.

## Owner Plan A engineering amendment — October14, before any P0 accuracy outcome

The owner selected a common high-throughput vLLM setting for all new evaluations and a fresh full P0 under that configuration. Original eager/32-sequence P0 failed its time gate with128 unscored rows; it remains failed and those rows do not enter the new P0. The unattempted identical-engine suffix is retired. NewP0 uses original base638/correct969 references, same2638 prompts/frozen parsing/greedy512, no training. Candidate shared settings are frozen in `high_throughput_v1.py`: V1/bf16/context2048/TP1,CUDA FULL_AND_PIECEWISE,level3,max256sequences,8192batchedtokens,0.80GPUmemory,chunkedprefilltrue/prefixcachefalse,seed17. Future teacher sampling still keeps original temperature/top-p/seed/EOS/max1024; future endpoint implementations require their own exact source/input/numeric review and must use the shared settings. This amendment does not infer parity for a different model or MATH task.

Exact freshP0/runtime/bootstrap numeric review is required before a call. One first-base256 chunk is a paid measurement exception; every laterchunk uses all new complete batch times and actual elapsed. Oldeager forecasts are not substituted. New252c and old248c total500c, leaving500c in Stage0; other stagecaps and the unallocated500c remain unchanged. Planning$5–6/5–10x/1–2h are estimates. Every later admission still needs real science and financial gates, with no automatic retry or hidden use of unallocated funds. Original historical protocol and source snapshots are retained.

## October14 explicit owner budget increase (2026-10-14 21:53 UTC recorded)

The owner directly authorized increasing the budget to prevent a small overrun
from delaying the already authorized finite experiment. Codex stated and
allocated a bounded **$110 total: Stage0 $20, Stage1 $50, Stage2 $35,
unallocated $5**. This supersedes the historical $100/$10 figures above; it
does not change scientific groups, doses, gates or retry restrictions. Project
spending remains at most$450 with$50 protected. Exact authority and allocation
are in `reports/p009_20261014/p0_entry_repair_preflight_v1/OWNER_BUDGET_AMENDMENT.json`.
The pending entry repair retains every prior failed-call allowance: $7.52 plus
$2.52 for its new slot, $10.04 total, leaving$9.96 within Stage0. No proposed
closed-failure settlement release is needed for this admission. New exact code,
input, numeric and scientific reviews still govern progression.

## Direct owner post-result internal-only amendment — recorded 2026-10-14 16:15:12 PDT

After the complete P0 outcomes were disclosed, the owner explicitly designated
base as internal-only too: P009 will use vLLM throughout generation/evaluation,
make no cross-engine scientific comparison, and publish both discordance rates.
The exact authority and amendment are in
`reports/p009_20261014/p0_internal_only_amendment_v1/AMENDMENT.json` and its
OWNER_AUTHORITY.json. This is a post-result scope change. The original four-case
P0 rule above, `gates.py`, raw outputs and blocked base decision remain historical
evidence; no original threshold is silently altered or retrospectively passed.

Base650 versus historicalHF638 has126/1319 discordance(9.552691%); correct950
versusHF969 has77/1319(5.837756%). All future P009 comparisons and G0/G1 inputs
use the common reviewed vLLM engine/endpoint definitions. HF scores are only
historical engine diagnostics. Reuse the existing same-endpoint base650 after
actualA2; do not regenerate P0. Each future admission binds this amendment and
both actual A2/amendment reviews plus exact engine source/observed settings.
All other scientific/input/runtime/budget/once-only gates and training libraries
are unchanged. This amendment adds zero calls, outputs, training updates or cost.
Actual A2 and exact amendment review remain required before later science.
