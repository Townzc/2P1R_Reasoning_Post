# P010 审计 20261020l：seed29 A1/A2、E9 运行时 A2、C6 选择 A3

- **审计方**：Claude
- **时间**：2026-10-20 09:21 UTC
- **审计对象**：`a447320f`

## 1. seed29 输入 A1（`p010-Tier3-seed29-exact-input-and-plan-A1`）：PASS

- **绑定文件**：BASIS `e42035ec7f763e61…`；`actual_inputs.tar.gz` `2a32a9fc942624e5…`
- **输入与 seed17 逐字节一致**：四格的 encoded（`path_id`、`input_ids`、`labels`）都与对应的 seed17 输入逐字节相同。
  - T72 两格对照 20261020f 中审过的 `selected_inputs`，`rows` 的 response 也一致。
  - T1.5 两格对照 P009 `s1_s17_n400/n3200_encoded.json`。
- **题目集合取自 seed17，不是 P009 的 s29 名单**：这些格**没有**使用 P009 自带的 `ROSTER_s29` / `s1_s29_*`（那套名单的题目顺序不同）。这符合计划 v3 §3.7"题目不变，只换训练种子"。
- **只换了训练调度**：
  - 四格 plan 的 seed 都是 29，调度都与 seed17 不同。
  - 目标 token 总数为 2,097,148，更新步数 1024，每条样本的出现次数与暴露数一致，LR 为 `14ac59d2`。
  - 每条样本的暴露数：T72 n400 为 10–11，n3200 为 1–2；T1.5 n400 为 11–12，n3200 为 1–2。
- **评测端点**：`MATH_ENDPOINT.json` 与已跑通的端点逐字节相同。

## 2. seed29 运行时 A2（`p010-Tier3-seed29-complete-runtime-A2`）：PASS

- **绑定文件**：SPEC `b0232000…`
- **代码差异**：与已审的 K1/E1d 运行时相比，改动的源文件只有准入、分派相关的四个：`modal_students_seed29.py`、`tier3_dispatch.py`、`student_dispatch_v2.py`，以及被替换掉的 `modal_students_k1_e1d.py`。
  - 两个 worker 文件之间，函数层面只有 `main`（以及 `main` 内部的嵌套函数）不同；训练和评测的 worker 函数 AST 没有变化。
- **准入条件**：新增了以下要求——A4 报告与实际 A3 结果的绑定、seed29 数据绑定、只允许这四格运行。
- **预算**：每格 4,500 秒，预留 $6.55。

## 3. E9 完整运行时 A2（`p010-E9-complete-runtime-A2`）：PASS

- **绑定文件**：SPEC `1e937c58…`

| 检查项 | 结果 |
|---|---|
| `actual_model_prompt_tokenization_required` | true。`verify_prompt_texts` 在模型侧用 OLMo 分词器把 500 条提示文本重新编码，逐条与端点 token 比对，并核对 `source_row_sha256`。这补上了我在 20261020k 中指出的局限 |
| 提示文本 | 我独立核对：`PROMPT_TEXTS.json` 500/500 条都等于 `"Problem: " + problem + "\nSolution:\n"`，problem 取自冻结的 `math500.jsonl` |
| `original_training_AST_unchanged` | true。`e9_training.train_and_merge` 与已审过的 E4 适配器（`training.py`）AST 相同 |
| 评测循环 | 端点是列表，切片是正确的（这正是 E4 当时出 bug 的地方）。只做 greedy，T = 0，最多 1024 个新 token，在 EOS 100257 停止，每批先存原始输出，再核对 `candidate_id` 和 prompt token |
| `baseline_zero_training` | true。基线分支直接加载 base 模型 |
| `three_original_E9_calls_only` | true：n400、n3200、基线，共三次调用 |
| 预算 | T 两格各预留 $6.55，I 类基线预留 $2.52，与 D2 一致 |

## 4. C6 完整选择 A3（`p010-C6-complete-search-selection-A3`）：PASS

- **观测完整性**：从保存的 `grouping/OBSERVATIONS.json` 独立重算，共 10,080 条观测（21 个候选 × 30 题 × 16 次 rollout），每个格子都恰好 16 条。
- **熵**：我按"缺失算作一个单独类别"计算香农熵（bits），每个候选的平均熵与 Codex 的结果一致到小数点后 3 位。
- **独立选择结果**：无 cue 候选的缺失率为 26.3%，平均熵 2.340 bits。剔除缺失率比无 cue 高出 10 pp 以上的候选（例如 candidate 10，缺失率 38.3%）之后，平均熵最低的是 **candidate 2，token [1249]**，缺失率 25.6%，平均熵 1.931 bits，与 Codex 的选择一致。
- **其他确认**：731 个已确认的键被复用；新的 parser 尝试 815 次，其中对 ∞ 键 1 次；没有新的模型输出；没有使用 gold 或测试集。
- **局限**：本地无法运行 math-verify，所以 815 次新解析得到的答案键没有独立重算。
- **需要披露**：所有候选（包括无 cue）的缺失率都在 23–38% 之间，原因是续写上限只有 1,024 个 token。
