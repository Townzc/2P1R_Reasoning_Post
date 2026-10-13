# P008 v3.1 — common acquisition cap, joint scaling and conditional B×T bridge

**Owner authorized execution on October13, after Claude closure9547f2ea.** This document consolidates v3, Codex F1–F5, Claude N1/N2 and A1–A3. It supersedes the unexecuted v2/11-student alternatives. G0 acceptance of the exact Phase0 source/config is required before cloud dispatch. G0 is not a claim that later, unbuilt main-run software passed review.

## 1. Questions and fixed comparisons

Within a fixed acquisition cap B, training contract T and problem price p, compare breadth (retire a problem after1usable answer) against depth (retire after4usable answers). Both stop at8attempts/problem. The main path increases B and T together; it is **joint scaling**, not a data-only effect. Two independent procurement draws D1/D2 each share their own question order and candidate streams across prices, policies and budgets. The P007B results remain external context, not a third draw or a compatible1× control.

Main design:2draws×B∈{1,8}×p∈{0,4m}×2policies=16students. D1/p0 adds both policies at(B8,T1) and(B1,T8), four bridge students. Total20students/90training units, plus one base evaluation. Student seed17 is common. Same seed fixes initialization/random stream, but schedules depend on the acquired corpus: differences between D1/D2 reflect procurement **and its induced training trajectory**, not pure procurement variance. Two draws do not support a reliable procurement-population confidence interval.

The bridge reports conditional changes and interactions, not a unique decomposition of improvement into data and training contributions. Its scope is D1/p0 only.

## 2. Data, teacher and no future-output leakage

GSM8K official train7473 is hashed and partitioned before P008 generation. Sort IDs by `stable_seed('dev_split',0,id)`; reserve the first500 for development/engineering and exclude them from both main pools. Of those, first256×attempts1–4 are Phase0teacher inputs; next8 are gold-answer smoke training fixtures; next16 are smoke evaluation. This is a newly reserved P008 split, **not a claim of no historical exposure**. Main6973parent IDs/order hashes and all Phase0 input hashes are published in INPUT_IDENTITY.json. Historical teacher/student overlap is reported before G1; it does not silently change this split. The official1319test has been seen by the researchers, so no pristine-test claim.

Teacher: Qwen/Qwen2.5-Math-1.5B-Instruct revision`aafeb0fc6f22cbf0eaeed126eff8be45b0360a35`; same system/prompt and primary answer checker as P007A. vLLM0.11.0,torch2.8.0,transformers4.56.2,tokenizers0.22.1,BF16,one H100,TP1,eager,context2048,maxcompletion1024,temperature.8,top_p.95,top_k unrestricted,repeat_penalty1,n1,native EOS151645/151643. No truncation or prompt wrapping change. Teacher image uses NumPy2.2.6 for vLLM's numba compatibility; student keeps the original NumPy2.3.2 stack. Full installed versions and CUDA/driver are captured; this is a new teacher-backend protocol, not HF/vLLM equivalence.

Draw/order/attempt seeds use domain-tagged, unambiguous JSON→SHA256→nonnegative63-bit values. The finite complete potential roster is collision-checked. Each main draw uses its own order and teacher seeds. Each cache key is(draw,problem,attempt). Physical generation uses only the union requested by the frozen virtual policies. No wholesale6973×8generation. Hard bound per draw:16,384physical completions; the theoretical6973×8parent-attempt space does not override this smaller cap. Each draw stops at the earliest finite attempt/time/token/provider bound fixed after Phase0. Attempt cap includes failed, duplicate and uncertain requests; no hidden refill/retry. An incomplete pool is reported as censored; no students are dispatched on an unreviewed/incomplete required policy state.

Within a policy, decide the next16-slot action from only its own legally consumed past, known prompt lengths and fixed worst-case1024completion reserve. A cached candidate's correctness, actual length or later attempts are unavailable until that policy commits the current action. Consume attempts in order. Duplicate checking is within problem, normalized NFC/whitespace; only previously accepted usable text blocks a new valid answer. Final-answer validity is not proof of reasoning validity or strategy diversity.

## 3. Acquisition accounting

Fixed hypothetical tariff: one unit per prompt and returned completion token including native EOS; m=191151/512=373.341796875; problem price0 or4m=1493.3671875; B0=211257. These are predetermined hypothetical units, **not vLLM/API dollars**. B8=1690056. Every virtual policy pays its own problem fee and every consumed attempt, including failed/duplicate candidates, even when another policy populated the shared cache. Prompt/output token IDs and payment receipts make this replayable.

A full16-action batch reserves all new-parent fees + exact known prompts +16×1024before seeing outputs. If it cannot afford this worst case, it stops; no hindsight tail packing, smaller result-dependent batch or free cached suffix. Report actual charge and unusedcap, not equal actual spend or dollar optimality. Platform invoices/metering count all physical work/setup/storage/failures/unused outputs separately. Shared-cache execution savings are not strategy-acquisition savings.

## 4. Student contract and A1

Qwen2.5-1.5B base, existing locked revision/assets; same FP32 LoRA weights/r16/alpha32/dropout0/targets, BF16forward, AdamW, complete answers, prompt/padding mask, total-target loss normalization, no packing/truncation as P007B. Each lowT run U0=256updates,T0=524287supervised response tokens including EOS; highT U=2048,T=4194296. SameT has identical published LR vector. Base has no updates.

New P008-only LR: w=U/16 integer warmup; `1e-4*(i+1)/w` for i<w; then `1e-5+(1e-4-1e-5)*0.5*(1+cos(pi*(i-w+1)/(U-w)))`. CPU tests verify byte-identical original256vector, monotone decay after warmup, final1e-5 for U256/1024/2048. Old P007 code/vector/results are untouched. Smoke uses only the first8 entries of the frozen2048vector; it is not a new8-step scientific schedule.

Keep all usable complete answers in the acquired inventory. Training exposure is q/q+1 balanced across that inventory, **including q=0** when the high-B/low-T bridge cannot afford one pass. A seeded exact subset-sum chooses the residual using only lengths and seed, never scores. Report both acquired and exposed N/P and the zero-exposure count; this is not uniform answer sampling and not a guarantee that every purchased answer trains. P008 uses a new isolated schedule module; the old all-answers-once P007 planner is unchanged. This bridge feasibility clarification is explicitly included in G0 review. Build every required corpus's schedules before its draw's student scores. At each T level search target value downward from the nominal target by at most0.1%, in descending integers, and select the first jointly feasible value across **both draws/all retained cells at that T**. Publish the feasibility record and revised common T after both pool local oracles and before any main student dispatch. Nominal requested units are reported alongside exact realized targets; if this small common tolerance fails, hold instead of single-cell dropping/truncation. This CPU feasibility dependency requires both acquired corpora to exist, but G1 can still audit D2 while verified D1 runs. Changes after a main outcome are not allowed.

Endpoint once per checkpoint: all1319officialtest, HFgreedy,maxnew512/context2048/batch16, same frozen boundary/EOS/checker semantics as P007B. No interim test evaluation or best-checkpoint selection.20student endpoints=26380 plusbase1319=27699. Save full rawtoken/prompt/stop events, complete optimizer/RNG/cursor/dose terminalstate and provenance. Truncations remain incorrect under primary checker, never removed from denominator. HF/vLLM student evaluation replacement and avg@8 are outside this stage.

## 5. Phase0 exact finite calls

See PHASE0_ADMISSION.json (exact plan/config hashes) and modal_phase0.py. Four roles share one finite detached application; no cloud CPU controller, no permanent service. Each role is claimed once before work. Four GPUs must overlap through a bounded readiness/sharedVolume barrier, each writing/reading the four unique8MiB probes with SHA validation. Submit records alone do not establish concurrency. Max4GPU total; min0/single-use; actual stopped apps/zero containers verified at closeout.

| Role | Maximum scientific/engineering work | Worker hard limit | Reservation |
|---|---|---:|---:|
| teacher_calibration | exactly up to1024requests,256reservedparents×4;32batches of32;0updates |2400s|$6|
| student_smoke |8updates on8fixedgold fixtures,921supervisedtokens;16reserveddev outputs once |1500s|$4|
| io_probe_a | one8MiBprobe/four reads,0model calls |600s|$1.50|
| io_probe_b | same,0model calls |600s|$1.50|
| unallocated overhead | build/storage/setup/transport headroom, no extra call slot | — |$2|

Total≤$15 inside the$250stage cap. Allroles4CPU/32GiB/H100; platformstartup600s, function caps2500teacher/1600HFrole, but worker's earlier role timer wins. Using current Modal rate H100.001097/s+4CPU.0000524/s+32GiB.00007104/s=4.393584/h (previous4.3952is a slightly conservative rounded estimate), even startup+function upper bounds fit these reservations. Barrier180s occurs before model loading and is inside worker limit. Missing readiness/ack leads to failure, not new calls. All failures/unknowns retained. No automaticclaimreset, replay or backend change.

Phase0 outputs estimate throughput/length/stops/score accounting, sharedI/O and release. They do not select a winner, claim distribution equivalence, estimate model accuracy on officialtest, or replace old measured full training/evaluation durations. vLLM initialization/build time is separately recorded and included in cost planning. New model work cannot precede exact G0 acceptance + independently verified input upload.

## 6. Engineering-only scope selection and budget

Use P007B's measured8worker records (56.50summedGPUminutes in updates;9.778totalGPUhours, remainder includes evaluation, loading and I/O) plus new Phase0teacher timing. Forecast CPUaudit, onebase, setup/exports and explicit20%timing/cost margin. Publish all branch forecasts and start-time assumptions. Four-way wall time is scheduled from per-run upper estimates, not GPUhours/4 without dependency/straggler accounting. Hard per-run/time limits are an additional reserve check, not an average-cost forecast. Main exact call/config/source/slot caps are published after Phase0, within$250, before their dispatch.

One-time branch choice before any main student outcome; choose first branch whose conservative complete-stage cost≤$200 and completion≤18:00PDT:
1.20students/90units, Bhigh8, complete bridge, D1/D2.
2.18/74:remove(B1,T8)bothpolicies; bridge incomplete, no fullJ.
3.18/42:uniformhigh8→4, same incomplete bridge.
4.10/22:also removeD2; no procurement replication and no fullJ.
If none fits, hold/close engineering with evidence; never select by accuracy. Do not silently drop one policy/price or revise after seeing a main score. $50stage headroom remains **inside$250**, distinct from the protected$50project balance. Total project≤$450; latest delayed workspace meter$87.20111458, not an invoice. Old$369.50reservation is not spending. Upper-bound new spending plus old confirmed/unsettled costs must fit both envelopes. No reliance on future credits.

## 7. Gates, pipeline and deadlines

- **G0:** Claude fixedcommit code/protocol/input/calllist review. Source/plan hashes must match at dispatch. No response after45minutes means hold; it never meansPASS.
- **Phase0closeout/scopefreeze:** local full rawtoken recomputation, dosage/source/concurrency/provider verification; publish engineering measurements and frozen branch before main outcomes.
- **G1-D1:** independent fullraw pool scoring and each virtualpolicy payment/no-lookahead replay; code/source/pool and all student plans bound. Once passed, D1eight main cells may run. D2pool can be audited during those runs. The common feasibility check above uses data only, never student results.
- **G1-D2:** same checks for independentD2; only then its eightmain cells. Scheduling priority D1main+base → D2main → bridge; within each set fixed pairedpolicy order, up to4GPU, no cancellation of healthy workers to chase a result.
- **G2:** engineering/supply/cost/time reconciliation only, no formaltest effect threshold. No extra hidden grant/seed or automatically admitted repair. Any interrupted batch remains unknown until reconciled; never repeated merely because a local connection failed.
- **G3:** independent finalraw/hash/contrast/figure recomputation for actual covered roster; incomplete cells markedpending, not filled with0. Final result notification follows full verification before long analysis.

Hard compute stop **2026-10-14 02UTC / TueOct13 19PDT**. Technical material freeze **Tue21PDT**. Existing P007B evidence is already ready and remains a valid midpoint deliverable if P008 is incomplete. Phase0target02:00, branch03:30, D1around05:00 are forecasts, not fabricated event times. Wednesday newly reviewed exploratory additions require explicitowner choice and a separate bounded plan; do not revise the frozen core. User authors final slides/personal explanation; no AI-generatedslides or uploads.

## 8. A2 mandatory reporting, all signs retained

For each draw:Δ_p(B)=accuracy(depth)−accuracy(breadth) (8total); C_p=Δ_p(high)−Δ_p(1) (4); I(B)=Δ_4m(B)−Δ_0(B) (4); I(high)−I(1) (2). Directional motivation C0<0 is a hypothesis, not a promise. No directional p4 prior. D1p0report eachpolicy's2×2 conditionaleffects and interaction, plus J=Δ(high,high)−Δ(high,1)−Δ(1,high)+Δ(1,1) only if fullbridgecompleted. Report all cells/base,raw counts/denominators,parse failures/caps,usableN/coveredP/purchasedP,failed/duplicateattempts,answerexposures,unusedcap,pool exhaustion,D1/D2highBproblem overlap,actualtokencharges and actualplatformcost separately.

Eachdraw contrasts first, then mean/range. Shared paired-question10kbootstrapseed20261013 is conditional on these trained models and pools, not a trainingseed/procurement-population CI. No significant difference does not mean equivalence; an interaction alone does not establish a winner. No universal4pp detection threshold. All registered contrasts remain visible without significance-based selection; any additional analysis labeledposthoc.

Secondary unifiedparser-v2 sensitivity fixes E1percent/units and E2emptyanswerstatement fallback under a separately frozen CPU rule/tests before P008student outcomes; apply to everyoutput/allcells, list changedcases, retain originalprimarytable. It must not alter procurement acceptance, traineddata, main stopping or primaryscores. If its implementation is not reviewed in time, markthissecondaryitempending instead of selectively correcting examples.

## 9. Evidence and collaboration

Raw/proof/config/source hashes and immutableattempt/done records precede claims of execution/completion. Failed and unknown work is not erased. Local oracles are not ClaudePASS. INDEX review_requests bind targetcommit/manifest/questions/blocking_for; WORKBOARD distinguishes event time/readtime/role. Claude reviews are scoped to that version. NormalGitHubpush only; #13/externalmessages remain drafts forowner. New reading is checked beforephasechanges; latestPapers ea8befd5notes39–42 read, no fabricatedPro contribution.
