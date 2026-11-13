# Current P012 — 2026-11-13T23:08:48.245135+00:00

Owner approved amendment6 `18f64e2df34944da9b8fc6378609ccbdeed1c587` and result audit `d2db987a476b25055b912755021d2d44fd4e347c`. Modal sole gate: unsettled + next buffered batch <= actual balance -$4; cumulative85cap canceled; no topup. Llama remainingTier1/pass8 first, Tier2P/R/L(Qwen thenLlama), Tier2K8, thenInstructbridge. BasebridgeL retained; otherbasebridgecells canceled. Add first-boxed diagnostic wherevercap>20percent, registered scores unchanged. No new Modal exploratory cells.

A6-2M512 lengthcontrol andA6-3E4/E8/L64 authorized, exploratory excludedH0-H3. A6prediction18f64e2d must precede anyA6 scoring. Data construction explicitly exempt from pre-run review, requires3selfchecks. Toriginal340 + A6caps50/35 =425, protected325. PriorityA6-2 9B, A6-3 9B, A6-2 4B/Base, A6-3 4B; originalT continuesparallel. Current Llama admission: 15.7123+20.2416<=43.16. Status details andoriginal IDs in privateamendment6; neverresubmitcompletedcalls. Result audit accepts original91b650c5 only, lateraddendum pendingnextaudit. No newsubagents/chats/externalmessages.

Earlier entries below are historical.

# Current P012 — 2026-11-13T22:48:21.501956+00:00

T4 repair is complete and published. All three v2 endpoints passed4000unique seeds and the required diversity check before scoring: Base99.4%,4B90.0%,9B99.8%. Corrected pass@1/pass@8:65.125/93.0%,79.325/95.2%,89.725/95.4%. All v1 sampled metrics are superseded; original evidence remains immutable. Accepted reviewa56115d6, prediction8bbf06a7 unchanged.

Five main seed17 settings are complete: all four Qwen settings plus Llama base MATH. Llama P/K8/R/K4/L:6.40/6.72/3.80/6.16/4.46%; all raw outputs and termination diagnostics are published. Llama C7 NLL4 andfour-shot4 are complete. Base four-shot MATH0/500 andGSM4/1319 have99.8%/100% caps; flag the degenerate baseline when interpreting delta-SFT. No protocol changes or reruns. A5 allcomplete and remains exploratory, excluded H0-H3.

All Modal calls are COMPLETE; provider snapshot shows50 recent apps stopped and0tasks. NEW Modal calls STOP under the literal A4 hard gate. Owner decision is pending on `modal_next_gate_20261113_v1` (proposed accounting correction,85total/4protected unchanged). Latest balance47.16; after-batch accounting and both formulas are in POST_BATCH_RECONCILIATION.json. Do not execute unadmitted Llama/C7/Tier2 calls before that decision.

Tinker10original training calls remain active:4B P/R,9B-Base P/R, andK8/K4 for allthree models. Originals are in private LAUNCHES_4,7,12. Allthree L and9B P/R training+greedy+scoring arecomplete. Future greedy evaluations of these active training runs are already included in the190.6054reservation; no newseed29 started. Remaining bridge4 STOP afterLcap99.98%,4203loops. No bridge recipe change is authorized.

Result audit91b650c5 plus its new ADDENDUM is pending; it does not block otherwise authorized T execution. No externalmessages,newchats/subagents,R3/E2 or repeated completed model calls. Historical entries follow.

# Current P012 — 2026-11-13T22:24:26.051096+00:00

T4 repair accepted at a56115d6 is complete. All three v2 endpoints passed the unique-seed and diversity checks before scoring. Fractions with at least seven distinct outputs: 9B-Base 99.4%, 4B 90.0%, 9B 99.8%. Pass@1/pass@8: 65.125/93.0%, 79.325/95.2%, 89.725/95.4%. All three v1 metrics are superseded and excluded; original raw evidence remains immutable.

All four Qwen main settings (MATH/GSM8K × base/Instruct, seed17) and all A5 supplements are complete. Newly published packets include the Instruct GSM setting and all three Tinker L cells. Tinker P/R jobs continue, with 9B P/R training complete and their greedy requests ready. The prediction commit remains 8bbf06a7.

The Modal LoRA bridge L failed B-3: 4999/5000 length caps (99.98%), 4203 loops, one normal termination; accuracy 42.18%. Other four bridge cells stay unstarted and STOPPED pending an amended protocol. No automatic bridge recipe change. The original full-L call is complete; never replay it.

Next admitted batches: Llama base MATH five cells plus four C7 NLL measurements (Modal total accounting plus buffered batch 45.8244 <= observed52.04 - protected4); Tinker K8 then K4 for each model (combined reservation190.6054, below230 planning and340 hard). Requests use existing reviewed code and frozen data. Other Llama requests are prepared but unadmitted. Track each original CLI in private LAUNCHES_10 and subsequent files. No external messages, new chats/subagents, R3/E2, or repeated completed calls.

Historical entries follow; this entry supersedes earlier running or pending statements.

# Current P012 — 2026-11-13T21:50:18.909524+00:00

Owner acceptedT4review a56115d6. Samplingfix approved; neutralT1guardcomment applied. Everyv2mustverify4000uniqueseeds and>=80percentquestions with>=7distinctoutputs BEFOREscoring; failurestop/report. Allthreev1pass1/pass8 removedfromaggregates, originalraw/scoresretained. 9BBaseformaltrainingRELEASED, no needwaitv2. T-samplingforecasts measuredtokensx1.5; current9LPR+greedy+3repairs+completedpre/smokereservation137.2572, below230planning/340hard, protected400ofinitial750. Predictions8bbf06a7unchanged.

A5-1/2/3 ALLCOMPLETE, published8203d5c1/a2354fff includingallrawZIPs. Base P/E4/E8/R MATH42.06/37.36/37.06/33.14; Instruct42.94/37.64/36.02/32.72. A5exploratoryexcludedH0-H3. BaseGSMall5traincomplete; originalfivegreedyactive, IDsLAUNCHES_8. AftercompleteupdateforecastandrunInstructGSM. Modaladmissiona5c9d79448.3281<=58.55-4 withbridgeinflight/conditionalreserved. BridgefullLoriginalstillactive; missingexecsessionID, usefiles; neverresubmit. B3fullcap>25stopsother4.

T9BLtrain+5000greedycomplete; CPUscore3915active with8bbpredictionrecord. T4BLtraincomplete, greedy56306active. T9BBasev2pass8original36818active; whenPASSfirstcheckthenCPUscoreandlaunch4Bv2then9Bv2. BaseL/P/Rtraining66205/86857/84728 active. OtheroriginalTtrain4BP42541/4BR99799/9BP68326/9BR94083 active. All launches persistedLAUNCHES_4..8; T9BLgreedy57604COMPLETE/EXIT0consumed. Currentreviewhasno pendingownerapproval. No newchats/subagents/externalmessages, no R3/E2, no reruns ofcompletedcalls.

# Current P012 — 2026-11-13T21:29:16.787699+00:00

Owner approved T4 64-response diagnostic. Complete: original n8 unique counts1/3/1/4/3/1/1/2 vs independentseed n1 all8. Costupper .053869506, noanswersscored. Allthree original Tpass8 independent-draw metrics invalid, rawretained. Fixed perdraw n1/unique seeds code0519677e; two meaningful regressiontests PASS. ActualClaude review requested for packet9d1079c8; do notrunv2 untilreview. 9BBaseformalheld. Independent4B/9BLPR originaltrainingactive, IDs inprivateLAUNCHES_4; greedyunchangedandmaycontinue.

A5-1andA5-2complete/public0519677e; A5-3E4/E8fouroriginaldetachedtrainjobsactive (82127/65661/48128/17730), thenevalandQwenGSM. BaseL64/L128/L256caps81.94/90.82/99.38percent; explorationexcludedH0-H3. BridgeL originalfull5000greedyactive; B3params/adapterloadPASS, fullcap>25percent stopsother4. Nootherbridgecalls. CurrentconservativeModalreservation47.7898 <=63.02-4; updatedadmissionpublished944d1a75. Tpriority LPR sixruns+worstgreedy184.0022 totalreserve, plusdiagnosticbuffer. Alloriginalsimmutable.

# Current P012 results — 2026-11-13

Both Qwen × MATH settings are complete (seed 17, full MATH test 5,000, greedy 4,096/8,192). Base L reuses the accepted probe. All Qwen C7 mandatory endpoints and all three authorized Tinker smokes are complete.

| Initialization | P | K8 | R | K4 | L |
|---|---:|---:|---:|---:|---:|
| base | 42.06% | 40.12% | 33.14% | 41.34% | 42.88% |
| Instruct | 42.94% | 41.00% | 32.72% | 41.88% | 42.88% |

- [Base evidence and termination diagnostics](tier1_qwen_base_math_s17_v1/README.md)
- [Instruct evidence and termination diagnostics](tier1_qwen_instruct_math_s17_v1/README.md)
- [Complete Qwen C7 results](c7_qwen_complete_v1/README.md)
- [Current balance, accounting and measured forecast](amendment4_completed_budget_v1/README.md)
- [Tinker / LoRA bridge review packet](tinker_lora_bridge_review_v1/README.md): formal execution awaits the single combined review required by Amendment 4.

R is 9.74pp below L for base and 10.16pp below L for Instruct, while R has fewer truncated outputs. P differs from L by -0.82pp and +0.06pp respectively. These are first-seed observations; the registered two-seed decision remains pending.

Amendments 3 and 4 are approved at `claude/audit` 77a2520e. Phase budgets are soft. The sole hard budget condition is accounted cost plus the buffered next batch exceeding actual Modal credit balance minus $4. The current completed batch passed admission; the previous phase-cost stops below are superseded.

---

Historical milestones follow.

# Latest results — 2026-11-12

R1 and R2 both pass the registered reproduction gates. Remaining Tier 1 and C7 are stopped at their separate owner-defined cost gates. All submitted model jobs are complete; final R1/R2 weights have independent, SHA256-verified copies.

| Reproduction | MATH-500 exact OR math-verify | GSM8K | Paper targets | Gate |
|---|---:|---:|---|---|
| R1 Qwen2.5-1.5B-Instruct | 51.20% | 72.63% | 52.3 / 71.7 | PASS |
| R2 Llama-3.2-1B-Instruct | 33.40% | 51.48% | 33.4 / 49.2 | PASS |

| Cost gate | Cap | Direct extrapolation | With time/tail allowances | Status |
|---|---:|---:|---:|---|
| Tier 1 training + evaluation | $30 | $49.56 | $63.99 | Remaining grid stopped |
| C7 required classes 1–3 | $4 | $5.69 | $7.54 | Remaining endpoints stopped |

The completed main-grid L cell gives 42.88% greedy accuracy on full MATH test (MATH-500 subset 41.80%). The completed C7 Qwen base × MATH group gives four-shot test accuracy 26.60%, held-out pass@1 19.05% / pass@8 56.40%, and teacher NLL 0.212939 nats/character. These endpoints use their registered conditions; raw output and label files are included below.

- [R1 complete evidence](r1_b16_results_v1/README.md)
- [R2 complete evidence and backup](r2_b16_results_v1/README.md)
- [L probe and Tier 1 cost forecast](l_cost_probe_v1/README.md)
- [C7 first group and complete endpoint forecast](c7_first_group_results_v1/README.md)
- [Latest budget reconciliation](budget_22utc_v1/RECONCILIATION.json): $12.21 accounted including reserves, within the $85 total; phase caps remain binding.
- [Current execution state](EXECUTION_STATUS.json) and [completed generation inventory](RUN_INVENTORY_CURRENT.json).

Next decisions concern resources, phase budgets or execution scope. R3 remains held. No remaining grid or C7 calls have been launched after their cost stops.

---

Earlier checkpoint notes follow; the status above supersedes their pending-work statements.

# P012 执行状态 — 2026-11-12

Modal 总上限 $85，保护余额 $4；负责人已批准 G0-E $8、应急 $8。8 组 Li 协议下的 Instruct／公开检查点评测已保存原始输出和初次评分，当前没有运行中的模型任务。

- [最新结果、待审事项和预算](g0_completion_handoff_final_v1/README.md)
- [合并审查补充包，代码 fae6656d](pre_c8_review_addendum_v1/README.md)，连同 [F4/F5 与启动器原包](pre_c8_review_v1/README.md)
- [机器可读执行状态](EXECUTION_STATUS.json)
- [已接受审查与修订 2](review_020017ae/README.md)
- [预算授权](budget_adjustment_20261112/AUTHORIZATION.json)
- [C1 资产与版本清单](c1/C1_MANIFEST.json)

四组 MATH 有 742 条待统一判分。UWNSL short 和 long 的 GSM8K 均通过论文对照的数值门槛。标准 few-shot base 与集中判分的新路径等待一次共享代码审查；独立 10% 结果抽查也尚未完成。G0-E 尚未结束，G0-T 和 C8 尚未启动。

Built with Llama.
