# P011 C2 完整路径：源码 CR

- **审计方**：Claude，2026-10-21 09:05 UTC 前后（负责人夜间全权审核期间）
- **请求**：`p011-C2-generation-student-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-C2-generation-student-complete-path-CR`（只做源码这一阶段）

## 结论：PASS-WITH-NOTES

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| target_commit | `f0a1d8aafc98c671f433f838a9ef278e670d848a` |
| packet | `reports/p011_20261020/c2_full_path_preflight_v1`，MANIFEST `b343cb629dc678e3eec4522495ab957e714748c6a231ece2d9bceea5850d8cff`，SOURCE_BINDING `fc597862…` |
| source_files | 78 个，在 HEAD `fc5c892a` 上逐个重算 sha，全部一致 |
| original_plan_commit | `e0dee182972f9910b707fac68800dcb5a3aff2d3` |
| original_reuse_files / original_acceptance_files / original_encoded_pair_files / student_endpoint_files | 与 SOURCE_BINDING 中的对应字段逐项相同 |
| window_size | 700 |
| budget_owner_decision_sha256 | `364aaf6c…`（负责人 23:02 PDT 预算决定） |
| input_preparation_authorized | **true** |
| read_only_original_Boolean_and_prompt_reuse_accepted | **true** |
| missing_T15_only_first_four_and_original_E1d_order_accepted | **true** |
| old_selected_encoding_reuse_accepted | **true** |
| 不授权 | 上传、生成、训练、任何付费调用。要等实际输入 A1 和数值 A2-lite（scope `…-CR-A1-A2-lite`，9 个数值 flag）通过 |

## 逐项要点

- **源码闭包**：78 个文件，AST 扫描本仓库内 import，无遗漏。
- **测试**：9 个 C2 测试模块（full_path、no_reencoding、student_inputs、student_numeric、input_consumer、reuse_projection、window_execution、scoring_journal、new_output_evidence）在本机全部 OK。
- **复用投影 `c2_reuse_projection`**：只读 E1d 原顺序和 P1 已保存的 T72 前四次判定，不重跑旧评分或旧解码（`old_symbolic_scores_or_raw_decodes_repeated = 0`）。
- **生成窗口**：`c2_generation_window.plan_window` 按 E1d 顺序取父题，窗口 ≤ 700；只为缺失的 T1.5 attempt 1–4（T=0.8，seed 与 P010 相同）发请求，总数 ≤ 2,800，每批 256 条（1–11 批）。
- **学生输入 `c2_student_inputs.construct`**：
  - 要求 common400 的顺序与 selection 完全一致，C2a/C2b 两组 path_id 分别对应 T15/T72，且没有未验证兜底；
  - `encoding_key = digest(problem_id, path_id, prompt, response)`；已有的原始编码直接复用（`checked_encoding` 核对 token 与掩码），只有新选中的答案才调用一次 `encode_row(…, 2048)`；`old_encoding_reruns = 0`；
  - 失败时写 FAILED.json 并保留部分结果，不自动重试。
- **训练 `c2_student_training`**：与 B 版本逐行相同，唯一区别是把 `rt.encode` 换成 `checked_encoding`。由于 P010 的 `rt.encode` 本身就是 `encode_row(…, 2048)`，而 `checked_encoding` 只做比对、不重新编码，这一替换不改变训练数据 ✓ 其余（1024 次更新、2,097,148 个 target、seed 17、LR 向量、FP32 合并 BF16 保存、子进程 join 后再加载 vLLM）与 P010/B 相同。
- **`c2_path` 与 `b_current_path` 的差异**只有四处：new_generation_batches 为有限的 1–11；生成 score_seconds ≤ 28,000；common_ordered400 相等检查；类别为 C。其余生命周期（账本、4 槽、fence、失败保全）共用 ✓

## 注意

1. **C 类预算很可能装不下两个学生训练**：C 上限 12，已保留 C1 r1 的 3.74 和 r2 的 2.64，共 6.38（保留不释放）。剩 5.62，按 80% 规则约 $4.50。生成加两个学生的预留大概率超出。按计划 §7.3，先砍 C2 的训练。数值 A2-lite 必须按实际费率和 D1 写出明确的可行性判断；不可行时不得挪用其他类别或那 $48。
2. **公共支撑不足 400**：如果窗口 700 内凑不满 400 个公共可用父题，`construct` 会拒绝；届时需要负责人处置，不得自动扩大窗口。
3. **复用部分没有重读**：P009/P010 原文件只核对了 sha 和既往生产使用，新文件逐行审阅。
4. 本地没有 GPU/vLLM，结论来自代码阅读和 mock 测试。
