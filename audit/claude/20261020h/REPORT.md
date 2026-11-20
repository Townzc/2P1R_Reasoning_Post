# P010 审计 20261020h：C6 cue 搜索 A2，以及 S1 补做四次采样评测 A2

- **审计方**：Claude
- **时间**：2026-10-20 06:54 UTC
- **审计对象**：`2a5955c0`

## 1. C6 搜索（`p010-C6-search-input-runtime-and-selection-A2`）——PASS-WITH-NOTES

**绑定文件**
- SPEC：`5014f3ce…`
- 开发集输入：`e4eb6ff5…`
- BASIS：`d74d01f2…`

| 字段 | 结论 | 依据 |
|---|---|---|
| gold_and_test_excluded | true | `DEV_PROMPTS.json` 每行只有 `problem_id` 和 `input_ids` |
| original_30_dev_order_preserved | true | 与 `MATH_ROSTERS.e2_dev` 的题目和顺序完全一致 |
| 开发集与训练集、E1d 是否重叠 | 不重叠 | 与 S1 n3200 交集为 0；与 E1d 已接收的 3,200 题交集为 0 |
| 提示词模板 | 与 MATH 端点一致 | 开发集提示词与 MATH 端点用同一个 0-shot 模板（首尾 token 相同）。只用作 cue 开头的前缀，不涉及评测 |
| exact_10080_original_outputs | true | 21 个候选（20 个开头 + 无 cue）× 30 题 × 16 次 rollout = 10,080。采样设置：seed 0–15，T = .6，p = .95，最多 1024 个新 token，上下文 2048 |
| hf_process_exit_before_vllm | true | 写在 SPEC.proposal 中 |
| full_probability_and_raw_preservation | true | — |
| no_automatic_retry | true | — |
| new_I_reserved_usd | 3.26 | I 子上限 15 |
| first_paid_measurement_exceptions | 0 | — |
| uncalibrated_timing_transfer_disclosed | true | — |
| 选择规则 | 与计划 §3.3 一致 | 先排除缺答案率比无 cue 高 10 pp 以上的候选，再在剩余候选中取平均答案熵最低者；平局时优先无 cue，再按 beam 排名。全程不用正确性 |

**需要写进报告的方法差异（notes）**
1. beam 按平均联合概率排序，并把深度 1 和深度 2 的候选合并起来取 20 个；论文的默认做法不同。这一点已在 `c6_selection_draft_v1` 中披露。
2. 续写上限是 1,024 个 token，论文是 16,384。
3. 我们用的是 S1 的 0-shot 提示词，没有用论文里的 boxed 或 RL-Zero 提示词。

## 2. S1 四次采样评测，只补做采样（`p010-C5-existing-S1-sample-only-A2`）——PASS

**绑定文件**
- SPEC：`fbb07d3d…`

| 字段 | 结论 | 依据 |
|---|---|---|
| 端点 | 与已跑通的端点相同 | `MATH_ENDPOINT.json` 与 C4、K1 端点逐字节相同（`8f9a0500…`） |
| original_4_sample_protocol_unchanged | true | `sampling(seed)` 与 C4 的 sample0–3 参数逐项相同：T = .6，p = .95，max 1024，EOS 151643，seed 0–3 |
| exact_new_outputs_per_model | 2000 | 4 × 500 |
| greedy_regeneration | false | 原有的 greedy 结果 273 和 276 直接复用 |
| new_training_updates | 0 | — |
| restore_exit_before_vllm | true | — |
| original_merged_bytes_required | true | — |
| original_parent_proofs_accepted | true | 两个 S1 父运行的 merge 和 state 证明都已绑定 |
| frozen_symbolic_scorer_unchanged | true | — |
| new_T_reserved_usd | 5.04 | 本项完成后 T 预留合计 69.03，上限 150 |
| first_paid_measurement_exceptions | 0 | — |

**意义**：补上这一项后，K1 与 K4/K8 之间就能比较采样平均 pass@1。见 20261020g，那一节此前缺少 K1 的采样基线。

## 进度提醒

截至 `2a5955c0`（23:52 PDT），五个 K1/E1d 训练格还没有发出调用：输入传输较慢，正在做 missing-only 补传。按 v3 §6，如果周二 05:00 PDT 时 Tier 1 仍未启动，就要按既定顺序削减项目。
