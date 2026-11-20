# B1/B3 学生完整结果与对比：A3（实际结果）

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求 / scope**：`p011-B-student-complete-results-and-contrasts-actual-A3-r1` / `p011-B-student-complete-results-and-contrasts-actual-A3`
- **target_commit**：`4d4f0e680c760d6c4125f1c28acd05666e973dbb`
- **绑定**：ACTUAL_RESULT_BINDING `3bad44e5302536084f4d202b9fcc85fae4a0219c8dbfd16ccdc429b1848dad19`；MANIFEST `ec81a017120a644d84e3f649ac08585ebd6dc1f6f59803f30004ffb48a554294`；归档 part000 `3c7cd189…`（我自己解开读取）
- **引用**：剩余 oracle 例外 fe2d39d4；模型路径 2423ae52；输入 A1 acea0550

## 结论：PASS-WITH-NOTES

| flag | 值 |
|---|---|
| complete_B1_B3_original_results_and_local_tail_exception_accepted | **true** |
| independent_token_decode_and_correctness_check_scope_disclosed | **true**（见下文） |
| unchanged_training_inputs_dose_state_and_endpoint_evidence_accepted | **true** |
| all_new_contrasts_and_old_label_reuse_accepted | **true** |
| private_binary_and_review_limits_explicitly_disclosed | **true** |

## 独立检查（脚本 `b_student_a3/b_student_a3.py`，输出 `B_STUDENT_A3.json`）

1. **解码（全量 2 × 2,500 条）**：
   - 我用自己写的 BPE 解码器，直接从 `runtime/raw/<eval>/*.json` 的原始 token 重算答案片段：native_eos 取第一个 EOS 之前，length_cap 取全部。
   - 与 DECODED 和 SCORING_ROWS **全部逐字一致，0 处不符**；没有未映射 token。
   - 停止原因：B1 为 native_eos 2,225、length_cap 275（都正好 1,024 个 token）；B3 为 2,237 / 263。
2. **评分一致性（全量；没有重跑 math-verify，因为本环境无法访问 PyPI）**：
   - 我自己提取的最后一个 `\boxed{}` 与保存的 `extracted_answer` **0 处不同**。
   - 字符串相等的全部判对；非 native 停止的全部判错。
   - 只靠符号比较判对的：B1 117 行 / 32 对，B3 111 行 / 31 对，合计 **39 个不同的对，我逐一人工看过**。38 对是合理的等价，例如平面方程乘以常数、`\frac{2187}{5625}`↔`\frac{243}{625}`、`137.5`↔`137\frac12`、`3+2\sqrt2, 3-2\sqrt2`↔`3\pm2\sqrt2`。
   - **1 对是误判**：`0.00006704` 被判为等于 gold `.0000672`（相对差约 0.24%，是冻结评分器的数值容差造成的）。只影响 B1 的 `sample0` 和 `sample3` 中的 `math500/176` 两行。按冻结规则不改分，但**必须披露**：B1 采样正确数如果按严格口径是 1,029 而不是 1,031，均值低 0.1pp。
3. **计数（由 ALL_SCORED_ROWS 重算）**：B1 greedy 246/500（49.2%），采样 1,031/2,000（51.55%）；B3 279/500（55.8%），1,082/2,000（54.10%）✓
4. **对比向量**：
   - B1/B3 的向量与我按行重建的 greedy 和 4 次采样均值**完全一致**。
   - T0.8 的向量均值为 54.6 / 55.8（greedy）、52.15 / 52.7（采样），等于 P010 已审计的 273、279、1,043、1,054 ✓
   - 我用独立的 numpy 代码（不同 seed）重算了点估计和配对 bootstrap，结果与保存的一致：

   | 对比 | greedy 点估计 | 保存的 95% 区间 | 我重算的区间 | 采样点估计 | 保存的区间 | 我重算的区间 |
   |---|---:|---|---|---:|---|---|
   | 温度 × K 交互（Δ_TK） | +5.4 | [0.2, 10.4] | [0.2, 10.6] | +2.0 | [−1.25, 5.2] | [−1.2, 5.3] |
   | B1 − T0.8 K1 | −5.4 | [−9.4, −1.2] | [−9.6, −1.2] | −0.6 | [−3.3, 2.1] | [−3.3, 2.05] |
   | B3 − T0.8 K8 | 0.0 | [−3.6, 3.4] | [−3.6, 3.6] | +1.4 | [−0.5, 3.3] | [−0.55, 3.3] |

5. **训练**：两者都是 1,024 次更新，累计 target 2,097,148（与 A1 一致）；COMPLETE_PROOF 中 full_state_loaded 和 training_state_verified 都为 true，technical_unknown 为 0。

## 局限（必须披露）

- 完整的模型、状态二进制和私有记账没有公开，我**没有独立读取**。状态和轨迹的验证依赖 Codex 本地 oracle（源码 101，已审）。
- 符号等价没有独立重跑，见上文第 2 点；有 1 处已知的冻结评分器误判。
- 区间是**题目层面**的配对 bootstrap，不代表训练 seed 之间的变异，也不能证明机制。B 的 bootstrap seed 沿用 P010（20261019），在报告中注明。
- B2 按削减规则没有训练。
