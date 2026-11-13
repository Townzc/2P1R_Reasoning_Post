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
