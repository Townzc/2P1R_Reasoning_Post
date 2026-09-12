# Draft acquisition measurement protocol

Version LT001, 2026-09-11. **Reviewable protocol, not a launcher or an approved compute stage.** The first implementation must have its own immutable source/config/input release and finite shared-budget proposal. No collection was performed for this document.

## 1. Population and source contract

Use the existing group-level GSM8K split and exposure history. Do not open final tests or reserved development contents to implement this protocol. [Validation roles](VALIDATION_PLAN.md) specify future releases.

Proposed acquisition calibration: 128 parents selected from the **entire original 1,024-parent C017 audit draw**, by SHA256 ordering of `lt001-acquisition-calibration-v1|group_id`, before inspecting new teacher outcomes. Include parents with no cached response or known reference flags. These are observed pilot-pool parents, not independent confirmation. IDs may be materialized only in the later CPU input release; this document does not select by cached K.

The candidate local generator is Qwen2.5-Math-1.5B-Instruct, **unvalidated and unselected**. Before sampling, pin its full model/tokenizer revision, chat template, precision, inference implementation and acceptance/serialization code. Do not replace it with a larger teacher, an API or the student's tuned checkpoint. The calibration concerns this generator only; it cannot price OpenMathInstruct-2 responses.

Draft generation settings for review: independent response samples, batch one, temperature 0.7, top-p 0.95, top-k disabled, at most 768 generated tokens and context 2,048. Fix a prompt requesting step-by-step solving and a final `#### <number>` line; supply only the problem, never its reference answer or earlier responses. Freeze the exact bytes with the generator's actual template. Over-context inputs become recorded onboarding failures, not replacements. Per-attempt RNG seed is derived from the immutable namespace, pool ID, parent ID and attempt index; different policies requesting the same event receive the same recorded response.

Sampling at batch one simplifies attribution and replay. Changing batching requires a separate throughput calibration and cost model for all compared policies. Existing student E017 batch-eight timings do not price this generator.

## 2. Finite calibration and acceptance

Request eight attempts per onboarded calibration parent **even if earlier attempts succeeded**, so later-attempt yield is not measured only among initially unsuccessful parents. Maximum 1,024 generation calls and 786,432 generated tokens before early stops; this is a count ceiling, not a seconds/money authorization. A profile-derived process and whole-rental cap must be added before launch. Preserve an interrupted collection as incomplete; do not quietly fill it later.

Apply one ordered automated pipeline to every dispatched response:

1. Record dispatch and durable completion/error, raw output IDs/text, observed stop reason and input/output token counts. Provider/runtime failure and missing receipt are different from a wrong answer.
2. Require the frozen completion/serialization contract and parseable final marker. Preserve truncation, format failure and abstention separately.
3. Compare the final answer against the source reference using the reviewed exact numeric checker. A reference ambiguity or unresolved equivalence is a separate status. Do not silently repair a reference.
4. Deduplicate within parent by a fixed normalized response hash: Unicode NFC, canonical newlines and stripped outer whitespace, with all internal reasoning retained. This defines exact normalized-text duplication, not semantic equivalence. Charge the work even for duplicates.
5. Record student-tokenized whole-response length, masks and EOS. A response that cannot fit the frozen student serialization is unusable for SFT and remains in acquisition accounting. Do not truncate it or replace its parent.

Keep raw verification flags and one mutually exclusive first-failure category. An accepted final answer does not certify every reasoning step. Near-duplicate and semantic-strategy annotations are diagnostics with separately logged cost; they do not change primary acceptance post hoc.

Per-parent outputs include M_i, K_i, first accepted attempt, first occurrence of each retained response, verification/duplicate counts and time to each attainable K. A parent with K_i=0 is present in the final summary. Time to K> K_i is right-censored at the cap; never extrapolate eventual success as if observed. Missing events after a phase timeout are unknown rather than unsuccessful draws.

## 3. Minimum auditable records

Store immutable append-only JSONL records plus manifests. Separate the event log from the single canonical resource ledger: event logs describe research measurements, do not create allowances or reserve compute.

| Record | Required fields |
| --- | --- |
| Run manifest | protocol/source commit and hashes; pool/group manifest hash; model/tokenizer/template/checker revisions; decoding; maximum attempts/tokens/process/rental; stop criteria; calibration/validation role; source-matched training release reference |
| Onboarding | parent/group IDs; fixed rank; known pre-outcome strata; source/reference hash; eligibility and first exclusion; wall/CPU duration; optional actually timed human review; information exposed to policy |
| Attempt | event ID; parent ID; ordinal; RNG seed; dispatch/completion timestamps; status; raw-token/text hashes; raw artifact reference; input/emitted/padding token counts; stop reason; generation wall time and timing method |
| Verification | checker version; parsed answer status; reference agreement/abstention; correctness and completion flags; duplicate-of ID; student length; accepted flag; first-failure reason; verifier/dedup/tokenizer time |
| Policy decision | policy/version; pre-action state hash; visible event IDs; next action; remaining ceilings; maximum reservation; realized charge; slack; stop reason |
| Training link | accepted event IDs; exact presentation schedule; per-response exposure counts; T/U/processed/padding totals; shared recipe hash; run IDs for completed endpoints, including failures |

Record private provider details only in existing private coordination material. Public records contain sanitized IDs, hashes and timing provenance; no credentials, local absolute paths, endpoints, task IDs or correspondence. Raw third-party text follows the repository's existing cache/license practice.

## 4. Three policies with equal available information

At the held-out nominal scale, use the same ordered pool of 768 eligible parent slots and the same admissible action space (onboard a new parent, request the next response, or stop), maximum eight attempts per parent and maximum four accepted responses. Policy-specific P/K targets below are choices within that common action space, not access to a different pool.

| Policy | Deterministic queue | Nominal allocation if all targets succeed |
| --- | --- | --- |
| Problem-first (PF) | Visit the first 768 parents in order; for each, request until the first accepted nonduplicate response or eight attempts, then advance | (768,1) |
| Solution-first (SF) | Visit the first 192 parents; request until four accepted nonduplicate responses or eight attempts, then advance | (192,4) |
| Fixed mix (FM) | Visit the first 384 parents; request until two accepted nonduplicate responses or eight attempts, then advance | (384,2) |

All stop earlier when a common acquisition ceiling prevents admitting the next action. Keep incomplete parents and unused budget. Never backfill a failed parent, substitute one with known high K, choose the shortest successful response after seeing all attempts, or continue beyond a target just to exhaust money. Within a parent, use the **first** qualifying responses in event order. Targets describe tested simple policies, not every possible PF/SF strategy; a round-robin or adaptive version would be a new policy.

The policy sees the shared pool's opaque IDs/order and already acquired problem content plus past acceptance/duplicate/abstention statuses. A verifier can access a purchased reference; the generator cannot. Future outputs, hidden capacities, solution lengths and student validation scores are inaccessible to the acquisition decision. If problem descriptors are provided up front, give them to every policy and charge that common screening work. No policy receives free semantic labels.

Conceptual execution:

```text
for parent in policy_prefix(common_order):
    admit onboarding only if all ceilings permit its maximum charge
    record onboarding, including failure; never replace the parent
    if onboarding failed: continue
    while accepted_count < policy_K and attempts < 8:
        reserve worst-case next-event cost under all hard ceilings
        if reservation does not fit: stop policy; retain slack and partial data
        reveal or collect only the next (parent, ordinal) event
        charge generation + frozen verification + deduplication, even on failure
        update visible state; retain first qualifying nonduplicates
return all selected/acquired parents, all queried events, accepted training rows
```

No past outcome determines which RNG stream exists next. A missing event invalidates a replay beyond that point; it is not evidence of zero success. If a maximum-time reservation repeatedly leaves unusable slack, report that admission effect; do not swap to an expected-cost guard mid-comparison.

## 5. Cost semantics and calibration

Use a **metered serial service-time** axis for the primary measured comparison: observed generation wall seconds plus measured onboarding/verification/deduplication time in the frozen serial pipeline. Preserve every component and its hardware provenance. This is an operational resource unit, **not an invoice**. For batched/parallel execution, overlapping durations cannot be summed this way; re-profile and revise prospectively.

Let C_cal be total metered calibration service time including failed/duplicate events and K_cal its total accepted nonduplicate responses. If K_cal>0 and collection is complete, freeze `c_bar = C_cal / K_cal`, `B0 = 1024*c_bar` and held-out `B1 = 0.75*B0`. This outcome-independent formula sets a nominal 768-response acquisition scale from calibration, before any validation training accuracy. It is not a hypothesis that every policy can attain 768 responses. Hard attempt, token, process and rental caps override service-time admission and require conservative per-action reservations.

For the constant-yield baseline, separate onboarding to avoid double counting: `c_p = C_onboard / 128` and `c_s = (C_cal - C_onboard) / K_cal`; predict `C_const(P,N) = P*c_p + N*c_s`, with N the nominal usable-pair target. The c_bar above sets the common budget scale and must not also be added to c_p. Compare constant-cost feasibility predictions with actual K_i and parent coverage, retaining uncertainty from calibration parents. Report first/second/third/fourth-response incremental yields as well as attempt-index yields; they condition on different risk sets. At eight attempts, cumulative coverage is directly estimable, but unlimited-retry cost is not.

For economic views, report marginal data-service attribution, one-off model/setup/curation overhead and whole-project cash separately. Count generation, CPU work and failed transfers in the actual shared expenditure. State any CNY8/hour conversion as a rate-based estimate unless backed by a provider invoice. Human labor is reported in observed minutes; an hourly wage and positive problem-authoring price are explicit scenarios. Public-problem access has no invented authoring bill.

Every method receives the same calibration information. For a learned selector, count its extra fitting/training overhead and give comparators equal access or report a separate amortized analysis with a stated deployment count. No free oracle fitting.

## 6. Replay, quality audit and release criteria

Economical future collection may generate the union of events requested by the three policies once. A replay reveals only its queried prefix, despite the research process storing a larger union. Charge each replay its event-based counterfactual costs; record actual union cost once in the canonical history. Label replay costs as estimates, not three independently paid executions. Actual policy latency requires a later online check because cache state and execution order can change time.

For a blinded quality audit, prespecify up to 48 accepted responses (balanced across first versus later accepted positions) and 16 rejects/abstentions, with parent clustering and sampling probabilities recorded. Reviewers see problem/reference/response, not policy or student outcome. Distinguish final-answer correctness, step validity, ambiguous reference and genuinely different strategy. If only AI review is available, call it AI-assisted screening. Human adjudication and agreement remain pending; never fabricate them. Use weighted estimates for a deliberately stratified audit. Material error triggers a versioned correction and new independent confirmation, not selective rescoring of a preferred arm.

Before implementation is declared ready, verify with synthetic event fixtures: zero-success parents, exact duplicates, abstention, missing records, budget-boundary stopping, refusal to peek at future events, identical event reuse across policies and refusal to overwrite outputs. Check count/token/time reconciliation against raw events independently. These are future protocol checks, not claimed passed tests.

Before any server startup, supply one finite stage with measured profile, per-job caps, total powered-on/export/shutdown allowance, additive authorization reference and recovery plan. The sprint owns the existing GPU window and canonical ledger. This proposal grants no E018, acquisition, SFT-grid, paid-API or additional-machine authorization.
